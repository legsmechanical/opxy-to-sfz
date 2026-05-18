# opxy-to-sfz

Converts OP-XY multisample instrument presets to SFZ v2 format. Drag and drop one or more `.preset` folders into the browser, download a per-preset ZIP (or all at once) containing the SFZ file and trimmed WAV samples.

## Requirements

- Python 3.11+
- Chrome or Edge (required for folder drag-and-drop via the File System Access API)

## Setup

```bash
pip install -r requirements.txt
```

## Launch

```bash
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in Chrome or Edge.

## Usage

1. Drag one or more `.preset` folders from your OP-XY library onto the drop zone.
2. Each preset appears in the list with a download button for its individual ZIP.
3. Use **Download All** to get a single ZIP with all SFZ files and sample folders merged at the root — unzip and drop the contents into your SFZ player's library.

## Output format

Each preset produces:
```
PresetName.sfz
PresetName/sample_C3.wav
PresetName/sample_F3.wav
...
```

Leading and trailing silence is trimmed from every sample, and loop points, envelope, and filter settings are carried over from the OP-XY preset as accurately as possible.

## Running tests

```bash
pytest
```
