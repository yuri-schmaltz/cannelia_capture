#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 yuri-schmaltz
"""Build an architecture-independent Debian binary from the tracked source."""
import argparse
import gzip
import hashlib
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
from email.utils import formatdate

ROOT = Path(__file__).resolve().parent.parent
VERSION = runpy.run_path(str(ROOT / 'files/usr/share/cinnamon/cinnamon-screenshot/branding.py'))['VERSION']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH') or subprocess.check_output(
        ['git', 'log', '-1', '--format=%ct'], cwd=ROOT, text=True).strip())
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch), LC_ALL='C', TZ='UTC')
    with tempfile.TemporaryDirectory(prefix='cannelia-deb-') as temporary:
        stage = Path(temporary) / 'root'
        app = stage / 'usr/share/cannelia-capture'
        app.mkdir(parents=True)
        source = Path('files/usr/share/cinnamon/cinnamon-screenshot')
        shutil.copytree(ROOT / source, app / source, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'po'))
        shutil.copy2(ROOT / 'run-screenshot.py', app / 'run-screenshot.py')
        (app / 'data').mkdir()
        shutil.copy2(ROOT / 'data/org.cinnamon.gschema.xml', app / 'data/org.cinnamon.gschema.xml')
        subprocess.run(['glib-compile-schemas', '--strict', str(app / 'data')], check=True, env=env)
        for catalog in sorted((ROOT / source / 'po').glob('*.po')):
            mo = app / 'locale' / catalog.stem / 'LC_MESSAGES/cinnamon-screenshot-local.mo'
            mo.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['msgfmt', '--check', str(catalog), '-o', str(mo)], check=True, env=env)
        binary = stage / 'usr/bin/cannelia-capture'
        binary.parent.mkdir(parents=True)
        binary.write_text('''#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
import os
from pathlib import Path
import runpy
import sys
sys.dont_write_bytecode = True
os.environ.setdefault('CINNAMON_SCREENSHOT_STATE_DIR', str(Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'cinnamon-screenshot-local'))
os.environ.setdefault('CINNAMON_SCREENSHOT_CONFIG_DIR', str(Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'cinnamon-screenshot-local'))
runpy.run_path('/usr/share/cannelia-capture/run-screenshot.py', run_name='__main__')
''')
        for relative in ['applications/cannelia-capture.desktop', 'icons/hicolor/scalable/apps/cannelia-capture.svg']:
            target = stage / 'usr/share' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / 'packaging' / target.name, target)
        subprocess.run(['desktop-file-validate', str(stage / 'usr/share/applications/cannelia-capture.desktop')], check=True)
        doc = stage / 'usr/share/doc/cannelia-capture'
        doc.mkdir(parents=True)
        for name in ['README.md', 'NOTICE.md', 'AUTHORS.md', 'LICENSE']:
            shutil.copy2(ROOT / name, doc / name)
        shutil.copy2(ROOT / 'packaging/copyright', doc / 'copyright')
        changes = (f'cannelia-capture ({VERSION}) unstable; urgency=medium\n\n'
                   '  * Public release. Install independent GTK screenshot application.\n\n'
                   f' -- yuri-schmaltz <63480675+yuri-schmaltz@users.noreply.github.com>  {formatdate(epoch, localtime=False)}\n')
        (doc / 'changelog.gz').write_bytes(gzip.compress(changes.encode(), mtime=0))
        (doc / 'changelog.upstream.gz').write_bytes(gzip.compress((ROOT / 'CHANGELOG.md').read_bytes(), mtime=0))
        manual = stage / 'usr/share/man/man1/cannelia-capture.1.gz'
        manual.parent.mkdir(parents=True)
        manual.write_bytes(gzip.compress((ROOT / 'packaging/cannelia-capture.1').read_bytes(), mtime=0))
        control = stage / 'DEBIAN'
        control.mkdir()
        size = sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())
        (control / 'control').write_text(f'''Package: cannelia-capture
Version: {VERSION}
Section: graphics
Priority: optional
Architecture: all
Maintainer: yuri-schmaltz <63480675+yuri-schmaltz@users.noreply.github.com>
Installed-Size: {(size + 1023) // 1024}
Depends: python3 (>= 3.10), python3-gi, python3-gi-cairo, python3-cairo, gir1.2-gtk-3.0, gir1.2-xapp-1.0, python3-xapp
Recommends: cinnamon
Homepage: https://github.com/yuri-schmaltz/cannelia-capture
Description: Screenshot application for Linux Mint and Cinnamon
 Capture screens, windows and regions with automatic saving, clipboard
 integration, cropping, zoom and a Brazilian Portuguese interface.
 Derived from the Cinnamon screenshot application under GPL-2.0-or-later.
''')
        files = sorted(p for p in stage.rglob('*') if p.is_file() and control not in p.parents)
        (control / 'md5sums').write_text(''.join(
            f'{hashlib.md5(p.read_bytes()).hexdigest()}  {p.relative_to(stage)}\n' for p in files))
        for path in sorted(stage.rglob('*'), reverse=True):
            path.chmod(0o755 if path.is_dir() or path == binary else 0o644)
            os.utime(path, (epoch, epoch))
        stage.chmod(0o755)
        os.utime(stage, (epoch, epoch))
        package = output / f'cannelia-capture_{VERSION}_all.deb'
        subprocess.run(['dpkg-deb', '--root-owner-group', '-Zxz', '--build', str(stage), str(package)], check=True, env=env)
    print(package)


if __name__ == '__main__':
    main()
