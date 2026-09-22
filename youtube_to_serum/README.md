# youtube_to_serum — Isolated Product Folder

Self-contained pipeline: YouTube URL → video download → transcript → frame analysis → Serum control inference → preset generation → Serum 2.0.21.

**Runtime requirements:**
- Python 3.8+
- yt-dlp
- youtube-transcript-api
- ffmpeg / ffprobe (for frame extraction)
- serum-mcp (included in vendor/)

**Entry point:** See EXECUTION_PLAN.md (NOT YET IMPLEMENTED; folder creation + validation only)

**Manifests:**
- SOURCE_MANIFEST.json — exact origin of every copied file
- DEPENDENCY_GRAPH.json — entrypoint → imports → data files

**Status:** Folder creation + validation complete. Implementation blocked by phase transition gate.
