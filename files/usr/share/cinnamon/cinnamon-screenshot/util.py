# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
import os
import sys
import tempfile
import uuid

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk
from branding import APP_NAME


_FILE_MANAGER1_BUS = 'org.freedesktop.FileManager1'
_FILE_MANAGER1_PATH = '/org/freedesktop/FileManager1'

_PIXBUF_FORMAT_FOR_EXT = {
    '.png':  ('png',  []),
    '.jpg':  ('jpeg', [('quality', '95')]),
    '.jpeg': ('jpeg', [('quality', '95')]),
    '.bmp':  ('bmp',  []),
    '.tif':  ('tiff', []),
    '.tiff': ('tiff', []),
}

def format_for_path(path):
    ext = os.path.splitext(path)[1].lower()
    return _PIXBUF_FORMAT_FOR_EXT.get(ext, _PIXBUF_FORMAT_FOR_EXT['.png'])

def save_pixbuf(pixbuf, path):
    fmt, options = format_for_path(path)
    keys = [k for k, _ in options]
    values = [v for _, v in options]
    directory = os.path.dirname(os.path.abspath(path))
    fd, temporary = tempfile.mkstemp(prefix='.capture-', dir=directory)
    os.close(fd)
    try:
        pixbuf.savev(temporary, fmt, keys, values)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def copy_pixbuf_to_clipboard(pixbuf):
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    if clipboard is None:
        raise RuntimeError(_('The clipboard is unavailable.'))
    clipboard.set_image(pixbuf)
    clipboard.store()
    if not clipboard.wait_is_image_available():
        raise RuntimeError(_('The image could not be copied to the clipboard.'))

def monitor_rect(idx):
    """Return (x, y, w, h) of the monitor at the given index, or None if
    the index is out of range or there's only one monitor (caller should
    treat that as 'use the whole screen')."""
    if idx is None:
        return None
    display = Gdk.Display.get_default()
    if display is None:
        return None
    n = display.get_n_monitors()
    if n <= 1 or idx < 0 or idx >= n:
        return None
    geom = display.get_monitor(idx).get_geometry()
    return (geom.x, geom.y, geom.width, geom.height)

def monitor_rect_for_window(gdk_window):
    """Return (x, y, w, h) of the monitor the given GdkWindow is on,
    or None if it can't be determined."""
    if gdk_window is None:
        return None
    display = Gdk.Display.get_default()
    if display is None:
        return None
    monitor = display.get_monitor_at_window(gdk_window)
    if monitor is None:
        return None
    geom = monitor.get_geometry()
    return (geom.x, geom.y, geom.width, geom.height)

def build_filename(directory, file_type='png'):
    """Build a 'Screenshot <iso-timestamp>.<ext>' path inside directory.
    Caller is responsible for passing an existing directory."""
    timestamp = GLib.DateTime.new_now_local().format('%Y-%m-%d %H-%M-%S.%f')
    return os.path.join(directory, f'{_("Screenshot")} {timestamp}-{uuid.uuid4().hex[:8]}.{file_type}')

def show_in_file_manager(uri):
    f = Gio.File.new_for_uri(uri)
    is_dir = False
    try:
        info = f.query_info(Gio.FILE_ATTRIBUTE_STANDARD_TYPE,
                            Gio.FileQueryInfoFlags.NONE, None)
        is_dir = info.get_file_type() == Gio.FileType.DIRECTORY
    except GLib.Error:
        pass

    if not is_dir:
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                _FILE_MANAGER1_BUS, _FILE_MANAGER1_PATH, _FILE_MANAGER1_BUS,
                'ShowItems',
                GLib.Variant('(ass)', ([uri], '')),
                None, Gio.DBusCallFlags.NONE, -1, None,
            )
            return
        except GLib.Error:
            pass

    target = uri if is_dir else (f.get_parent() or f).get_uri()
    try:
        Gio.AppInfo.launch_default_for_uri(target, None)
    except GLib.Error as exc:
        print(f'{APP_NAME}: failed to open file manager: {exc.message}',
              file=sys.stderr)


def notify_saved(path, copied, on_done):
    folder = os.path.basename(os.path.dirname(path)) or os.path.dirname(path)
    body = _('Saved in %(folder)s') % {'folder': folder}
    if copied:
        body += ' · ' + _('Copied')
    _notify(APP_NAME, body, on_done, path)


def notify_error(message, on_done):
    _notify(_('Capture failed'), message, on_done)


def _notify(title, body, on_done, path=None):
    """Replace this app's previous popup and ignore actions on superseded ones."""
    import fcntl
    import json
    from runtime import runtime_directory
    directory = runtime_directory()
    record = directory / 'notification.json'
    token = uuid.uuid4().hex
    state = {'id': 0, 'finished': False, 'timer': 0}
    try:
        proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
            None, 'org.freedesktop.Notifications', '/org/freedesktop/Notifications',
            'org.freedesktop.Notifications', None)
    except GLib.Error:
        GLib.idle_add(lambda: (on_done(), GLib.SOURCE_REMOVE)[1])
        return

    def finish():
        if state['finished']:
            return
        state['finished'] = True
        if state['timer']:
            GLib.source_remove(state['timer'])
        proxy.disconnect(handler)
        on_done()

    def expired():
        state['timer'] = 0
        finish()
        return GLib.SOURCE_REMOVE

    def signal(_proxy, _sender, name, parameters):
        values = parameters.unpack()
        if name not in ('ActionInvoked', 'NotificationClosed') or values[0] != state['id']:
            return
        try:
            current = json.loads(record.read_text()).get('token') == token
        except (OSError, ValueError):
            current = False
        if current and name == 'ActionInvoked' and path and values[1] in ('open-folder', 'default'):
            show_in_file_manager(Gio.File.new_for_path(path).get_uri())
        finish()

    handler = proxy.connect('g-signal', signal)
    try:
        # Serialize the read/replace transaction across separate shortcut processes.
        with (directory / 'notification.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            owner = proxy.get_name_owner()
            try:
                previous = json.loads(record.read_text())
            except (OSError, ValueError):
                previous = {}
            replace_id = previous.get('id', 0) if previous.get('owner') == owner else 0
            reply = proxy.call_sync('Notify', GLib.Variant('(susssasa{sv}i)', (
                APP_NAME, replace_id, 'applets-screenshooter' if path else 'dialog-warning',
                title, body, ['open-folder', _('Open folder')] if path else [],
                {'transient': GLib.Variant('b', True)}, 5000)),
                Gio.DBusCallFlags.NONE, 3000, None)
            state['id'] = reply.unpack()[0]
            temporary = record.with_suffix('.tmp')
            temporary.write_text(json.dumps({'id': state['id'], 'owner': owner, 'token': token}))
            temporary.replace(record)
    except (GLib.Error, OSError):
        GLib.idle_add(lambda: (finish(), GLib.SOURCE_REMOVE)[1])
        return
    state['timer'] = GLib.timeout_add_seconds(6, expired)
