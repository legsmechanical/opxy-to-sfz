import io
import wave

import numpy as np

SILENCE_THRESHOLD_DBFS = -60.0


def load_wav(data: bytes) -> tuple[np.ndarray, int, int]:
    """
    Returns (samples, sample_rate, sample_width).
    samples shape: (n_frames,) for mono, (n_frames, n_channels) for stereo.
    samples dtype: float32, range -1..1.
    """
    with wave.open(io.BytesIO(data)) as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())

    if sample_width == 2:
        dtype = np.int16
    elif sample_width == 3:
        # Promote 24-bit to 32-bit
        padded = bytearray()
        for i in range(0, len(raw), 3):
            padded += b"\x00" + raw[i : i + 3]
        raw = bytes(padded)
        dtype = np.int32
    else:
        raise ValueError(f"Unsupported sample width: {sample_width} bytes")

    samples = np.frombuffer(raw, dtype=dtype).astype(np.float32)
    samples /= float(np.iinfo(dtype).max)

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels)

    return samples, sample_rate, sample_width


def _encode_wav(samples: np.ndarray, sample_rate: int, sample_width: int) -> bytes:
    if sample_width not in (2, 3):
        raise ValueError(f"Unsupported sample width for encoding: {sample_width}")
    # Always encode to 16-bit for simplicity
    max_val = 32767
    raw = (samples * max_val).clip(-max_val, max_val).astype(np.int16).tobytes()
    n_channels = samples.shape[1] if samples.ndim > 1 else 1
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setframerate(sample_rate)
        wf.setsampwidth(2)
        wf.writeframes(raw)
    return buf.getvalue()


def _find_trim_points(
    samples: np.ndarray, threshold_dbfs: float = SILENCE_THRESHOLD_DBFS
) -> tuple[int, int]:
    threshold = 10 ** (threshold_dbfs / 20.0)
    amplitude = np.abs(samples).max(axis=1) if samples.ndim > 1 else np.abs(samples)
    nonsilent = np.where(amplitude >= threshold)[0]
    if len(nonsilent) == 0:
        return 0, len(samples)
    return int(nonsilent[0]), int(nonsilent[-1]) + 1


def trim_silence(wav_data: bytes) -> tuple[bytes, int]:
    """
    Trim leading and trailing silence from a WAV file.
    Returns (trimmed_wav_bytes, leading_frames_trimmed).
    """
    samples, sample_rate, sample_width = load_wav(wav_data)
    start, end = _find_trim_points(samples)
    return _encode_wav(samples[start:end], sample_rate, sample_width), start
