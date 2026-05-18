import io
import wave
import numpy as np


def make_wav(samples: np.ndarray, sample_rate: int = 22050, n_channels: int = 1) -> bytes:
    """Encode a float32 numpy array (-1..1) into 16-bit PCM WAV bytes."""
    if samples.ndim == 1 and n_channels > 1:
        samples = np.stack([samples] * n_channels, axis=1)
    raw = (samples * 32767).clip(-32767, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        ch = samples.shape[1] if samples.ndim > 1 else 1
        wf.setnchannels(ch)
        wf.setframerate(sample_rate)
        wf.setsampwidth(2)
        wf.writeframes(raw.tobytes())
    return buf.getvalue()
