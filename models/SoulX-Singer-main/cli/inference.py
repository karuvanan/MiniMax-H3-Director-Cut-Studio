import os
import torch
import json
import argparse
from tqdm import tqdm
import numpy as np
import soundfile as sf
from collections import OrderedDict
from omegaconf import DictConfig
from typing import Any

from soulxsinger.utils.device_utils import is_cuda_device, resolve_device
from soulxsinger.utils.file_utils import load_config
from soulxsinger.models.soulxsinger import SoulXSinger
from soulxsinger.utils.data_processor import DataProcessor


def build_model(
    model_path: str,
    config: DictConfig,
    device: Any = "cuda",
    use_fp16: bool = False,
):
    """
    Build the model from the pre-trained model path and model configuration.

    Args:
        model_path (str): Path to the checkpoint file.
        config (DictConfig): Model configuration.
        device (str, optional): Device to use. Defaults to "cuda".
        use_fp16 (bool, optional): If True and device is CUDA, convert model to FP16 after load. Defaults to False.

    Returns:
        SoulXSinger: The initialized model.
    """

    if not os.path.isfile(model_path):
        raise FileNotFoundError(
            f"Model checkpoint not found: {model_path}. "
            "Please download the pretrained model and place it at the path, or set --model_path."
        )
    model = SoulXSinger(config).to(device)
    print("Model initialized.")
    print("Model parameters:", sum(p.numel() for p in model.parameters()) / 1e6, "M")
    
    checkpoint = torch.load(model_path, weights_only=False, map_location="cpu")
    if "state_dict" not in checkpoint:
        raise KeyError(
            f"Checkpoint at {model_path} has no 'state_dict' key. "
            "Expected a checkpoint saved with model.state_dict()."
        )
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    
    if use_fp16 and is_cuda_device(device):
        model.half()
        model.mel.float()
        print("Model converted to FP16 (mel kept in FP32).")
    model.eval()
    model.to(device)
    print("Model checkpoint loaded.")

    return model


def process(args, config, model: torch.nn.Module, progress_cb=None):
    """Run the full inference pipeline given a data_processor and model.

    ``progress_cb(done, total)`` is optional (one call per target metadata
    segment) so a desktop front-end can drive a progress bar; tqdm already
    covers the CLI.
    """
    if args.control not in ("melody", "score"):
        raise ValueError(f"control must be 'melody' or 'score', got: {args.control}")

    print(f"prompt_metadata_path: {args.prompt_metadata_path}")
    print(f"target_metadata_path: {args.target_metadata_path}")

    os.makedirs(args.save_dir, exist_ok=True)
    data_processor = DataProcessor(
        hop_size=config.audio.hop_size,
        sample_rate=config.audio.sample_rate,
        phoneset_path=args.phoneset_path,
        device=args.device,
    )

    with open(args.prompt_metadata_path, "r", encoding="utf-8") as f:
        prompt_meta_list = json.load(f)
    if not prompt_meta_list:
        raise ValueError("Prompt metadata is empty. Please run preprocess on prompt audio first.")
    prompt_meta = prompt_meta_list[0]  # load the first segment as the prompt
    with open(args.target_metadata_path, "r", encoding="utf-8") as f:
        target_meta_list = json.load(f)
    infer_prompt_data = data_processor.process(prompt_meta, args.prompt_wav_path)

    assert len(target_meta_list) > 0, "No target segments found in the target metadata."
    generated_len = int(target_meta_list[-1]["time"][1] / 1000 * config.audio.sample_rate)
    generated_merged = np.zeros(generated_len, dtype=np.float32)

    for idx, target_meta in enumerate(
        tqdm(target_meta_list, total=len(target_meta_list), desc="Inferring segments"),
    ):
        start_sample_idx = int(target_meta["time"][0] / 1000 * config.audio.sample_rate)
        end_sample_idx = int(target_meta["time"][1] / 1000 * config.audio.sample_rate)
        infer_target_data = data_processor.process(target_meta, None)

        infer_data = {
            "prompt": infer_prompt_data,
            "target": infer_target_data,
        }

        with torch.no_grad():
            generated_audio = model.infer(
                infer_data,
                auto_shift=args.auto_shift,
                pitch_shift=args.pitch_shift,
                n_steps=config.infer.n_steps,
                cfg=config.infer.cfg,
                control=args.control,
                use_fp16=args.use_fp16,
            )

        generated_audio = generated_audio.squeeze().cpu().numpy()
        gen_len = min(generated_audio.shape[0], generated_merged.shape[0] - start_sample_idx)
        generated_merged[start_sample_idx: start_sample_idx + gen_len] = generated_audio[:gen_len]

        if progress_cb is not None:
            progress_cb(idx + 1, len(target_meta_list))

    merged_path = os.path.join(args.save_dir, "generated.wav")
    sf.write(merged_path, generated_merged, 24000)
    print(f"Generated audio saved to {merged_path}")


def main(args, config):
    args.device = resolve_device(args.device)
    args.use_fp16 = bool(getattr(args, "use_fp16", False)) and is_cuda_device(args.device)
    model = build_model(
        model_path=args.model_path,
        config=config,
        device=args.device,
        use_fp16=getattr(args, "use_fp16", False),
    )
    process(args, config, model)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--model_path", type=str, default='pretrained_models/soulx-singer/model.pt')
    parser.add_argument("--config", type=str, default='soulxsinger/config/soulxsinger.yaml')
    parser.add_argument("--prompt_wav_path", type=str, default='example/audio/zh_prompt.wav')
    parser.add_argument("--prompt_metadata_path", type=str, default='example/metadata/zh_prompt.json')
    parser.add_argument("--target_metadata_path", type=str, default='example/metadata/zh_target.json')
    parser.add_argument("--phoneset_path", type=str, default='soulxsinger/utils/phoneme/phone_set.json')
    parser.add_argument("--save_dir", type=str, default='outputs')
    parser.add_argument("--auto_shift", action="store_true")
    parser.add_argument("--pitch_shift", type=int, default=0)
    parser.add_argument(
        "--control",
        type=str,
        default="melody",
        choices=["melody", "score"],
        help="Control mode: melody or score only",
    )
    parser.add_argument(
        "--fp16",
        action="store_true",
        default=False,
        help="Use FP16 inference (faster on GPU)",
    )
    args = parser.parse_args()
    args.use_fp16 = args.fp16

    config = load_config(args.config)
    main(args, config)
