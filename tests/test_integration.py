import io
import json
import zipfile

import numpy as np
import pytest
from fastapi.testclient import TestClient

from tests.helpers import make_wav


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def preset_files(name="TestPreset", with_silence=True):
    patch = {
        "version": 4,
        "type": "multisampler",
        "name": name,
        "envelope": {
            "amp": {"attack": 0, "decay": 20295, "release": 16383, "sustain": 14989},
            "filter": {"attack": 0, "decay": 16895, "release": 19968, "sustain": 16896},
        },
        "fx": {"type": "svf", "active": False, "params": [0, 0, 0, 0, 0, 0, 0, 0]},
        "regions": [
            {
                "sample": "sample_60.wav",
                "pitch.keycenter": 60,
                "lokey": 48,
                "hikey": 72,
                "tune": 0,
                "gain": 0,
                "loop.enabled": False,
                "sample.start": 0,
                "sample.end": 120,
                "reverse": False,
            }
        ],
    }
    samples = np.zeros(120, dtype=np.float32)
    if with_silence:
        samples[10:110] = 0.5  # 10 frames silence at start and end
    else:
        samples[:] = 0.5
    return {"patch.json": json.dumps(patch).encode(), "sample_60.wav": make_wav(samples)}


def post_preset(client, files: dict):
    return client.post(
        "/convert",
        files=[
            ("files", (name, data, "application/octet-stream"))
            for name, data in files.items()
        ],
    )


def test_convert_returns_200(client):
    response = post_preset(client, preset_files())
    assert response.status_code == 200


def test_convert_returns_zip(client):
    response = post_preset(client, preset_files())
    assert response.headers["content-type"] == "application/zip"


def test_convert_zip_contains_dspreset(client):
    response = post_preset(client, preset_files())
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        assert "TestPreset.dspreset" in zf.namelist()


def test_convert_zip_contains_wav_in_samples_directory(client):
    response = post_preset(client, preset_files())
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        assert "Samples/sample_60.wav" in zf.namelist()


def test_convert_dspreset_has_envelope_knobs(client):
    import xml.etree.ElementTree as ET
    response = post_preset(client, preset_files())
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        xml = zf.read("TestPreset.dspreset").decode()
    root = ET.fromstring(xml.strip())
    labels = {k.get("label") for k in root.findall(".//labeled-knob")}
    assert "Attack" in labels
    assert "Sustain" in labels


def test_convert_dspreset_has_sample_mapping(client):
    import xml.etree.ElementTree as ET
    response = post_preset(client, preset_files())
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        xml = zf.read("TestPreset.dspreset").decode()
    root = ET.fromstring(xml.strip())
    sample = root.find(".//sample")
    assert sample.get("rootNote") == "60"
    assert sample.get("loNote") == "48"
    assert sample.get("hiNote") == "72"


def test_silence_is_trimmed(client):
    response = post_preset(client, preset_files(with_silence=True))
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        wav_data = zf.read("Samples/sample_60.wav")
    import wave
    with wave.open(io.BytesIO(wav_data)) as wf:
        n_frames = wf.getnframes()
    assert n_frames == 100  # 10 frames silence trimmed from each end


def test_missing_patch_json_returns_400(client):
    response = client.post(
        "/convert",
        files=[("files", ("sample_60.wav", b"RIFF....", "application/octet-stream"))],
    )
    assert response.status_code == 400


def test_convert_zip_filename_header(client):
    response = post_preset(client, preset_files(name="MyPad"))
    disposition = response.headers.get("content-disposition", "")
    assert "MyPad.zip" in disposition
