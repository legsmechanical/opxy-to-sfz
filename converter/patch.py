import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Region:
    sample: str
    pitch_keycenter: int
    lokey: int
    hikey: int
    tune: int
    volume: float
    loop_mode: str
    loop_start: Optional[int]
    loop_end: Optional[int]
    loop_crossfade: int
    offset: int
    end: Optional[int]
    direction: str


@dataclass
class Preset:
    name: str
    regions: list[Region]
    amp_envelope: dict
    filter_envelope: dict
    fx_active: bool
    fx_params: list[int]
    fx_type: str = "svf"
    engine_volume: float = 0.0   # dB, 0.0 = unity (no change)
    velocity_sensitivity: float = 100.0  # 0–100, maps to amp_veltrack
    transpose: int = 0           # semitones
    playmode: str = "poly"       # "poly", "mono", "legato"


def _engine_volume_to_db(value: int) -> float:
    """Convert OP-XY engine.volume (0–32767) to dB. 32767 = 0 dB (unity)."""
    return 20.0 * math.log10(max(1, value) / 32767.0)


def parse_patch(patch: dict) -> Preset:
    name = patch.get("name", "preset")
    envelope = patch.get("envelope", {})
    fx = patch.get("fx", {})
    engine = patch.get("engine", {})
    regions = []

    for r in patch.get("regions", []):
        if "loop.enabled" in r:
            loop_enabled = bool(r["loop.enabled"])
        else:
            loop_enabled = int(r.get("loop.start", 0)) > 0

        loop_on_release = r.get("loop.onrelease", True)
        if not loop_enabled:
            loop_mode = "no_loop"
        elif loop_on_release:
            loop_mode = "loop_continuous"
        else:
            loop_mode = "loop_sustain"
        regions.append(
            Region(
                sample=r["sample"],
                pitch_keycenter=r.get("pitch.keycenter", 60),
                lokey=r.get("lokey", 0),
                hikey=r.get("hikey", 127),
                tune=r.get("tune", 0),
                volume=float(r.get("gain", 0.0)),
                loop_mode=loop_mode,
                loop_start=r.get("loop.start") if loop_enabled else None,
                loop_end=r.get("loop.end") if loop_enabled else None,
                loop_crossfade=int(r.get("loop.crossfade", 0)) if loop_enabled else 0,
                offset=r.get("sample.start", 0),
                end=r.get("sample.end"),
                direction="reverse" if r.get("reverse", False) else "forward",
            )
        )

    raw_vol = engine.get("volume")
    engine_volume = _engine_volume_to_db(raw_vol) if raw_vol is not None else 0.0

    raw_vel = engine.get("velocity.sensitivity")
    velocity_sensitivity = (raw_vel / 32767.0) * 100.0 if raw_vel is not None else 100.0

    octave = int(patch.get("octave", 0))
    engine_transpose = int(engine.get("transpose", 0))
    transpose = engine_transpose + octave * 12

    playmode = engine.get("playmode", "poly")

    return Preset(
        name=name,
        regions=regions,
        amp_envelope=envelope.get("amp", {}),
        filter_envelope=envelope.get("filter", {}),
        fx_active=bool(fx.get("active", False)),
        fx_params=list(fx.get("params", [])),
        fx_type=fx.get("type", "svf"),
        engine_volume=engine_volume,
        velocity_sensitivity=velocity_sensitivity,
        transpose=transpose,
        playmode=playmode,
    )
