import json
import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from converter.audio import trim_silence
from converter.patch import parse_patch
from converter.sfz import build_zip, generate_sfz

logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/convert")
async def convert(files: list[UploadFile] = File(...)):
    patch_file = next((f for f in files if f.filename == "patch.json"), None)
    if patch_file is None:
        raise HTTPException(status_code=400, detail="No patch.json found in uploaded files")

    patch_json = json.loads(await patch_file.read())
    preset = parse_patch(patch_json)

    wav_files = {f.filename: await f.read() for f in files if f.filename.endswith(".wav")}

    trimmed_wavs: dict[str, bytes] = {}
    trim_offsets: dict[str, int] = {}
    skipped: set[str] = set()

    for region in preset.regions:
        filename = region.sample
        if filename not in wav_files:
            logger.warning("Missing sample %s in preset %s", filename, preset.name)
            skipped.add(filename)
            continue
        try:
            trimmed, leading = trim_silence(wav_files[filename])
        except Exception as exc:
            logger.warning("Could not process %s in preset %s: %s", filename, preset.name, exc)
            skipped.add(filename)
            continue
        trimmed_wavs[filename] = trimmed
        trim_offsets[filename] = leading

    preset.regions = [r for r in preset.regions if r.sample not in skipped]

    sfz_text = generate_sfz(preset, trim_offsets)
    zip_bytes = build_zip(preset, sfz_text, trimmed_wavs)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{preset.name}.zip"'},
    )


app.mount("/", StaticFiles(directory="static", html=True), name="static")
