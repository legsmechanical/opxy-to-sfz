import io
import zipfile
import xml.etree.ElementTree as ET
import pytest

from converter.patch import Preset, Region
from converter.dspreset import generate_dspreset, build_dspreset_zip


def make_preset(name="TestPreset", fx_active=False, loop=False, loop_crossfade=0, loop_sustain=False):
    return Preset(
        name=name,
        regions=[
            Region(
                sample="sample_60.wav",
                pitch_keycenter=60,
                lokey=48,
                hikey=72,
                tune=0,
                volume=-3.0,
                loop_mode=("loop_sustain" if loop_sustain else "loop_continuous") if loop else "no_loop",
                loop_start=100 if loop else None,
                loop_end=5000 if loop else None,
                loop_crossfade=loop_crossfade,
                offset=0,
                end=6000,
                direction="forward",
            )
        ],
        amp_envelope={"attack": 0, "decay": 20295, "release": 16383, "sustain": 14989},
        filter_envelope={"attack": 0, "decay": 16895, "release": 19968, "sustain": 16896},
        fx_active=fx_active,
        fx_params=[19661, 0, 7391, 24063, 0, 32767, 0, 0],
    )


def parse_xml(preset, **kwargs):
    xml = generate_dspreset(preset, **kwargs)
    return ET.fromstring(xml.strip())


def test_dspreset_root_element():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    assert root.tag == "DecentSampler"


def test_dspreset_has_ui_with_4_knobs():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    knobs = root.findall(".//labeled-knob")
    assert len(knobs) == 4


def test_dspreset_knob_labels():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    labels = {k.get("label") for k in root.findall(".//labeled-knob")}
    assert labels == {"Attack", "Decay", "Sustain", "Release"}


def test_dspreset_attack_binding():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    bindings = root.findall(".//labeled-knob[@label='Attack']/binding")
    assert len(bindings) == 1
    assert bindings[0].get("parameter") == "ENV_ATTACK"


def test_dspreset_sustain_range_0_to_1():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    knob = root.find(".//labeled-knob[@label='Sustain']")
    assert float(knob.get("minValue")) == 0.0
    assert float(knob.get("maxValue")) == 1.0


def test_dspreset_fx_inactive_no_filter_knobs():
    root = parse_xml(make_preset(fx_active=False), trim_offsets={}, sample_rates={})
    knobs = root.findall(".//labeled-knob")
    labels = {k.get("label") for k in knobs}
    assert "Cutoff" not in labels
    assert "Resonance" not in labels


def test_dspreset_fx_active_has_6_knobs():
    root = parse_xml(make_preset(fx_active=True), trim_offsets={}, sample_rates={})
    knobs = root.findall(".//labeled-knob")
    assert len(knobs) == 6


def test_dspreset_fx_active_cutoff_binding():
    root = parse_xml(make_preset(fx_active=True), trim_offsets={}, sample_rates={})
    cutoff_knob = root.find(".//labeled-knob[@label='Cutoff']")
    assert cutoff_knob is not None
    binding = cutoff_knob.find("binding")
    assert binding.get("parameter") == "FX_FILTER_FREQUENCY"
    assert binding.get("translation") == "table"


def test_dspreset_fx_active_resonance_binding():
    root = parse_xml(make_preset(fx_active=True), trim_offsets={}, sample_rates={})
    res_knob = root.find(".//labeled-knob[@label='Resonance']")
    assert res_knob is not None
    binding = res_knob.find("binding")
    assert binding.get("parameter") == "FX_FILTER_RESONANCE"


def test_dspreset_has_groups_element():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    assert root.find("groups") is not None


def test_dspreset_group_has_attack_attr():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    groups = root.find("groups")
    assert groups.get("attack") is not None
    assert float(groups.get("attack")) >= 0.0


def test_dspreset_sample_path():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    sample = root.find(".//sample")
    assert sample.get("path") == "Samples/sample_60.wav"


def test_dspreset_sample_root_note():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    sample = root.find(".//sample")
    assert sample.get("rootNote") == "60"


def test_dspreset_sample_key_range():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    sample = root.find(".//sample")
    assert sample.get("loNote") == "48"
    assert sample.get("hiNote") == "72"


def test_dspreset_loop_enabled_when_looping():
    root = parse_xml(make_preset(loop=True), trim_offsets={}, sample_rates={})
    sample = root.find(".//sample")
    assert sample.get("loopEnabled") == "true"
    assert sample.get("loopStart") == "100"
    assert sample.get("loopEnd") == "5000"


def test_dspreset_no_loop_attr_when_not_looping():
    root = parse_xml(make_preset(loop=False), trim_offsets={}, sample_rates={})
    sample = root.find(".//sample")
    assert sample.get("loopEnabled") is None


def test_dspreset_loop_adjusted_for_trim():
    root = parse_xml(make_preset(loop=True), trim_offsets={"sample_60.wav": 10}, sample_rates={})
    sample = root.find(".//sample")
    assert sample.get("loopStart") == "90"
    assert sample.get("loopEnd") == "4990"


def test_dspreset_fx_active_has_effect_element():
    root = parse_xml(make_preset(fx_active=True), trim_offsets={}, sample_rates={})
    effects = root.find("effects")
    assert effects is not None
    effect = effects.find("effect")
    assert effect is not None


def test_dspreset_fx_inactive_no_effect():
    root = parse_xml(make_preset(fx_active=False), trim_offsets={}, sample_rates={})
    effects = root.find("effects")
    assert effects is None or len(list(effects)) == 0


def test_dspreset_fx_active_has_filter_modulator():
    root = parse_xml(make_preset(fx_active=True), trim_offsets={}, sample_rates={})
    modulators = root.find("modulators")
    assert modulators is not None
    env = modulators.find("envelope")
    assert env is not None


def test_build_dspreset_zip_contains_dspreset():
    wav_map = {"sample_60.wav": b"RIFF...."}
    xml = generate_dspreset(make_preset(), trim_offsets={}, sample_rates={})
    zip_bytes = build_dspreset_zip(make_preset(), xml, wav_map)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert "TestPreset.dspreset" in zf.namelist()


def test_build_dspreset_zip_wav_in_samples_dir():
    wav_map = {"sample_60.wav": b"RIFF...."}
    xml = generate_dspreset(make_preset(), trim_offsets={}, sample_rates={})
    zip_bytes = build_dspreset_zip(make_preset(), xml, wav_map)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert "Samples/sample_60.wav" in zf.namelist()


def test_dspreset_mono_sets_poly_limit():
    preset = make_preset()
    preset.playmode = "mono"
    root = parse_xml(preset, trim_offsets={}, sample_rates={})
    group = root.find(".//group")
    assert group.get("polyLimit") == "1"


def test_dspreset_poly_no_poly_limit():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    group = root.find(".//group")
    assert group.get("polyLimit") is None


def test_dspreset_veltrack_emitted():
    preset = make_preset()
    preset.velocity_sensitivity = 60.0
    root = parse_xml(preset, trim_offsets={}, sample_rates={})
    groups = root.find("groups")
    assert groups.get("ampVelTrack") is not None


def test_dspreset_veltrack_100_omitted():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    groups = root.find("groups")
    assert groups.get("ampVelTrack") is None
