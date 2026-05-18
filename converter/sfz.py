import io
import zipfile

from .envelope import convert_amp_envelope, convert_filter_envelope
from .patch import Preset

CUTOFF_MIN_HZ = 20.0
CUTOFF_MAX_HZ = 20000.0

# OP-XY fx.type → SFZ fil_type
_FX_TYPE_TO_FIL_TYPE = {
    "svf": "lpf_2p",      # State Variable Filter (2-pole LP)
    "ladder": "lpf_4p",   # Moog ladder (4-pole LP)
    "z_lowpass": "lpf_1p", # Z-plane lowpass (1-pole)
    "z_hipass": "hpf_2p", # Z-plane highpass (2-pole)
}


def _opxy_to_cutoff_hz(value: int) -> float:
    return CUTOFF_MIN_HZ * (CUTOFF_MAX_HZ / CUTOFF_MIN_HZ) ** (value / 32767.0)


def _opxy_to_resonance_db(value: int) -> float:
    return (value / 32767.0) * 40.0


def generate_sfz(
    preset: Preset,
    trim_offsets: dict[str, int],
    sample_rates: dict[str, int],
) -> str:
    lines: list[str] = []

    lines.append("<global>")

    if preset.engine_volume != 0.0:
        lines.append(f"volume={preset.engine_volume:.2f}")

    if preset.velocity_sensitivity != 100.0:
        lines.append(f"amp_veltrack={preset.velocity_sensitivity:.1f}")

    if preset.transpose != 0:
        lines.append(f"transpose={preset.transpose}")

    if preset.playmode in ("mono", "legato"):
        lines.append("polyphony=1")

    amp = convert_amp_envelope(preset.amp_envelope)
    for k, v in amp.items():
        lines.append(f"{k}={v}")

    if preset.fx_active and len(preset.fx_params) >= 3:
        cutoff = _opxy_to_cutoff_hz(preset.fx_params[0])
        resonance = _opxy_to_resonance_db(preset.fx_params[2])
        fil_type = _FX_TYPE_TO_FIL_TYPE.get(preset.fx_type, "lpf_2p")
        lines.append(f"cutoff={cutoff:.1f}")
        lines.append(f"resonance={resonance:.1f}")
        lines.append(f"fil_type={fil_type}")
        fil = convert_filter_envelope(preset.filter_envelope)
        for k, v in fil.items():
            lines.append(f"{k}={v}")
        lines.append("fileg_depth=3600")

    lines.append("")

    for region in preset.regions:
        trim = trim_offsets.get(region.sample, 0)
        sr = sample_rates.get(region.sample, 22050)
        lines.append("<region>")
        lines.append(f"sample={preset.name}/{region.sample}")
        lines.append(f"pitch_keycenter={region.pitch_keycenter}")
        lines.append(f"lokey={region.lokey}")
        lines.append(f"hikey={region.hikey}")
        if region.tune != 0:
            lines.append(f"tune={region.tune}")
        lines.append(f"volume={region.volume}")
        lines.append(f"loop_mode={region.loop_mode}")
        if region.loop_start is not None:
            lines.append(f"loop_start={max(0, region.loop_start - trim)}")
        if region.loop_end is not None:
            lines.append(f"loop_end={max(0, region.loop_end - trim)}")
        if region.loop_crossfade > 0:
            lines.append(f"loop_crossfade={region.loop_crossfade / sr:.4f}")
        if region.offset and region.offset - trim > 0:
            lines.append(f"offset={region.offset - trim}")
        if region.end is not None:
            lines.append(f"end={max(0, region.end - trim)}")
        if region.direction == "reverse":
            lines.append("direction=reverse")
        lines.append("")

    return "\n".join(lines)


def build_zip(preset: Preset, sfz_text: str, wav_map: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{preset.name}.sfz", sfz_text)
        for filename, wav_bytes in wav_map.items():
            zf.writestr(f"{preset.name}/{filename}", wav_bytes)
    return buf.getvalue()
