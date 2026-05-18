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
    assert region.loop_crossfade == 0
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


def test_loop_crossfade_parsed():
    patch = {**MINIMAL_PATCH, "regions": [{**MINIMAL_PATCH["regions"][0], "loop.crossfade": 441}]}
    region = parse_patch(patch).regions[0]
    assert region.loop_crossfade == 441


def test_loop_crossfade_zero_when_loop_disabled():
    patch = {**MINIMAL_PATCH, "regions": [{**MINIMAL_PATCH["regions"][0], "loop.enabled": False, "loop.crossfade": 441}]}
    region = parse_patch(patch).regions[0]
    assert region.loop_crossfade == 0


def test_loop_onrelease_false_gives_loop_sustain():
    patch = {**MINIMAL_PATCH, "regions": [{**MINIMAL_PATCH["regions"][0], "loop.onrelease": False}]}
    region = parse_patch(patch).regions[0]
    assert region.loop_mode == "loop_sustain"


def test_loop_onrelease_true_gives_loop_continuous():
    patch = {**MINIMAL_PATCH, "regions": [{**MINIMAL_PATCH["regions"][0], "loop.onrelease": True}]}
    region = parse_patch(patch).regions[0]
    assert region.loop_mode == "loop_continuous"


def test_loop_inferred_from_loop_start_without_loop_enabled():
    region_data = {k: v for k, v in MINIMAL_PATCH["regions"][0].items() if k != "loop.enabled"}
    region_data["loop.start"] = 100
    region_data["loop.end"] = 5000
    patch = {**MINIMAL_PATCH, "regions": [region_data]}
    region = parse_patch(patch).regions[0]
    assert region.loop_mode == "loop_continuous"
    assert region.loop_start == 100
    assert region.loop_end == 5000


def test_no_loop_start_means_no_loop():
    region_data = {k: v for k, v in MINIMAL_PATCH["regions"][0].items() if k != "loop.enabled"}
    region_data.pop("loop.start", None)
    region_data.pop("loop.end", None)
    patch = {**MINIMAL_PATCH, "regions": [region_data]}
    region = parse_patch(patch).regions[0]
    assert region.loop_mode == "no_loop"


def test_engine_volume_parsed():
    patch = {**MINIMAL_PATCH, "engine": {"volume": 32767}}
    result = parse_patch(patch)
    assert abs(result.engine_volume - 0.0) < 0.01  # 32767 = unity = 0 dB


def test_engine_volume_attenuated():
    import math
    patch = {**MINIMAL_PATCH, "engine": {"volume": 18348}}
    result = parse_patch(patch)
    expected = 20.0 * math.log10(18348 / 32767)
    assert abs(result.engine_volume - expected) < 0.01


def test_engine_volume_default_when_absent():
    result = parse_patch(MINIMAL_PATCH)
    assert result.engine_volume == 0.0


def test_velocity_sensitivity_parsed():
    patch = {**MINIMAL_PATCH, "engine": {"velocity.sensitivity": 16384}}
    result = parse_patch(patch)
    assert abs(result.velocity_sensitivity - 50.0) < 0.1


def test_velocity_sensitivity_default_when_absent():
    result = parse_patch(MINIMAL_PATCH)
    assert result.velocity_sensitivity == 100.0


def test_transpose_from_engine():
    patch = {**MINIMAL_PATCH, "engine": {"transpose": 3}}
    result = parse_patch(patch)
    assert result.transpose == 3


def test_transpose_includes_octave():
    patch = {**MINIMAL_PATCH, "octave": 2, "engine": {"transpose": 1}}
    result = parse_patch(patch)
    assert result.transpose == 25  # 1 + 2*12


def test_playmode_parsed():
    patch = {**MINIMAL_PATCH, "engine": {"playmode": "mono"}}
    result = parse_patch(patch)
    assert result.playmode == "mono"


def test_playmode_default_poly():
    result = parse_patch(MINIMAL_PATCH)
    assert result.playmode == "poly"


def test_fx_type_parsed():
    result = parse_patch(MINIMAL_PATCH)
    assert result.fx_type == "svf"


def test_fx_type_ladder():
    patch = {**MINIMAL_PATCH, "fx": {**MINIMAL_PATCH["fx"], "type": "ladder"}}
    result = parse_patch(patch)
    assert result.fx_type == "ladder"
