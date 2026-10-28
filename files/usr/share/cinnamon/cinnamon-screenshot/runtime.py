# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
"""Per-user capture exclusion and runtime state shared by installed/local runs."""
import fcntl
import os
from pathlib import Path
import tempfile


def runtime_directory():
    base = Path(os.environ.get('CINNAMON_SCREENSHOT_RUNTIME_BASE',
                               os.environ.get('XDG_RUNTIME_DIR', tempfile.gettempdir())))
    directory = base / ('cinnamon-screenshot-' + str(os.getuid()))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory


class CaptureLock:
    def __init__(self):
        self._file = None

    def acquire(self):
        if self._file is not None:
            return False
        handle = (runtime_directory() / 'capture.lock').open('a')
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return False
        self._file = handle
        return True

    def release(self):
        if self._file is not None:
            self._file.close()
            self._file = None
