"""
app.py — Main application shell: sidebar, routing, toast notifications
"""

import customtkinter as ctk
import threading
import time

import core.database as db
from ui.components import C, FONT_HEAD, FONT_SUB, FONT_SMALL

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

NAV_ITEMS = [
    ("⬇", "Download",  "page_down"),
    ("📋", "History",   "page_hist"),
    ("⚙", "Settings",  "page_set"),
]


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YT Vault")
        self.geometry("1000x680")
        self.minsize(900, 620)
        self.configure(fg_color=C["bg"])

        self._pages   = {}
        self._active  = None
        self._toast   = None

        self._build_shell()
        self._show_page("page_down")

    # ── Shell layout ──────────────────────────────────────────────────────────
    def _build_shell(self):
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(
            root, fg_color=C["panel"], corner_radius=0, width=200
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=80)
        logo.pack(fill="x")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="YT", font=("Georgia", 26, "bold"),
                     text_color=C["accent"]).place(relx=0.18, rely=0.5, anchor="center")
        ctk.CTkLabel(logo, text="Vault", font=("Georgia", 26),
                     text_color=C["fg"]).place(relx=0.56, rely=0.5, anchor="center")

        ctk.CTkFrame(self.sidebar, fg_color=C["border"], height=1).pack(fill="x")

        # Nav buttons
        self._nav_btns = {}
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", pady=16)

        for icon, label, page_id in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}   {label}",
                font=("Helvetica", 13),
                anchor="w",
                fg_color="transparent",
                hover_color=C["card"],
                text_color=C["fg2"],
                height=44,
                corner_radius=8,
                command=lambda p=page_id: self._show_page(p),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_btns[page_id] = btn

        # Sidebar footer
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=10, pady=16)
        ctk.CTkLabel(footer, text="v2.0  •  yt-dlp powered",
                     font=("Helvetica", 9), text_color=C["fg3"]).pack()

        # ── Content area ──────────────────────────────────────────────────────
        self.content = ctk.CTkFrame(root, fg_color=C["bg"], corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        # Lazy-init pages
        from ui.page_downloader import DownloaderPage
        from ui.page_history    import HistoryPage
        from ui.page_settings   import SettingsPage

        self._pages["page_down"] = DownloaderPage(self.content, self._toast_msg)
        self._pages["page_hist"] = HistoryPage(self.content,    self._toast_msg)
        self._pages["page_set"]  = SettingsPage(self.content,   self._toast_msg,
                                                 self._on_theme_change)

        for p in self._pages.values():
            p.place(relwidth=1, relheight=1)

        # ── Toast overlay ─────────────────────────────────────────────────────
        self._toast_lbl = ctk.CTkLabel(
            self, text="",
            font=("Helvetica", 12), text_color="white",
            fg_color="#222233", corner_radius=10,
            padx=18, pady=10,
        )

    # ── Navigation ────────────────────────────────────────────────────────────
    def _show_page(self, page_id):
        if page_id == "page_hist":
            self._pages["page_hist"].refresh()

        self._pages[page_id].tkraise()
        self._active = page_id

        for pid, btn in self._nav_btns.items():
            if pid == page_id:
                btn.configure(fg_color=C["card2"], text_color=C["fg"])
            else:
                btn.configure(fg_color="transparent", text_color=C["fg2"])

    # ── Toast notifications ───────────────────────────────────────────────────
    def _toast_msg(self, msg, kind="info"):
        colors = {
            "success": C["green"],
            "error":   C["accent"],
            "warn":    C["yellow"],
            "info":    C["blue"],
        }
        bg_map = {
            "success": "#0f2a1a",
            "error":   "#2a0f10",
            "warn":    "#2a220a",
            "info":    "#0a1a2a",
        }
        fg  = colors.get(kind, C["fg2"])
        bg  = bg_map.get(kind, C["card2"])

        self._toast_lbl.configure(text=f"  {msg}  ", text_color=fg, fg_color=bg)
        self._toast_lbl.place(relx=0.5, rely=0.95, anchor="s")
        self._toast_lbl.lift()

        if self._toast and self._toast.is_alive():
            self._toast_hide_flag = True
        self._toast_hide_flag = False

        def hide():
            time.sleep(3)
            if not self._toast_hide_flag:
                self.after(0, self._toast_lbl.place_forget)

        self._toast = threading.Thread(target=hide, daemon=True)
        self._toast.start()

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _on_theme_change(self, mode):
        pass   # CustomTkinter handles it globally


# ── Entry point ────────────────────────────────────────────────────────────────
def launch():
    # Show splash first, then open main window
    root = ctk.CTk()
    root.withdraw()   # hidden holder window (keeps event loop alive)

    def open_main():
        root.destroy()
        app = MainApp()
        app.mainloop()

    from ui.splash import SplashScreen
    SplashScreen(on_done=open_main)
    root.mainloop()
