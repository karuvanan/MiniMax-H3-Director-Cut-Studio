<div align="center">
  <h1>🎤 SoulX-Singer</h1>
  <p>
    Official inference code for<br>
    <b><em>SoulX-Singer: Towards High-Quality Zero-Shot Singing Voice Synthesis</em></b>
  </p>
  <p>
    <img src="assets/soulx-logo.png" alt="SoulX-Logo" style="height:85px;">
  </p>
  <p>
    <a href="https://soul-ailab.github.io/soulx-singer/"><img src="https://img.shields.io/badge/Demo-Page-lightgrey" alt="Demo Page"></a>
    <a href="https://huggingface.co/spaces/Soul-AILab/SoulX-Singer"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20HF%20Space-Online%20Demo-ffda16" alt="HF Space Demo"></a>
    <a href="https://huggingface.co/Soul-AILab/SoulX-Singer"><img src='https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Model-blue' alt="HF-model"></a>
    <a href="assets/technical-report.pdf"><img src="https://img.shields.io/badge/Report-Github-red" alt="Technical Report"></a>
    <a href="https://arxiv.org/abs/2602.07803"><img src="https://img.shields.io/badge/arXiv-2602.07803-b31b1b" alt="arXiv"></a>
    <a href="https://github.com/Soul-AILab/SoulX-Singer"><img src="https://img.shields.io/badge/License-Apache%202.0-blue" alt="License"></a>
  </p>
</div>

---

## 🎵 Overview

**SoulX-Singer** is a high-fidelity, zero-shot singing voice synthesis model that enables users to generate realistic singing voices for unseen singers. It supports **melody-conditioned (F0 contour)** and **score-conditioned (MIDI notes)** control for precise pitch, rhythm, and expression.

**SoulX-Singer-SVC** is a singing voice conversion (SVC) model finetuned from **SoulX-Singer**. Singing Voice Conversion aims to transform a source singing recording into the target singer’s voice while preserving the original melody, rhythm, and lyrical content. Based on the strong generative capability of SoulX-Singer, SoulX-Singer-SVC enables high-quality singing voice conversion directly from raw singing audio, without requiring lyric or MIDI transcriptions.

---

## ✨ Key Features

#### SoulX-Singer
- **🎤 Zero-Shot Singing** – Generate high-fidelity voices for unseen singers, no fine-tuning needed.  
- **🎵 Flexible Control Modes** – Melody (F0) and Score (MIDI) conditioning.  
- **📚 Large-Scale Dataset** – 42,000+ hours of aligned vocals, lyrics, notes across Mandarin, English, Cantonese.  
- **🧑‍🎤 Timbre Cloning** – Preserve singer identity across languages, styles, and edited lyrics.  
- **✏️ Singing Voice Editing** – Modify lyrics while keeping natural prosody.  
- **🌐 Cross-Lingual Synthesis** – High-fidelity synthesis by disentangling timbre from content.  

#### SoulX-Singer-SVC
- **🎙️ Zero-Shot Timbre and Style Transfer** – Transfer singer identity and style to unseen voices without per-speaker fine-tuning.
- **🌍 Language-Agnostic Conversion** – Works across multilingual singing content.
- **🔄 Transcription-Free Audio-to-Audio Conversion** – Convert target singing directly without lyrics transcription or MIDI inputs.

---

<p align="center">
  <img src="assets/performance_radar.png" width="80%" alt="Performance Radar"/>
</p>

---

## 🎬 Demo Examples

### Singing Voice Synthesis (SVS)
<div align="center">

<https://github.com/user-attachments/assets/13306f10-3a29-46ba-bcef-d6308d05cbcc>

</div>
<div align="center">

<https://github.com/user-attachments/assets/2eb260fe-6f0b-408c-aab8-5b81ddddb284>

</div>

### Singing Voice Conversion (SVC)
<div align="center">

<https://github.com/user-attachments/assets/aed15fc9-14c3-44fc-9146-f6d9fef894d3>

</div>

---

## 📰 News
- **[2026-10-31]** 🖱️ New desktop GUI for SVS (lyrics + MIDI) — [Desktop GUI for SVS](#-desktop-gui-for-svs-gui-py): run `launch_gui.pyw` (double-click) or `python gui.py`. Models load lazily, and closing the window unloads them and releases RAM/VRAM.
- **[2026-10-31]** 🎧 Long-audio patch for SVC in this build: whole songs (>10 min) are supported and the "silent past 5 minutes" bug is fixed — see [Full-length input for SVC](#-full-length-input-for-svc-long-audio-patch) and [handoff.md](handoff.md).
- **[2026-03-16]** [SoulX-Singer-SVC](https://huggingface.co/Soul-AILab/SoulX-Singer/blob/main/model-svc.pt) is released, and [SoulX-Singer Online Demo](https://huggingface.co/spaces/Soul-AILab/SoulX-Singer) has been updated to support singing voice conversion (SVC).
- **[2026-02-12]** [SoulX-Singer Eval Dataset](https://huggingface.co/datasets/Soul-AILab/SoulX-Singer-Eval-Dataset) is now available on Hugging Face Datasets.
- **[2026-02-09]** [SoulX-Singer Online Demo](https://huggingface.co/spaces/Soul-AILab/SoulX-Singer) is live on Hugging Face Spaces — try singing voice synthesis in your browser.
- **[2026-02-08]** [MIDI Editor](https://huggingface.co/spaces/Soul-AILab/SoulX-Singer-Midi-Editor) is available on Hugging Face Spaces.
- **[2026-02-06]** SoulX-Singer inference code and models released.

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/Soul-AILab/SoulX-Singer.git
cd SoulX-Singer
```

### 2. Set Up Environment

**1. Install Conda** (if not already installed): https://docs.conda.io/en/latest/miniconda.html

**2. Create and activate a Conda environment:**
```
conda create -n soulxsinger -y python=3.10
conda activate soulxsinger
```
**3. Install dependencies:**
```
pip install -r requirements.txt
```
⚠️ If you are in mainland China, use a PyPI mirror:
```
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com
```


---

### 3. Download Pretrained Models

Install Hugging Face Hub if needed:

```
pip install -U huggingface_hub
```

Download the SVS, SVC model and preprocessing models:
```sh
pip install -U huggingface_hub

# Download the SoulX-Singer SVS and SVC model
hf download Soul-AILab/SoulX-Singer --local-dir pretrained_models/SoulX-Singer

# Download models required for preprocessing
hf download Soul-AILab/SoulX-Singer-Preprocess --local-dir pretrained_models/SoulX-Singer-Preprocess
```


### 4. Run the Demo

#### Run the SVS inference demo
``` sh
bash example/infer.sh
```

This script relies on metadata generated from the preprocessing pipeline, including vocal separation and transcription. Users should follow the steps in [preprocess](preprocess/README.md) to prepare the necessary metadata before running the demo with their own data.

**⚠️ Important Note**
The metadata produced by the automatic preprocessing pipeline may not perfectly align the singing audio with the corresponding lyrics and musical notes. For best synthesis quality, we strongly recommend manually correcting the alignment using the 🎼 [Midi-Editor](https://huggingface.co/spaces/Soul-AILab/SoulX-Singer-Midi-Editor). 

How to use the Midi-Editor:
- [Eiditing Metadata with Midi-Editor](preprocess/README.md#L104-L105)

#### Run the SVC inference demo

```sh
bash example/infer_svc.sh
```

This example performs audio-to-audio SVC, converting the target singing into the prompt timbre using waveform and F0 inputs.
To prepare your own SVC data, run `example/preprocess.sh` with `midi_transcribe=False`.



### 🌐 WebUI

You can launch the interactive interface for SVS (Synthesised from lyrics and MIDI transcriptions) with:
```
python webui.py
```

For SVC WebUI (audio-to-audio conversion):

```
python webui_svc.py
```

A desktop (Tkinter) front-end for the same SVC pipeline is also available:

```
python gui_svc.py
```

And a desktop (Tkinter) front-end for SVS — lyrics + MIDI, no browser, unload on
exit — is described in the next section:

```
python gui.py
```

---

## 🎧 Full-length input for SVC (long-audio patch)

This build removes the length limits that made SVC stop at 10 minutes and go **silent after 5 minutes**:

- 🖥️ **No 10-minute cap.** `TARGET_MAX_SEC_DEFAULT` is now `0` = *no limit*, and both front-ends expose the control (WebUI slider 「Target 时长上限（秒，0 = 不限制）」, desktop field "Target seconds (0 = whole file)").
- 🧮 **F0 no longer stops at 300 s.** `F0Extractor(max_duration=None)` keeps the whole contour — this was the real cause of the broken tail, because vocal segments are built from F0, so everything past 5 min simply never reached the model and stayed zero.
- 🧠 **Length-independent memory/speed.** RMVPE now runs in 30 s sliding windows with 2 s overlap (interior frames only), and the salience decoder was vectorised, so neither VRAM nor runtime grows with the song (measured F0 peak: **0.62 GiB** on a 17-minute track; the previous single pass needed several GB plus ~15 min of CPU for the decoder alone).
- 🔊 **Whisper >30 s no longer loses content.** Inputs longer than Whisper's native 30 s window are split on the 50 Hz frame grid and concatenated instead of being zero-padded past 30 s.
- 🪡 **Seamless joins.** Vocal segments are crossfaded over 0.2 s at each split point, and both UIs report real per-segment progress.

Verified end-to-end on a **17 min 35 s** target: full-length output (1055.1 s), continuous loudness across the whole timeline (no silent tail), 61 segments, ~9 min total on one GPU.

Two design limits are *not* bugs and were left alone: the **prompt is capped at its first 30 s** (Whisper's encoder window) and internal vocal segments stay **≤ 30 s** to match the model's training distribution. The SVS front-end ([webui.py](webui.py), lyrics + MIDI) still defaults to a 60 s target because it also runs lyric/MIDI transcription — the [desktop GUI](#-desktop-gui-for-svs-gui-py) exposes the same field and accepts `0` = whole file.

📄 Implementation notes, measurements, known issues and next steps: **[handoff.md](handoff.md)**.

中文小结：原来 Target 被硬截到 10 分钟，且 F0 只算到 300 秒导致 5 分钟之后输出静音；现在两处限制都已解除（上限可调，默认不限制），F0 改为 30 秒滑窗（显存不再随时长增长）并修掉了 O(N²) 的解码循环，>30 秒的 Whisper 输入会自动分窗，分段之间加 0.2 秒淡化。详见 [handoff.md](handoff.md)。


## 🖱️ Desktop GUI for SVS (gui.py)

A Tkinter window for the lyrics + MIDI pipeline — the same steps as
[webui.py](webui.py), but no browser and no port to babysit:

```
python gui.py
```

or double-click `launch_gui.pyw` (starts the `soulxsinger` env without a console;
`launch_gui.py` does the same with a console).

| Tab | What it does |
| --- | --- |
| ① 参考音频 | pick the reference voice → vocal separation + lyric/note transcription → `prompt metadata.json` (+ `vocal.mid`) |
| ② 目标旋律 | **A** transcribe a singing audio, or **B** import a **`.mid`** you wrote (optionally aligned to a `vocal.wav`, which is what fills the `f0` field) → `target metadata.json` |
| ③ 合成 | control type (曲谱控制 / 旋律控制), auto pitch shift, ±36 semitones, seed, `n_steps`, `cfg`, device, FP16 → `generated.wav` (24 kHz) |

Things the web UI does not give you:

- ✏️ **Lyric editor.** The metadata notes are laid out as a table (`#`, start ms, duration, MIDI pitch, lyric). Select a row → type the word → Enter (应用) → 保存 metadata (Ctrl+S). `phoneme` is recomputed with the project G2P on save, the original file is kept as `.bak`, and one row is always one note, so `duration` / `note_pitch` can never drift out of sync. One character per row: G2P maps single CJK characters, so a multi-character token becomes `<SP>` (a rest) — the editor warns you at apply time and in the log.
- 🎼 **MIDI in *and* out.** 「MIDI → 歌词/音符」 regenerates the metadata from your score (exactly what re-uploading a `.mid` does in the web UI); 「导出 target vocal.mid」 writes the transcribed melody back out, so you can fix the alignment in the [Midi-Editor](https://huggingface.co/spaces/Soul-AILab/SoulX-Singer-Midi-Editor) and import it again.
- 📦 **Lazy models.** Opening the window touches no GPU. The weights load inside the worker on the first action (device / FP16 are honoured because `SOULX_DEVICE` and `--fp16` are set *before* `AppState` is built), and 「卸载模型」 frees them mid-session.
- 🚪 **Closing the window releases the memory.** The close handler destroys the window, drops `webui.APP_STATE` (and `webui_svc._APP_STATES` in the SVC GUI), runs `gc.collect()` → `torch.cuda.empty_cache()` / `ipc_collect()`, prints how much RAM/VRAM came back, and finishes with `os._exit` — needed because torchaudio / ASR worker threads would otherwise keep a windowless process holding gigabytes. All of that lives in [resource_release.py](resource_release.py) and is wired into [gui_svc.py](gui_svc.py) too; measured on a 3 GiB GPU allocation: `reserved 3.00 GiB -> 0.00 GiB`, free VRAM back up by the same amount (`outputs/_release_check.py`).
- 📊 **Real progress.** SVS synthesis reports `done / total` segments ([cli/inference.py](cli/inference.py) now takes an optional `progress_cb`, mirroring the SVC path), and both length caps are editable — 「目标时长上限 s（0=整首）」 lifts the web UI's fixed 60 s target limit.
- 🧪 **One-click examples.** 「载入示例」 points at `example/audio/*`; those ship with ready metadata, so 开始合成 works without any transcription step.

Implementation notes and the full list of measured numbers: [handoff.md](handoff.md) §10.

中文小结：`gui.py` 是 SVS（歌词 + MIDI）的桌面版，和 WebUI 流程一致，另外加了「歌词逐字编辑（保存时自动重算 phoneme，并留 `.bak`）」、「MIDI 导入 / 导出」、真实进度（第 N / 共 M 段）、可改的目标时长上限（0 = 整首）。模型是懒加载的，窗口打开不占显存；**关闭窗口会自动卸载模型并回收内存/显存**（`resource_release.py`：释放引用 → `gc.collect()` → `empty_cache()`/`ipc_collect()` → `os._exit`，退出时会打印释放了多少），同样的退出清理也加到了 `gui_svc.py`。

## 🚧 Roadmap

- [x] 🖥️ Web-based UI for easy and interactive inference  
- [x] 🌐 Online MIDI Editor deployment on Hugging Face Spaces
- [x] 🌐 Online demo deployment on Hugging Face Spaces  
- [x] 📊 Release the SoulX-Singer-Eval benchmark  
- [ ] 🎹 Inference support for user-friendly MIDI-based input
- [ ] 📚 Comprehensive tutorials and usage documentation  
- [x] 🎵 Support for wav-to-wav singing voice conversion (without transcription)


## 🙏 Acknowledgements

Special thanks to the following open-source projects:

- [F5-TTS](https://github.com/SWivid/F5-TTS)
- [Amphion](https://github.com/open-mmlab/Amphion/tree/main)
- [Music Source Separation Training](https://github.com/ZFTurbo/Music-Source-Separation-Training)
- [Lead Vocal Separation](https://huggingface.co/becruily/mel-band-roformer-karaoke)
- [Vocal Dereverberation](https://huggingface.co/anvuew/dereverb_mel_band_roformer)
- [RMVPE](https://github.com/Dream-High/RMVPE)
[Paraformer](https://modelscope.cn/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch)
- [Parakeet-tdt-0.6b-v2](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)
- [ROSVOT](https://github.com/RickyL-2000/ROSVOT)



## 📄 License

We use the Apache 2.0 license. Researchers and developers are free to use the codes and model weights of our SoulX-Singer. Check the license at [LICENSE](LICENSE) for more details.


##  ⚠️ Usage Disclaimer

SoulX-Singer is intended for academic research, educational purposes, and legitimate applications such as personalized singing synthesis and assistive technologies.

Please note:

- 🎤 Respect intellectual property, privacy, and personal consent when generating singing content.
- 🚫 Do not use the model to impersonate individuals without authorization or to create deceptive audio.
- ⚠️ The developers assume no liability for any misuse of this model.

We advocate for the responsible development and use of AI and encourage the community to uphold safety and ethical principles. For ethics or misuse concerns, please contact us.


## 📄 Citation

If you use SoulX-Singer in your research, please cite:

```bibtex
@misc{soulxsinger,
      title={SoulX-Singer: Towards High-Quality Zero-Shot Singing Voice Synthesis}, 
      author={Jiale Qian and Hao Meng and Tian Zheng and Pengcheng Zhu and Haopeng Lin and Yuhang Dai and Hanke Xie and Wenxiao Cao and Ruixuan Shang and Jun Wu and Hongmei Liu and Hanlin Wen and Jian Zhao and Zhonglin Jiang and Yong Chen and Shunshun Yin and Ming Tao and Jianguo Wei and Lei Xie and Xinsheng Wang},
      year={2026},
      eprint={2602.07803},
      archivePrefix={arXiv},
      primaryClass={eess.AS},
      url={https://arxiv.org/abs/2602.07803}, 
}
```


## 📬 Contact Us

We welcome your feedback, questions, and collaboration:

- **Email**: qianjiale@soulapp.cn | menghao@soulapp.cn | wangxinsheng@soulapp.cn

- **Join discussions**: WeChat or Soul APP groups for technical discussions and updates:

<p align="center">
  <!-- <em>Due to group limits, if you can't scan the QR code, please add my WeChat for group access  -->
      <!-- : <strong>Tiamo James</strong></em> -->
  <br>
  <span style="display: inline-block; margin-right: 10px;">
    <img src="assets/soul_wechat01.jpg" width="500" alt="WeChat Group QR Code"/>
  </span>
  <!-- <span style="display: inline-block;">
    <img src="assets/wechat_tiamo.jpg" width="300" alt="WeChat QR Code"/>
  </span> -->
</p>