import math

ATTACK_MIN_SECONDS = 0.01037
ATTACK_MAX_SECONDS = 365.0
ATTACK_CURVE_B = 10.4687
RELEASE_MIN_SECONDS = 2.405
RELEASE_MAX_SECONDS = 16.325
RELEASE_CURVE_P = 0.9572


def opxy_to_attack_seconds(value: int) -> float:
    """Inverts scale_attack_seconds from sf2-to-opxy. Used for attack and decay."""
    if value <= 0:
        return 0.0
    x = value / 32767.0
    seconds = ATTACK_MIN_SECONDS * math.exp(x * ATTACK_CURVE_B)
    return min(seconds, ATTACK_MAX_SECONDS)


def opxy_to_release_seconds(value: int) -> float:
    """Inverts scale_release_seconds from sf2-to-opxy."""
    if value >= 32767:
        return RELEASE_MIN_SECONDS
    if value <= 0:
        return RELEASE_MAX_SECONDS
    x = value / 32767.0
    normalized = (1.0 - x) ** RELEASE_CURVE_P
    return RELEASE_MIN_SECONDS + normalized * (RELEASE_MAX_SECONDS - RELEASE_MIN_SECONDS)


def opxy_sustain_to_sfz_percent(value: int) -> float:
    """Converts OP-XY linear amplitude 0–32767 to SFZ sustain percent 0–100."""
    clamped = max(0, min(32767, value))
    return (clamped / 32767.0) * 100.0


def convert_amp_envelope(amp: dict) -> dict:
    """Maps OP-XY amp envelope dict to SFZ ampeg_* opcodes."""
    return {
        "ampeg_attack": round(opxy_to_attack_seconds(amp.get("attack", 0)), 4),
        "ampeg_decay": round(opxy_to_attack_seconds(amp.get("decay", 0)), 4),
        "ampeg_sustain": round(opxy_sustain_to_sfz_percent(amp.get("sustain", 32767)), 2),
        "ampeg_release": round(opxy_to_release_seconds(amp.get("release", 32767)), 4),
    }


def convert_filter_envelope(fil: dict) -> dict:
    """Maps OP-XY filter envelope dict to SFZ fileg_* opcodes."""
    return {
        "fileg_attack": round(opxy_to_attack_seconds(fil.get("attack", 0)), 4),
        "fileg_decay": round(opxy_to_attack_seconds(fil.get("decay", 0)), 4),
        "fileg_sustain": round(opxy_sustain_to_sfz_percent(fil.get("sustain", 32767)), 2),
        "fileg_release": round(opxy_to_release_seconds(fil.get("release", 32767)), 4),
    }
