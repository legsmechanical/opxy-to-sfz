import math
import pytest
from converter.envelope import (
    opxy_to_attack_seconds,
    opxy_to_release_seconds,
    opxy_sustain_to_sfz_percent,
    convert_amp_envelope,
    convert_filter_envelope,
)

def test_attack_zero_returns_zero():
    assert opxy_to_attack_seconds(0) == 0.0

def test_attack_max_returns_max():
    result = opxy_to_attack_seconds(32767)
    assert abs(result - 365.0) < 1.0  # within 1s of max

def test_attack_midpoint_is_reasonable():
    result = opxy_to_attack_seconds(16383)
    assert 0.01 < result < 365.0

def test_release_max_value_returns_min_seconds():
    # value 32767 = shortest release
    result = opxy_to_release_seconds(32767)
    assert abs(result - 2.405) < 0.01

def test_release_zero_returns_max_seconds():
    result = opxy_to_release_seconds(0)
    assert abs(result - 16.325) < 0.01

def test_sustain_zero_is_zero_percent():
    assert opxy_sustain_to_sfz_percent(0) == pytest.approx(0.0)

def test_sustain_max_is_100_percent():
    assert opxy_sustain_to_sfz_percent(32767) == pytest.approx(100.0)

def test_sustain_half_is_50_percent():
    assert opxy_sustain_to_sfz_percent(16383) == pytest.approx(49.998, abs=0.01)

def test_convert_amp_envelope_keys():
    result = convert_amp_envelope({"attack": 0, "decay": 20295, "release": 16383, "sustain": 14989})
    assert set(result.keys()) == {"ampeg_attack", "ampeg_decay", "ampeg_sustain", "ampeg_release"}

def test_convert_amp_envelope_attack_zero():
    result = convert_amp_envelope({"attack": 0, "decay": 0, "release": 0, "sustain": 32767})
    assert result["ampeg_attack"] == 0.0

def test_convert_filter_envelope_keys():
    result = convert_filter_envelope({"attack": 0, "decay": 16895, "release": 19968, "sustain": 16896})
    assert set(result.keys()) == {"fileg_attack", "fileg_decay", "fileg_sustain", "fileg_release"}

def test_sustain_clamped_below_zero():
    assert opxy_sustain_to_sfz_percent(-100) == pytest.approx(0.0)

def test_sustain_clamped_above_max():
    assert opxy_sustain_to_sfz_percent(40000) == pytest.approx(100.0)
