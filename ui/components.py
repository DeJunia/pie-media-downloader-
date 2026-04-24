"""
ui/components.py — Shared reusable widgets
"""

import customtkinter as ctk
from tkinter import StringVar

# ── Palette (used app-wide) ────────────────────────────────────────────────────
C = {
    "bg":       "#0b0b0e",
    "panel":    "#111116",
    "card":     "#18181f",
    "card2":    "#1e1e28",
    "border":   "#252530",
    "border2":  "#303040",
    "accent":   "#e63946",
    "accent2":  "#c1121f",
    "green":    "#4ade80",
    "yellow":   "#facc15",
    "blue":     "#60a5fa",
    "muted":    "#4a4a60",
    "fg":       "#eaeaf5",
    "fg2":      "#9898b8",
    "fg3":      "#5a5a7a",
}

FONT_TITLE  = ("Georgia", 22, "bold")
FONT_HEAD   = ("Georgia", 15, "bold")
FONT_SUB    = ("Helvetica", 12)
FONT_MONO   = ("Courier New", 11)
FONT_SMALL  = ("Helvetica", 10)
FONT_LABEL  = ("Helvetica", 10, "bold")


class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, text, **kw):
        super().__init__(
            master, text=text.upper(),
            font=FONT_LABEL, text_color=C["muted"], anchor="w", **kw
        )


class Card(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(
            master,
            fg_color=kw.pop("fg_color", C["card"]),
            corner_radius=kw.pop("corner_radius", 12),
            border_width=kw.pop("border_width", 1),
            border_color=kw.pop("border_color", C["border"]),
            **kw
        )


class IconBtn(ctk.CTkButton):
    def __init__(self, master, text, command=None, accent=False, **kw):
        kw.setdefault("height", 38)
        kw.setdefault("corner_radius", 9)
        kw.setdefault("font", ("Helvetica", 13))
        super().__init__(
            master, text=text, command=command,
            fg_color=C["accent"] if accent else C["border"],
            hover_color=C["accent2"] if accent else C["border2"],
            text_color=C["fg"],
            **kw
        )


class Divider(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=C["border"], height=1, **kw)


class StatusBadge(ctk.CTkLabel):
    COLORS = {
        "done":       ("#4ade80", "#0f2a1a"),
        "error":      ("#e63946", "#2a0f10"),
        "converting": ("#facc15", "#2a220a"),
        "downloading":("#60a5fa", "#0a1a2a"),
    }

    def __init__(self, master, status="done", **kw):
        fg, bg = self.COLORS.get(status, (C["muted"], C["card"]))
        super().__init__(
            master,
            text=f"  {status.upper()}  ",
            font=("Helvetica", 9, "bold"),
            text_color=fg,
            fg_color=bg,
            corner_radius=4,
            **kw
        )


class ProgressRow(ctk.CTkFrame):
    """Progress bar + speed + ETA in one widget."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)

        self.bar = ctk.CTkProgressBar(
            self, fg_color=C["border"], progress_color=C["accent"],
            height=5, corner_radius=3,
        )
        self.bar.set(0)
        self.bar.pack(fill="x")

        info_row = ctk.CTkFrame(self, fg_color="transparent")
        info_row.pack(fill="x", pady=(4, 0))

        self.pct_lbl  = ctk.CTkLabel(info_row, text="0%",   font=FONT_SMALL, text_color=C["fg2"], width=40, anchor="w")
        self.pct_lbl.pack(side="left")
        self.spd_lbl  = ctk.CTkLabel(info_row, text="",     font=FONT_SMALL, text_color=C["muted"], anchor="center")
        self.spd_lbl.pack(side="left", expand=True)
        self.eta_lbl  = ctk.CTkLabel(info_row, text="",     font=FONT_SMALL, text_color=C["muted"], anchor="e")
        self.eta_lbl.pack(side="right")

    def update(self, pct, speed="", eta=""):
        self.bar.set(pct)
        self.pct_lbl.configure(text=f"{int(pct*100)}%")
        self.spd_lbl.configure(text=speed)
        self.eta_lbl.configure(text=f"ETA {eta}" if eta else "")

    def reset(self):
        self.update(0)