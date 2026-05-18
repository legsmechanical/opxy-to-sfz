import io
import math
import zipfile
import xml.etree.ElementTree as ET
from xml.dom import minidom

from .envelope import convert_amp_envelope, convert_filter_envelope
from .patch import Preset
from .sfz import _FX_TYPE_TO_FIL_TYPE

CUTOFF_MIN_HZ = 20.0
CUTOFF_MAX_HZ = 20000.0

_CUTOFF_TRANSLATION_TABLE = (
    "0,20;0.1,45;0.2,110;0.3,280;0.4,700;0.5,1700;0.6,3500;0.7,7000;0.85,14000;1.0001,20000"
)

_SFZ_TO_DS_FILTER = {
    "lpf_2p": "lowpass",
    "lpf_4p": "lowpass",
    "lpf_1p": "lowpass",
    "hpf_2p": "highpass",
}

# Fixed positions in the <effects> chain
_FX_FILTER = 0
_FX_CHORUS = 1
_FX_REVERB = 2

_BLUE  = "FF4FC3F7"
_RED   = "FFEF9A9A"
_GREEN = "FF80CBC4"


def _opxy_to_cutoff_hz(value: int) -> float:
    return CUTOFF_MIN_HZ * (CUTOFF_MAX_HZ / CUTOFF_MIN_HZ) ** (value / 32767.0)


def _cutoff_hz_to_knob(hz: float) -> float:
    return math.log(hz / CUTOFF_MIN_HZ) / math.log(CUTOFF_MAX_HZ / CUTOFF_MIN_HZ)


def _opxy_to_resonance_db(value: int) -> float:
    return (value / 32767.0) * 40.0


def _pretty(elem: ET.Element) -> str:
    raw = ET.tostring(elem, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding=None)


def generate_dspreset(
    preset: Preset,
    trim_offsets: dict[str, int],
    sample_rates: dict[str, int],
) -> str:
    amp = convert_amp_envelope(preset.amp_envelope)
    attack_s   = amp["ampeg_attack"]
    decay_s    = amp["ampeg_decay"]
    sustain_fr = amp["ampeg_sustain"] / 100.0
    release_s  = amp["ampeg_release"]

    has_filter = preset.fx_active and len(preset.fx_params) >= 2
    if has_filter:
        cutoff_hz    = _opxy_to_cutoff_hz(preset.fx_params[0])
        resonance_db = _opxy_to_resonance_db(preset.fx_params[1])
        ds_fil_type  = _SFZ_TO_DS_FILTER.get(
            _FX_TYPE_TO_FIL_TYPE.get(preset.fx_type, "lpf_2p"), "lowpass"
        )
    else:
        cutoff_hz    = CUTOFF_MAX_HZ
        resonance_db = 0.0
        ds_fil_type  = "lowpass"

    root = ET.Element("DecentSampler", pluginVersion="1")

    # ------------------------------------------------------------------ UI --
    # Always 8 knobs: 4 amp ADSR · 2 filter · chorus · reverb
    knob_w = 90
    ui = ET.SubElement(root, "ui", width=str(8 * knob_w), height="130", bgColor="FF1A1A2E")
    tab = ET.SubElement(ui, "tab", name="main")

    def add_knob(x, label, lo, hi, val, color, bindings):
        k = ET.SubElement(
            tab, "labeled-knob",
            x=str(x), y="15", label=label,
            type="float",
            minValue=str(lo), maxValue=str(hi),
            value=str(round(val, 5)),
            width="80", height="100", textSize="14",
            trackForegroundColor=color, textColor="FFFFFFFF",
        )
        for b in bindings:
            ET.SubElement(k, "binding", **b)

    x = 5
    add_knob(x, "Attack",  0, 30, attack_s,   _BLUE,
             [{"type": "amp", "level": "instrument", "parameter": "ENV_ATTACK"}])
    x += knob_w
    add_knob(x, "Decay",   0, 30, decay_s,    _BLUE,
             [{"type": "amp", "level": "instrument", "parameter": "ENV_DECAY"}])
    x += knob_w
    add_knob(x, "Sustain", 0, 1,  sustain_fr, _BLUE,
             [{"type": "amp", "level": "instrument", "parameter": "ENV_SUSTAIN"}])
    x += knob_w
    add_knob(x, "Release", 0, 20, release_s,  _BLUE,
             [{"type": "amp", "level": "instrument", "parameter": "ENV_RELEASE"}])
    x += knob_w
    add_knob(x, "Cutoff", 0, 1, _cutoff_hz_to_knob(cutoff_hz), _RED,
             [{"type": "effect", "level": "instrument",
               "position": str(_FX_FILTER),
               "parameter": "FX_FILTER_FREQUENCY",
               "translation": "table",
               "translationTable": _CUTOFF_TRANSLATION_TABLE}])
    x += knob_w
    add_knob(x, "Resonance", 0, 40, resonance_db, _RED,
             [{"type": "effect", "level": "instrument",
               "position": str(_FX_FILTER),
               "parameter": "FX_FILTER_RESONANCE"}])
    x += knob_w
    add_knob(x, "Chorus", 0, 1, 0.0, _GREEN,
             [{"type": "effect", "level": "instrument",
               "position": str(_FX_CHORUS),
               "parameter": "FX_WET_LEVEL"}])
    x += knob_w
    add_knob(x, "Reverb", 0, 1, 0.0, _GREEN,
             [{"type": "effect", "level": "instrument",
               "position": str(_FX_REVERB),
               "parameter": "FX_REVERB_WET_LEVEL"}])

    # --------------------------------------------------------------- Groups --
    fil = convert_filter_envelope(preset.filter_envelope)
    groups_elem = ET.SubElement(
        root, "groups",
        attack=str(attack_s), decay=str(decay_s),
        sustain=str(sustain_fr), release=str(release_s),
    )
    if preset.velocity_sensitivity != 100.0:
        groups_elem.set("ampVelTrack", str(preset.velocity_sensitivity / 100.0))
    if preset.transpose != 0:
        groups_elem.set("groupTuning", str(preset.transpose))

    group = ET.SubElement(groups_elem, "group")
    if preset.playmode in ("mono", "legato"):
        group.set("polyLimit", "1")

    for region in preset.regions:
        trim = trim_offsets.get(region.sample, 0)
        attrs: dict[str, str] = {
            "path": f"Samples/{region.sample}",
            "rootNote": str(region.pitch_keycenter),
            "loNote": str(region.lokey),
            "hiNote": str(region.hikey),
            "loVel": "0", "hiVel": "127",
        }
        if region.volume != 0.0:
            attrs["volume"] = f"{region.volume:.1f}dB"
        if region.tune != 0:
            attrs["tuning"] = str(region.tune / 100.0)
        if region.loop_mode != "no_loop":
            attrs["loopEnabled"] = "true"
            if region.loop_start is not None:
                attrs["loopStart"] = str(max(0, region.loop_start - trim))
            if region.loop_end is not None:
                attrs["loopEnd"] = str(max(0, region.loop_end - trim))
            if region.loop_crossfade > 0:
                attrs["loopCrossfade"] = str(region.loop_crossfade)
        if region.offset and region.offset - trim > 0:
            attrs["start"] = str(region.offset - trim)
        if region.end is not None:
            attrs["end"] = str(max(0, region.end - trim))
        ET.SubElement(group, "sample", **attrs)

    # --------------------------------------------------------------- Effects --
    # Always: filter (pos 0) → chorus (pos 1) → reverb (pos 2)
    effects = ET.SubElement(root, "effects")
    ET.SubElement(effects, "effect",
                  type=ds_fil_type,
                  frequency=str(round(cutoff_hz, 1)),
                  resonance=str(round(resonance_db / 40.0, 4)))
    ET.SubElement(effects, "effect",
                  type="chorus", rate="0.5", depth="0.3", mix="0.0")
    ET.SubElement(effects, "effect",
                  type="reverb", roomSize="0.5", damping="0.5", wetLevel="0.0")

    # ----------------------------------------- Filter envelope (baked, optional) --
    if has_filter:
        modulators = ET.SubElement(root, "modulators")
        env_mod = ET.SubElement(
            modulators, "envelope",
            attack=str(fil["fileg_attack"]),
            decay=str(fil["fileg_decay"]),
            sustain=str(fil["fileg_sustain"] / 100.0),
            release=str(fil["fileg_release"]),
            scope="voice",
        )
        depth_hz   = cutoff_hz * (2 ** (3600 / 1200) - 1)
        target_hz  = min(CUTOFF_MAX_HZ, cutoff_hz + depth_hz)
        ET.SubElement(env_mod, "binding",
                      type="effect", level="instrument",
                      position=str(_FX_FILTER),
                      parameter="FX_FILTER_FREQUENCY",
                      translation="linear",
                      translationOutputMin=str(round(cutoff_hz, 1)),
                      translationOutputMax=str(round(target_hz, 1)))

    return _pretty(root)


def build_dspreset_zip(preset: Preset, dspreset_xml: str, wav_map: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{preset.name}.dspreset", dspreset_xml)
        for filename, wav_bytes in wav_map.items():
            zf.writestr(f"Samples/{filename}", wav_bytes)
    return buf.getvalue()
