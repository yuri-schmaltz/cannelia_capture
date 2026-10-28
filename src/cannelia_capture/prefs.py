# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk
from branding import APP_NAME

SCHEMA_ID = 'org.cinnamon.screenshot'

DELAY_KEY = 'delay'
INCLUDE_POINTER_KEY = 'include-pointer'
INCLUDE_SHADOW_KEY = 'include-shadow'
SAVE_DIRECTORY_KEY = 'save-directory'
DEFAULT_FILE_TYPE_KEY = 'default-file-type'
LAUNCH_FILE_MANAGER_KEY = 'launch-file-manager-after-save'
AUTOSAVE_TO_FILE_KEY = 'autosave-to-file'
AUTOSAVE_TO_CLIPBOARD_KEY = 'autosave-to-clipboard'
USE_FLASH_KEY = 'use-flash'

settings = Gio.Settings.new(SCHEMA_ID)
if not settings.get_string(SAVE_DIRECTORY_KEY):
    path = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) or GLib.get_home_dir()
    if path:
        settings.set_string(SAVE_DIRECTORY_KEY, Gio.File.new_for_path(path).get_uri())

def get_delay():
    return settings.get_int(DELAY_KEY)

def set_delay(value):
    settings.set_int(DELAY_KEY, value)

def get_include_pointer():
    return settings.get_boolean(INCLUDE_POINTER_KEY)

def set_include_pointer(value):
    settings.set_boolean(INCLUDE_POINTER_KEY, value)

def get_include_shadow():
    return settings.get_boolean(INCLUDE_SHADOW_KEY)

def get_save_directory_uri():
    return settings.get_string(SAVE_DIRECTORY_KEY)

def get_save_directory():
    """Resolve the configured folder; never silently save somewhere else."""
    uri = get_save_directory_uri()
    if uri:
        try:
            path = Gio.File.new_for_uri(uri).get_path() or ''
        except Exception:
            path = ''
        if path and os.path.isdir(path):
            return path
        raise FileNotFoundError(_('The save folder is unavailable: %(folder)s') % {'folder': uri})
    return GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) or GLib.get_home_dir()

def get_default_file_type():
    return settings.get_string(DEFAULT_FILE_TYPE_KEY) or 'png'

def set_default_file_type(value):
    settings.set_string(DEFAULT_FILE_TYPE_KEY, value)

def get_launch_file_manager():
    return settings.get_boolean(LAUNCH_FILE_MANAGER_KEY)

def get_autosave_to_file():
    return settings.get_boolean(AUTOSAVE_TO_FILE_KEY)

def get_autosave_to_clipboard():
    return settings.get_boolean(AUTOSAVE_TO_CLIPBOARD_KEY)

def get_use_flash():
    return settings.get_boolean(USE_FLASH_KEY)

_current_window = None


def open_preferences(parent, backend=None):
    global _current_window
    if _current_window is not None:
        _current_window.window.present()
        return
    _current_window = PreferencesWindow(parent, backend)


class PreferencesWindow:
    def __init__(self, parent, backend=None):
        from xapp.GSettingsWidgets import GSettingsComboBox, GSettingsFileChooser, GSettingsSpinButton, GSettingsSwitch
        from xapp.SettingsWidgets import SettingsPage

        self.window = Gtk.Window(title=_('Preferences') + ' · ' + APP_NAME)
        self.window.set_transient_for(parent)
        self.window.set_destroy_with_parent(True)
        self.window.set_default_size(600, 200)
        self.window.connect('destroy', self._on_destroy)

        page = SettingsPage()
        self.window.add(page)

        section = page.add_section(_('Saving'))

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        section.add_row(GSettingsFileChooser(
            _('Default save folder'),
            SCHEMA_ID, SAVE_DIRECTORY_KEY,
            size_group=size_group, dir_select=True,
        ))
        section.add_row(GSettingsComboBox(
            _('Default file type'),
            SCHEMA_ID, DEFAULT_FILE_TYPE_KEY,
            options=[
                ('png',  'PNG'),
                ('jpg',  'JPEG'),
                ('bmp',  'BMP'),
                ('tiff', 'TIFF'),
            ],
            valtype=str,
            size_group=size_group,
        ))
        section.add_row(GSettingsSwitch(
            _('Launch file manager after saving'),
            SCHEMA_ID, LAUNCH_FILE_MANAGER_KEY,
        ))

        section_capture = page.add_section(_('Capture settings'))
        self.delay_control = GSettingsSpinButton(
            _('Delay (seconds)'), SCHEMA_ID, DELAY_KEY,
            mini=0, maxi=3600, step=1, page=5,
        )
        section_capture.add_row(self.delay_control)
        self.pointer_control = GSettingsSwitch(
            _('Include pointer'), SCHEMA_ID, INCLUDE_POINTER_KEY,
        )
        section_capture.add_row(self.pointer_control)
        self.shadow_control = GSettingsSwitch(
            _('Include window shadow'), SCHEMA_ID, INCLUDE_SHADOW_KEY,
        )
        section_capture.add_row(self.shadow_control)
        self._backend = backend
        self._backend_handler = None
        if backend is not None:
            self._backend_handler = backend.connect('online-changed', self._update_capture_controls)
            self._update_capture_controls()

        section_behavior = page.add_section(_('Behavior'))
        section_behavior.add_row(GSettingsSwitch(
            _('Autosave to default folder'),
            SCHEMA_ID, AUTOSAVE_TO_FILE_KEY,
        ))
        section_behavior.add_row(GSettingsSwitch(
            _('Copy to clipboard when saving'),
            SCHEMA_ID, AUTOSAVE_TO_CLIPBOARD_KEY,
        ))
        section_behavior.add_row(GSettingsSwitch(
            _('Use a flash'),
            SCHEMA_ID, USE_FLASH_KEY,
        ))

        self.window.show_all()

    def _on_destroy(self, _w):
        global _current_window
        if self._backend_handler is not None:
            self._backend.disconnect(self._backend_handler)
        _current_window = None

    def _update_capture_controls(self, *_args):
        self.pointer_control.set_sensitive(self._backend.is_available())
        self.shadow_control.set_sensitive(self._backend.supports_window_selection())
