# YouTube → Serum 2.0.21 Preset Generator

Convert any YouTube video into a Serum 2.0.21 preset with a minimal web UI.

## Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Web UI
```bash
python app.py
```
Open **http://localhost:5000** → paste YouTube URL → click **Run** → download results.

### CLI
```bash
python main.py "https://www.youtube.com/watch?v=<VIDEO_ID>"
```

## Features

- ✅ **Real execution**: No mocks, no placeholders, no print-only pipelines
- ✅ **Exhaustive frames**: 1-second intervals from actual video (not 45sec/8-frame defaults)
- ✅ **Live logs**: Watch the pipeline in real-time via web UI
- ✅ **Real artifacts**: 
  - `.SerumPreset` file (Serum 2.0.21 binary preset)
  - Documentation report (JSON)
- ✅ **Download buttons**: Get files directly from browser
- ✅ **Zero hardcoding**: Every run is fresh from YouTube URL

## How It Works

```
YouTube URL → Video + Transcript
         ↓
Extract EVERY frame (1sec intervals)
         ↓
Local model analyzes each frame
         ↓
Existing system:
  - State observation & fusion
  - Expected inventory / state ledger
  - Producer brain reasoning
  - Capability resolution & admission
         ↓
serum-mcp generates real preset
         ↓
Document non-executable parameters
```

## Web UI

- Clean dark theme (minimal)
- Real-time log streaming
- Auto-detect result paths
- One-click downloads
- Works on any YouTube URL

## CLI

Single command operation:
```bash
python main.py "https://www.youtube.com/shorts/4vukJalYegE"
```

Prints absolute paths to:
- `.SerumPreset` file
- Documentation JSON

## Files

- `main.py` — CLI entry point
- `app.py` — Flask backend
- `orchestrator.py` — Core pipeline orchestration
- `templates/index.html` — Web UI
- `serum2/pathmerge.py` — Utility helper
- Parent dirs: `serum2/`, `vendor/serum-mcp/` (canonical resources)

## Requirements

```
Flask==2.3.3
flask-cors==4.0.0
yt-dlp==2023.11.16
youtube-transcript-api==0.6.2
faster-whisper==0.9.1
python-docx==0.8.11
```

## Notes

- Frame extraction: ~1 second per frame of video
- ML models: ~1GB download on first run (Whisper fallback)
- Presets: Saved to Serum's default location
- Reports: Saved to `output/` directory

## Examples

**Web UI** (recommended for interactive use):
```bash
python app.py
```
Then: http://localhost:5000

**CLI** (recommended for scripting):
```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Both produce identical real preset files.
