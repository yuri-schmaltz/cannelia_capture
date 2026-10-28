#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
"""Run the screenshot app from this checkout without installing Cinnamon."""
import os
from pathlib import Path
import sys
import fcntl
import time


def prepare():
    root = Path(__file__).resolve().parent
    state = Path(os.environ.get('CINNAMON_SCREENSHOT_STATE_DIR', root / '.local-screenshot'))
    schemas = state / 'schemas'
    schemas.mkdir(parents=True, exist_ok=True)
    schema_source = root / 'data/org.cinnamon.gschema.xml'
    compiled = schemas / 'gschemas.compiled'
    signature_file = schemas / '.source-version'
    stat = schema_source.stat()
    signature = str(stat.st_mtime_ns) + ':' + str(stat.st_size)
    with (state / 'prepare.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not compiled.exists() or not signature_file.exists() or signature_file.read_text() != signature:
            import subprocess
            import xml.etree.ElementTree as ET
            source = ET.parse(schema_source).getroot()
            isolated = ET.Element('schemalist')
            for item in source:
                if item.get('id', '').startswith('org.cinnamon.screenshot'):
                    isolated.append(item)
            ET.ElementTree(isolated).write(schemas / 'org.cinnamon.screenshot.gschema.xml',
                                          encoding='utf-8', xml_declaration=True)
            subprocess.run(['glib-compile-schemas', '--strict', str(schemas)], check=True)
            signature_file.write_text(signature)
    os.environ['GSETTINGS_SCHEMA_DIR'] = str(schemas)
    os.environ['GSETTINGS_BACKEND'] = 'keyfile'
    config = Path(os.environ.get('CINNAMON_SCREENSHOT_CONFIG_DIR', state / 'config'))
    config.mkdir(parents=True, exist_ok=True)
    user_dirs = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'user-dirs.dirs'
    local_user_dirs = config / 'user-dirs.dirs'
    if user_dirs.is_file() and user_dirs.resolve() != local_user_dirs.resolve():
        content = user_dirs.read_bytes()
        if not local_user_dirs.exists() or local_user_dirs.read_bytes() != content:
            local_user_dirs.write_bytes(content)
    os.environ['XDG_CONFIG_HOME'] = str(config)
    translations = root / 'files/usr/share/cinnamon/cinnamon-screenshot/po'
    locale_dir = state / 'locale'
    for catalog in translations.glob('*.po'):
        output = locale_dir / catalog.stem / 'LC_MESSAGES/cinnamon-screenshot-local.mo'
        output.parent.mkdir(parents=True, exist_ok=True)
        if not output.exists() or catalog.stat().st_mtime > output.stat().st_mtime:
            import subprocess
            with (state / 'prepare.lock').open('w') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                if not output.exists() or catalog.stat().st_mtime > output.stat().st_mtime:
                    temporary = output.with_suffix('.tmp')
                    subprocess.run(['msgfmt', '--check', str(catalog), '-o', str(temporary)], check=True)
                    temporary.replace(output)
    os.environ['CINNAMON_SCREENSHOT_LOCALEDIR'] = str(locale_dir)
    sys.path.insert(0, str(root / 'files/usr/share/cinnamon/cinnamon-screenshot'))


if __name__ == '__main__':
    os.environ['CINNAMON_SCREENSHOT_START_NS'] = str(time.monotonic_ns())
    if '--help' in sys.argv or '-h' in sys.argv:
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'files/usr/share/cinnamon/cinnamon-screenshot'))
        from cli import build_arg_parser
        build_arg_parser().parse_args()
        sys.exit(0)
    prepare()
    import application
    sys.exit(application.main())
