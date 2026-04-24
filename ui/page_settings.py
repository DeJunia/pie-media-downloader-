"""
ui/page_settings.py — App settings: theme, download dir, about
"""

import customtkinter as ctk
import sys
import subprocess
from pathlib import Path
from tkinter import filedialog

from ui.components import (C, Card, SectionLabel, IconBtn, Divider,
                            FONT_HEAD, FONT_SUB, FONT_SMALL, FONT_LABEL)
import core.database as db


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, notify, on_theme_change):
        super().__init__(master, fg_color="transparent")
        self.notify          = notify
        self.on_theme_change = on_theme_change
        self._build()

    def _build(self):
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["border2"],
        )
        scroll.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(scroll, text="Settings", font=FONT_HEAD,
                     text_color=C["fg"]).pack(anchor="w", pady=(0, 20))

        # ── Download directory ────────────────────────────────────────────────
        self._section(scroll, "📁  Default Download Folder")
        dir_card = Card(scroll)
        dir_card.pack(fill="x", pady=(6, 20))
        dir_inner = ctk.CTkFrame(dir_card, fg_color="transparent")
        dir_inner.pack(fill="x", padx=16, pady=14)

        self._dl_dir = db.get_setting("download_dir", str(Path.home()/"Downloads"))
        self.dir_lbl = ctk.CTkLabel(
            dir_inner, text=self._dl_dir, font=FONT_SUB,
            text_color=C["fg2"], anchor="w", wraplength=500,
        )
        self.dir_lbl.pack(side="left", fill="x", expand=True)
        IconBtn(dir_inner, "Change", command=self._change_dir,
                width=90).pack(side="right")

        # ── Appearance ────────────────────────────────────────────────────────
        self._section(scroll, "🎨  Appearance")
        app_card = Card(scroll)
        app_card.pack(fill="x", pady=(6, 20))
        app_inner = ctk.CTkFrame(app_card, fg_color="transparent")
        app_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(app_inner, text="Theme", font=FONT_SUB,
                     text_color=C["fg"], width=120, anchor="w").pack(side="left")
        self.theme_var = ctk.StringVar(value=db.get_setting("theme", "dark").capitalize())
        ctk.CTkSegmentedButton(
            app_inner, values=["Dark", "Light", "System"],
            variable=self.theme_var,
            fg_color=C["card2"], selected_color=C["accent"],
            selected_hover_color=C["accent2"],
            unselected_color=C["card2"],
            unselected_hover_color=C["border2"],
            text_color=C["fg"],
            command=self._apply_theme,
        ).pack(side="left", padx=20)

        # ── ffmpeg check ──────────────────────────────────────────────────────
        self._section(scroll, "🔧  System")
        sys_card = Card(scroll)
        sys_card.pack(fill="x", pady=(6, 20))
        sys_inner = ctk.CTkFrame(sys_card, fg_color="transparent")
        sys_inner.pack(fill="x", padx=16, pady=14)

        ffmpeg_ok = self._check_ffmpeg()
        status_txt = "✅  ffmpeg found" if ffmpeg_ok else "❌  ffmpeg NOT found — 1080p & audio conversion will fail"
        status_col = C["green"] if ffmpeg_ok else C["accent"]
        ctk.CTkLabel(sys_inner, text=status_txt, font=FONT_SUB,
                     text_color=status_col, anchor="w").pack(anchor="w")

        if not ffmpeg_ok:
            ctk.CTkLabel(
                sys_inner,
                text="Install: sudo apt install ffmpeg  (Linux)  |  brew install ffmpeg  (Mac)  |  winget install ffmpeg  (Windows)",
                font=FONT_SMALL, text_color=C["fg3"], anchor="w",
            ).pack(anchor="w", pady=(6, 0))

        # ── About ─────────────────────────────────────────────────────────────
        self._section(scroll, "ℹ️  About")
        ab_card = Card(scroll)
        ab_card.pack(fill="x", pady=(6, 20))
        ab_inner = ctk.CTkFrame(ab_card, fg_color="transparent")
        ab_inner.pack(fill="x", padx=16, pady=16)

        for line, col, fnt in [
            ("YT Vault  v2.0", C["fg"],   ("Georgia", 16, "bold")),
            ("Your personal media archive", C["fg2"], FONT_SUB),
            ("Powered by yt-dlp  •  Built with CustomTkinter", C["fg3"], FONT_SMALL),
        ]:
            ctk.CTkLabel(ab_inner, text=line, font=fnt,
                         text_color=col, anchor="w").pack(anchor="w", pady=2)

        # ── Data management ───────────────────────────────────────────────────
        self._section(scroll, "🗂  Data")
        data_card = Card(scroll)
        data_card.pack(fill="x", pady=(6, 20))
        data_inner = ctk.CTkFrame(data_card, fg_color="transparent")
        data_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            data_inner,
            text=f"App data stored at: {db.APP_DIR}",
            font=FONT_SMALL, text_color=C["fg3"], anchor="w"
        ).pack(anchor="w")

        IconBtn(data_inner, "Open App Folder",
                command=lambda: self._open_dir(str(db.APP_DIR)),
                width=160).pack(anchor="w", pady=(10, 0))

    def _section(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Helvetica", 12, "bold"),
                     text_color=C["fg2"], anchor="w").pack(anchor="w", pady=(8, 0))

    def _change_dir(self):
        d = filedialog.askdirectory(initialdir=self._dl_dir)
        if d:
            self._dl_dir = d
            db.set_setting("download_dir", d)
            self.dir_lbl.configure(text=d)
            self.notify("Default download folder updated.", "success")

    def _apply_theme(self, val):
        mode = val.lower()
        db.set_setting("theme", mode)
        ctk.set_appearance_mode(mode)
        self.on_theme_change(mode)

    def _check_ffmpeg(self):
        try:
            subprocess.run(["ffmpeg", "-version"],
                           capture_output=True, timeout=3)
            return True
        except Exception:
            return False

    def _open_dir(self, path):
        import os
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.notify(str(e), "error")
