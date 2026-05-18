import numpy as np
import pytest
from tests.helpers import make_wav
from converter.audio import trim_silence, load_wav, normalize_preset_wavs, NORMALIZE_TARGET_PEAK


def test_trim_leading_silence():
    samples = np.zeros(100, dtype=np.float32)
    samples[20:80] = 0.5
    trimmed, leading, _ = trim_silence(make_wav(samples))
    assert leading == 20
    result, _, _ = load_wav(trimmed)
    assert len(result) == 60


def test_trim_trailing_silence():
    samples = np.zeros(100, dtype=np.float32)
    samples[10:50] = 0.5
    trimmed, leading, _ = trim_silence(make_wav(samples))
    assert leading == 10
    result, _, _ = load_wav(trimmed)
    assert len(result) == 40


def test_trim_both_ends():
    samples = np.zeros(100, dtype=np.float32)
    samples[15:85] = 0.3
    trimmed, leading, _ = trim_silence(make_wav(samples))
    assert leading == 15
    result, _, _ = load_wav(trimmed)
    assert len(result) == 70


def test_no_silence_unchanged():
    samples = np.full(100, 0.5, dtype=np.float32)
    trimmed, leading, _ = trim_silence(make_wav(samples))
    assert leading == 0
    result, _, _ = load_wav(trimmed)
    assert len(result) == 100


def test_fully_silent_not_trimmed():
    # Fully silent WAV: return as-is rather than empty
    samples = np.zeros(100, dtype=np.float32)
    trimmed, leading, _ = trim_silence(make_wav(samples))
    assert leading == 0
    result, _, _ = load_wav(trimmed)
    assert len(result) == 100


def test_stereo_trim():
    left = np.zeros(100, dtype=np.float32)
    right = np.zeros(100, dtype=np.float32)
    left[10:90] = 0.5
    right[10:90] = 0.5
    stereo = np.stack([left, right], axis=1)
    trimmed, leading, _ = trim_silence(make_wav(stereo))
    assert leading == 10
    result, _, _ = load_wav(trimmed)
    assert len(result) == 80


def test_normalize_loudest_sample_hits_target():
    # loudest sample peaks at 0.25, quieter at 0.1
    loud = np.full(100, 0.25, dtype=np.float32)
    quiet = np.full(100, 0.1, dtype=np.float32)
    wav_map = {"loud.wav": make_wav(loud), "quiet.wav": make_wav(quiet)}
    result = normalize_preset_wavs(wav_map)
    loud_out, _, _ = load_wav(result["loud.wav"])
    quiet_out, _, _ = load_wav(result["quiet.wav"])
    assert abs(loud_out.max() - NORMALIZE_TARGET_PEAK) < 0.002


def test_normalize_preserves_relative_levels():
    loud = np.full(100, 0.4, dtype=np.float32)
    quiet = np.full(100, 0.2, dtype=np.float32)
    wav_map = {"loud.wav": make_wav(loud), "quiet.wav": make_wav(quiet)}
    result = normalize_preset_wavs(wav_map)
    loud_out, _, _ = load_wav(result["loud.wav"])
    quiet_out, _, _ = load_wav(result["quiet.wav"])
    ratio_before = 0.4 / 0.2
    ratio_after = loud_out.max() / quiet_out.max()
    assert abs(ratio_after - ratio_before) < 0.01


def test_normalize_empty_map_returns_empty():
    assert normalize_preset_wavs({}) == {}


def test_normalize_fully_silent_unchanged():
    silent = np.zeros(100, dtype=np.float32)
    wav_map = {"silent.wav": make_wav(silent)}
    result = normalize_preset_wavs(wav_map)
    out, _, _ = load_wav(result["silent.wav"])
    assert out.max() == 0.0
