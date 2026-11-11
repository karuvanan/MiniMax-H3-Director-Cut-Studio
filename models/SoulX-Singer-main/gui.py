"""SoulX-Singer 歌声合成（歌词 + MIDI）桌面 GUI。

Desktop front-end for the *synthesis* pipeline of ``webui.py`` — same steps, but
as a window instead of a web page:

    ① 参考音频  → 人声分离 + 歌词/音符转录 → prompt metadata.json (+ vocal.mid)
    ② 目标旋律  → A. 从人声音频转录   或   B. 直接导入 MIDI (.mid) → target metadata.json
    ③ 合成      → 旋律控制 / 曲谱控制 → generated.wav

和 Gradio WebUI 的差别：歌词可以直接在窗口里逐字编辑（保存时自动重算 phoneme），
MIDI 也用一个「导入」按钮代替了上传框。

模型是懒加载的：打开窗口不会占显存，第一次执行任务时才加载；「卸载模型」按钮和
关闭窗口都会调用 ``resource_release``，把权重释放掉并把显存交还给系统（见 §退出）。

    python gui.py                    # 直接运行
    launch_gui.pyw                   # 双击启动（用 soulxsinger conda 环境，无控制台）
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import sys
import threading
import time
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import tkinter as tk

import resource_release as rr


ROOT = Path(__file__).resolve().parent

_G2P_LOCK = threading.Lock()
_G2P_FN = None

DEVICE_LABELS = {
    "Auto (自动)": "auto",
    "CUDA": "cuda",
    "DirectML": "dml",
    "CPU": "cpu",
}

LYRIC_LANGS = {
    "普通话 Mandarin": "Mandarin",
    "粤语 Cantonese": "Cantonese",
    "英语 English": "English",
}

CONTROL_LABELS = {
    "曲谱控制 Score": "score-controlled",
    "旋律控制 Melody": "melody-controlled",
}

EXAMPLES = {
    "普通话 zh (prompt+target 现成 metadata)": {
        "prompt_audio": "example/audio/zh_prompt.mp3",
        "prompt_meta": "example/audio/zh_prompt.json",
        "target_meta": "example/audio/zh_target.json",
        "lang": "普通话 Mandarin",
        "control": "旋律控制 Melody",
    },
    "英语 en": {
        "prompt_audio": "example/audio/en_prompt.mp3",
        "prompt_meta": "example/audio/en_prompt.json",
        "target_meta": "example/audio/en_target.json",
        "lang": "英语 English",
        "control": "曲谱控制 Score",
    },
    "粤语 yue (target)": {
        "prompt_audio": "example/audio/zh_prompt.mp3",
        "prompt_meta": "example/audio/zh_prompt.json",
        "target_meta": "example/audio/yue_target.json",
        "lang": "粤语 Cantonese",
        "control": "曲谱控制 Score",
    },
    "音乐剧 music (target)": {
        "prompt_audio": "example/audio/zh_prompt.mp3",
        "prompt_meta": "example/audio/zh_prompt.json",
        "target_meta": "example/audio/music.json",
        "lang": "普通话 Mandarin",
        "control": "曲谱控制 Score",
    },
}

AUDIO_TYPES = [
    ("Audio 音频", "*.wav *.mp3 *.flac *.m4a *.ogg"),
    ("All files 全部", "*.*"),
]
MIDI_TYPES = [("MIDI", "*.mid *.midi"), ("All files 全部", "*.*")]
JSON_TYPES = [("metadata JSON", "*.json"), ("All files 全部", "*.*")]


class SoulXSvsGui:
    """Tkinter front-end for the lyrics/MIDI-driven singing synthesis pipeline."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SoulX-Singer 歌声合成 · 歌词 + MIDI (GUI)")
        self.root.geometry("1240x900")
        self.root.minsize(1080, 760)

        # --- inputs -----------------------------------------------------------
        self.prompt_audio = tk.StringVar()
        self.prompt_meta = tk.StringVar()
        self.prompt_midi = tk.StringVar()
        self.prompt_lang = tk.StringVar(value="普通话 Mandarin")
        self.prompt_sep = tk.BooleanVar(value=False)
        self.prompt_max_sec = tk.IntVar(value=30)

        self.target_audio = tk.StringVar()
        self.target_meta = tk.StringVar()
        self.target_midi = tk.StringVar()
        self.target_vocal = tk.StringVar()
        self.target_lang = tk.StringVar(value="普通话 Mandarin")
        self.target_sep = tk.BooleanVar(value=True)
        self.target_max_sec = tk.IntVar(value=60)
        self.midi_side = tk.StringVar(value="target")

        self.control = tk.StringVar(value="曲谱控制 Score")
        self.auto_shift = tk.BooleanVar(value=True)
        self.pitch_shift = tk.IntVar(value=0)
        self.seed = tk.IntVar(value=12306)
        self.n_step = tk.IntVar(value=32)
        self.cfg = tk.DoubleVar(value=3.0)
        self.device_label = tk.StringVar(value="Auto (自动)")
        self.use_fp16 = tk.BooleanVar(value=True)

        # --- status -----------------------------------------------------------
        self.output_path = tk.StringVar()
        self.model_status = tk.StringVar(value="模型 Model: 未加载（首次执行任务时自动加载）")
        self.status_text = tk.StringVar(value="就绪 Idle")
        self.progress_value = tk.DoubleVar(value=0.0)
        self.editor_status = tk.StringVar(value="歌词编辑器：未载入 Load a metadata.json first")
        self.example_choice = tk.StringVar(value=list(EXAMPLES)[0])

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self._spinning = False
        self._closing = False

        # Lazy handles: importing webui.py builds APP_STATE (several GB of models).
        self._webui = None
        self._loaded_device = None
        self._loaded_fp16 = None

        # editor state: {"prompt": {...}, "target": {...}}
        self._editor_target = tk.StringVar(value="target")
        self._editor_data: dict[str, dict | None] = {"prompt": None, "target": None}
        self._selected_cell = None
        self._edit_token = tk.StringVar()
        self._dirty: set[str] = set()

        self._build_ui()
        self._poll_queue()
        # Loading g2p takes a few seconds (nltk data); do it off the UI thread so
        # the first lyric save never freezes the window.
        threading.Thread(target=self._warm_g2p, daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Control-s>", lambda _event: self._editor_save())
        self.root.bind("<Control-q>", lambda _event: self._on_close())

    # ------------------------------------------------------------------ UI ---
    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="SoulX-Singer 歌声合成（歌词 / MIDI）", font=("Segoe UI", 17, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, textvariable=self.model_status, foreground="#334155").grid(
            row=1, column=0, sticky="w", pady=(2, 0)
        )
        ttk.Button(header, text="加载模型 Load", command=self._act_load_model).grid(row=0, column=1, padx=4)
        ttk.Button(header, text="卸载模型 Unload", command=self._act_unload_model).grid(row=0, column=2, padx=4)
        ttk.Label(header, text="退出会自动卸载并释放显存", foreground="#64748b").grid(row=1, column=1, columnspan=2, sticky="e")

        tabs = ttk.Notebook(outer)
        tabs.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        outer.rowconfigure(1, weight=0)

        tabs.add(self._build_prompt_tab(tabs), text=" ① 参考音频（音色 / 歌词） ")
        tabs.add(self._build_target_tab(tabs), text=" ② 目标旋律（音频 / MIDI） ")
        tabs.add(self._build_synthesis_tab(tabs), text=" ③ 合成 Synthesis ")

        run_bar = ttk.Frame(outer)
        run_bar.grid(row=2, column=0, sticky="ew", pady=(6, 4))
        run_bar.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(run_bar, variable=self.progress_value, maximum=100, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew")
        ttk.Label(run_bar, textvariable=self.status_text).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Button(run_bar, text="打开输出 Open", command=self._act_open_output).grid(row=0, column=1, rowspan=2, padx=6)
        ttk.Button(run_bar, text="输出目录 Folder", command=self._act_open_folder).grid(row=0, column=2, rowspan=2, padx=2)

        out_row = ttk.Frame(outer)
        out_row.grid(row=3, column=0, sticky="ew")
        out_row.columnconfigure(0, weight=1)
        ttk.Label(out_row, text="生成结果 generated.wav").grid(row=0, column=0, sticky="w")
        ttk.Entry(out_row, textvariable=self.output_path, state="readonly").grid(row=1, column=0, sticky="ew", pady=(2, 0))

        body = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        body.grid(row=4, column=0, sticky="nsew", pady=(10, 0))

        editor_box = ttk.Labelframe(body, text="歌词 / 音符编辑器  metadata.json")
        log_box = ttk.Labelframe(body, text="日志 Log")
        body.add(editor_box, weight=3)
        body.add(log_box, weight=2)

        self._build_editor(editor_box)
        self._build_log(log_box)

    def _build_prompt_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(notebook, padding=14)
        frame.columnconfigure(1, weight=1)

        self._path_row(frame, 0, "参考音频 Prompt audio", self.prompt_audio, lambda: self._browse(AUDIO_TYPES, "选择参考音频", self.prompt_audio))
        self._path_row(frame, 1, "prompt metadata.json", self.prompt_meta, lambda: self._browse(JSON_TYPES, "选择 prompt metadata.json", self.prompt_meta))
        self._path_row(frame, 2, "prompt vocal.mid（导出）", self.prompt_midi, None)

        opts = ttk.Frame(frame)
        opts.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        for col in range(4):
            opts.columnconfigure(col, weight=1)
        self._combo(opts, 0, 0, "歌词语言 Lyric language", self.prompt_lang, list(LYRIC_LANGS))
        ttk.Checkbutton(opts, text="人声分离 Vocal separation", variable=self.prompt_sep).grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=4
        )
        self._number(opts, 1, 3, "参考时长上限 s（0=整首）", self.prompt_max_sec, 0, 600, 5)
        ttk.Button(opts, text="① 转录参考音频（分离 + 歌词 + 音符）", command=self._act_transcribe_prompt).grid(
            row=1, column=1, columnspan=2, sticky="w", padx=6
        )
        ttk.Label(
            opts,
            text="参考音频只需 10-30 秒干净清唱；WebUI 同样只取前 30 秒（Whisper 窗口）。",
            foreground="#64748b",
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        return frame

    def _build_target_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(notebook, padding=14)
        frame.columnconfigure(1, weight=1)

        from_audio = ttk.Labelframe(frame, text="A. 从人声音频转录（自动歌词 + 音符）")
        from_audio.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        from_audio.columnconfigure(1, weight=1)
        self._path_row(from_audio, 0, "目标音频 Target audio", self.target_audio, lambda: self._browse(AUDIO_TYPES, "选择目标音频", self.target_audio))
        opts_a = ttk.Frame(from_audio)
        opts_a.grid(row=1, column=0, columnspan=3, sticky="ew")
        for col in range(3):
            opts_a.columnconfigure(col, weight=1)
        self._combo(opts_a, 0, 0, "歌词语言 Lyric language", self.target_lang, list(LYRIC_LANGS))
        ttk.Checkbutton(opts_a, text="人声分离 Vocal separation", variable=self.target_sep).grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=4
        )
        self._number(opts_a, 1, 2, "目标时长上限 s（0=整首）", self.target_max_sec, 0, 600, 5)
        ttk.Button(opts_a, text="②A 转录目标音频", command=self._act_transcribe_target).grid(
            row=1, column=1, sticky="w", padx=6
        )

        from_midi = ttk.Labelframe(frame, text="B. 从 MIDI 导入旋律（自己写谱 → 直接唱）")
        from_midi.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        from_midi.columnconfigure(1, weight=1)
        self._path_row(from_midi, 0, "MIDI 文件 (.mid/.midi)", self.target_midi, lambda: self._browse(MIDI_TYPES, "选择 MIDI 文件", self.target_midi))
        self._path_row(
            from_midi,
            1,
            "对齐用 vocal.wav（可选，给了才会写 f0）",
            self.target_vocal,
            lambda: self._browse(AUDIO_TYPES, "选择对齐用人声", self.target_vocal),
        )
        opts_b = ttk.Frame(from_midi)
        opts_b.grid(row=2, column=0, columnspan=3, sticky="ew")
        for col in range(3):
            opts_b.columnconfigure(col, weight=1)
        ttk.Label(opts_b, text="写入到哪一侧:").grid(row=0, column=0, sticky="w", padx=(0, 4))
        for idx, (label, value) in enumerate((("目标 Target", "target"), ("参考 Prompt", "prompt"))):
            ttk.Radiobutton(opts_b, text=label, value=value, variable=self.midi_side).grid(row=0, column=idx + 1, sticky="w")
        ttk.Button(opts_b, text="②B MIDI → 歌词/音符 metadata", command=self._act_midi_to_meta).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )
        ttk.Label(
            opts_b,
            text="MIDI 里每个音符对应一个字；歌词在下面的编辑器里逐字填/改（保存时自动转 phoneme）。",
            foreground="#64748b",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

        bottom = ttk.Frame(frame)
        bottom.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        bottom.columnconfigure(0, weight=1)
        self._path_row(bottom, 0, "target metadata.json", self.target_meta, lambda: self._browse(JSON_TYPES, "选择 target metadata.json", self.target_meta))
        ttk.Button(bottom, text="导出 target vocal.mid", command=self._act_export_midi).grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        return frame

    def _build_synthesis_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(notebook, padding=14)
        for col in range(4):
            frame.columnconfigure(col, weight=1)

        self._combo(frame, 0, 0, "控制方式 Control", self.control, list(CONTROL_LABELS))
        self._combo(frame, 0, 1, "设备 Device", self.device_label, list(DEVICE_LABELS))
        self._combo(frame, 0, 2, "示例 Examples", self.example_choice, list(EXAMPLES))
        ttk.Checkbutton(frame, text="FP16（仅 CUDA）", variable=self.use_fp16).grid(
            row=1, column=1, sticky="w", padx=6, pady=(0, 6)
        )
        self._number(frame, 2, 0, "移调 Pitch shift (semitones)", self.pitch_shift, -36, 36, 1)
        self._number(frame, 2, 1, "随机种子 Seed", self.seed, 0, 999999, 1)
        self._number(frame, 2, 2, "扩散步数 n_steps", self.n_step, 4, 128, 1)
        self._number(frame, 3, 0, "CFG 强度", self.cfg, 0.0, 10.0, 0.1)
        ttk.Checkbutton(frame, text="自动移调 Auto pitch shift", variable=self.auto_shift).grid(
            row=3, column=1, sticky="w", padx=6, pady=6
        )
        ttk.Label(
            frame,
            text="n_steps / CFG 默认取自 soulxsinger/config/soulxsinger.yaml，改这里只对下一次合成生效。",
            foreground="#64748b",
        ).grid(row=3, column=2, columnspan=2, sticky="w", padx=6, pady=6)

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(14, 0))
        ttk.Button(buttons, text="③ 开始合成 Synthesize", command=self._act_synthesize).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(buttons, text="载入示例 Load example", command=self._act_load_example).grid(row=0, column=1)
        ttk.Label(
            buttons,
            text="（示例自带 metadata，直接点「开始合成」就能出声，不需要先转录）",
            foreground="#64748b",
        ).grid(row=0, column=2, padx=10)
        return frame

    def _build_editor(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        top = ttk.Frame(parent)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        top.columnconfigure(4, weight=1)
        ttk.Label(top, text="编辑:").grid(row=0, column=0, sticky="w")
        for idx, (label, value) in enumerate((("参考 Prompt", "prompt"), ("目标 Target", "target"))):
            ttk.Radiobutton(
                top, text=label, value=value, variable=self._editor_target, command=self._editor_refresh
            ).grid(row=0, column=idx + 1, sticky="w", padx=6)
        ttk.Button(top, text="载入/刷新", command=self._editor_refresh).grid(row=0, column=3, padx=6)
        ttk.Button(top, text="保存 metadata (Ctrl+S)", command=self._editor_save).grid(row=0, column=5, padx=4)
        ttk.Button(top, text="另存为…", command=self._editor_save_as).grid(row=0, column=6, padx=4)

        grid = ttk.Frame(parent)
        grid.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        grid.columnconfigure(0, weight=1)
        grid.rowconfigure(0, weight=1)
        columns = ("idx", "start", "dur", "pitch", "text")
        self.tree = ttk.Treeview(grid, columns=columns, show="headings", selectmode="browse")
        for key, label, width, anchor in (
            ("idx", "#", 46, tk.CENTER),
            ("start", "开始 (ms)", 90, tk.E),
            ("dur", "时长 (s)", 80, tk.E),
            ("pitch", "音高 MIDI", 80, tk.E),
            ("text", "歌词 Lyric", 320, tk.W),
        ):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor=anchor, stretch=(key == "text"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(grid, command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._editor_on_select)

        edit_row = ttk.Frame(parent)
        edit_row.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 0))
        edit_row.columnconfigure(0, weight=1)
        ttk.Label(edit_row, text="选中行的歌词:").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(edit_row, textvariable=self._edit_token)
        entry.grid(row=0, column=1, sticky="ew", padx=6)
        entry.bind("<Return>", lambda _event: self._editor_apply())
        entry.bind("<KP_Enter>", lambda _event: self._editor_apply())
        ttk.Button(edit_row, text="应用 Apply", command=self._editor_apply).grid(row=0, column=2, padx=2)
        ttk.Label(edit_row, textvariable=self.editor_status, foreground="#475569").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )
        ttk.Label(
            parent,
            text="只改歌词文字；字数/音符数保持不变（要改旋律请用 MIDI 或改 metadata 的 note_pitch）。",
            foreground="#64748b",
        ).grid(row=3, column=0, sticky="w", padx=8, pady=(2, 8))

    def _build_log(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        self.log_text = tk.Text(parent, height=18, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        scroll = ttk.Scrollbar(parent, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns", pady=8, padx=(0, 8))
        self.log_text.configure(yscrollcommand=scroll.set)

    def _path_row(self, parent, row, label, var: tk.StringVar, browse_command) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4)
        if browse_command:
            ttk.Button(parent, text="浏览…", command=browse_command).grid(row=row, column=2, padx=(6, 0), pady=4)

    def _combo(self, parent, row, column, label, var: tk.StringVar, values) -> None:
        box = ttk.LabelFrame(parent, text=label)
        box.grid(row=row, column=column, sticky="ew", padx=6, pady=4)
        box.columnconfigure(0, weight=1)
        ttk.Combobox(box, textvariable=var, values=list(values), state="readonly").grid(
            row=0, column=0, sticky="ew", padx=6, pady=4
        )

    def _number(self, parent, row, column, label, var, start, end, step) -> None:
        box = ttk.LabelFrame(parent, text=label)
        box.grid(row=row, column=column, sticky="ew", padx=6, pady=4)
        box.columnconfigure(0, weight=1)
        ttk.Spinbox(box, textvariable=var, from_=start, to=end, increment=step).grid(
            row=0, column=0, sticky="ew", padx=6, pady=4
        )

    # ------------------------------------------------------------- browse ---
    def _browse(self, filetypes, title: str, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if path:
            var.set(os.path.normpath(path))

    # ------------------------------------------------------- job machinery ---
    def _post(self, kind: str, payload: str = "") -> None:
        self.log_queue.put(f"{kind}::{payload}")

    def _is_busy(self) -> bool:
        return bool(self.worker and self.worker.is_alive())

    def _submit(self, busy_text: str, work) -> bool:
        if self._closing:
            return False
        if self._is_busy():
            messagebox.showinfo("正在执行", "上一个任务还没结束，请等它完成。")
            return False
        self.status_text.set(busy_text)
        self.progress_value.set(0.0)
        self._start_spinner()
        self.worker = threading.Thread(target=self._worker_main, args=(work,), daemon=True)
        self.worker.start()
        return True

    def _worker_main(self, work) -> None:
        def log(message: str) -> None:
            self._post("LOG", str(message))

        started = time.time()
        try:
            work(log)
            self._post("LOG", f"耗时 elapsed {time.time() - started:.1f}s")
            self._post("DONE", "ok")
        except Exception as exc:  # noqa: BLE001 - surfaced in the GUI log
            self._post("LOG", traceback.format_exc())
            self._post("ERROR", f"{type(exc).__name__}: {exc}")
            self._post("DONE", "error")

    def _start_spinner(self) -> None:
        self.progress.configure(mode="indeterminate")
        self._spinning = True
        self._spin()

    def _spin(self) -> None:
        if not self._spinning:
            return
        try:
            self.progress.step(6)
        except tk.TclError:
            return
        self.root.after(180, self._spin)

    def _stop_spinner(self) -> None:
        self._spinning = False
        try:
            self.progress.configure(mode="determinate")
        except tk.TclError:
            pass

    def _poll_queue(self) -> None:
        try:
            while True:
                message = self.log_queue.get_nowait()
                kind, _, payload = message.partition("::")
                if kind == "LOG":
                    self._log(payload)
                elif kind == "DONE":
                    self._stop_spinner()
                    if payload == "ok":
                        self.progress_value.set(100)
                        self.status_text.set("完成 Done")
                    else:
                        self.status_text.set("失败 Failed")
                elif kind == "ERROR":
                    self._log("ERROR: " + payload)
                    self.editor_status.set("保存/执行失败：" + payload)
                    if not self._closing:
                        messagebox.showerror("执行失败 Failed", payload)
                elif kind == "SAVED":
                    key, _, path = payload.partition("::")
                    getattr(self, f"{key}_meta").set(path)
                    self._dirty.discard(key)
                    data = self._editor_data.get(key)
                    if data:
                        data["path"] = path
                        data["dirty"] = False
                    self.editor_status.set(f"{key}: 已保存 {os.path.basename(path)}（phoneme 已按新歌词重算）")
                elif kind == "STATE":
                    self.model_status.set(payload)
                elif kind == "PARAMS":
                    steps, _, cfg = payload.partition("::")
                    try:
                        self.n_step.set(int(steps))
                        self.cfg.set(float(cfg))
                    except ValueError:
                        pass
                elif kind == "PROGRESS":
                    fraction, _, message = payload.partition("::")
                    self._stop_spinner()
                    try:
                        self.progress_value.set(max(0.0, min(100.0, float(fraction) * 100.0)))
                    except ValueError:
                        pass
                    if message:
                        self.status_text.set(message)
                elif kind == "OUT":
                    self.output_path.set(payload)
                    self._log(f"输出 output: {payload}")
                elif kind == "META":
                    key, _, path = payload.partition("::")
                    getattr(self, f"{key}_meta").set(path)
                    self._editor_target.set(key)
                    self._editor_load(key, path)
                elif kind == "MIDI":
                    key, _, path = payload.partition("::")
                    getattr(self, f"{key}_midi").set(path)
                elif kind == "VOCAL":
                    self.target_vocal.set(payload)
        except queue.Empty:
            pass
        if not self._closing:
            self.root.after(150, self._poll_queue)

    def _log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message.rstrip() + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _warm_g2p(self) -> None:
        try:
            _load_g2p()
            self._post("LOG", "拼音/音标模块已就绪 g2p ready（保存歌词会自动重算 phoneme）")
        except Exception as exc:  # noqa: BLE001
            self._post("LOG", f"拼音/音标模块加载失败，保存歌词时会再试：{exc}")

    # -------------------------------------------------------------- models ---
    @staticmethod
    def _int(var, default: int) -> int:
        try:
            return int(var.get())
        except (tk.TclError, ValueError):
            return default

    @staticmethod
    def _float(var, default: float) -> float:
        try:
            return float(var.get())
        except (tk.TclError, ValueError):
            return default

    def _settings(self) -> dict:
        """Snapshot every control the jobs need — call it on the main thread.

        Tkinter refuses Tcl calls from a worker thread ("main thread is not in
        main loop"), so a job never reads a StringVar itself: the values are
        captured here before the thread starts.
        """
        return {
            "device": DEVICE_LABELS.get(self.device_label.get(), "auto"),
            "fp16": bool(self.use_fp16.get()),
            "n_step": self._int(self.n_step, 32),
            "cfg": self._float(self.cfg, 3.0),
            "seed": self._int(self.seed, 12306),
            "pitch_shift": self._int(self.pitch_shift, 0),
            "auto_shift": bool(self.auto_shift.get()),
            "control": CONTROL_LABELS.get(self.control.get(), "score-controlled"),
            "prompt_lang": LYRIC_LANGS.get(self.prompt_lang.get(), "Mandarin"),
            "target_lang": LYRIC_LANGS.get(self.target_lang.get(), "Mandarin"),
            "prompt_sep": bool(self.prompt_sep.get()),
            "target_sep": bool(self.target_sep.get()),
            # 0 = 整首: webui._trim_and_save_audio slices audio[:max_sec*sr], so 0
            # would cut everything; an effectively unlimited cap means the same thing.
            "prompt_sec": self._int(self.prompt_max_sec, 30) or 10**9,
            "target_sec": self._int(self.target_max_sec, 60) or 10**9,
            "prompt_audio": self.prompt_audio.get().strip(),
            "target_audio": self.target_audio.get().strip(),
            "target_vocal": self.target_vocal.get().strip(),
            "prompt_meta": self.prompt_meta.get().strip(),
            "target_meta": self.target_meta.get().strip(),
        }

    @staticmethod
    def _sec_label(seconds: int) -> str:
        return "整首" if seconds >= 10**9 else f"{seconds}s"

    def _models_current(self, device: str, want_fp16: bool) -> bool:
        return (
            self._webui is not None
            and getattr(self._webui, "APP_STATE", None) is not None
            and self._loaded_fp16 == want_fp16
            and self._loaded_device == device
        )

    def _ensure_models(self, log, settings: dict) -> object:
        """Import ``webui`` (which builds APP_STATE) on first need, in the worker.

        ``settings`` is a snapshot from :meth:`_settings`; the ``--fp16`` flag and
        ``SOULX_DEVICE`` have to be right *before* ``AppState`` is constructed,
        which is why the import is deferred into the worker thread.
        """
        device, want_fp16 = settings["device"], settings["fp16"]
        os.environ["SOULX_DEVICE"] = device
        if want_fp16 and not _cuda_available():
            want_fp16 = False
            log("FP16 需要 CUDA，已自动关闭 FP16")

        if self._webui is None:
            log(
                "正在加载模型… loading models. 第一次会很久（本机实测数分钟）："
                "导入 NeMo / funasr / whisper 等转录栈本身就要几分钟，日志安静不代表卡死。"
            )
            argv_backup = list(sys.argv)
            try:
                # webui.py decides fp16 from the command line at import time.
                if want_fp16 and "--fp16" not in sys.argv:
                    sys.argv.append("--fp16")
                import webui

                self._webui = webui
            finally:
                sys.argv = argv_backup
        elif not self._models_current(device, want_fp16):
            log(f"设备/精度已变化，重新加载 device={device} fp16={want_fp16}")
            import webui

            webui.APP_STATE = webui.AppState(use_fp16=want_fp16)
            self._webui = webui

        state = getattr(self._webui, "APP_STATE", None)
        if state is None:
            raise RuntimeError("模型加载失败：APP_STATE is None")
        self._loaded_device = device
        self._loaded_fp16 = want_fp16
        self._post("STATE", f"模型 Model: 已加载 device={state.device} fp16={state.use_fp16}")
        try:
            self._post("PARAMS", f"{int(state.svs_config.infer.n_steps)}::{float(state.svs_config.infer.cfg)}")
        except Exception:
            pass
        return self._webui

    def _act_load_model(self) -> None:
        settings = self._settings()
        self._submit("加载模型中…", lambda log: self._ensure_models(log, settings))

    def _act_unload_model(self) -> None:
        def work(log):
            if self._webui is None:
                log("模型尚未加载，无需卸载。")
                return
            log("卸载模型中… unloading")
            rr.unload_all(modules=[self._webui], device=self._loaded_device, log=log)
            self._loaded_device = None
            self._loaded_fp16 = None
            self._post("STATE", "模型 Model: 已卸载 Unloaded")

        self._submit("卸载模型中…", work)

    # -------------------------------------------------------------- actions ---
    def _act_transcribe_prompt(self) -> None:
        settings = self._settings()
        audio = settings["prompt_audio"]
        if not audio or not Path(audio).is_file():
            messagebox.showwarning("缺少参考音频", "请先选择参考音频。")
            return
        lang, sep, max_sec = settings["prompt_lang"], settings["prompt_sep"], settings["prompt_sec"]

        def work(log):
            webui = self._ensure_models(log, settings)
            log(f"转录参考音频（language={lang}, vocal_sep={sep}, 上限 {self._sec_label(max_sec)}）…")
            meta, midi = webui._transcribe_prompt(audio, None, lang, sep, max_sec)
            if not meta:
                raise RuntimeError("转录失败：没有生成 prompt metadata（详情见日志/终端）")
            self._post("META", f"prompt::{meta}")
            if midi:
                self._post("MIDI", f"prompt::{midi}")
            log(f"prompt metadata: {meta}")
            prompt_wav = Path(meta).resolve().parents[2] / "audio" / "prompt.wav"
            if prompt_wav.is_file():
                log(f"合成将直接使用这个 prompt.wav: {prompt_wav}")

        self._submit("转录参考音频中…（人声分离 + ASR + 音符转录）", work)

    def _act_transcribe_target(self) -> None:
        settings = self._settings()
        audio = settings["target_audio"]
        if not audio or not Path(audio).is_file():
            messagebox.showwarning("缺少目标音频", "请先选择目标音频。")
            return
        lang, sep, max_sec = settings["target_lang"], settings["target_sep"], settings["target_sec"]

        def work(log):
            webui = self._ensure_models(log, settings)
            log(f"转录目标音频（language={lang}, vocal_sep={sep}, 上限 {self._sec_label(max_sec)}）…")
            meta, midi, vocal = webui._transcribe_target(audio, None, lang, sep, max_sec)
            if not meta:
                raise RuntimeError("转录失败：没有生成 target metadata（详情见日志/终端）")
            self._post("META", f"target::{meta}")
            if midi:
                self._post("MIDI", f"target::{midi}")
            if vocal:
                self._post("VOCAL", vocal)
            log(f"target metadata: {meta}")

        self._submit("转录目标音频中…（人声分离 + ASR + 音符转录）", work)

    def _act_midi_to_meta(self) -> None:
        settings = self._settings()
        midi = self.target_midi.get().strip()
        if not midi or not Path(midi).is_file():
            messagebox.showwarning("缺少 MIDI", "请先选择 MIDI 文件（.mid/.midi）。")
            return
        side = self.midi_side.get()
        meta = getattr(self, f"{side}_meta").get().strip() or None
        lang = settings["target_lang"]
        vocal = settings["target_vocal"] or None
        if vocal and not Path(vocal).is_file():
            vocal = None

        def work(log):
            webui = self._ensure_models(log, settings)
            before = Path(meta).stat().st_mtime if meta and Path(meta).is_file() else 0.0
            log(f"MIDI → metadata（side={side}, language={lang}, vocal={vocal or '无'}）…")
            new_meta = webui._edit_metadata(meta, midi, vocal, lang)
            if not new_meta or not Path(str(new_meta)).is_file():
                raise RuntimeError("MIDI 转换失败：没有生成 metadata")
            if meta and os.path.normpath(str(new_meta)) == os.path.normpath(meta):
                if Path(meta).stat().st_mtime == before:
                    log("警告：metadata 没有被改写，MIDI 可能没被接受（旋律为空？见上方异常输出）")
            self._post("META", f"{side}::{os.path.normpath(str(new_meta))}")
            log(f"metadata: {new_meta}")

        self._submit("解析 MIDI 中…", work)

    def _act_export_midi(self) -> None:
        side = self._editor_target.get()
        meta = getattr(self, f"{side}_meta").get().strip()
        if not meta or not Path(meta).is_file():
            messagebox.showwarning("缺少 metadata", "请先转录或导入 MIDI，得到 metadata.json。")
            return
        default_name = f"{Path(meta).stem}.mid"
        out = filedialog.asksaveasfilename(
            title="导出 vocal.mid", defaultextension=".mid", filetypes=MIDI_TYPES, initialfile=default_name
        )
        if not out:
            return

        settings = self._settings()

        def work(log):
            webui = self._ensure_models(log, settings)
            webui.APP_STATE.midi_parser.meta2midi(meta, out)
            log(f"已导出 MIDI: {out}")

        self._submit("导出 MIDI 中…", work)

    def _act_synthesize(self) -> None:
        settings = self._settings()
        prompt_meta, target_meta = settings["prompt_meta"], settings["target_meta"]
        if not prompt_meta or not Path(prompt_meta).is_file():
            messagebox.showwarning("缺少 prompt metadata", "请先转录参考音频（或载入示例）。")
            return
        if not target_meta or not Path(target_meta).is_file():
            messagebox.showwarning("缺少 target metadata", "请先转录目标音频 / 导入 MIDI（或载入示例）。")
            return
        if self._dirty:
            messagebox.showwarning("歌词还没保存", "编辑器里有未保存的修改，先按「保存 metadata」。")
            return
        n_step, cfg = settings["n_step"], settings["cfg"]
        seed, pitch_shift, auto_shift = settings["seed"], settings["pitch_shift"], settings["auto_shift"]

        def work(log):
            import random

            import numpy as np
            import torch

            webui = self._ensure_models(log, settings)
            state = webui.APP_STATE
            try:
                state.svs_config.infer.n_steps = n_step
                state.svs_config.infer.cfg = cfg
            except Exception as exc:  # noqa: BLE001
                log(f"n_steps/cfg 设置失败（用配置默认值）：{exc}")
            prompt_wav = self._prompt_wav_for(webui, prompt_meta, settings["prompt_audio"], log)
            # run_svs_from_paths wants the internal short names ("score"/"melody").
            control = webui._control_to_internal(settings["control"])
            log(
                f"合成中 control={control} auto_shift={auto_shift} pitch_shift={pitch_shift} "
                f"seed={seed} n_steps={n_step} cfg={cfg}"
            )

            # Same global seeding the WebUI's Run handler does (cli path has no RNG object).
            torch.manual_seed(seed)
            np.random.seed(seed)
            random.seed(seed)

            logged_bucket = [-1]

            def progress(done: int, total: int) -> None:
                total = max(1, int(total))
                fraction = int(done) / total
                self._post("PROGRESS", f"{fraction:.4f}::合成进度 {done}/{total} 段")
                bucket = int(fraction * 10)
                if bucket != logged_bucket[0] and bucket < 10:
                    logged_bucket[0] = bucket
                    log(f"合成进度 {done}/{total} 段（约 {bucket * 10}%）")

            ok, msg, merged = state.run_svs_from_paths(
                prompt_wav_path=prompt_wav,
                prompt_metadata_path=prompt_meta,
                target_metadata_path=target_meta,
                control=control,
                auto_shift=auto_shift,
                pitch_shift=pitch_shift,
                progress_cb=progress,
            )
            if not ok or merged is None:
                raise RuntimeError(str(msg or "合成失败：没有生成 generated.wav"))
            self._post("OUT", os.path.normpath(str(merged)))

        self._submit("合成中…（扩散 + 声码器）", work)

    def _prompt_wav_for(self, webui, prompt_meta: str, prompt_audio: str, log) -> str:
        """Prompt wav to feed the synthesis — always a real 44.1 kHz mono wav.

        ``run_svs_from_paths`` *copies* the file it is given (no resampling), so
        handing it an mp3 named ``prompt.wav`` is fragile. The transcription step
        already writes ``<session>/audio/prompt.wav`` (its metadata lives at
        ``<session>/transcriptions/prompt/metadata.json``); when that is missing —
        e.g. when an example ``metadata.json`` was loaded — convert the user's
        audio into a fresh session dir, exactly like the WebUI does.
        """
        session = Path(prompt_meta).resolve().parents[2]
        trimmed = session / "audio" / "prompt.wav"
        if trimmed.is_file():
            return str(trimmed)

        audio = (prompt_audio or "").strip()
        if not audio or not Path(audio).is_file():
            raise FileNotFoundError(f"找不到可用的参考音频（试过了 {trimmed} 和参考音频输入框）")
        session = webui._session_dir()
        audio_dir = session / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        wav_path = audio_dir / "prompt.wav"
        webui._trim_and_save_audio(audio, wav_path, webui.PROMPT_MAX_SEC_DEFAULT)
        log(f"参考音频已转成 {webui.PROMPT_MAX_SEC_DEFAULT}s 内 44.1kHz 单声道 wav → {wav_path}")
        return str(wav_path)

    def _act_load_example(self) -> None:
        choice = EXAMPLES.get(self.example_choice.get()) or {}
        missing = []
        for key, rel in (("prompt_audio", "prompt_audio"), ("prompt_meta", "prompt_meta"), ("target_meta", "target_meta")):
            rel_path = choice.get(key)
            if not rel_path:
                continue
            path = ROOT / rel_path
            if path.is_file():
                getattr(self, key).set(str(path))
            else:
                getattr(self, key).set("")
                missing.append(rel_path)
        if choice.get("lang"):
            self.prompt_lang.set(choice["lang"])
            self.target_lang.set(choice["lang"])
        if choice.get("control"):
            self.control.set(choice["control"])
        self._editor_target.set("target")
        self._editor_refresh()
        if missing:
            self._log(f"示例缺少文件 missing: {', '.join(missing)}")
        else:
            self._log(f"已载入示例: {self.example_choice.get()} → 可直接点「开始合成」")

    def _act_open_output(self) -> None:
        path = self.output_path.get()
        if not path or not Path(path).is_file():
            messagebox.showinfo("输出", "还没有生成文件。")
            return
        os.startfile(path)  # noqa: S606 - Windows only, plays the wav

    def _act_open_folder(self) -> None:
        path = self.output_path.get()
        folder = Path(path).parent if path and Path(path).is_file() else ROOT / "outputs"
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))  # noqa: S606

    # -------------------------------------------------------------- editor ---
    def _editor_refresh(self) -> None:
        key = self._editor_target.get()
        path = getattr(self, f"{key}_meta").get().strip()
        if not path or not Path(path).is_file():
            self._editor_data[key] = None
            self.tree.delete(*self.tree.get_children())
            self.editor_status.set(f"{key}: 没有 metadata.json（先转录 / 导入 MIDI / 载入示例）")
            return
        self._editor_load(key, path)

    def _editor_load(self, key: str, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                segments = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            self.editor_status.set(f"{key}: 读取失败 {exc}")
            return
        if not isinstance(segments, list):
            self.editor_status.set(f"{key}: metadata 格式不对（期望 list）")
            return

        data = {"path": os.path.normpath(path), "segments": segments, "tokens": [], "dirty": False}
        self.tree.delete(*self.tree.get_children())
        count = 0
        for seg_index, segment in enumerate(segments):
            tokens = str(segment.get("text", "")).split()
            durations = str(segment.get("duration", "")).split()
            pitches = str(segment.get("note_pitch", "")).split()
            data["tokens"].append(list(tokens))
            for token_index, token in enumerate(tokens):
                self.tree.insert(
                    "",
                    tk.END,
                    iid=f"{seg_index}:{token_index}",
                    values=(
                        count + 1,
                        _field(segment, "time", 0),
                        durations[token_index] if token_index < len(durations) else "",
                        pitches[token_index] if token_index < len(pitches) else "",
                        token,
                    ),
                )
                count += 1
        self._editor_data[key] = data
        self._dirty.discard(key)
        first_time = data["segments"][0].get("time") if data["segments"] else None
        self.editor_status.set(
            f"{key}: {os.path.basename(path)}  共 {count} 个音符/字，{len(segments)} 句  起始 {first_time}"
        )

    def _editor_on_select(self, _event) -> None:
        selection = self.tree.selection()
        self._selected_cell = selection[0] if selection else None
        if not self._selected_cell:
            return
        values = self.tree.item(self._selected_cell, "values")
        self._edit_token.set(values[-1] if values else "")

    def _editor_apply(self) -> None:
        key = self._editor_target.get()
        data = self._editor_data.get(key)
        cell = self._selected_cell
        if not data or not cell:
            self.editor_status.set("先在表格里选中一行")
            return
        seg_index, token_index = (int(part) for part in cell.split(":"))
        token = self._edit_token.get().strip()
        if not token:
            self.editor_status.set("歌词不能为空（要表示休止请用 <SP>）")
            return
        data["tokens"][seg_index][token_index] = token
        values = list(self.tree.item(cell, "values"))
        values[-1] = token
        self.tree.item(cell, values=values)
        data["dirty"] = True
        self._dirty.add(key)
        hint = ""
        if len(token) > 1 and not token.isascii() and token != "<SP>":
            # g2p only maps single CJK characters; a multi-char token turns into
            # <SP> (a rest) in the phoneme list, so the note would go silent.
            hint = "　⚠ 这是多个汉字：保存后 phoneme 会变成 <SP>（该音符不出声），请一行只填一个字。"
        self.editor_status.set(f"{key}: 已修改第 {seg_index}:{token_index} 个音符 → 记得按「保存 metadata」{hint}")

    def _editor_save(self) -> None:
        key = self._editor_target.get()
        if self._editor_data.get(key) is None:
            self._editor_refresh()
        if self._editor_data.get(key) is None:
            messagebox.showinfo("歌词编辑器", "还没有载入 metadata。")
            return
        language = LYRIC_LANGS.get(getattr(self, f"{key}_lang").get(), "Mandarin")
        self._submit(
            "保存 metadata 中…（首次会加载拼音/音标模块）",
            lambda log: self._write_meta(key, None, language, log),
        )

    def _editor_save_as(self) -> None:
        key = self._editor_target.get()
        data = self._editor_data.get(key) or {}
        if not data:
            messagebox.showinfo("歌词编辑器", "还没有载入 metadata。")
            return
        out = filedialog.asksaveasfilename(
            title="另存 metadata.json",
            defaultextension=".json",
            filetypes=JSON_TYPES,
            initialfile=os.path.basename(data.get("path", "metadata.json")),
        )
        if not out:
            return
        language = LYRIC_LANGS.get(getattr(self, f"{key}_lang").get(), "Mandarin")
        self._submit("保存 metadata 中…", lambda log: self._write_meta(key, os.path.normpath(out), language, log))

    def _write_meta(self, key: str, destination: str | None, language: str, log) -> None:
        """Rewrite text + phoneme from the edited tokens (runs in the worker).

        One tree row is one note, so the token count never changes here and
        ``duration`` / ``note_pitch`` / ``note_type`` stay aligned; they are still
        re-checked so a hand-edited file is not saved into a broken state.
        ``language`` comes from the UI (the stored value can be "zh"/"en" from ASR,
        which g2p would misread — only "Cantonese" vs the rest matters to it).
        """
        data = self._editor_data.get(key)
        if not data:
            raise RuntimeError("没有载入 metadata")
        g2p = _load_g2p()

        segments, tokens_list = data["segments"], data["tokens"]
        silent = []
        for index, segment in enumerate(segments):
            tokens = tokens_list[index]
            for field in ("duration", "note_pitch", "note_type"):
                items = len(str(segment.get(field, "")).split())
                if items and items != len(tokens):
                    raise RuntimeError(
                        f"第 {index} 句：歌词 {len(tokens)} 个 vs {field} {items} 个，数量必须一致"
                    )
            phonemes = g2p(tokens, language)
            for position, (token, phoneme) in enumerate(zip(tokens, phonemes)):
                if token != "<SP>" and phoneme == "<SP>":
                    silent.append((index, position, token))
            segment["text"] = " ".join(tokens)
            segment["language"] = language
            segment["phoneme"] = " ".join(phonemes)

        target_path = os.path.normpath(destination or data["path"])
        if target_path == os.path.normpath(data["path"]) and os.path.isfile(target_path):
            backup = target_path + ".bak"
            if not os.path.isfile(backup):
                # No undo in this editor, so keep the first original next to it.
                shutil.copy2(target_path, backup)
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as handle:
            json.dump(segments, handle, ensure_ascii=False, indent=2)

        log(f"[{key}] metadata 已保存 -> {target_path}")
        log(f"[{key}] 歌词: " + " / ".join(" ".join(row) for row in tokens_list))
        if silent:
            names = "，".join(f"句{index} 第{position + 1}个「{token}」" for index, position, token in silent[:6])
            log(
                f"[{key}] 警告：{len(silent)} 个音符的 phoneme 被转成了 <SP>（合成时会当休止）。"
                f"每个音符只放一个汉字或一个英文单词：{names}"
            )
        self._post("SAVED", f"{key}::{target_path}")

    # -------------------------------------------------------------- shutdown ---
    def _on_close(self) -> None:
        """Close the window, unload the models, hand RAM/VRAM back, then exit."""
        if self._is_busy():
            if not messagebox.askyesno(
                "正在生成",
                "还有任务在跑。\n确定要退出吗？（会停止任务、卸载模型并释放显存）",
            ):
                return
        self._closing = True
        self._spinning = False
        try:
            self.root.destroy()
        except tk.TclError:
            pass

        # The Tk window is gone; release the weights before exiting so the GPU is
        # free even for the second in which the interpreter is still winding down.
        modules = [self._webui] if self._webui is not None else []
        try:
            stats = rr.unload_all(modules=modules, device=self._loaded_device, log=_stdout_log)
            dropped = stats.get("dropped", 0)
            after = stats.get("cuda_after")
            if after:
                _stdout_log(
                    f"退出清理 exit cleanup: 释放 {dropped} 个模型引用，"
                    f"显存空闲 VRAM free {_gib(after['free'])} / {_gib(after['total'])}"
                )
            else:
                _stdout_log(f"退出清理 exit cleanup: 释放 {dropped} 个模型引用（无 CUDA）")
        except Exception:
            traceback.print_exc()
        finally:
            # os._exit guarantees the CUDA context dies here: worker threads from
            # torchaudio / ASR / Nemo would otherwise keep the process alive.
            rr.force_exit(0)


def _stdout_log(message: str) -> None:
    print(f"[cleanup] {message}", flush=True)


def _gib(value: float) -> str:
    return f"{float(value) / 1024 ** 3:.2f} GiB"


def _field(segment: dict, key: str, index: int) -> str:
    value = segment.get(key)
    if isinstance(value, list) and len(value) > index:
        return str(value[index])
    return ""


def _cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _load_g2p():
    """Return ``g2p_transform`` (pinyin / jyutping / IPA), loading g2p.py alone.

    ``import preprocess.tools.g2p`` runs ``preprocess/tools/__init__.py``, which
    constructs the separation / ASR / note-transcription stacks — gigabytes of
    weights and minutes of waiting, for a helper that only needs ToJyutping,
    g2pM and g2p_en. Loading the module file directly skips that package
    initialisation (``webui`` still imports the package when models are loaded).
    """
    global _G2P_FN
    with _G2P_LOCK:
        if _G2P_FN is not None:
            return _G2P_FN
        try:
            import importlib.util

            path = ROOT / "preprocess" / "tools" / "g2p.py"
            spec = importlib.util.spec_from_file_location("soulxsinger_g2p_standalone", str(path))
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load {path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _G2P_FN = module.g2p_transform
        except Exception:
            from preprocess.tools.g2p import g2p_transform

            _G2P_FN = g2p_transform
        return _G2P_FN


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    SoulXSvsGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
