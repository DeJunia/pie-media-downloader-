"""
YT Vault — Production YouTube Downloader
Entry point: launches splash screen then main app.
"""

import sys
import os

# ── Ensure project root is on path ─────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import launch

if __name__ == "__main__":
    launch()
