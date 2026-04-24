"""
ui/page_downloader.py — Main download page
"""

import customtkinter as ctk
import threading
from tkinter import StringVar
from PIL import Image, ImageTk
import requests
import io
from pathlib import Path

from ui.components import (C, Card, SectionLabel, IconBtn,
                            Divider, ProgressRow, FONT_HEAD,
                            FONT_SUB, FONT_MONO, FONT_SMALL, FONT_LABEL)
import core.downloader as engine
import core.database as db


class DownloaderPage(ctk.CTkFrame):
    def __init__(self, master, notify):
        super().__init__(master, fg_color="transparent")
        self.notify = notify          # callback to show toast
        self._info  = None
        self._cancel = threading.Event()
        self._thumb_img = None

        self._build()

    # ── Layout ──────────────────────────────────────────────────────────────────
    def _build(self):
        # ── URL search bar ────────────────────────────────────────────────────
        search_card = Card(self)
        search_card.pack(fill="x", padx=24, pady=(20, 0))

        inner = ctk.CTkFrame(search_card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(inner, text="🔗", font=("Helvetica", 18),
                     text_color=C["muted"]).pack(side="left", padx=(0, 8))

        self.url_var = StringVar()
        self.url_entry = ctk.CTkEntry(
            inner, textvariable=self.url_var,
            placeholder_text="Paste a YouTube URL and press Fetch…",
            font=FONT_MONO, fg_color="transparent", border_width=0,
            text_color=C["fg"], placeholder_text_color=C["muted"],
            height=40,
        )
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.url_entry.bind("<Return>", lambda _: self._fetch())

        self.fetch_btn = IconBtn(inner, "  Fetch Info", command=self._fetch,
                                 accent=True, width=120)
        self.fetch_btn.pack(side="right")

        # ── Info panel (hidden until fetch) ──────────────────────────────────
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")

        # Thumbnail + meta
        top_row = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=24, pady=(16, 0))

        # Thumbnail
        self.thumb_label = ctk.CTkLabel(top_row, text="", width=200, height=112)
        self.thumb_label.pack(side="left", padx=(0, 16))

        # Meta
        meta = ctk.CTkFrame(top_row, fg_color="transparent")
        meta.pack(side="left", fill="both", expand=True)

        self.title_lbl = ctk.CTkLabel(
            meta, text="", font=FONT_HEAD, text_color=C["fg"],
            anchor="w", wraplength=420,
        )
        self.title_lbl.pack(anchor="w")

        self.channel_lbl = ctk.CTkLabel(
            meta, text="", font=FONT_SUB, text_color=C["accent"], anchor="w"
        )
        self.channel_lbl.pack(anchor="w", pady=(4, 0))

        self.meta_lbl = ctk.CTkLabel(
            meta, text="", font=FONT_SMALL, text_color=C["fg3"], anchor="w"
        )
        self.meta_lbl.pack(anchor="w", pady=(4, 0))

        # ── Mode tabs ─────────────────────────────────────────────────────────
        tab_row = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        tab_row.pack(fill="x", padx=24, pady=(18, 0))

        SectionLabel(tab_row, "Download Mode").pack(side="left")

        self.mode_var = StringVar(value="video")
        for label, val in [("🎬  Video (MP4)", "video"), ("🎵  Audio Only", "audio")]:
            ctk.CTkRadioButton(
                tab_row, text=label, variable=self.mode_var, value=val,
                fg_color=C["accent"], hover_color=C["accent2"],
                text_color=C["fg"], font=FONT_SUB,
                command=self._on_mode_change,
            ).pack(side="left", padx=(20, 0))

        # ── Quality + audio selectors ─────────────────────────────────────────
        opts_row = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        opts_row.pack(fill="x", padx=24, pady=(14, 0))

        # Video quality
        self.vid_col = ctk.CTkFrame(opts_row, fg_color="transparent")
        self.vid_col.pack(side="left", padx=(0, 16), fill="x")
        SectionLabel(self.vid_col, "Quality").pack(anchor="w", pady=(0, 6))
        self.quality_var = StringVar(value="1080p")
        self.quality_menu = ctk.CTkOptionMenu(
            self.vid_col, variable=self.quality_var, values=["—"],
            fg_color=C["card2"], button_color=C["accent"],
            button_hover_color=C["accent2"],
            dropdown_fg_color=C["card2"],
            dropdown_hover_color=C["border2"],
            text_color=C["fg"], font=FONT_SUB,
            corner_radius=9, height=40, width=180,
        )
        self.quality_menu.pack()

        # Audio format
        self.aud_col = ctk.CTkFrame(opts_row, fg_color="transparent")
        self.audio_var = StringVar(value="MP3 (Best)")
        self.audio_menu = ctk.CTkOptionMenu(
            self.aud_col, variable=self.audio_var,
            values=["MP3 (Best)", "MP3 (128k)", "M4A (Best)", "WAV"],
            fg_color=C["card2"], button_color=C["accent"],
            button_hover_color=C["accent2"],
            dropdown_fg_color=C["card2"],
            dropdown_hover_color=C["border2"],
            text_color=C["fg"], font=FONT_SUB,
            corner_radius=9, height=40, width=180,
        )
        SectionLabel(self.aud_col, "Audio Format").pack(anchor="w", pady=(0, 6))
        self.audio_menu.pack()

        # Save location
        loc_col = ctk.CTkFrame(opts_row, fg_color="transparent")
        loc_col.pack(side="left", fill="x", expand=True)
        SectionLabel(loc_col, "Save To").pack(anchor="w", pady=(0, 6))
        loc_inner = ctk.CTkFrame(loc_col, fg_color=C["card2"],
                                  corner_radius=9, border_width=1,
                                  border_color=C["border"], height=40)
        loc_inner.pack(fill="x")
        loc_inner.pack_propagate(False)

        self._save_dir = db.get_setting("download_dir", str(Path.home()/"Downloads"))
        self.dir_lbl = ctk.CTkLabel(
            loc_inner, text=self._shorten(self._save_dir),
            font=FONT_SMALL, text_color=C["fg2"], anchor="w"
        )
        self.dir_lbl.pack(side="left", padx=10, fill="x", expand=True)
        IconBtn(loc_inner, "📁", command=self._pick_dir, width=40, height=36).pack(side="right", padx=4)

        # ── Progress area ─────────────────────────────────────────────────────
        self.progress_card = Card(self.info_frame)
        self.progress_card.pack(fill="x", padx=24, pady=(16, 0))
        p_inner = ctk.CTkFrame(self.progress_card, fg_color="transparent")
        p_inner.pack(fill="x", padx=16, pady=14)

        self.status_lbl = ctk.CTkLabel(
            p_inner, text="Ready to download.",
            font=FONT_SUB, text_color=C["fg2"], anchor="w"
        )
        self.status_lbl.pack(fill="x")

        self.progress = ProgressRow(p_inner)
        self.progress.pack(fill="x", pady=(10, 0))

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(14, 24))

        self.dl_btn = ctk.CTkButton(
            btn_row, text="↓  Download",
            font=("Helvetica", 14, "bold"),
            fg_color=C["accent"], hover_color=C["accent2"],
            text_color="white", height=48, corner_radius=10,
            command=self._start_download,
        )
        self.dl_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.cancel_btn = IconBtn(
            btn_row, "✕  Cancel", command=self._cancel_download,
            width=120, height=48,
        )
        self.cancel_btn.pack(side="right")
        self.cancel_btn.configure(state="disabled")

        # Initial mode
        self._on_mode_change()

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _shorten(self, path, max=45):
        return path if len(path) <= max else "…" + path[-max+1:]

    def _pick_dir(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(initialdir=self._save_dir)
        if d:
            self._save_dir = d
            self.dir_lbl.configure(text=self._shorten(d))
            db.set_setting("download_dir", d)
    
    def _on_mode_change(self):
        mode = self.mode_var.get()
        if mode == "video":
            self.aud_col.pack_forget()
            self.vid_col.pack(side="left", padx=(0, 16))
        else:
            self.vid_col.pack_forget()
            self.aud_col.pack(side="left", padx=(0, 16))

    def set_save_dir(self, d):
        self._save_dir = d
        self.dir_lbl.configure(text=self._shorten(d))

    # ── Fetch info ─────────────────────────────────────────────────────────────
    def _fetch(self):
        url = self.url_var.get().strip()
        if not url:
            self.notify("Please paste a YouTube URL first.", "warn")
            return
        self.fetch_btn.configure(state="disabled", text="  Fetching…")
        self.info_frame.pack_forget()
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        try:
            info = engine.fetch_info(url)
            self._info = info
            self.after(0, self._populate_info, info)
        except Exception as e:
            self.after(0, self.notify, f"Error: {e}", "error")
            self.after(0, self.fetch_btn.configure, {"state": "normal", "text": "  Fetch Info"})

    def _populate_info(self, info):
        self.title_lbl.configure(text=info["title"])
        self.channel_lbl.configure(text=f"  {info['channel']}")

        views = f"{info['view_count']:,}" if info.get("view_count") else "—"
        self.meta_lbl.configure(
            text=f"⏱  {info['duration']}   👁  {views} views"
        )

        # Quality menu
        labels = [f["label"] for f in info["video_formats"]] or ["Best"]
        self.quality_menu.configure(values=labels)
        self.quality_var.set(labels[0])

        # Show info panel
        self.info_frame.pack(fill="both", expand=True)
        self.fetch_btn.configure(state="normal", text="  Fetch Info")

        # Load thumbnail async
        threading.Thread(
            target=self._load_thumb, args=(info["thumbnail"],), daemon=True
        ).start()

    def _load_thumb(self, url):
        try:
            r = requests.get(url, timeout=10)
            img = Image.open(io.BytesIO(r.content)).resize((200, 112), Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 112))
            self.after(0, self.thumb_label.configure, {"image": ctk_img, "text": ""})
            self._thumb_img = ctk_img
        except Exception:
            pass

    # ── Download ───────────────────────────────────────────────────────────────
    def _start_download(self):
        if not self._info:
            self.notify("Fetch a video first.", "warn")
            return

        self._cancel.clear()
        self.dl_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress.reset()

        mode    = self.mode_var.get()
        quality = self.quality_var.get()
        audio   = self.audio_var.get()
        url     = self.url_var.get().strip()

        threading.Thread(
            target=engine.download,
            args=(url, mode, quality, audio,
                  self._save_dir,
                  self._on_progress,
                  self._on_status,
                  self._on_done,
                  self._cancel),
            daemon=True,
        ).start()

    def _cancel_download(self):
        self._cancel.set()
        self._on_status("Cancelling…")

    def _on_progress(self, pct, speed, eta):
        self.after(0, self.progress.update, pct, speed, eta)

    def _on_status(self, msg):
        self.after(0, self.status_lbl.configure, {"text": msg})

    def _on_done(self, success, path, info_dict):
        def _ui():
            self.dl_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            if success:
                self.notify(f"✅  Saved: {Path(path).name}", "success")
                self._on_status("✅  Download complete!")
                # Save to history
                thumb_local = ""
                if self._info and self._info.get("thumbnail"):
                    thumb_local = engine.download_thumbnail(
                        self._info["thumbnail"],
                        self._info.get("title", "")
                    )
                db.add_download(
                    title      = self._info.get("title", info_dict.get("title", "?")),
                    url        = self.url_var.get().strip(),
                    quality    = self.quality_var.get() if self.mode_var.get() == "video" else "Audio",
                    fmt        = self.mode_var.get(),
                    duration   = self._info.get("duration", ""),
                    filesize   = "",
                    saved_path = path,
                    thumb_path = thumb_local,
                    channel    = self._info.get("channel", ""),
                )
            else:
                if not self._cancel.is_set():
                    self._on_status("❌  Download failed. Check the URL or your connection.")
                else:
                    self._on_status("Cancelled.")
        self.after(0, _ui)
