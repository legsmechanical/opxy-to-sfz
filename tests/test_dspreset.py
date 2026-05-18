import io
import zipfile
import xml.etree.ElementTree as ET

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


# ------------------------------------------------------------------ structure

def test_dspreset_root_element():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    assert root.tag == "DecentSampler"


def test_dspreset_always_8_knobs():
    for fx_active in (False, True):
        root = parse_xml(make_preset(fx_active=fx_active), trim_offsets={}, sample_rates={})
        assert len(root.findall(".//labeled-knob")) == 8, f"expected 8 knobs when fx_active={fx_active}"


def test_dspreset_knob_labels():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    labels = {k.get("label") for k in root.findall(".//labeled-knob")}
    assert labels == {"Attack", "Decay", "Sustain", "Release", "Cutoff", "Resonance", "Chorus", "Reverb"}


# ------------------------------------------------------------------ amp ADSR bindings

def test_dspreset_attack_binding():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    b = root.find(".//labeled-knob[@label='Attack']/binding")
    assert b.get("parameter") == "ENV_ATTACK"
    assert b.get("type") == "amp"


def test_dspreset_sustain_range_0_to_1():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    k = root.find(".//labeled-knob[@label='Sustain']")
    assert float(k.get("minValue")) == 0.0
    assert float(k.get("maxValue")) == 1.0


# ------------------------------------------------------------------ filter knobs

def test_dspreset_cutoff_wide_open_when_fx_inactive():
    root = parse_xml(make_preset(fx_active=False), trim_offsets={}, sample_rates={})
    k = root.find(".//labeled-knob[@label='Cutoff']")
    # knob value should be 1.0 (fully open)
    assert abs(float(k.get("value")) - 1.0) < 0.001


def test_dspreset_resonance_zero_when_fx_inactive():
    root = parse_xml(make_preset(fx_active=False), trim_offsets={}, sample_rates={})
    k = root.find(".//labeled-knob[@label='Resonance']")
    assert float(k.get("value")) == 0.0


def test_dspreset_cutoff_from_opxy_when_fx_active():
    root = parse_xml(make_preset(fx_active=True), trim_offsets={}, sample_rates={})
    k = root.find(".//labeled-knob[@label='Cutoff']")
    # params[0]=19661 → not fully open and not zero
    val = float(k.get("value"))
    assert 0.0 < val < 1.0


def test_dspreset_cutoff_uses_table_translation():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    b = root.find(".//labeled-knob[@label='Cutoff']/binding")
    assert b.get("translation") == "table"
    assert b.get("parameter") == "FX_FILTER_FREQUENCY"


def test_dspreset_resonance_binding():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    b = root.find(".//labeled-knob[@label='Resonance']/binding")
    assert b.get("parameter") == "FX_FILTER_RESONANCE"


# ------------------------------------------------------------------ effects knobs

def test_dspreset_chorus_binding():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    b = root.find(".//labeled-knob[@label='Chorus']/binding")
    assert b.get("parameter") == "FX_WET_LEVEL"


def test_dspreset_reverb_binding():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    b = root.find(".//labeled-knob[@label='Reverb']/binding")
    assert b.get("parameter") == "FX_REVERB_WET_LEVEL"


def test_dspreset_chorus_default_zero():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    k = root.find(".//labeled-knob[@label='Chorus']")
    assert float(k.get("value")) == 0.0


def test_dspreset_reverb_default_zero():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    k = root.find(".//labeled-knob[@label='Reverb']")
    assert float(k.get("value")) == 0.0


# ------------------------------------------------------------------ effects chain

def test_dspreset_always_3_effects():
    for fx_active in (False, True):
        root = parse_xml(make_preset(fx_active=fx_active), trim_offsets={}, sample_rates={})
        effects = root.find("effects")
        assert effects is not None
        assert len(list(effects)) == 3


def test_dspreset_effects_order():
    root = parse_xml(make_preset(fx_active=False), trim_offsets={}, sample_rates={})
    types = [e.get("type") for e in root.find("effects")]
    assert types[0] in ("lowpass", "highpass")
    assert types[1] == "chorus"
    assert types[2] == "reverb"


def test_dspreset_filter_wide_open_when_fx_inactive():
    root = parse_xml(make_preset(fx_active=False), trim_offsets={}, sample_rates={})
    f = root.find("effects")[0]
    assert float(f.get("frequency")) == 20000.0


def test_dspreset_chorus_wetlevel_zero():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    chorus = root.find("effects")[1]
    assert float(chorus.get("mix")) == 0.0


def test_dspreset_reverb_wetlevel_zero():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    reverb = root.find("effects")[2]
    assert float(reverb.get("wetLevel")) == 0.0


# ------------------------------------------------------------------ filter modulator

def test_dspreset_filter_modulator_present_when_fx_active():
    root = parse_xml(make_preset(fx_active=True), trim_offsets={}, sample_rates={})
    assert root.find("modulators/envelope") is not None


def test_dspreset_no_modulator_when_fx_inactive():
    root = parse_xml(make_preset(fx_active=False), trim_offsets={}, sample_rates={})
    mods = root.find("modulators")
    assert mods is None or len(list(mods)) == 0


# ------------------------------------------------------------------ groups / samples

def test_dspreset_group_has_envelope_attrs():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    g = root.find("groups")
    assert g.get("attack") is not None
    assert g.get("release") is not None


def test_dspreset_sample_path():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    assert root.find(".//sample").get("path") == "Samples/sample_60.wav"


def test_dspreset_sample_key_range():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    s = root.find(".//sample")
    assert s.get("loNote") == "48"
    assert s.get("hiNote") == "72"
    assert s.get("rootNote") == "60"


def test_dspreset_loop_attrs():
    root = parse_xml(make_preset(loop=True), trim_offsets={}, sample_rates={})
    s = root.find(".//sample")
    assert s.get("loopEnabled") == "true"
    assert s.get("loopStart") == "100"
    assert s.get("loopEnd") == "5000"


def test_dspreset_no_loop_when_not_looping():
    root = parse_xml(make_preset(loop=False), trim_offsets={}, sample_rates={})
    assert root.find(".//sample").get("loopEnabled") is None


def test_dspreset_loop_adjusted_for_trim():
    root = parse_xml(make_preset(loop=True), trim_offsets={"sample_60.wav": 10}, sample_rates={})
    s = root.find(".//sample")
    assert s.get("loopStart") == "90"
    assert s.get("loopEnd") == "4990"


# ------------------------------------------------------------------ misc

def test_dspreset_mono_sets_poly_limit():
    preset = make_preset()
    preset.playmode = "mono"
    root = parse_xml(preset, trim_offsets={}, sample_rates={})
    assert root.find(".//group").get("polyLimit") == "1"


def test_dspreset_poly_no_poly_limit():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    assert root.find(".//group").get("polyLimit") is None


def test_dspreset_veltrack_emitted():
    preset = make_preset()
    preset.velocity_sensitivity = 60.0
    root = parse_xml(preset, trim_offsets={}, sample_rates={})
    assert root.find("groups").get("ampVelTrack") is not None


def test_dspreset_veltrack_100_omitted():
    root = parse_xml(make_preset(), trim_offsets={}, sample_rates={})
    assert root.find("groups").get("ampVelTrack") is None


# ------------------------------------------------------------------ zip

def test_build_zip_contains_dspreset():
    xml = generate_dspreset(make_preset(), trim_offsets={}, sample_rates={})
    z = build_dspreset_zip(make_preset(), xml, {"sample_60.wav": b"RIFF...."})
    with zipfile.ZipFile(io.BytesIO(z)) as zf:
        assert "TestPreset.dspreset" in zf.namelist()


def test_build_zip_wav_in_samples_dir():
    xml = generate_dspreset(make_preset(), trim_offsets={}, sample_rates={})
    z = build_dspreset_zip(make_preset(), xml, {"sample_60.wav": b"RIFF...."})
    with zipfile.ZipFile(io.BytesIO(z)) as zf:
        assert "Samples/sample_60.wav" in zf.namelist()
