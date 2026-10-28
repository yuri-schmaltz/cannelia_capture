# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
"""Local screenshot translations, with the system Cinnamon catalog as fallback."""
import gettext
import os
import xml.etree.ElementTree as ET


def initialize():
    directory = os.environ.get('CINNAMON_SCREENSHOT_LOCALEDIR',
                               os.path.join(os.path.dirname(__file__), 'locale'))
    translation = gettext.translation('cinnamon-screenshot-local', directory, fallback=True)
    translation.add_fallback(gettext.translation('cinnamon', '/usr/share/locale', fallback=True))
    translation.install()


def load_builder(path):
    from gi.repository import Gtk
    tree = ET.parse(path)
    for prop in tree.iter():
        if prop.get('translatable') == 'yes':
            prop.text = _(prop.text or '')
            prop.attrib.pop('translatable')
    return Gtk.Builder.new_from_string(ET.tostring(tree.getroot(), encoding='unicode'), -1)
