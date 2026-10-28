#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
"""Regression checks with synthetic images; never captures the desktop."""
from pathlib import Path
import os
import atexit
import runpy
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
runtime_temp = tempfile.TemporaryDirectory()
atexit.register(runtime_temp.cleanup)
os.environ['CINNAMON_SCREENSHOT_RUNTIME_BASE'] = runtime_temp.name
runpy.run_path(str(root / 'run-screenshot.py'))['prepare']()

import application
from gi.repository import GdkPixbuf, GLib, Gtk
from main_window import MainWindow
from backends.legacy import LegacyBackend
import util


class ScreenshotTests(unittest.TestCase):
    def setUp(self):
        self.app = application.ScreenshotApplication(
            application._build_arg_parser().parse_args(['--interactive']))
        self.app.quit = lambda: None
        self.window = MainWindow(self.app)
        self.pixbuf = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, False, 8, 100, 100)
        self.pixbuf.fill(0x224466ff)
        self.window._set_preview(self.pixbuf)
        self.window._render_rect = (50, 50, 100, 100, 1.0)

    def tearDown(self):
        self.window.window.destroy()
        self.app._capture_lock.release()
        if self.app._capture_timer:
            GLib.source_remove(self.app._capture_timer)
            self.app._capture_timer = 0

    def crop(self, start, end):
        if self.window._on_press(None, SimpleNamespace(x=start[0], y=start[1], button=1)):
            self.window._on_release(None, SimpleNamespace(x=end[0], y=end[1], button=1))
        self.window._on_crop(None)

    def test_outside_crop_keeps_image_and_undo_history(self):
        for start, end in [((160, 60), (170, 80)),
                           ((60, 160), (80, 170)),
                           ((0, 0), (20, 20))]:
            self.crop(start, end)
            self.assertIs(self.window._pixbuf, self.pixbuf)
            self.assertEqual(self.window._undo_stack, [])

    def test_partial_crop_intersects_image_and_can_undo(self):
        self.crop((80, 90), (30, 60))
        cropped = self.window._pixbuf
        self.assertEqual((cropped.get_width(), cropped.get_height()), (30, 30))
        self.window._on_undo(None)
        self.assertIs(self.window._pixbuf, self.pixbuf)

    def test_scaled_reverse_drag(self):
        self.window._render_rect = (50, 50, 50, 50, 0.5)
        self.crop((90, 90), (60, 60))
        cropped = self.window._pixbuf
        self.assertEqual((cropped.get_width(), cropped.get_height()), (60, 60))

    def test_local_resources_and_preferences(self):
        self.assertIsInstance(self.window.window, Gtk.Window)
        import prefs
        prefs.open_preferences(self.window.window, self.app.backend)
        self.assertIsInstance(prefs._current_window.window, Gtk.Window)
        self.assertTrue(prefs._current_window.delay_control.is_ancestor(prefs._current_window.window))
        self.assertTrue(prefs._current_window.pointer_control.is_ancestor(prefs._current_window.window))
        self.assertTrue(prefs._current_window.shadow_control.is_ancestor(prefs._current_window.window))
        self.assertEqual(prefs._current_window.shadow_control.get_sensitive(),
                         self.app.backend.supports_window_selection())
        prefs._current_window.window.destroy()

    def test_about_has_product_version_credits_and_gpl(self):
        from branding import APP_NAME, VERSION, PROJECT_URL
        self.window._on_about(None)
        about = self.window._about_dialog
        self.assertEqual(about.get_program_name(), APP_NAME)
        self.assertEqual(about.get_version(), VERSION)
        self.assertEqual(about.get_website(), PROJECT_URL)
        self.assertEqual(about.get_license_type(), Gtk.License.GPL_2_0)
        self.assertIn('Michael Webster', about.get_authors())
        about.hide()

    def test_save_synthetic_image(self):
        with tempfile.TemporaryDirectory() as temp:
            for ext in ('png', 'jpg', 'bmp', 'tiff'):
                path = str(Path(temp) / ('image.' + ext))
                util.save_pixbuf(self.pixbuf, path)
                loaded = GdkPixbuf.Pixbuf.new_from_file(path)
                self.assertEqual((loaded.get_width(), loaded.get_height()), (100, 100))

    def test_legacy_dbus_signatures(self):
        backend = LegacyBackend()
        calls = []
        backend._call = lambda method, params, done: calls.append((method, params))
        with patch('prefs.get_use_flash', return_value=True):
            backend.screenshot(True, lambda image: None)
            backend.screenshot_window(True, False, lambda image: None)
            backend.screenshot_area(1, 2, 3, 4, False, lambda image: None)
        self.assertEqual([(name, value.get_type_string()) for name, value in calls],
                         [('Screenshot', '(bbs)'), ('ScreenshotWindow', '(bbbs)'),
                          ('ScreenshotArea', '(iiiibs)')])
        self.assertEqual(calls[1][1].unpack()[:3], (True, True, True))

    def test_legacy_flash_respects_preference_in_all_modes(self):
        backend = LegacyBackend()
        calls = []
        backend._call = lambda method, params, done: calls.append(params.unpack())
        for enabled in (False, True):
            calls.clear()
            with patch('prefs.get_use_flash', return_value=enabled):
                backend.screenshot(False, lambda image: None)
                backend.screenshot_window(False, True, lambda image: None)
                backend.screenshot_area(0, 0, 10, 10, False, lambda image: None)
            self.assertEqual([params[-2] for params in calls], [enabled] * 3)

    def test_legacy_clipboard_uses_gtk(self):
        from unittest.mock import patch
        with patch.object(self.app.backend, 'handles_clipboard', return_value=False), \
             patch.object(util, 'copy_pixbuf_to_clipboard') as copy, \
             patch.object(application.GLib, 'idle_add'):
            self.assertTrue(self.app._clipboard_via_gtk_if_needed(self.pixbuf))
            copy.assert_called_once_with(self.pixbuf)

    def test_initial_layout_hides_editor_and_has_no_options_or_close_buttons(self):
        self.window._pixbuf = None
        self.window._update_action_sensitivity()
        self.window.run()
        self.assertFalse(self.window.preview_section.get_visible())
        self.assertFalse(self.window.copy_button.get_visible())
        self.assertFalse(self.window.save_button.get_visible())
        self.assertFalse(self.window.action_bar.get_visible())
        for name in ('options_button', 'options_popover', 'cancel_button', 'delay_spin'):
            self.assertIsNone(self.window.builder.get_object(name))

    def test_capture_reads_preferences_without_reopening_main_window(self):
        with patch('prefs.get_delay', return_value=7), \
             patch('prefs.get_include_pointer', return_value=True), \
             patch('prefs.get_include_shadow', return_value=False), \
             patch.object(self.app, 'capture') as capture:
            self.window._capture()
            self.assertEqual(capture.call_args.args[:4], ('screen', True, False, 7))

    def test_clipboard_and_file_flags_save_and_copy_together(self):
        self.app.args = application._build_arg_parser().parse_args(['--clipboard', '--file', '/tmp/test.png'])
        with patch.object(self.app, '_run_save_to_file') as save:
            self.app._activate()
            save.assert_called_once_with('/tmp/test.png', copy_to_clipboard=True)

    def test_cancellation_with_explicit_file_returns_failure_without_error_popup(self):
        self.app.args.file = '/tmp/test.png'
        self.app.last_error = None
        with patch.object(util, 'notify_error') as error:
            self.app.capture_unsuccessful()
            error.assert_not_called()
        self.assertEqual(self.app._exit_code, 1)

    def test_saving_keeps_preview_and_offers_saved_file(self):
        import prefs
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(prefs, 'get_autosave_to_clipboard', return_value=True), \
             patch.object(prefs, 'get_launch_file_manager', return_value=False), \
             patch.object(util, 'copy_pixbuf_to_clipboard') as copy, \
             patch.object(util, 'show_in_file_manager') as reveal:
            path = str(Path(temp) / 'capture.png')
            self.assertTrue(self.window._save_current(path))
            self.assertTrue(Path(path).exists())
            self.assertTrue(self.window.status_row.get_visible())
            self.assertTrue(self.window.open_folder_button.get_visible())
            self.assertTrue(self.window._saved)
            copy.assert_called_once_with(self.pixbuf)
            self.window._on_open_saved_folder(None)
            reveal.assert_called_once_with(Path(path).as_uri())
            self.crop((60, 60), (90, 90))
            self.assertFalse(self.window._saved)
            self.assertFalse(self.window.status_row.get_visible())

    def test_clipboard_failure_does_not_hide_successful_save(self):
        import prefs
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(prefs, 'get_autosave_to_clipboard', return_value=True), \
             patch.object(prefs, 'get_launch_file_manager', return_value=False), \
             patch.object(util, 'copy_pixbuf_to_clipboard', side_effect=RuntimeError('clipboard failed')):
            path = str(Path(temp) / 'saved.png')
            self.assertTrue(self.window._save_current(path))
            self.assertTrue(Path(path).exists())
            self.assertTrue(self.window._saved)
            self.assertIn(_('Copy failed'), self.window.status_label.get_text())
            self.assertNotIn(' · '+_('Copied'), self.window.status_label.get_text())

    def test_zoom_preserves_selection_dimensions_and_crop(self):
        self.window._selection.rect = (10, 20, 60, 40)
        self.window.zoom_combo.set_active_id('2')
        self.assertEqual(self.window._selection.rect, (10, 20, 60, 40))
        self.assertEqual(self.window.preview_area.get_size_request(), (200, 200))
        self.window._update_action_sensitivity()
        self.assertEqual(self.window.selection_label.get_text(), '60 × 40 px')
        self.window._on_crop(None)
        self.assertEqual((self.window._pixbuf.get_width(), self.window._pixbuf.get_height()), (60, 40))

    def test_missing_folder_keeps_editable_preview_and_reports_problem(self):
        import prefs
        with patch.object(prefs, 'get_save_directory', side_effect=FileNotFoundError('folder missing')):
            self.window._set_preview(self.pixbuf)
        self.assertIs(self.window._pixbuf, self.pixbuf)
        self.assertIsNone(self.window._suggested_path)
        self.assertEqual(self.window.status_label.get_text(), 'folder missing')

    def test_notification_open_folder_action(self):
        from unittest.mock import MagicMock
        proxy = MagicMock()
        proxy.call_sync.return_value = GLib.Variant('(u)', (42,))
        proxy.get_name_owner.return_value = ':1.test'
        done = MagicMock()
        with patch.object(util.Gio.DBusProxy, 'new_for_bus_sync', return_value=proxy), \
             patch.object(util, 'show_in_file_manager') as reveal:
            util.notify_saved('/tmp/capture.png', True, done)
            call = proxy.call_sync.call_args.args
            self.assertEqual(call[0], 'Notify')
            self.assertIn('open-folder', call[1].unpack()[5])
            callback = proxy.connect.call_args.args[1]
            callback(proxy, None, 'ActionInvoked', GLib.Variant('(us)', (42, 'open-folder')))
            reveal.assert_called_once_with('file:///tmp/capture.png')
            done.assert_called_once()


class OptimizationTests(unittest.TestCase):
    def test_modern_direct_calls_match_the_actual_cinnamon_dbus_contract(self):
        import xml.etree.ElementTree as ET
        from backends.cinnamon import CinnamonBackend
        xml = (root / 'upstream/org.cinnamon.Screenshot.xml').read_text()
        methods = {m.get('name'): '('+''.join(a.get('type') for a in m.findall('arg')
                    if a.get('direction') == 'in')+')' for m in ET.fromstring(xml).iter('method')}
        backend = CinnamonBackend()
        for mode, rect, wid in [('screen', None, None), ('window', None, None),
                                ('area', (1,2,3,4), None), ('select_window', None, 100)]:
            method, params = backend._file_parameters(mode, '/tmp/image.png', True, True, True, rect, wid)
            self.assertEqual(params.get_type_string(), methods[method])

    def test_cache_does_not_recompile_unchanged_assets(self):
        prepare = runpy.run_path(str(root / 'run-screenshot.py'))['prepare']
        prepare()
        compiled = root / '.local-screenshot/schemas/gschemas.compiled'
        before = compiled.stat().st_mtime_ns
        with patch('subprocess.run') as run:
            prepare()
            run.assert_not_called()
        self.assertEqual(before, compiled.stat().st_mtime_ns)

    def test_unavailable_save_folder_is_reported(self):
        import prefs
        with patch.object(prefs, 'get_save_directory_uri', return_value='file:///missing-capture-folder'):
            with self.assertRaises(FileNotFoundError):
                prefs.get_save_directory()

    def test_atomic_save_preserves_existing_file_on_encoding_error(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'existing.png'
            path.write_bytes(b'original')
            pixbuf = MagicMock()
            pixbuf.savev.side_effect = RuntimeError('encoding failed')
            with self.assertRaises(RuntimeError):
                util.save_pixbuf(pixbuf, str(path))
            self.assertEqual(path.read_bytes(), b'original')
            self.assertEqual(list(Path(temp).iterdir()), [path])

    def test_unique_capture_names_and_temporary_files(self):
        names = {util.build_filename('/tmp') for _ in range(100)}
        self.assertEqual(len(names), 100)
        backend = LegacyBackend()
        paths = [backend._tempfile() for _ in range(10)]
        try:
            self.assertEqual(len(set(paths)), 10)
        finally:
            for path in paths:
                Path(path).unlink()

    def test_capture_lock_excludes_other_processes_and_recovers(self):
        from runtime import CaptureLock
        lock = CaptureLock()
        self.assertTrue(lock.acquire())
        code = ('import sys; sys.path.insert(0, ' + repr(str(root / 'files/usr/share/cinnamon/cinnamon-screenshot')) + '); '
                'from runtime import CaptureLock; lock=CaptureLock(); print(lock.acquire())')
        try:
            result = subprocess.check_output(['/usr/bin/python3', '-c', code], text=True)
            self.assertEqual(result.strip(), 'False')
        finally:
            lock.release()
        result = subprocess.check_output(['/usr/bin/python3', '-c', code], text=True)
        self.assertEqual(result.strip(), 'True')

    def test_direct_png_avoids_decode_and_second_save(self):
        from capture_result import SavedCapture
        backend = LegacyBackend()
        image = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 2, 2)
        image.fill(0x112233ff)
        received = []
        with tempfile.TemporaryDirectory() as temp:
            destination = str(Path(temp) / 'direct.png')
            def capture(method, parameters, done):
                self.assertEqual(method, 'ScreenshotArea')
                self.assertEqual(parameters.unpack()[-1], destination)
                image.savev(destination, 'png', [], [])
                done((True, destination))
            with patch.object(backend, '_call', side_effect=capture), \
                 patch.object(GdkPixbuf.Pixbuf, 'new_from_file') as decode, \
                 patch.object(util, 'save_pixbuf') as second_save:
                backend.capture_file('area', destination, False, False, received.append, area_rect=(0,0,2,2))
                decode.assert_not_called()
                second_save.assert_not_called()
            self.assertIsInstance(received[0], SavedCapture)
            self.assertEqual(received[0].path, destination)
            self.assertGreater(Path(destination).stat().st_size, 0)

    def test_direct_png_legacy_decodes_only_for_clipboard(self):
        backend = LegacyBackend()
        image = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 2, 2)
        received = []
        with tempfile.TemporaryDirectory() as temp:
            destination = str(Path(temp) / 'clipboard.png')
            def capture(method, parameters, done):
                image.savev(destination, 'png', [], [])
                done((True, destination))
            with patch.object(backend, '_call', side_effect=capture):
                backend.capture_file('screen', destination, False, False, received.append, copy_to_clipboard=True)
            self.assertIsNotNone(received[0].pixbuf)
            self.assertTrue(Path(destination).exists())

    def test_direct_capture_failure_removes_reserved_destination(self):
        backend = LegacyBackend()
        received = []
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / 'failed.png')
            with patch.object(backend, '_call', side_effect=lambda method, params, done: done((False, path))):
                backend.capture_file('screen', path, False, False, received.append)
            self.assertEqual(received, [None])
            self.assertFalse(Path(path).exists())
            self.assertTrue(backend.last_error)

    def test_direct_capture_never_overwrites_an_existing_file(self):
        backend = LegacyBackend()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'existing.png'
            path.write_bytes(b'original')
            with patch.object(backend, '_call') as call:
                backend.capture_file('screen', str(path), False, False, lambda result: None)
                call.assert_not_called()
            self.assertEqual(path.read_bytes(), b'original')

    def test_failed_temporary_capture_is_cleaned_up(self):
        backend = LegacyBackend()
        path = backend._tempfile()
        backend._deliver_image(path, (False, path), lambda image: self.assertIsNone(image))
        self.assertFalse(Path(path).exists())

    def test_notifications_replace_previous_and_ignore_stale_actions(self):
        from unittest.mock import MagicMock
        proxy = MagicMock()
        proxy.call_sync.return_value = GLib.Variant('(u)', (55,))
        proxy.get_name_owner.return_value = ':1.notify'
        first_done, second_done = MagicMock(), MagicMock()
        with tempfile.TemporaryDirectory() as temp, \
             patch('runtime.runtime_directory', return_value=Path(temp)), \
             patch.object(util.Gio.DBusProxy, 'new_for_bus_sync', return_value=proxy), \
             patch.object(util, 'show_in_file_manager') as reveal:
            util.notify_saved('/tmp/first.png', False, first_done)
            first_handler = proxy.connect.call_args.args[1]
            util.notify_saved('/tmp/second.png', False, second_done)
            self.assertEqual(proxy.call_sync.call_args.args[1].unpack()[1], 55)
            second_handler = proxy.connect.call_args.args[1]
            event = GLib.Variant('(us)', (55, 'open-folder'))
            first_handler(proxy, None, 'ActionInvoked', event)
            reveal.assert_not_called()
            second_handler(proxy, None, 'ActionInvoked', event)
            reveal.assert_called_once_with('file:///tmp/second.png')
            first_done.assert_called_once()
            second_done.assert_called_once()

    def test_installer_is_independent_of_checkout_and_can_uninstall(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            prefix = Path(temp) / 'installation with spaces'
            subprocess.run(['/usr/bin/python3', str(root / 'install-screenshot.py'),
                            '--prefix', str(prefix), '--no-shortcuts'], check=True, stdout=subprocess.DEVNULL)
            launcher = prefix / 'bin/cinnamon-screenshot-local'
            result = json.loads(subprocess.check_output([str(launcher), '--check'], cwd='/tmp', text=True))
            self.assertIn(str(prefix), result['module'])
            desktop = prefix / 'share/applications/cinnamon-screenshot-local.desktop'
            from gi.repository import Gio
            self.assertIsNotNone(Gio.DesktopAppInfo.new_from_filename(str(desktop)))
            subprocess.run(['/usr/bin/python3', str(root / 'install-screenshot.py'),
                            '--prefix', str(prefix), '--uninstall'], check=True, stdout=subprocess.DEVNULL)
            self.assertFalse(launcher.exists())
            self.assertFalse(desktop.exists())
            self.assertTrue((prefix / 'config').is_dir())

    def test_shortcut_install_is_idempotent_and_restores_previous_settings(self):
        code = """
import runpy
from pathlib import Path
from gi.repository import Gio
module = runpy.run_path(INSTALLER)
settings = Gio.Settings.new('org.cinnamon.desktop.keybindings')
settings.set_strv('custom-list', ['custom9', 'custom2'])
other = module['custom_settings']('custom9')
other.set_string('name', 'Other app')
other.set_string('command', 'other-command')
other.set_strv('binding', ['<Super>x'])
prior = module['custom_settings']('custom2')
prior.set_string('name', 'Captura: desktop inteiro')
prior.set_string('command', '/old/capture')
prior.set_strv('binding', ['<Super><Shift>a'])
launcher = Path('/test/installed/capture')
backup = module['install_shortcuts'](launcher)
module['install_shortcuts'](launcher, backup)
assert len(settings.get_strv('custom-list')) == 4
module['restore_shortcuts'](launcher, backup)
assert settings.get_strv('custom-list') == ['custom9', 'custom2']
assert prior.get_string('command') == '/old/capture'
assert other.get_string('command') == 'other-command'
other.set_strv('binding', ['<Super><Shift>s'])
try:
    module['install_shortcuts'](launcher)
except RuntimeError:
    pass
else:
    raise AssertionError('conflict was ignored')
""".replace('INSTALLER', repr(str(root / 'install-screenshot.py')))
        env = dict(os.environ, GSETTINGS_BACKEND='memory')
        subprocess.run(['/usr/bin/python3', '-c', code], env=env, check=True)



class SelectionTests(unittest.TestCase):
    def test_resize_handle_and_move_keep_pixel_bounds(self):
        from selection import Selection
        selection = Selection(400, 300)
        selection.begin(20, 30)
        selection.end(180, 130)
        self.assertEqual(selection.rect, (20, 30, 160, 100))
        selection.begin(180, 130)
        selection.end(250, 190)
        self.assertEqual(selection.rect, (20, 30, 230, 160))
        selection.begin(100, 100)
        selection.end(390, 290)
        self.assertEqual(selection.rect, (170, 140, 230, 160))

    def test_all_eight_handles_and_clipping(self):
        from selection import Selection
        for handle in ('nw','n','ne','e','se','s','sw','w'):
            selection = Selection(100, 100)
            selection.rect = (20, 20, 60, 60)
            x, y = selection.handles()[handle]
            self.assertTrue(selection.begin(x, y, scale=2))
            self.assertEqual(selection.drag[0], handle)
            selection.end(-200, 300)
            left, top, width, height = selection.rect
            self.assertGreaterEqual(left, 0)
            self.assertGreaterEqual(top, 0)
            self.assertLessEqual(left+width, 100)
            self.assertLessEqual(top+height, 100)
            self.assertGreater(width, 0)
            self.assertGreater(height, 0)


if __name__ == '__main__':
    unittest.main()
