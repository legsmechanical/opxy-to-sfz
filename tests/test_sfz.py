import io
import zipfile
import pytest
from converter.patch import Preset, Region
from converter.sfz import generate_sfz, build_zip


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


def test_sfz_contains_global():
    sfz = generate_sfz(make_preset(), trim_offsets={}, sample_rates={})
    assert "<global>" in sfz


def test_sfz_contains_amp_envelope():
    sfz = generate_sfz(make_preset(), trim_offsets={}, sample_rates={})
    assert "ampeg_attack=" in sfz
    assert "ampeg_decay=" in sfz
    assert "ampeg_sustain=" in sfz
    assert "ampeg_release=" in sfz


def test_sfz_contains_filter_envelope():
    sfz = generate_sfz(make_preset(fx_active=True), trim_offsets={}, sample_rates={})
    assert "fileg_attack=" in sfz
    assert "fileg_release=" in sfz
    assert "fileg_depth=3600" in sfz
    assert "fil_type=lpf_2p" in sfz


def test_sfz_no_filter_envelope_when_fx_inactive():
    sfz = generate_sfz(make_preset(fx_active=False), trim_offsets={}, sample_rates={})
    assert "fileg_attack=" not in sfz


def test_sfz_no_cutoff_when_fx_inactive():
    sfz = generate_sfz(make_preset(fx_active=False), trim_offsets={}, sample_rates={})
    assert "cutoff=" not in sfz


def test_sfz_cutoff_when_fx_active():
    sfz = generate_sfz(make_preset(fx_active=True), trim_offsets={}, sample_rates={})
    assert "cutoff=" in sfz
    assert "resonance=" in sfz


def test_sfz_region_opcodes():
    sfz = generate_sfz(make_preset(), trim_offsets={}, sample_rates={})
    assert "<region>" in sfz
    assert "sample=TestPreset/sample_60.wav" in sfz
    assert "pitch_keycenter=60" in sfz
    assert "lokey=48" in sfz
    assert "hikey=72" in sfz
    assert "volume=-3.0" in sfz
    assert "loop_mode=no_loop" in sfz


def test_sfz_loop_opcodes():
    sfz = generate_sfz(make_preset(loop=True), trim_offsets={}, sample_rates={})
    assert "loop_mode=loop_continuous" in sfz
    assert "loop_start=100" in sfz
    assert "loop_end=5000" in sfz


def test_sfz_loop_points_adjusted_for_trim():
    sfz = generate_sfz(
        make_preset(loop=True),
        trim_offsets={"sample_60.wav": 10},
        sample_rates={},
    )
    assert "loop_start=90" in sfz
    assert "loop_end=4990" in sfz


def test_sfz_sample_path_uses_subdirectory():
    sfz = generate_sfz(make_preset(name="MyPreset"), trim_offsets={}, sample_rates={})
    assert "sample=MyPreset/sample_60.wav" in sfz


def test_build_zip_contains_sfz_and_wav():
    wav_map = {"sample_60.wav": b"RIFF...."}
    zip_bytes = build_zip(make_preset(), sfz_text="<global>\n", wav_map=wav_map)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
    assert "TestPreset.sfz" in names
    assert "TestPreset/sample_60.wav" in names


def test_build_zip_sfz_content():
    sfz_text = "<global>\nampeg_attack=0.0\n"
    zip_bytes = build_zip(make_preset(), sfz_text=sfz_text, wav_map={})
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        content = zf.read("TestPreset.sfz").decode()
    assert content == sfz_text


def test_sfz_end_adjusted_for_trim():
    sfz = generate_sfz(make_preset(), trim_offsets={"sample_60.wav": 10}, sample_rates={})
    assert "end=5990" in sfz  # 6000 - 10


def test_sfz_end_clamped_to_zero():
    sfz = generate_sfz(make_preset(), trim_offsets={"sample_60.wav": 9999}, sample_rates={})
    assert "end=0" in sfz


def test_sfz_reverse_direction():
    preset = make_preset()
    preset.regions[0].direction = "reverse"
    sfz = generate_sfz(preset, trim_offsets={}, sample_rates={})
    assert "direction=reverse" in sfz


def test_sfz_tune_zero_omitted():
    sfz = generate_sfz(make_preset(), trim_offsets={}, sample_rates={})
    assert "tune=" not in sfz


def test_sfz_loop_crossfade_emitted():
    sfz = generate_sfz(
        make_preset(loop=True, loop_crossfade=441),
        trim_offsets={},
        sample_rates={"sample_60.wav": 22050},
    )
    assert "loop_crossfade=0.0200" in sfz


def test_sfz_loop_crossfade_omitted_when_zero():
    sfz = generate_sfz(make_preset(loop=True, loop_crossfade=0), trim_offsets={}, sample_rates={})
    assert "loop_crossfade=" not in sfz


def test_sfz_loop_sustain_mode():
    sfz = generate_sfz(make_preset(loop=True, loop_sustain=True), trim_offsets={}, sample_rates={})
    assert "loop_mode=loop_sustain" in sfz


def test_sfz_global_volume_fixed():
    sfz = generate_sfz(make_preset(), trim_offsets={}, sample_rates={})
    global_section = sfz.split("<region>")[0]
    assert "volume=-8" in global_section


def test_sfz_engine_volume_not_emitted():
    # engine_volume is parsed but not used — global volume=-8 is always fixed
    preset = make_preset()
    preset.engine_volume = -5.04
    sfz = generate_sfz(preset, trim_offsets={}, sample_rates={})
    global_section = sfz.split("<region>")[0]
    assert "volume=-8" in global_section
    assert global_section.count("volume=") == 1


def test_sfz_amp_veltrack_emitted():
    preset = make_preset()
    preset.velocity_sensitivity = 60.0
    sfz = generate_sfz(preset, trim_offsets={}, sample_rates={})
    assert "amp_veltrack=60.0" in sfz


def test_sfz_amp_veltrack_100_omitted():
    sfz = generate_sfz(make_preset(), trim_offsets={}, sample_rates={})
    assert "amp_veltrack=" not in sfz


def test_sfz_transpose_emitted():
    preset = make_preset()
    preset.transpose = 3
    sfz = generate_sfz(preset, trim_offsets={}, sample_rates={})
    assert "transpose=3" in sfz


def test_sfz_transpose_zero_omitted():
    sfz = generate_sfz(make_preset(), trim_offsets={}, sample_rates={})
    assert "transpose=" not in sfz


def test_sfz_polyphony_mono():
    preset = make_preset()
    preset.playmode = "mono"
    sfz = generate_sfz(preset, trim_offsets={}, sample_rates={})
    assert "polyphony=1" in sfz


def test_sfz_polyphony_poly_omitted():
    sfz = generate_sfz(make_preset(), trim_offsets={}, sample_rates={})
    assert "polyphony=" not in sfz


def test_sfz_fil_type_ladder():
    preset = make_preset(fx_active=True)
    preset.fx_type = "ladder"
    sfz = generate_sfz(preset, trim_offsets={}, sample_rates={})
    assert "fil_type=lpf_4p" in sfz


def test_sfz_fil_type_z_hipass():
    preset = make_preset(fx_active=True)
    preset.fx_type = "z_hipass"
    sfz = generate_sfz(preset, trim_offsets={}, sample_rates={})
    assert "fil_type=hpf_2p" in sfz


def test_sfz_fil_type_z_lowpass():
    preset = make_preset(fx_active=True)
    preset.fx_type = "z_lowpass"
    sfz = generate_sfz(preset, trim_offsets={}, sample_rates={})
    assert "fil_type=lpf_1p" in sfz


def test_sfz_fil_type_svf_default():
    preset = make_preset(fx_active=True)
    preset.fx_type = "svf"
    sfz = generate_sfz(preset, trim_offsets={}, sample_rates={})
    assert "fil_type=lpf_2p" in sfz
