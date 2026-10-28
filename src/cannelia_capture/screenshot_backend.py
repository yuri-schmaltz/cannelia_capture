# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
from gi.repository import GObject

from backends.cinnamon import CinnamonBackend
from backends.x11 import X11Backend
from backends.legacy import LegacyBackend


class Backend(GObject.Object):
    """Routes screenshot calls to the cinnamon DBus backend when it is
    available, falling back to the X11 backend for full-screen captures
    otherwise. Emits 'online-changed' whenever the cinnamon service appears
    or disappears so the UI can adjust which modes are offered."""

    __gsignals__ = {
        'online-changed': (GObject.SignalFlags.RUN_LAST, None, (bool,)),
    }

    def __init__(self):
        super().__init__()
        self._cinnamon = CinnamonBackend()
        self._legacy = LegacyBackend()
        self._x11 = X11Backend()
        self._cinnamon.connect('online-changed', self._on_cinnamon_online_changed)
        self._legacy.connect('online-changed', self._on_cinnamon_online_changed)

    def _on_cinnamon_online_changed(self, _backend, online):
        self.emit('online-changed', self.is_available())

    def is_available(self):
        return self._cinnamon.is_available() or self._legacy.is_available()

    def supports_window_selection(self):
        return self._cinnamon.is_available()

    def handles_clipboard(self):
        return self._cinnamon.is_available()

    def error(self):
        return getattr(self._active(), 'last_error', None)

    def cancelled(self):
        return getattr(self._active(), 'last_cancelled', False)

    def capture_file(self, *args, **kwargs):
        self._active().capture_file(*args, **kwargs)

    def _active(self):
        if self._cinnamon.is_available():
            return self._cinnamon
        return self._legacy if self._legacy.is_available() else self._x11

    def screenshot(self, include_pointer, on_done, copy_to_clipboard=False):
        self._active().screenshot(include_pointer, on_done, copy_to_clipboard=copy_to_clipboard)

    def screenshot_window(self, include_pointer, include_shadow, on_done, copy_to_clipboard=False):
        self._active().screenshot_window(include_pointer, include_shadow, on_done, copy_to_clipboard=copy_to_clipboard)

    def screenshot_window_by_id(self, window_id, include_pointer, include_shadow, on_done, copy_to_clipboard=False):
        self._active().screenshot_window_by_id(window_id, include_pointer, include_shadow, on_done, copy_to_clipboard=copy_to_clipboard)

    def screenshot_area(self, x, y, w, h, include_pointer, on_done, copy_to_clipboard=False):
        self._active().screenshot_area(x, y, w, h, include_pointer, on_done, copy_to_clipboard=copy_to_clipboard)

    def select_area(self, on_done):
        self._active().select_area(on_done)

    def select_window(self, on_done):
        self._active().select_window(on_done)
