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


def parse_patch(patch: dict) -> Preset:
    name = patch.get("name", "preset")
    envelope = patch.get("envelope", {})
    fx = patch.get("fx", {})
    regions = []

    for r in patch.get("regions", []):
        loop_enabled = r.get("loop.enabled", False)
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

    return Preset(
        name=name,
        regions=regions,
        amp_envelope=envelope.get("amp", {}),
        filter_envelope=envelope.get("filter", {}),
        fx_active=bool(fx.get("active", False)),
        fx_params=list(fx.get("params", [])),
    )
