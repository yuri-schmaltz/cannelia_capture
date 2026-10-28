#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 yuri-schmaltz. See NOTICE.md.
"""Render only this app's windows with a synthetic image for public documentation."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / 'run-screenshot.py'))['prepare']()

import application
import prefs
import cairo
from gi.repository import Gdk, GLib, Gtk
from main_window import MainWindow


def main():
    output = ROOT / 'docs/images'
    output.mkdir(parents=True, exist_ok=True)
    app = application.ScreenshotApplication(application._build_arg_parser().parse_args(['-i']))
    app.quit = lambda: None
    window = MainWindow(app)
    window.run()

    def save(widget, name):
        surface = widget.get_window()
        image = Gdk.pixbuf_get_from_window(surface, 0, 0, surface.get_width(), surface.get_height())
        image.savev(str(output / name), 'png', [], [])

    def initial():
        save(window.window, 'main-window.png')
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 900, 480)
        cr = cairo.Context(surface)
        for y in range(0, 480, 40):
            for x in range(0, 900, 40):
                shade = 0.22 if (x//40 + y//40) % 2 else 0.32
                cr.set_source_rgb(shade, shade+0.08, shade+0.15)
                cr.rectangle(x, y, 40, 40)
                cr.fill()
        cr.set_source_rgb(1, 1, 1)
        cr.set_font_size(28)
        cr.move_to(100, 220)
        cr.show_text('Cannelia Capture')
        window.show_with_pixbuf(Gdk.pixbuf_get_from_surface(surface, 0, 0, 900, 480))
        window._selection.rect = (80, 80, 420, 220)
        window._update_action_sensitivity()
        GLib.timeout_add(250, editor)
        return False

    def editor():
        save(window.window, 'editor.png')
        prefs.open_preferences(window.window, app.backend)
        GLib.timeout_add(250, preferences)
        return False

    def preferences():
        save(prefs._current_window.window, 'preferences.png')
        prefs._current_window.window.destroy()
        window._on_about(None)
        GLib.timeout_add(250, about)
        return False

    def about():
        save(window._about_dialog, 'about.png')
        window.window.destroy()
        Gtk.main_quit()
        return False

    GLib.timeout_add(250, initial)
    Gtk.main()
    print('Documentation screenshots:', output)


if __name__ == '__main__':
    main()
