# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
import os
import sys
import tempfile

import gi
from gi.repository import GdkPixbuf, Gio, GLib, GObject

from backends.base import Backend
from capture_result import SavedCapture
from runtime import runtime_directory
from branding import APP_NAME


BUS_NAME = 'org.cinnamon.Screenshot'
OBJECT_PATH = '/org/cinnamon/Screenshot'
INTERFACE = 'org.cinnamon.Screenshot'


class CinnamonBackend(Backend, GObject.Object):
    __gsignals__ = {
        'online-changed': (GObject.SignalFlags.RUN_LAST, None, (bool,)),
    }

    def __init__(self):
        GObject.Object.__init__(self)
        self._proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
            None,
            BUS_NAME, OBJECT_PATH, INTERFACE,
            None,
        )
        self._proxy.connect('notify::g-name-owner', self._on_name_owner_changed)

    def _on_name_owner_changed(self, *_args):
        self.emit('online-changed', self.is_available())

    def is_available(self):
        return self._proxy.get_name_owner() is not None

    def _tempfile(self):
        fd, path = tempfile.mkstemp(prefix='capture-', suffix='.png', dir=runtime_directory())
        os.close(fd)
        return path

    def _call(self, method, params, on_result):
        """Invoke a DBus method asynchronously; deliver the unpacked
        result tuple (or None on failure) to on_result."""
        self.last_error = None
        self.last_cancelled = False
        def cb(proxy, res):
            try:
                result = proxy.call_finish(res).unpack()
            except GLib.Error as exc:
                self.last_cancelled = exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED)
                if not self.last_cancelled:
                    self.last_error = exc.message
                    print(f'{APP_NAME}: DBus {method} failed: {exc.message}', file=sys.stderr)
                result = None
            on_result(result)
        timeout = 2147483647 if method in ('SelectArea', 'SelectWindow') else 10000
        self._proxy.call(method, params, Gio.DBusCallFlags.NONE, timeout, None, cb)

    def _load_and_unlink(self, path):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        except GLib.Error as exc:
            self.last_error = exc.message
            pixbuf = None
        try:
            os.unlink(path)
        except OSError:
            pass
        return pixbuf

    def _deliver_image(self, path, result, on_done):
        if not result or not result[0]:
            try:
                os.unlink(path)
            except OSError:
                pass
            if not getattr(self, 'last_cancelled', False) and not getattr(self, 'last_error', None):
                self.last_error = _('The screenshot service could not capture the image.')
            on_done(None)
            return
        on_done(self._load_and_unlink(result[1] or path))

    def _file_parameters(self, mode, path, include_pointer, include_shadow,
                         copy_to_clipboard, area_rect=None, window_id=None):
        if area_rect is not None:
            return 'ScreenshotArea', GLib.Variant('(iiiibsb)',
                (*area_rect, include_pointer, path, copy_to_clipboard))
        if window_id is not None:
            return 'ScreenshotWindowById', GLib.Variant('(tbbsb)',
                (window_id, include_shadow, include_pointer, path, copy_to_clipboard))
        if mode == 'window':
            return 'ScreenshotWindow', GLib.Variant('(bbsb)',
                (include_shadow, include_pointer, path, copy_to_clipboard))
        return 'Screenshot', GLib.Variant('(bsb)', (include_pointer, path, copy_to_clipboard))

    def capture_file(self, mode, path, include_pointer, include_shadow, on_done,
                     copy_to_clipboard=False, area_rect=None, window_id=None):
        """Ask the compositor to write PNG directly; decode only for GTK clipboard."""
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        except OSError as exc:
            self.last_error = str(exc)
            on_done(None)
            return
        method, params = self._file_parameters(mode, path, include_pointer, include_shadow,
                                               copy_to_clipboard, area_rect, window_id)
        def done(result):
            if not result or not result[0]:
                try:
                    os.unlink(path)
                except OSError:
                    pass
                if not getattr(self, 'last_cancelled', False) and not getattr(self, 'last_error', None):
                    self.last_error = _('The screenshot service could not save the image.')
                on_done(None)
                return
            actual = result[1] or path
            image = None
            if copy_to_clipboard and getattr(self, 'clipboard_via_gtk', False):
                try:
                    image = GdkPixbuf.Pixbuf.new_from_file(actual)
                except GLib.Error as exc:
                    self.last_error = exc.message
            on_done(SavedCapture(actual, image))
        self._call(method, params, done)

    def screenshot(self, include_pointer, on_done, copy_to_clipboard=False):
        path = self._tempfile()
        self._call('Screenshot',
                   GLib.Variant('(bsb)', (include_pointer, path, copy_to_clipboard)),
                   lambda result: self._deliver_image(path, result, on_done))

    def screenshot_window(self, include_pointer, include_shadow, on_done, copy_to_clipboard=False):
        path = self._tempfile()
        self._call('ScreenshotWindow',
                   GLib.Variant('(bbsb)', (include_shadow, include_pointer, path, copy_to_clipboard)),
                   lambda result: self._deliver_image(path, result, on_done))

    def screenshot_window_by_id(self, window_id, include_pointer, include_shadow, on_done, copy_to_clipboard=False):
        path = self._tempfile()
        self._call('ScreenshotWindowById',
                   GLib.Variant('(tbbsb)', (window_id, include_shadow, include_pointer, path, copy_to_clipboard)),
                   lambda result: self._deliver_image(path, result, on_done))

    def screenshot_area(self, x, y, w, h, include_pointer, on_done, copy_to_clipboard=False):
        path = self._tempfile()
        self._call('ScreenshotArea',
                   GLib.Variant('(iiiibsb)', (x, y, w, h, include_pointer, path, copy_to_clipboard)),
                   lambda result: self._deliver_image(path, result, on_done))

    def select_area(self, on_done):
        self._call('SelectArea', None,
                   lambda result: on_done(tuple(result) if result else None))

    def select_window(self, on_done):
        self._call('SelectWindow', None,
                   lambda result: on_done(result[0] if result else None))
