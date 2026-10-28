# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
import os

import cairo

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk

import prefs
import util
from localization import load_builder
from selection import Selection
from branding import APP_NAME, VERSION, PROJECT_URL


PKGDATADIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(PKGDATADIR, 'icons')

Gtk.IconTheme.get_default().append_search_path(ICON_DIR)


class MainWindow:
    def __init__(self, app):
        self.app = app
        self.builder = load_builder(os.path.join(PKGDATADIR, 'main-window.ui'))
        self.window = self.builder.get_object('window')

        self.mode_screen = self.builder.get_object('mode_screen')
        self.mode_monitor = self.builder.get_object('mode_monitor')
        self.mode_window = self.builder.get_object('mode_window')
        self.mode_area = self.builder.get_object('mode_area')
        self.take_button = self.builder.get_object('take_button')

        self.preview_stack = self.builder.get_object('preview_stack')
        self.preview_area = self.builder.get_object('preview_area')
        self.zoom_combo = self.builder.get_object('zoom_combo')
        self.selection_label = self.builder.get_object('selection_label')

        self.crop_button = self.builder.get_object('crop_button')
        self.undo_button = self.builder.get_object('undo_button')
        self.copy_button = self.builder.get_object('copy_button')
        self.save_button = self.builder.get_object('save_button')
        self.action_bar = self.builder.get_object('action_bar')
        self.preview_section = self.builder.get_object('preview_section')
        self.status_row = self.builder.get_object('status_row')
        self.status_label = self.builder.get_object('status_label')
        self.open_folder_button = self.builder.get_object('open_folder_button')

        self.service_infobar = self.builder.get_object('service_infobar')

        # Widgets that only work when the cinnamon screenshot service is
        # owned. The X11 fallback can't pick specific windows or arbitrary
        # regions, and can't overlay the cursor or apply window shadows.
        self.service_widgets = [
            self.mode_window,
            self.mode_area,
        ]

        self._pixbuf = None
        self._undo_stack = []
        self._suggested_path = None
        self._selection = None
        self._zoom = 0.0
        self._render_rect = (0, 0, 0, 0, 1.0)
        self._capture_timeout_id = 0
        self._saved = False
        self._saved_path = None
        self._had_preview = False
        self._about_dialog = None

        self.window.get_style_context().add_class('screenshot-app')
        self.window.get_style_context().add_class('unified')
        css = Gtk.CssProvider()
        css.load_from_data(b'''
            window.screenshot-app.unified {
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }
            .screenshot-app .capture-mode:checked {
                border-color: @theme_selected_bg_color;
                box-shadow: inset 0 -3px @theme_selected_bg_color;
            }
            .screenshot-app .capture-mode { padding: 8px; }
            .screenshot-app drawingarea { background-color: alpha(#000, 0.12); }
        ''')
        Gtk.StyleContext.add_provider_for_screen(self.window.get_screen(), css,
                                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        for mode in (self.mode_screen, self.mode_monitor, self.mode_window, self.mode_area):
            mode.get_style_context().add_class('capture-mode')

        self.window.connect('destroy', self._on_window_destroy)

        self._init_options()
        self._init_preview()
        self._init_actions()
        self._init_service_monitor()
        self._update_action_sensitivity()

    def run(self):
        if self.app.args.interactive:
            self.window.show_all()
        else:
            self._capture(initial=True)

    def show_with_pixbuf(self, pixbuf):
        self._set_preview(pixbuf)
        self.window.show_all()

    # ------------------------------------------------------------------
    # init
    # ------------------------------------------------------------------

    def _init_options(self):
        self.mode_monitor.set_sensitive(Gdk.Display.get_default().get_n_monitors() > 1)

        args = self.app.args
        if args.window or args.select_window:
            self.mode_window.set_active(True)
        elif args.area:
            self.mode_area.set_active(True)
        elif args.monitor is not None and self.mode_monitor.get_sensitive():
            self.mode_monitor.set_active(True)

        self.take_button.connect('clicked', self._on_take_clicked)

    def _init_preview(self):
        self.preview_area.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )
        self.preview_area.connect('realize', self._on_preview_realize)
        self.preview_area.connect('draw', self._on_draw)
        self.preview_area.connect('button-press-event', self._on_press)
        self.preview_area.connect('motion-notify-event', self._on_motion)
        self.preview_area.connect('button-release-event', self._on_release)

        self.zoom_combo.set_active_id('fit')
        self.zoom_combo.connect('changed', self._on_zoom_changed)
        self.crop_button.connect('clicked', self._on_crop)
        self.undo_button.connect('clicked', self._on_undo)
        self.copy_button.connect('clicked', self._on_copy)

        accel = Gtk.AccelGroup()
        accel.connect(Gdk.KEY_z, Gdk.ModifierType.CONTROL_MASK,
                      Gtk.AccelFlags.VISIBLE,
                      lambda *_: self._on_undo(None) or True)
        accel.connect(Gdk.KEY_Escape, 0, Gtk.AccelFlags.VISIBLE,
                      lambda *_: self._on_cancel(None) or True)
        self.window.add_accel_group(accel)

    def _on_preview_realize(self, widget):
        widget.get_window().set_cursor(
            Gdk.Cursor.new_for_display(
                Gdk.Display.get_default(), Gdk.CursorType.CROSSHAIR))

    def _init_service_monitor(self):
        self.app.backend.connect('online-changed', self._on_service_online_changed)
        self._update_service_state(self.app.backend.is_available())

    def _on_service_online_changed(self, _backend, online):
        self._update_service_state(online)

    def _update_service_state(self, online):
        self.service_infobar.set_revealed(not online)
        self.service_infobar.set_visible(not online)
        self.mode_monitor.set_sensitive(Gdk.Display.get_default().get_n_monitors() > 1)
        for widget in self.service_widgets:
            widget.set_sensitive(online)
        if not online and (self.mode_window.get_active() or self.mode_area.get_active()):
            self.mode_screen.set_active(True)

    def _init_actions(self):
        self.save_button.connect('clicked', self._on_save)
        self.open_folder_button.connect('clicked', self._on_open_saved_folder)

        menu = Gtk.Menu()
        open_folder_item = Gtk.MenuItem(label=_('Open save folder'))
        open_folder_item.connect('activate', self._on_open_save_folder)
        menu.append(open_folder_item)
        menu.append(Gtk.SeparatorMenuItem())
        prefs_item = Gtk.MenuItem(label=_('Preferences'))
        prefs_item.connect('activate', self._on_preferences)
        menu.append(prefs_item)
        about_item = Gtk.MenuItem(label=_('About Cannelia Capture'))
        about_item.connect('activate', self._on_about)
        menu.append(about_item)
        menu.show_all()
        self.builder.get_object('menu_button').set_popup(menu)

    # ------------------------------------------------------------------
    # mode handling and capture
    # ------------------------------------------------------------------

    def _on_take_clicked(self, _b):
        self._capture()

    def _capture(self, initial=False):
        if self.mode_window.get_active():
            mode = ('window' if (initial and self.app.args.window)
                    or not self.app.backend.supports_window_selection() else 'select_window')
        elif self.mode_area.get_active():
            mode = 'area'
        elif self.mode_monitor.get_active():
            mode = 'monitor'
        else:
            mode = 'screen'

        if initial:
            args = self.app.args
            delay = args.delay if args.delay is not None else prefs.get_delay()
            include_pointer = args.include_pointer or prefs.get_include_pointer()
            include_shadow = args.include_shadow or prefs.get_include_shadow()
        else:
            delay = prefs.get_delay()
            include_pointer = prefs.get_include_pointer()
            include_shadow = prefs.get_include_shadow()

        area_rect = None
        if mode == 'monitor':
            if initial and self.app.args.monitor is not None:
                area_rect = util.monitor_rect(self.app.args.monitor)
            else:
                area_rect = util.monitor_rect_for_window(self.window.get_window())
            if area_rect is None:
                mode = 'screen'

        def done(pixbuf):
            if pixbuf is None:
                if self.app.last_error:
                    self._show_status(self.app.last_error)
                self.window.show_all()
                return
            self._set_preview(pixbuf)
            if self._suggested_path and prefs.get_autosave_to_file() and not self.app.args.file:
                self._save_current(self._suggested_path)
            self.window.show_all()

        def start_capture():
            self._capture_timeout_id = 0
            self.app.capture(mode, include_pointer, include_shadow, delay, done, area_rect=area_rect)
            return GLib.SOURCE_REMOVE

        if self.window.get_visible():
            self.window.hide()
            self._capture_timeout_id = GLib.timeout_add(200, start_capture)
        else:
            start_capture()

    def _set_preview(self, pixbuf):
        if pixbuf is None:
            self._update_action_sensitivity()
            return
        self._pixbuf = pixbuf
        self._saved = False
        self._saved_path = None
        self.status_row.hide()
        self.save_button.set_label(_('Save'))
        self._undo_stack.clear()
        self._selection = Selection(pixbuf.get_width(), pixbuf.get_height())
        self.zoom_combo.set_active_id('fit')
        try:
            self._suggested_path = util.build_filename(
                prefs.get_save_directory(), file_type=prefs.get_default_file_type())
        except (OSError, ValueError) as exc:
            self._suggested_path = None
            self._show_status(str(exc))
        self._update_action_sensitivity()
        self.preview_area.queue_draw()

    def _update_action_sensitivity(self):
        has_preview = self._pixbuf is not None
        has_selection = self._current_selection_widget_coords() is not None
        self.preview_stack.set_visible_child_name('preview' if has_preview else 'placeholder')
        self.crop_button.set_sensitive(has_preview and has_selection)
        self.copy_button.set_sensitive(has_preview)
        self.save_button.set_sensitive(has_preview)
        self.undo_button.set_sensitive(has_preview and bool(self._undo_stack))
        self._update_dimensions()
        self.preview_section.set_visible(has_preview)
        self.action_bar.set_visible(has_preview)
        self.copy_button.set_visible(has_preview)
        self.save_button.set_visible(has_preview)
        self.take_button.set_label(_('New capture') if has_preview else _('Capture'))
        self.take_button.get_style_context().remove_class('suggested-action')
        if not has_preview:
            self.take_button.get_style_context().add_class('suggested-action')
        if has_preview and not self._had_preview:
            self.window.resize(620, 560)
        self._had_preview = has_preview

    # ------------------------------------------------------------------
    # preview rendering
    # ------------------------------------------------------------------

    def _on_draw(self, widget, cr):
        if self._pixbuf is None:
            return False
        alloc = widget.get_allocation()
        pw, ph = self._pixbuf.get_width(), self._pixbuf.get_height()
        if pw == 0 or ph == 0:
            return False

        scale = self._zoom or min(alloc.width / pw, alloc.height / ph, 1.0)
        rw, rh = pw * scale, ph * scale
        rx = (alloc.width - rw) / 2
        ry = (alloc.height - rh) / 2
        self._render_rect = (rx, ry, rw, rh, scale)

        cr.save()
        cr.translate(rx, ry)
        cr.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(cr, self._pixbuf, 0, 0)
        cr.paint()
        cr.restore()

        self._draw_crop_overlay(cr, alloc)

        return False

    def _draw_crop_overlay(self, cr, alloc):
        sel = self._current_selection_widget_coords()
        if sel is None:
            return
        sx, sy, sw, sh = sel
        rx, ry, rw, rh, scale = self._render_rect
        cr.save()
        cr.rectangle(rx, ry, rw, rh)
        cr.rectangle(sx, sy, sw, sh)
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        cr.set_source_rgba(0, 0, 0, 0.35)
        cr.fill()
        cr.set_fill_rule(cairo.FILL_RULE_WINDING)
        cr.set_line_width(1)
        cr.rectangle(sx+0.5, sy+0.5, sw, sh)
        cr.set_source_rgb(1, 1, 1)
        cr.stroke()
        for x, y in self._selection.handles().values():
            cr.rectangle(rx+x*scale-4, ry+y*scale-4, 8, 8)
            cr.set_source_rgb(1, 1, 1)
            cr.fill_preserve()
            cr.set_source_rgb(0, 0, 0)
            cr.stroke()
        cr.restore()

    def _current_selection_widget_coords(self):
        if self._selection is None or self._selection.rect is None:
            return None
        x, y, w, h = self._selection.rect
        rx, ry, _rw, _rh, scale = self._render_rect
        return rx+x*scale, ry+y*scale, w*scale, h*scale

    def _widget_to_image(self, x, y):
        rx, ry, _rw, _rh, scale = self._render_rect
        return (x-rx)/scale, (y-ry)/scale

    def _update_dimensions(self):
        if self._selection is not None and self._pixbuf is not None:
            rect = self._selection.rect
            w, h = rect[2:] if rect else (self._pixbuf.get_width(), self._pixbuf.get_height())
            self.selection_label.set_text(f'{w} × {h} px')

    def _on_zoom_changed(self, combo):
        active = combo.get_active_id()
        self._zoom = 0.0 if active == 'fit' or active is None else float(active)
        if self._pixbuf is None:
            return
        if self._zoom:
            self.preview_area.set_size_request(int(self._pixbuf.get_width()*self._zoom),
                                              int(self._pixbuf.get_height()*self._zoom))
        else:
            self.preview_area.set_size_request(-1, -1)
        self.preview_area.queue_draw()

    # Crop coordinates stay in image pixels when zoom/scroll/allocation changes.
    def _on_press(self, _w, event):
        if self._selection is None or event.button != 1:
            return False
        x, y = self._widget_to_image(event.x, event.y)
        if not self._selection.begin(x, y, self._render_rect[4]):
            return False
        self.preview_area.queue_draw()
        self._update_action_sensitivity()
        return True

    def _on_motion(self, _w, event):
        if self._selection is None or self._selection.drag is None:
            return False
        self._selection.update(*self._widget_to_image(event.x, event.y))
        self._update_action_sensitivity()
        self.preview_area.queue_draw()
        return True

    def _on_release(self, _w, event):
        if self._selection is None or self._selection.drag is None or event.button != 1:
            return False
        self._selection.end(*self._widget_to_image(event.x, event.y))
        self.preview_area.queue_draw()
        self._update_action_sensitivity()
        return True

    def _on_crop(self, _button):
        if self._selection is None or self._selection.rect is None:
            return
        x, y, w, h = self._selection.rect
        self._undo_stack.append(self._pixbuf)
        # Subpixbuf retains its parent; edits never mutate pixels, so no copy is needed.
        self._pixbuf = self._pixbuf.new_subpixbuf(x, y, w, h)
        self._selection = Selection(w, h)
        self._on_zoom_changed(self.zoom_combo)
        self._mark_unsaved()
        self._update_action_sensitivity()
        self.preview_area.queue_draw()

    def _on_undo(self, _button):
        if not self._undo_stack:
            return
        self._pixbuf = self._undo_stack.pop()
        self._selection = Selection(self._pixbuf.get_width(), self._pixbuf.get_height())
        self._on_zoom_changed(self.zoom_combo)
        self._mark_unsaved()
        self._update_action_sensitivity()
        self.preview_area.queue_draw()

    # ------------------------------------------------------------------
    # action buttons
    # ------------------------------------------------------------------

    def _on_cancel(self, _b):
        self.window.destroy()
        self.app.quit()

    def _on_window_destroy(self, _w):
        if self._capture_timeout_id != 0:
            GLib.source_remove(self._capture_timeout_id)
            self._capture_timeout_id = 0
        # When the caller (e.g. xdg-desktop-portal) pinned a destination
        # via --file, exit non-zero if the user closed the window without
        # saving so the caller can distinguish a save from a cancel.
        if self.app.args.file and not self._saved:
            self.app._exit_code = 1
        self.app.quit()

    def _on_copy(self, _b):
        if self._pixbuf is None:
            return
        try:
            util.copy_pixbuf_to_clipboard(self._pixbuf)
        except (RuntimeError, GLib.Error) as exc:
            self._show_status(str(exc))
            return
        self._show_status(_('Copied to clipboard'))

    def _mark_unsaved(self):
        self._saved = False
        self.status_row.hide()
        self.save_button.set_label(_('Save'))

    def _show_status(self, text):
        self.status_label.set_text(text)
        self.status_label.set_tooltip_text(self._saved_path)
        self.open_folder_button.set_visible(self._saved_path is not None)
        self.status_row.show()

    def _on_open_saved_folder(self, _button):
        if self._saved_path:
            util.show_in_file_manager(Gio.File.new_for_path(self._saved_path).get_uri())

    def _on_save(self, _b):
        if self._pixbuf is None:
            return

        # When --file is given alongside --interactive, the caller has
        # pre-chosen the destination (e.g. xdg-desktop-portal); skip the
        # chooser and save straight to that path.
        if self.app.args.file:
            path = self.app.args.file
        else:
            dialog = Gtk.FileChooserNative.new(
                _('Save Screenshot'),
                self.window,
                Gtk.FileChooserAction.SAVE,
                _('Save'),
                _('Cancel'),
            )
            dialog.set_do_overwrite_confirmation(True)
            dialog.set_current_name(os.path.basename(self._suggested_path) if self._suggested_path else _('Screenshot') + '.png')
            suggested_dir = os.path.dirname(self._suggested_path) if self._suggested_path else ''
            if suggested_dir and os.path.isdir(suggested_dir):
                dialog.set_current_folder(suggested_dir)

            response = dialog.run()
            path = dialog.get_filename() if response == Gtk.ResponseType.ACCEPT else None
            dialog.destroy()
            if not path:
                return

        if not self._save_current(path):
            return
        if self.app.args.file:
            self.window.destroy()

    def _save_current(self, path):
        try:
            util.save_pixbuf(self._pixbuf, path)
        except Exception as exc:
            err = Gtk.MessageDialog(
                transient_for=self.window,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text=_('Failed to save screenshot'),
                secondary_text=str(exc),
            )
            err.run()
            err.destroy()
            return False

        self._saved = True
        self._saved_path = path

        copied = False
        copy_error = None
        if prefs.get_autosave_to_clipboard():
            try:
                util.copy_pixbuf_to_clipboard(self._pixbuf)
                copied = True
            except (RuntimeError, GLib.Error) as exc:
                copy_error = str(exc)

        folder = os.path.basename(os.path.dirname(path)) or os.path.dirname(path)
        message = _('Saved in %(folder)s') % {'folder': folder}
        if copied:
            message += ' · ' + _('Copied')
        elif copy_error:
            message += ' · ' + _('Copy failed')
        self._show_status(message)
        self.save_button.set_label(_('Save as…'))
        if copy_error:
            self.status_label.set_tooltip_text(copy_error)

        # When --file is set the destination wasn't user-chosen (portal use),
        # so the post-save file-manager reveal would be confusing.
        if prefs.get_launch_file_manager() and not self.app.args.file:
            util.show_in_file_manager(Gio.File.new_for_path(path).get_uri())

        return True

    def _on_open_save_folder(self, _item):
        uri = prefs.get_save_directory_uri()
        if not uri:
            uri = Gio.File.new_for_path(prefs.get_save_directory()).get_uri()
        util.show_in_file_manager(uri)

    def _on_preferences(self, _item):
        prefs.open_preferences(self.window, self.app.backend)

    def _on_about(self, _item):
        if self._about_dialog is None:
            self._about_dialog = Gtk.AboutDialog(
                transient_for=self.window, destroy_with_parent=True,
                program_name=APP_NAME, version=VERSION,
                logo_icon_name='applets-screenshooter',
                comments=_('Screenshot tool for Linux Mint and Cinnamon.'),
                copyright='© 2026 yuri-schmaltz\nLinux Mint / Cinnamon contributors',
                authors=['yuri-schmaltz — Cannelia Capture',
                         'Linux Mint / Cinnamon contributors', 'Michael Webster', 'Cobinja'],
                website=PROJECT_URL, website_label='GitHub · yuri-schmaltz/cannelia-capture',
                license_type=Gtk.License.GPL_2_0, wrap_license=True,
            )
            self._about_dialog.connect('response', lambda dialog, _response: dialog.hide())
        self._about_dialog.present()
