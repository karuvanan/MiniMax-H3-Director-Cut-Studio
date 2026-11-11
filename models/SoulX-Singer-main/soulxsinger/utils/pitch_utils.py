# https://github.com/gwx314/TechSinger/blob/main/utils/audio/pitch/utils.py

import numpy as np
import torch


def to_lf0(f0):
    f0[f0 < 1.0e-5] = 1.0e-6
    lf0 = f0.log() if isinstance(f0, torch.Tensor) else np.log(f0)
    lf0[f0 < 1.0e-5] = - 1.0E+10
    return lf0


def to_f0(lf0):
    f0 = np.where(lf0 <= 0, 0.0, np.exp(lf0))
    return f0.flatten()


def f0_to_coarse_mel(f0, f0_bin=256, f0_max=900.0, f0_min=50.0, f0_shift=0):
    f0_mel_min = 1127 * np.log(1 + f0_min / 700)
    f0_mel_max = 1127 * np.log(1 + f0_max / 700)
    is_torch = isinstance(f0, torch.Tensor)
    f0_mel = 1127 * (1 + f0 / 700).log() if is_torch else 1127 * np.log(1 + f0 / 700)
    f0_mel[f0_mel > 0] = (f0_mel[f0_mel > 0] - f0_mel_min) * (f0_bin - 2) / (f0_mel_max - f0_mel_min) + 1

    f0_mel[f0_mel <= 1] = 1
    f0_mel[f0_mel > f0_bin - 1] = f0_bin - 1
    f0_coarse = (f0_mel + 0.5).long() if is_torch else np.rint(f0_mel).astype(int)

    if f0_shift != 0:
        if f0_shift > 0:
            f0_shift = min(f0_shift, f0_bin - 1 - f0_coarse[f0_coarse > 1].max().item())
        else:
            f0_shift = max(f0_shift, 1 - f0_coarse[f0_coarse > 1].min().item())
        
        f0_coarse[f0_coarse > 1] = f0_coarse[f0_coarse > 1] + f0_shift
    
    assert f0_coarse.max() <= 255 and f0_coarse.min() >= 1, (f0_coarse.max(), f0_coarse.min(), f0.min(), f0.max())
    return f0_coarse


def coarse_to_f0_mel(f0_coarse, f0_bin=256, f0_max=900.0, f0_min=50.0):
    f0_mel_min = 1127 * np.log(1 + f0_min / 700)
    f0_mel_max = 1127 * np.log(1 + f0_max / 700)
    uv = f0_coarse == 1
    f0 = f0_mel_min + (f0_coarse - 1) * (f0_mel_max - f0_mel_min) / (f0_bin - 2)
    f0 = ((f0 / 1127).exp() - 1) * 700
    f0[uv] = 0
    return f0

CONST_C1_FREQ = 32.7031956625  # C1 frequency in Hz
CONST_B6_FREQ = 1975.53320502  # B6 frequency in Hz

def f0_to_coarse_midi(f0, f0_bin=361, f0_max=CONST_B6_FREQ, f0_min=CONST_C1_FREQ, f0_shift=0):
    is_torch = isinstance(f0, torch.Tensor)
    uv_mask = f0 <= 0    

    if is_torch:  
        f0_safe = torch.maximum(f0, torch.tensor(f0_min))
        f0_cents = 1200 * torch.log2(f0_safe / f0_min)
    else:
        f0_safe = np.maximum(f0, f0_min)
        f0_cents = 1200 * np.log2(f0_safe / f0_min)

    f0_coarse = (f0_cents / 20) + 1
    
    if is_torch:
        f0_coarse = torch.round(f0_coarse).long()
        f0_coarse = torch.clamp(f0_coarse, min=1, max=f0_bin - 1)
    else:
        f0_coarse = np.rint(f0_coarse).astype(int)
        f0_coarse = np.clip(f0_coarse, 1, f0_bin - 1)

    f0_coarse[uv_mask] = 0

    if f0_shift != 0:
        if is_torch:
            voiced = f0_coarse > 0
            if voiced.any():
                shifted = f0_coarse[voiced] + f0_shift
                f0_coarse[voiced] = torch.clamp(shifted, 1, f0_bin - 1)
        else:
            voiced = f0_coarse > 0
            if np.any(voiced):
                shifted = f0_coarse[voiced] + f0_shift
                f0_coarse[voiced] = np.clip(shifted, 1, f0_bin - 1)
    
    return f0_coarse


def coarse_to_f0_midi(f0_coarse, f0_bin=361, f0_max=CONST_B6_FREQ, f0_min=CONST_C1_FREQ):
    
    uv_mask = f0_coarse == 0  
    cents = (f0_coarse - 1) * 20
    f0 = f0_min * (2 ** (cents / 1200))
    f0[uv_mask] = 0

    return f0


def norm_f0(f0, uv, pitch_norm='log', f0_mean=400, f0_std=100):
    is_torch = isinstance(f0, torch.Tensor)
    if pitch_norm == 'standard':
        f0 = (f0 - f0_mean) / f0_std
    if pitch_norm == 'log':
        f0 = torch.log2(f0 + 1e-8) if is_torch else np.log2(f0 + 1e-8)
    if uv is not None:
        f0[uv > 0] = 0
    return f0


def norm_interp_f0(f0, pitch_norm='log', f0_mean=None, f0_std=None):
    is_torch = isinstance(f0, torch.Tensor)
    if is_torch:
        device = f0.device
        f0 = f0.data.cpu().numpy()
    uv = f0 == 0
    f0 = norm_f0(f0, uv, pitch_norm, f0_mean, f0_std)
    if sum(uv) == len(f0):
        f0[uv] = 0
    elif sum(uv) > 0:
        f0[uv] = np.interp(np.where(uv)[0], np.where(~uv)[0], f0[~uv])
    if is_torch:
        uv = torch.FloatTensor(uv)
        f0 = torch.FloatTensor(f0)
        f0 = f0.to(device)
        uv = uv.to(device)
    return f0, uv


def denorm_f0(f0, uv, pitch_norm='log', f0_mean=400, f0_std=100, pitch_padding=None, min=50, max=900):
    is_torch = isinstance(f0, torch.Tensor)
    if pitch_norm == 'standard':
        f0 = f0 * f0_std + f0_mean
    if pitch_norm == 'log':
        f0 = 2 ** f0
    f0 = f0.clamp(min=min, max=max) if is_torch else np.clip(f0, a_min=min, a_max=max)
    if uv is not None:
        f0[uv > 0] = 0
    if pitch_padding is not None:
        f0[pitch_padding] = 0
    return f0
