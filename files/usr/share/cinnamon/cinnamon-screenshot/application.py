# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
import sys
import json
import os
import time

from cli import build_arg_parser as _build_arg_parser

from localization import initialize
initialize()

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

import screenshot_backend
import prefs
import util
from branding import APP_NAME
from capture_result import SavedCapture
from runtime import CaptureLock

GLib.set_application_name(APP_NAME)


class ScreenshotApplication:
    def __init__(self, args):
        self.args = args
        self.backend = screenshot_backend.Backend()
        self._exit_code = 0
        self.last_error = None
        self._capture_lock = CaptureLock()
        self._capture_timer = 0

    def quit(self):
        if self._capture_timer:
            GLib.source_remove(self._capture_timer)
            self._capture_timer = 0
        self._capture_lock.release()
        if Gtk.main_level():
            Gtk.main_quit()

    def run(self):
        def activate():
            try:
                self._activate()
            except (OSError, ValueError, RuntimeError, GLib.Error) as exc:
                self.fail(str(exc))
            return GLib.SOURCE_REMOVE
        GLib.idle_add(activate)
        Gtk.main()
        return self._exit_code

    def fail(self, message):
        self._exit_code = 1
        print(APP_NAME + ': ' + message, file=sys.stderr)
        if getattr(self.args, 'no_notification', False):
            self.quit()
        else:
            util.notify_error(message, self.quit)

    def profile_saved(self, path):
        if getattr(self.args, 'profile', False):
            start = int(os.environ.get('CINNAMON_SCREENSHOT_START_NS', time.monotonic_ns()))
            print(json.dumps({'event': 'saved', 'elapsed_ms': (time.monotonic_ns()-start)/1e6,
                              'path': path}), file=sys.stderr)

    def capture_unsuccessful(self):
        if self.last_error:
            self.fail(self.last_error)
        else:
            self._exit_code = 1 if self.args.file else 0
            self.quit()

    def _activate(self):
        args = self.args
        if args.clipboard and not args.file:
            self._run_clipboard()
        elif args.file and not args.interactive:
            self._run_save_to_file(args.file,
                                   copy_to_clipboard=args.clipboard or prefs.get_autosave_to_clipboard())
        elif args.interactive:
            self._run_window()
        elif prefs.get_autosave_to_file():
            filename = util.build_filename(
                prefs.get_save_directory(),
                file_type=prefs.get_default_file_type(),
            )
            self._run_save_to_file(filename, copy_to_clipboard=prefs.get_autosave_to_clipboard())
        else:
            self._run_capture_to_editor()

    def _resolve_mode(self):
        if self.args.select_window:
            return 'select_window'
        if self.args.window:
            return 'window'
        if self.args.area:
            return 'area'
        if self.args.monitor is not None:
            return 'monitor'
        return 'screen'

    def capture(self, mode, include_pointer, include_shadow, delay, on_done, area_rect=None, copy_to_clipboard=False, destination=None):
        # Monitor mode and area mode both end up calling screenshot_area,
        # which both grabs and flashes the captured rect on the server side.
        # Area mode without a rect runs the selector first to get one;
        # select_window mode runs the window picker first for an id.
        # copy_to_clipboard asks the compositor to also place the grab on the
        # clipboard. on_done still receives the pixbuf either way.
        window_id = None
        self.last_error = None
        if not self._capture_lock.acquire():
            self.last_error = _('Another capture is already in progress.')
            GLib.idle_add(lambda: (on_done(None), GLib.SOURCE_REMOVE)[1])
            return

        def completed(result):
            if result is None:
                self.last_error = self.backend.error()
                if not self.last_error and not self.backend.cancelled():
                    self.last_error = _('The image could not be captured. Check the capture service and try again.')
            try:
                on_done(result)
            finally:
                self._capture_lock.release()

        def do_capture():
            self._capture_timer = 0
            try:
                if destination:
                    self.backend.capture_file(mode, destination, include_pointer, include_shadow, completed,
                        copy_to_clipboard=copy_to_clipboard, area_rect=area_rect, window_id=window_id)
                elif area_rect is not None:
                    x, y, w, h = area_rect
                    self.backend.screenshot_area(x, y, w, h, include_pointer, completed, copy_to_clipboard=copy_to_clipboard)
                elif window_id is not None:
                    self.backend.screenshot_window_by_id(window_id, include_pointer, include_shadow, completed, copy_to_clipboard=copy_to_clipboard)
                elif mode == 'window':
                    self.backend.screenshot_window(include_pointer, include_shadow, completed, copy_to_clipboard=copy_to_clipboard)
                else:
                    self.backend.screenshot(include_pointer, completed, copy_to_clipboard=copy_to_clipboard)
            except (OSError, ValueError, RuntimeError, GLib.Error) as exc:
                self.last_error = str(exc)
                try:
                    on_done(None)
                finally:
                    self._capture_lock.release()
            return GLib.SOURCE_REMOVE

        def schedule(fn):
            if delay > 0:
                self._capture_timer = GLib.timeout_add_seconds(delay, fn)
            else:
                self._capture_timer = GLib.idle_add(fn)

        if mode == 'area' and area_rect is None:
            def after_select(rect):
                nonlocal area_rect
                if rect is None:
                    completed(None)
                    return
                area_rect = rect
                schedule(do_capture)
            try:
                self.backend.select_area(after_select)
            except (OSError, RuntimeError, GLib.Error) as exc:
                self.last_error = str(exc)
                try:
                    on_done(None)
                finally:
                    self._capture_lock.release()
        elif mode == 'select_window':
            def after_pick(wid):
                nonlocal window_id
                if wid is None:
                    completed(None)
                    return
                window_id = wid
                schedule(do_capture)
            try:
                self.backend.select_window(after_pick)
            except (OSError, RuntimeError, GLib.Error) as exc:
                self.last_error = str(exc)
                try:
                    on_done(None)
                finally:
                    self._capture_lock.release()
        else:
            schedule(do_capture)

    def _run_window(self):
        from main_window import MainWindow
        win = MainWindow(self)
        win.run()

    def _run_capture_to_editor(self):
        # Non-interactive launch (e.g. the screenshot keybinding): grab first
        # and only build the editor window once we have an image to show.
        mode = self._resolve_mode()
        area_rect = None
        if mode == 'monitor':
            area_rect = util.monitor_rect(self.args.monitor)
            if area_rect is None:
                mode = 'screen'
        include_pointer = self.args.include_pointer or prefs.get_include_pointer()
        include_shadow = self.args.include_shadow or prefs.get_include_shadow()
        delay = self.args.delay if self.args.delay is not None else prefs.get_delay()

        def done(pixbuf):
            if pixbuf is None:
                if self.last_error:
                    self.fail(self.last_error)
                else:
                    self.quit()
                return
            from main_window import MainWindow
            win = MainWindow(self)
            win.show_with_pixbuf(pixbuf)

        self.capture(mode, include_pointer, include_shadow, delay, done, area_rect=area_rect)

    def _run_clipboard(self):
        mode = self._resolve_mode()
        area_rect = None
        if mode == 'monitor':
            area_rect = util.monitor_rect(self.args.monitor)
            if area_rect is None:
                mode = 'screen'
        include_pointer = self.args.include_pointer or prefs.get_include_pointer()
        include_shadow = self.args.include_shadow or prefs.get_include_shadow()
        delay = self.args.delay if self.args.delay is not None else prefs.get_delay()

        def done(pixbuf):
            if pixbuf is None:
                self.capture_unsuccessful()
                return
            if not self._clipboard_via_gtk_if_needed(pixbuf):
                self.quit()

        self.capture(mode, include_pointer, include_shadow, delay, done,
                     area_rect=area_rect, copy_to_clipboard=True)

    def _clipboard_via_gtk_if_needed(self, pixbuf):
        if self.backend.handles_clipboard():
            return False
        try:
            util.copy_pixbuf_to_clipboard(pixbuf)
        except (RuntimeError, GLib.Error) as exc:
            self.fail(str(exc))
            return True
        GLib.idle_add(self._finish_clipboard)
        return True

    def _finish_clipboard(self):
        self.quit()
        return GLib.SOURCE_REMOVE

    def _run_save_to_file(self, path, copy_to_clipboard=False):
        mode = self._resolve_mode()
        area_rect = None
        if mode == 'monitor':
            area_rect = util.monitor_rect(self.args.monitor)
            if area_rect is None:
                mode = 'screen'
        include_pointer = self.args.include_pointer or prefs.get_include_pointer()
        include_shadow = self.args.include_shadow or prefs.get_include_shadow()
        delay = self.args.delay if self.args.delay is not None else prefs.get_delay()

        direct = (self.backend.is_available() and os.path.splitext(path)[1].lower() == '.png'
                  and not os.path.exists(path))

        def done(result):
            if result is None:
                self.capture_unsuccessful()
                return
            actual = result.path if isinstance(result, SavedCapture) else path
            pixbuf = result.pixbuf if isinstance(result, SavedCapture) else result
            try:
                if not isinstance(result, SavedCapture):
                    util.save_pixbuf(pixbuf, actual)
            except Exception as exc:
                self.fail(_('Could not save the screenshot: %(error)s') % {'error': str(exc)})
                return
            self.profile_saved(actual)
            if copy_to_clipboard and not self.backend.handles_clipboard():
                try:
                    if pixbuf is None:
                        raise RuntimeError(_('The image could not be copied to the clipboard.'))
                    util.copy_pixbuf_to_clipboard(pixbuf)
                except (RuntimeError, GLib.Error) as exc:
                    self.fail(_('The screenshot was saved, but copying failed: %(error)s') % {'error': str(exc)})
                    return
            if self.args.file is None and not getattr(self.args, 'no_notification', False):
                util.notify_saved(actual, copy_to_clipboard, self.quit)
                return
            self.quit()

        self.capture(mode, include_pointer, include_shadow, delay, done,
                     area_rect=area_rect, copy_to_clipboard=copy_to_clipboard,
                     destination=path if direct else None)



def main():
    parser = _build_arg_parser()
    args = parser.parse_args()
    if args.delay is not None and not 0 <= args.delay <= 3600:
        parser.error('--delay must be between 0 and 3600 seconds')

    target_flags = [args.window, args.select_window, args.area, args.monitor is not None]
    if sum(bool(f) for f in target_flags) > 1:
        parser.error('--window, --select-window, --area, and --monitor are mutually exclusive')
    if args.include_shadow and not (args.window or args.select_window):
        parser.error('--include-shadow requires --window or --select-window')
    if args.interactive and (args.delay is not None or args.include_pointer or args.include_shadow):
        parser.error('--interactive cannot be combined with --delay, --include-pointer, or --include-shadow')

    app = ScreenshotApplication(args)
    if args.check:
        from main_window import MainWindow
        window = MainWindow(app)
        print(json.dumps({'backend': type(app.backend._active()).__name__,
                          'service_available': app.backend.is_available(),
                          'title': window.window.get_title(), 'module': __file__}))
        window.window.destroy()
        return 0
    if args.select_window and not app.backend.supports_window_selection():
        parser.error('--select-window requires the new Cinnamon screenshot service; use --window to capture the focused window')
    return app.run()
