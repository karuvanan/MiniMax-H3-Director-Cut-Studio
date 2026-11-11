from __future__ import annotations

import os
import queue
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import webui_svc
import resource_release as rr
from webui_svc import (
    ROOT,
    SVC_EXAMPLE_PROMPT_AUDIO,
    SVC_EXAMPLE_TARGET_AUDIO,
    TARGET_MAX_SEC_DEFAULT,
    run_svc_conversion,
)


DEVICE_LABELS = {
    "Auto": "auto",
    "CUDA": "cuda",
    "DirectML": "directml",
    "CPU": "cpu",
}


class SoulXSvcGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SoulX-Singer SVC")
        self.root.geometry("820x700")
        self.root.minsize(760, 600)

        self.prompt_path = tk.StringVar()
        self.target_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.device_label = tk.StringVar(value="Auto")
        self.prompt_vocal_sep = tk.BooleanVar(value=False)
        self.target_vocal_sep = tk.BooleanVar(value=True)
        self.auto_shift = tk.BooleanVar(value=True)
        self.auto_mix_acc = tk.BooleanVar(value=True)
        self.use_fp16 = tk.BooleanVar(value=True)
        self.pitch_shift = tk.IntVar(value=0)
        self.n_step = tk.IntVar(value=32)
        self.cfg = tk.DoubleVar(value=1.0)
        self.seed = tk.IntVar(value=42)
        self.target_max_sec = tk.IntVar(value=TARGET_MAX_SEC_DEFAULT)
        self.progress_value = tk.DoubleVar(value=0.0)
        self.status_text = tk.StringVar(value="Idle")

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self._closing = False
        self._build_ui()
        self._poll_log_queue()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)

        title = ttk.Label(outer, text="SoulX-Singer SVC", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        files = ttk.LabelFrame(outer, text="Audio")
        files.grid(row=1, column=0, sticky="ew", pady=(14, 10))
        files.columnconfigure(1, weight=1)

        self._file_row(files, 0, "Prompt audio", self.prompt_path, self._browse_prompt)
        self._file_row(files, 1, "Target audio", self.target_path, self._browse_target)

        controls = ttk.LabelFrame(outer, text="Settings")
        controls.grid(row=2, column=0, sticky="ew", pady=10)
        for col in range(4):
            controls.columnconfigure(col, weight=1)

        ttk.Label(controls, text="Device").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        device_box = ttk.Combobox(
            controls,
            textvariable=self.device_label,
            values=list(DEVICE_LABELS.keys()),
            state="readonly",
            width=14,
        )
        device_box.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        ttk.Checkbutton(controls, text="FP16 (CUDA only)", variable=self.use_fp16).grid(
            row=1, column=1, sticky="w", padx=8, pady=(0, 8)
        )
        ttk.Checkbutton(controls, text="Prompt vocal separation", variable=self.prompt_vocal_sep).grid(
            row=2, column=0, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(controls, text="Target vocal separation", variable=self.target_vocal_sep).grid(
            row=2, column=1, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(controls, text="Auto pitch shift", variable=self.auto_shift).grid(
            row=2, column=2, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(controls, text="Auto mix accompaniment", variable=self.auto_mix_acc).grid(
            row=2, column=3, sticky="w", padx=8, pady=4
        )

        self._number_row(controls, 3, 0, "Pitch shift", self.pitch_shift, -36, 36, 1)
        self._number_row(controls, 3, 1, "n_step", self.n_step, 1, 200, 1)
        self._number_row(controls, 3, 2, "cfg", self.cfg, 0.0, 10.0, 0.1)
        self._number_row(controls, 3, 3, "Seed", self.seed, 0, 10000, 1)
        self._number_row(
            controls, 4, 0,
            "Target seconds (0 = whole file)",
            self.target_max_sec, 0, 7200, 30,
        )

        buttons = ttk.Frame(outer)
        buttons.grid(row=3, column=0, sticky="ew", pady=(4, 10))
        buttons.columnconfigure(4, weight=1)
        self.run_button = ttk.Button(buttons, text="Run conversion", command=self._start)
        self.run_button.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Load example", command=self._load_example).grid(row=0, column=1, padx=8)
        ttk.Button(buttons, text="Open output", command=self._open_output).grid(row=0, column=2, padx=8)

        progress = ttk.Frame(outer)
        progress.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        progress.columnconfigure(0, weight=1)
        ttk.Progressbar(
            progress,
            variable=self.progress_value,
            maximum=100,
            mode="determinate",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(progress, textvariable=self.status_text).grid(row=1, column=0, sticky="w", pady=(4, 0))

        output = ttk.LabelFrame(outer, text="Output")
        output.grid(row=5, column=0, sticky="ew", pady=10)
        output.columnconfigure(0, weight=1)
        ttk.Entry(output, textvariable=self.output_path, state="readonly").grid(
            row=0, column=0, sticky="ew", padx=8, pady=8
        )

        logs = ttk.LabelFrame(outer, text="Log")
        logs.grid(row=6, column=0, sticky="nsew", pady=(10, 0))
        outer.rowconfigure(6, weight=1)
        logs.rowconfigure(0, weight=1)
        logs.columnconfigure(0, weight=1)
        self.log_text = tk.Text(logs, height=10, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        scrollbar = ttk.Scrollbar(logs, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=8, padx=(0, 8))
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _file_row(self, parent: ttk.Frame, row: int, label: str, value: tk.StringVar, command) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=8)
        ttk.Entry(parent, textvariable=value).grid(row=row, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, padx=8, pady=8)

    def _number_row(self, parent: ttk.Frame, row: int, column: int, label: str, var, start, end, step) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=column, sticky="ew", padx=8, pady=8)
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=label).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(frame, textvariable=var, from_=start, to=end, increment=step, width=12).grid(
            row=1, column=0, sticky="ew"
        )

    def _browse_prompt(self) -> None:
        path = self._browse_audio()
        if path:
            self.prompt_path.set(path)

    def _browse_target(self) -> None:
        path = self._browse_audio()
        if path:
            self.target_path.set(path)

    def _browse_audio(self) -> str:
        return filedialog.askopenfilename(
            title="Select audio",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.m4a *.ogg"),
                ("All files", "*.*"),
            ],
        )

    def _load_example(self) -> None:
        self.prompt_path.set(str(ROOT / SVC_EXAMPLE_PROMPT_AUDIO))
        self.target_path.set(str(ROOT / SVC_EXAMPLE_TARGET_AUDIO))
        self._log("Example loaded.")

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.prompt_path.get() or not self.target_path.get():
            messagebox.showwarning("Missing audio", "Please select both prompt and target audio.")
            return

        self.output_path.set("")
        self.progress_value.set(0)
        self.status_text.set("Starting conversion...")
        self.run_button.configure(state=tk.DISABLED)
        self._log("Starting conversion...")

        self.worker = threading.Thread(target=self._run_worker, daemon=True)
        self.worker.start()

    def _run_worker(self) -> None:
        try:
            device_choice = DEVICE_LABELS.get(self.device_label.get(), "auto")
            generated = run_svc_conversion(
                prompt_audio=self.prompt_path.get(),
                target_audio=self.target_path.get(),
                prompt_vocal_sep=self.prompt_vocal_sep.get(),
                target_vocal_sep=self.target_vocal_sep.get(),
                auto_shift=self.auto_shift.get(),
                auto_mix_acc=self.auto_mix_acc.get(),
                pitch_shift=self.pitch_shift.get(),
                n_step=self.n_step.get(),
                cfg=self.cfg.get(),
                seed=self.seed.get(),
                target_max_sec=int(self.target_max_sec.get() or 0),
                device_choice=device_choice,
                use_fp16=self.use_fp16.get(),
                progress=self._thread_progress,
            )
            self.log_queue.put(f"OUTPUT::{generated}")
        except Exception as exc:
            self.log_queue.put("ERROR::" + str(exc))
            self.log_queue.put(traceback.format_exc())
        finally:
            self.log_queue.put("DONE::")

    def _thread_progress(self, fraction: float, message: str) -> None:
        self.log_queue.put(f"PROGRESS::{fraction:.4f}::{message}")

    def _poll_log_queue(self) -> None:
        try:
            while True:
                message = self.log_queue.get_nowait()
                if message.startswith("OUTPUT::"):
                    self.output_path.set(message.removeprefix("OUTPUT::"))
                elif message.startswith("PROGRESS::"):
                    _, fraction, text = message.split("::", 2)
                    percent = max(0.0, min(100.0, float(fraction) * 100.0))
                    self.progress_value.set(percent)
                    self.status_text.set(text)
                    self._log(f"{percent:5.1f}%  {text}")
                elif message.startswith("ERROR::"):
                    text = message.removeprefix("ERROR::")
                    self.status_text.set("Failed")
                    self._log("ERROR: " + text)
                    if not self._closing:
                        messagebox.showerror("Conversion failed", text)
                elif message.startswith("DONE::"):
                    if self.output_path.get():
                        self.progress_value.set(100)
                        self.status_text.set("Done")
                    self.run_button.configure(state=tk.NORMAL)
                else:
                    self._log(message)
        except queue.Empty:
            pass
        if not self._closing:
            self.root.after(200, self._poll_log_queue)

    def _log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _open_output(self) -> None:
        path = self.output_path.get()
        if not path or not Path(path).exists():
            messagebox.showinfo("Output", "No generated file is available yet.")
            return
        os.startfile(path)

    def _unload_models(self, log) -> None:
        """Drop the cached AppState(s) so the weights can be collected."""
        device = None
        for state in list(getattr(webui_svc, "_APP_STATES", {}) or {}).values():
            device = getattr(state, "device", device)
            break
        rr.unload_all(modules=[webui_svc], device=device, log=log)

    def _on_close(self) -> None:
        """Close the window, unload the models, release RAM/VRAM, then exit.

        The weights live on ``webui_svc._APP_STATES``, so simply destroying the
        window would leave the process holding several GB of VRAM; and after a
        CUDA run leftover worker threads can keep that process alive forever.
        """
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno(
                "Converting",
                "A conversion is still running.\nQuit anyway? Models will be unloaded and VRAM released.",
            ):
                return
        self._closing = True
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        try:
            self._unload_models(print)
        except Exception:
            traceback.print_exc()
        finally:
            rr.force_exit(0)


def main() -> None:
    root = tk.Tk()
    SoulXSvcGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
