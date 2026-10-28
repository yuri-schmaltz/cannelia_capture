# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
from dataclasses import dataclass


@dataclass
class SavedCapture:
    path: str
    pixbuf: object = None
