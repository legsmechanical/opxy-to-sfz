import io
import zipfile

from .envelope import convert_amp_envelope, convert_filter_envelope
from .patch import Preset

CUTOFF_MIN_HZ = 20.0
CUTOFF_MAX_HZ = 20000.0


# Best-effort mapping: OP-XY SVF params[0] → Hz (log scale 20–20000 Hz),
# params[2] → resonance dB (linear 0–40 dB). OP-XY param ranges are 0–32767.
def _opxy_to_cutoff_hz(value: int) -> float:
    return CUTOFF_MIN_HZ * (CUTOFF_MAX_HZ / CUTOFF_MIN_HZ) ** (value / 32767.0)


def _opxy_to_resonance_db(value: int) -> float:
    return (value / 32767.0) * 40.0


def generate_sfz(preset: Preset, trim_offsets: dict[str, int]) -> str:
    """
    Generate SFZ text for a preset.
    trim_offsets maps sample filename -> number of leading frames trimmed,
    so loop/offset indices can be adjusted.
    """
    lines: list[str] = []

    lines.append("<global>")
    amp = convert_amp_envelope(preset.amp_envelope)
    for k, v in amp.items():
        lines.append(f"{k}={v}")
    fil = convert_filter_envelope(preset.filter_envelope)
    for k, v in fil.items():
        lines.append(f"{k}={v}")

    if preset.fx_active and len(preset.fx_params) >= 3:
        cutoff = _opxy_to_cutoff_hz(preset.fx_params[0])
        resonance = _opxy_to_resonance_db(preset.fx_params[2])
        lines.append(f"cutoff={cutoff:.1f}")
        lines.append(f"resonance={resonance:.1f}")

    lines.append("")

    for region in preset.regions:
        trim = trim_offsets.get(region.sample, 0)
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
        if region.offset and region.offset - trim > 0:
            lines.append(f"offset={region.offset - trim}")
        if region.end is not None:
            lines.append(f"end={max(0, region.end - trim)}")
        if region.direction == "reverse":
            lines.append("direction=reverse")
        lines.append("")

    return "\n".join(lines)


def build_zip(preset: Preset, sfz_text: str, wav_map: dict[str, bytes]) -> bytes:
    """
    Package SFZ text + WAV bytes into a ZIP.
    Layout:
      PresetName.sfz
      PresetName/sample_60.wav
      ...
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{preset.name}.sfz", sfz_text)
        for filename, wav_bytes in wav_map.items():
            zf.writestr(f"{preset.name}/{filename}", wav_bytes)
    return buf.getvalue()
