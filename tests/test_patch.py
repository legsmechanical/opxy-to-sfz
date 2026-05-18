import pytest
from converter.patch import parse_patch, Preset, Region


MINIMAL_PATCH = {
    "version": 4,
    "type": "multisampler",
    "name": "MyPreset",
    "envelope": {
        "amp": {"attack": 0, "decay": 20295, "release": 16383, "sustain": 14989},
        "filter": {"attack": 0, "decay": 16895, "release": 19968, "sustain": 16896},
    },
    "fx": {"type": "svf", "active": False, "params": [19661, 0, 7391, 24063, 0, 32767, 0, 0]},
    "regions": [
        {
            "sample": "sample_60.wav",
            "pitch.keycenter": 60,
            "lokey": 48,
            "hikey": 72,
            "tune": 0,
            "gain": -3.0,
            "loop.enabled": True,
            "loop.start": 100,
            "loop.end": 5000,
            "sample.start": 0,
            "sample.end": 6000,
            "reverse": False,
        }
    ],
}


def test_parse_returns_preset():
    result = parse_patch(MINIMAL_PATCH)
    assert isinstance(result, Preset)


def test_preset_name():
    result = parse_patch(MINIMAL_PATCH)
    assert result.name == "MyPreset"


def test_region_count():
    result = parse_patch(MINIMAL_PATCH)
    assert len(result.regions) == 1


def test_region_fields():
    region = parse_patch(MINIMAL_PATCH).regions[0]
    assert isinstance(region, Region)
    assert region.sample == "sample_60.wav"
    assert region.pitch_keycenter == 60
    assert region.lokey == 48
    assert region.hikey == 72
    assert region.tune == 0
    assert region.volume == -3.0
    assert region.loop_mode == "loop_continuous"
    assert region.loop_start == 100
    assert region.loop_end == 5000
    assert region.offset == 0
    assert region.end == 6000
    assert region.direction == "forward"


def test_loop_disabled():
    patch = {**MINIMAL_PATCH, "regions": [{**MINIMAL_PATCH["regions"][0], "loop.enabled": False}]}
    region = parse_patch(patch).regions[0]
    assert region.loop_mode == "no_loop"
    assert region.loop_start is None
    assert region.loop_end is None


def test_reverse_region():
    patch = {**MINIMAL_PATCH, "regions": [{**MINIMAL_PATCH["regions"][0], "reverse": True}]}
    region = parse_patch(patch).regions[0]
    assert region.direction == "reverse"


def test_fx_active_false():
    result = parse_patch(MINIMAL_PATCH)
    assert result.fx_active is False


def test_fx_params_stored():
    result = parse_patch(MINIMAL_PATCH)
    assert result.fx_params[0] == 19661


def test_amp_envelope_stored():
    result = parse_patch(MINIMAL_PATCH)
    assert result.amp_envelope["attack"] == 0
    assert result.amp_envelope["decay"] == 20295


def test_missing_name_defaults():
    patch = {k: v for k, v in MINIMAL_PATCH.items() if k != "name"}
    result = parse_patch(patch)
    assert result.name == "preset"
