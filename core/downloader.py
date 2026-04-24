"""
core/downloader.py — yt-dlp wrapper: fetch info, available formats, download
"""

import yt_dlp
import threading
import subprocess
import sys
import os
import re
from pathlib import Path
from core.database import THUMB_DIR, get_setting


def _base_opts():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }


def fetch_info(url):
    """
    Returns dict with: title, channel, duration, thumbnail, formats
    formats = list of {"label": "1080p", "format_id": "...", "ext": "mp4", "filesize": ...}
    Raises on error.
    """
    opts = {**_base_opts(), "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats_raw = info.get("formats", [])

    # Build deduplicated quality list for video
    seen = set()
    video_formats = []
    for f in reversed(formats_raw):
        h = f.get("height")
        if not h:
            continue
        label = f"{h}p"
        if label in seen:
            continue
        seen.add(label)
        video_formats.append({
            "label":     label,
            "height":    h,
            "ext":       f.get("ext", "mp4"),
            "filesize":  f.get("filesize") or f.get("filesize_approx"),
            "vcodec":    f.get("vcodec", ""),
            "acodec":    f.get("acodec", "none"),
        })
    # Sort highest first
    video_formats.sort(key=lambda x: x["height"], reverse=True)

    # Audio formats
    audio_formats = [{"label": "MP3 (Best)", "ext": "mp3"},
                     {"label": "MP3 (128k)", "ext": "mp3", "abr": 128},
                     {"label": "M4A (Best)", "ext": "m4a"},
                     {"label": "WAV",        "ext": "wav"}]

    seconds = info.get("duration", 0)
    duration_str = _fmt_duration(seconds)

    return {
        "title":         info.get("title", "Unknown"),
        "channel":       info.get("uploader") or info.get("channel", "Unknown"),
        "duration":      duration_str,
        "duration_sec":  seconds,
        "thumbnail":     info.get("thumbnail", ""),
        "view_count":    info.get("view_count", 0),
        "upload_date":   info.get("upload_date", ""),
        "description":   (info.get("description") or "")[:300],
        "video_formats": video_formats,
        "audio_formats": audio_formats,
        "webpage_url":   info.get("webpage_url", url),
    }


def download(url, mode, quality_label, audio_ext,
             output_dir, progress_cb, status_cb, done_cb, cancel_event):
    """
    mode: "video" | "audio"
    progress_cb(pct: float, speed: str, eta: str)
    status_cb(msg: str)
    done_cb(success: bool, saved_path: str, info: dict)
    """

    out_tmpl = str(Path(output_dir) / "%(title)s.%(ext)s")
    info_holder = {}

    def progress_hook(d):
        if cancel_event.is_set():
            raise yt_dlp.utils.DownloadCancelled("Cancelled by user")
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)
            pct = downloaded / total
            speed = d.get("_speed_str", "").strip() or "—"
            eta   = d.get("_eta_str", "").strip()   or "—"
            progress_cb(pct, speed, eta)
        elif d["status"] == "finished":
            status_cb("⚙  Merging / converting…")

    opts = {
        **_base_opts(),
        "quiet":         False,
        "no_warnings":   True,
        "noplaylist":    True,
        "outtmpl":       out_tmpl,
        "progress_hooks":[progress_hook],
        "writethumbnail": False,
    }

    if mode == "audio":
        ext = audio_ext.split()[0].lower()   # "mp3", "m4a", "wav"
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key":            "FFmpegExtractAudio",
            "preferredcodec": ext,
            "preferredquality": "0",
        }]
    else:
        h = quality_label.replace("p", "")
        opts["format"] = (
            f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
        )
        opts["merge_output_format"] = "mp4"

    try:
        status_cb("⬇  Starting download…")
        with yt_dlp.YoutubeDL(opts) as ydl:
            raw = ydl.extract_info(url, download=True)
            info_holder = {
                "title":    raw.get("title", "Unknown"),
                "channel":  raw.get("uploader") or raw.get("channel", "Unknown"),
                "duration": _fmt_duration(raw.get("duration", 0)),
            }
            # Guess final path
            filename = ydl.prepare_filename(raw)
            if mode == "audio":
                filename = str(Path(filename).with_suffix(f".{ext}"))
        progress_cb(1.0, "", "")
        done_cb(True, filename, info_holder)
    except yt_dlp.utils.DownloadCancelled:
        done_cb(False, "", {})
    except Exception as e:
        status_cb(f"❌  {e}")
        done_cb(False, "", {})


def download_thumbnail(thumb_url, video_title):
    """Download thumbnail to app cache, return local path."""
    import requests, hashlib
    safe = hashlib.md5(video_title.encode()).hexdigest()
    dest = THUMB_DIR / f"{safe}.jpg"
    if dest.exists():
        return str(dest)
    try:
        r = requests.get(thumb_url, timeout=10)
        dest.write_bytes(r.content)
        return str(dest)
    except Exception:
        return ""


def _fmt_duration(seconds):
    if not seconds:
        return "0:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
