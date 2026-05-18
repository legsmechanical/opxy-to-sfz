import numpy as np
import pytest
from tests.helpers import make_wav
from converter.audio import trim_silence, load_wav


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
