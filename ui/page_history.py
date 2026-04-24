"""
ui/page_history.py — Download history with thumbnails, search, delete
"""

import customtkinter as ctk
import threading
import os
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageTk
import io

from ui.components import (C, Card, SectionLabel, IconBtn, Divider,
                            FONT_HEAD, FONT_SUB, FONT_SMALL, FONT_MONO,
                            FONT_LABEL)
import core.database as db


class HistoryPage(ctk.CTkFrame):
    def __init__(self, master, notify):
        super().__init__(master, fg_color="transparent")
        self.notify = notify
        self._rows  = []
        self._thumb_cache = {}
        self._build()

    def _build(self):
        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(toolbar, text="Download History",
                     font=FONT_HEAD, text_color=C["fg"]).pack(side="left")

        IconBtn(toolbar, "🗑  Clear All", command=self._clear_all,
                width=120).pack(side="right")
        IconBtn(toolbar, "↻  Refresh", command=self.refresh,
                width=100).pack(side="right", padx=(0, 8))

        # ── Search ──────────────────────────────────────────────────────────
        search_card = Card(self)
        search_card.pack(fill="x", padx=24, pady=(14, 0))

        s_inner = ctk.CTkFrame(search_card, fg_color="transparent")
        s_inner.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(s_inner, text="🔍", font=("Helvetica", 16),
                     text_color=C["muted"]).pack(side="left", padx=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        ctk.CTkEntry(
            s_inner, textvariable=self.search_var,
            placeholder_text="Search by title or channel…",
            font=FONT_MONO, fg_color="transparent", border_width=0,
            text_color=C["fg"], placeholder_text_color=C["muted"], height=36,
        ).pack(side="left", fill="x", expand=True)

        # ── Count label ──────────────────────────────────────────────────────
        self.count_lbl = ctk.CTkLabel(
            self, text="", font=FONT_SMALL, text_color=C["muted"], anchor="w"
        )
        self.count_lbl.pack(fill="x", padx=26, pady=(8, 0))

        # ── Scrollable list ──────────────────────────────────────────────────
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["border2"],
        )
        self.scroll.pack(fill="both", expand=True, padx=24, pady=(8, 24))

        self.refresh()

    def refresh(self):
        q = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        rows = db.search_history(q) if q else db.get_history()
        self._render(rows)

    def _on_search(self):
        q = self.search_var.get().strip()
        rows = db.search_history(q) if q else db.get_history()
        self._render(rows)

    def _render(self, rows):
        for w in self.scroll.winfo_children():
            w.destroy()
        self._rows = rows
        self.count_lbl.configure(text=f"{len(rows)} item{'s' if len(rows)!=1 else ''}")

        if not rows:
            ctk.CTkLabel(
                self.scroll, text="No downloads yet. Go grab something!",
                font=FONT_SUB, text_color=C["muted"]
            ).pack(pady=60)
            return

        for item in rows:
            self._make_row(item)

    def _make_row(self, item):
        card = Card(self.scroll)
        card.pack(fill="x", pady=(0, 10))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        # Thumbnail
        thumb_frame = ctk.CTkFrame(inner, fg_color=C["card2"],
                                    corner_radius=8, width=96, height=54)
        thumb_frame.pack(side="left", padx=(0, 14))
        thumb_frame.pack_propagate(False)

        thumb_lbl = ctk.CTkLabel(thumb_frame, text="🎬", font=("Helvetica", 22),
                                  text_color=C["muted"])
        thumb_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Load thumb in background
        thumb_path = item.get("thumb_path", "")
        if thumb_path and Path(thumb_path).exists():
            threading.Thread(
                target=self._load_thumb,
                args=(thumb_path, thumb_lbl),
                daemon=True
            ).start()

        # Text info
        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", fill="both", expand=True)

        title = item["title"] or "Unknown"
        ctk.CTkLabel(
            txt, text=title[:70] + ("…" if len(title) > 70 else ""),
            font=("Helvetica", 13, "bold"), text_color=C["fg"], anchor="w"
        ).pack(anchor="w")

        ch = item.get("channel") or "—"
        ctk.CTkLabel(
            txt, text=f"  {ch}", font=FONT_SMALL, text_color=C["accent"], anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        meta = []
        if item.get("quality"): meta.append(item["quality"])
        if item.get("fmt"):     meta.append(item["fmt"].upper())
        if item.get("duration"):meta.append(item["duration"])
        if item.get("downloaded_at"):
            meta.append(item["downloaded_at"][:16])

        ctk.CTkLabel(
            txt, text="  •  ".join(meta),
            font=FONT_SMALL, text_color=C["fg3"], anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        # Buttons
        btns = ctk.CTkFrame(inner, fg_color="transparent")
        btns.pack(side="right", padx=(10, 0))

        path = item.get("saved_path", "")
        if path and Path(path).exists():
            IconBtn(btns, "📂", command=lambda p=path: self._open_folder(p),
                    width=38, height=34).pack(pady=(0, 6))

        IconBtn(btns, "🗑", command=lambda i=item["id"]: self._delete(i),
                width=38, height=34).pack()

    def _load_thumb(self, path, label):
        try:
            img = Image.open(path).resize((96, 54), Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(96, 54))
            self.after(0, label.configure, {"image": ctk_img, "text": ""})
            label._img_ref = ctk_img
        except Exception:
            pass

    def _open_folder(self, path):
        folder = str(Path(path).parent)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            self.notify(f"Could not open folder: {e}", "error")

    def _delete(self, row_id):
        db.delete_download(row_id)
        self.refresh()
        self.notify("Entry removed.", "info")

    def _clear_all(self):
        db.clear_history()
        self.refresh()
        self.notify("History cleared.", "info")
