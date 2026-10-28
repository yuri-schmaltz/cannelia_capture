# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
"""Compatibility with the screenshot interface provided by Cinnamon 6.6.

Captures the focused window, not an interactively picked one. Frames are
always included; shadow control and area cursor capture are unavailable.
Clipboard ownership stays with the GTK client.
"""
import os

from gi.repository import Gio, GLib, GObject

from backends.cinnamon import CinnamonBackend
import prefs


class LegacyBackend(CinnamonBackend):
    clipboard_via_gtk = True

    def _file_parameters(self, mode, path, include_pointer, include_shadow,
                         copy_to_clipboard, area_rect=None, window_id=None):
        if area_rect is not None:
            return 'ScreenshotArea', GLib.Variant('(iiiibs)', (*area_rect, prefs.get_use_flash(), path))
        if mode == 'window':
            return 'ScreenshotWindow', GLib.Variant('(bbbs)', (True, include_pointer, prefs.get_use_flash(), path))
        return 'Screenshot', GLib.Variant('(bbs)', (include_pointer, prefs.get_use_flash(), path))
    def __init__(self):
        GObject.Object.__init__(self)
        self._proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
            None, 'org.gnome.Shell.Screenshot', '/org/gnome/Shell/Screenshot',
            'org.gnome.Shell.Screenshot', None,
        )
        self._proxy.connect('notify::g-name-owner', self._on_name_owner_changed)

    def is_available(self):
        # Modern GNOME restricts this API; only use it in Cinnamon sessions.
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower().split(':')
        return 'x-cinnamon' in desktop and super().is_available()

    def screenshot(self, include_pointer, on_done, copy_to_clipboard=False):
        path = self._tempfile()
        self._call('Screenshot',
                   GLib.Variant('(bbs)', (include_pointer, prefs.get_use_flash(), path)),
                   lambda result: self._deliver_image(path, result, on_done))

    def screenshot_window(self, include_pointer, include_shadow, on_done, copy_to_clipboard=False):
        path = self._tempfile()
        self._call('ScreenshotWindow',
                   GLib.Variant('(bbbs)', (True, include_pointer, prefs.get_use_flash(), path)),
                   lambda result: self._deliver_image(path, result, on_done))

    def screenshot_area(self, x, y, w, h, include_pointer, on_done, copy_to_clipboard=False):
        path = self._tempfile()
        self._call('ScreenshotArea',
                   GLib.Variant('(iiiibs)', (x, y, w, h, prefs.get_use_flash(), path)),
                   lambda result: self._deliver_image(path, result, on_done))

    def select_window(self, on_done):
        on_done(None)
