"""
downloader.py
=============
OmniGet – Universal Video Downloader
-------------------------------------
Encapsulates all yt-dlp logic, keeping the download engine completely
separate from the GUI layer. The module exposes a single public function:

    start_download(url, format_choice, progress_callback)

The `progress_callback` receives a dict on every yt-dlp hook event so the
GUI can update its widgets without touching any download internals.
"""

import os
import yt_dlp


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Map human-readable format labels (shown in the GUI) to internal keys.
FORMAT_BEST     = "Best Video + Audio"
FORMAT_AUDIO    = "Audio Only (MP3)"
FORMAT_VIDEO    = "Video Only (MP4)"

# Default save location: the user's Downloads folder.
DOWNLOADS_DIR = os.path.expanduser("~/Downloads")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_ydl_opts(format_choice: str, progress_hook) -> dict:
    """
    Build and return the yt-dlp options dictionary for the requested format.

    Parameters
    ----------
    format_choice : str
        One of the FORMAT_* constants defined above.
    progress_hook : callable
        A function that yt-dlp will call on every download event.

    Returns
    -------
    dict
        A complete options dict ready to pass to yt_dlp.YoutubeDL().
    """
    # Base options shared by every format.
    base_opts = {
        # Save to ~/Downloads/<title>.<ext>
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(title)s.%(ext)s"),
        # Let yt-dlp embed chapter markers when available.
        "addchapters": True,
        # Register our progress hook so we get real-time updates.
        "progress_hooks": [progress_hook],
        # Keep yt-dlp output quiet; we handle messaging via the hook.
        "quiet": True,
        "no_warnings": True,
    }

    if format_choice == FORMAT_AUDIO:
        # Audio-only: download the best audio stream, then transcode to MP3.
        return {
            **base_opts,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",   # 192 kbps – good quality
                }
            ],
        }

    elif format_choice == FORMAT_VIDEO:
        # Video-only: best video stream, no audio, remux to MP4.
        return {
            **base_opts,
            "format": "bestvideo[ext=mp4]/bestvideo",
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
        }

    else:
        # Default / "Best Video + Audio": best combined stream, merge to MP4.
        return {
            **base_opts,
            # Prefer formats that already contain both streams; otherwise
            # download the best video + best audio and let FFmpeg merge them.
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        }


def _make_progress_hook(callback):
    """
    Return a closure that acts as a yt-dlp progress hook.

    The returned function is called by yt-dlp with a status dict on every
    downloaded chunk. It computes the user-facing metrics and forwards them
    to `callback` so the GUI can update without any yt-dlp knowledge.

    Parameters
    ----------
    callback : callable
        A function that accepts a single dict argument with these keys:
            status      – "downloading" | "finished" | "error"
            percent     – float in [0.0, 1.0]  (or None if unknown)
            speed_str   – human-readable speed string (e.g. "3.2 MiB/s")
            eta_str     – human-readable ETA string  (e.g. "00:12")
            message     – short status string for the status label
    """
    def hook(d: dict):
        status = d.get("status")

        if status == "downloading":
            # --- Percentage ---
            # yt-dlp exposes downloaded/total bytes; compute fraction ourselves
            # so we always have a 0-1 float for CTkProgressBar.
            downloaded = d.get("downloaded_bytes") or 0
            total      = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            percent    = (downloaded / total) if total > 0 else None

            # --- Speed ---
            speed = d.get("speed")            # bytes/sec or None
            if speed is not None:
                speed_mb   = speed / (1024 * 1024)
                speed_str  = f"{speed_mb:.1f} MiB/s"
            else:
                speed_str = "– MiB/s"

            # --- ETA ---
            eta_secs = d.get("eta")           # seconds or None
            if eta_secs is not None:
                mins, secs = divmod(int(eta_secs), 60)
                eta_str = f"{mins:02d}:{secs:02d}"
            else:
                eta_str = "--:--"

            pct_display = f"{percent * 100:.1f}%" if percent is not None else "?%"
            message = f"Downloading… {pct_display}  |  {speed_str}  |  ETA {eta_str}"

            callback({
                "status":    "downloading",
                "percent":   percent,
                "speed_str": speed_str,
                "eta_str":   eta_str,
                "message":   message,
            })

        elif status == "finished":
            # yt-dlp fires "finished" after the raw download; post-processors
            # (FFmpeg merge/transcode) may still run. Notify the GUI.
            callback({
                "status":  "finished",
                "percent": 1.0,
                "message": "Processing / merging streams…",
            })

        elif status == "error":
            callback({
                "status":  "error",
                "percent": None,
                "message": "An error occurred during download.",
            })

    return hook


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_download(url: str, format_choice: str, progress_callback) -> None:
    """
    Download the media at `url` using yt-dlp.

    This function is designed to be called from a background thread so it
    will block until the download (and any post-processing) is complete.

    Parameters
    ----------
    url : str
        The URL of the video/audio to download (YouTube, Vimeo, etc.).
    format_choice : str
        One of the FORMAT_* constants (must match what the GUI passes).
    progress_callback : callable
        Called on every yt-dlp event; receives a dict (see _make_progress_hook).
        Also called with status="done" on clean completion and status="error"
        with a "message" key on failure.

    Raises
    ------
    Does NOT raise – all exceptions are caught and forwarded via callback so
    the GUI thread can display the error without crashing.
    """
    if not url or not url.strip():
        progress_callback({
            "status":  "error",
            "percent": None,
            "message": "Error: Please enter a valid URL.",
        })
        return

    hook     = _make_progress_hook(progress_callback)
    ydl_opts = _build_ydl_opts(format_choice, hook)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url.strip()])

        # All done (including post-processing).
        progress_callback({
            "status":  "done",
            "percent": 1.0,
            "message": "✅ Download complete! Saved to ~/Downloads",
        })

    except yt_dlp.utils.DownloadError as exc:
        # Covers unsupported URLs, geo-blocks, private videos, etc.
        progress_callback({
            "status":  "error",
            "percent": None,
            "message": f"Download error: {exc}",
        })

    except yt_dlp.utils.ExtractorError as exc:
        # Extractor could not parse the page (site layout changes, etc.).
        progress_callback({
            "status":  "error",
            "percent": None,
            "message": f"Extractor error: {exc}",
        })

    except Exception as exc:  # noqa: BLE001
        # Catch-all for unexpected failures (network outage, disk full, etc.).
        progress_callback({
            "status":  "error",
            "percent": None,
            "message": f"Unexpected error: {exc}",
        })
