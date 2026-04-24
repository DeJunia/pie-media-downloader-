"""
ui/splash.py — Animated loading screen shown on startup
"""

import customtkinter as ctk
import threading
import time
from ui.components import C


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, on_done):
        super().__init__()
        self.on_done = on_done
        self.overrideredirect(True)          # borderless
        self.configure(fg_color=C["bg"])
        self.attributes("-topmost", True)

        W, H = 480, 300
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        self._build()
        self._animate()

    def _build(self):
        # Logo area
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.place(relx=0.5, rely=0.38, anchor="center")

        ctk.CTkLabel(
            logo_frame, text="YT", font=("Georgia", 52, "bold"),
            text_color=C["accent"]
        ).pack(side="left")
        ctk.CTkLabel(
            logo_frame, text=" VAULT", font=("Georgia", 52),
            text_color=C["fg"]
        ).pack(side="left")

        ctk.CTkLabel(
            self, text="Your personal media archive",
            font=("Helvetica", 13), text_color=C["fg3"]
        ).place(relx=0.5, rely=0.60, anchor="center")

        # Progress bar
        self.bar = ctk.CTkProgressBar(
            self, width=300, height=3,
            fg_color=C["border"], progress_color=C["accent"],
            corner_radius=2,
        )
        self.bar.set(0)
        self.bar.place(relx=0.5, rely=0.78, anchor="center")

        self.status = ctk.CTkLabel(
            self, text="Initialising…",
            font=("Helvetica", 11), text_color=C["muted"]
        )
        self.status.place(relx=0.5, rely=0.87, anchor="center")

        ctk.CTkLabel(
            self, text="v2.0  •  Powered by yt-dlp",
            font=("Helvetica", 9), text_color=C["fg3"]
        ).place(relx=0.5, rely=0.96, anchor="center")

    def _animate(self):
        steps = [
            (0.15, "Loading database…"),
            (0.35, "Checking ffmpeg…"),
            (0.55, "Preparing UI…"),
            (0.75, "Loading history…"),
            (1.00, "Ready!"),
        ]

        def run():
            import core.database as db
            db.init()
            for pct, msg in steps:
                if not self.winfo_exists():
                    return
                self.after(0, self.bar.set, pct)
                self.after(0, self.status.configure, {"text": msg})
                time.sleep(0.35)
            self.after(200, self._finish)

        threading.Thread(target=run, daemon=True).start()

    def _finish(self):
        self.destroy()
        self.on_done()
