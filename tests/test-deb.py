#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 yuri-schmaltz
"""Integration checks for the actual Debian artifact, without root installation."""
import hashlib
import os
from pathlib import Path
import runpy
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = runpy.run_path(str(ROOT / 'files/usr/share/cinnamon/cinnamon-screenshot/branding.py'))['VERSION']


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def main():
    with tempfile.TemporaryDirectory(prefix='cannelia-deb-test-') as temporary:
        base = Path(temporary)
        env = dict(os.environ, SOURCE_DATE_EPOCH='1793203200')
        packages = []
        for name in ['first', 'second']:
            run('/usr/bin/python3', str(ROOT / 'tools/build-deb.py'), '--output', str(base / name), env=env)
            packages.append(base / name / f'cannelia-capture_{VERSION}_all.deb')
        assert packages[0].read_bytes() == packages[1].read_bytes(), 'Build is not reproducible'
        package = packages[0]
        assert run('dpkg-deb', '-f', str(package), 'Version') == VERSION
        assert run('dpkg-deb', '-f', str(package), 'Architecture') == 'all'
        subprocess.run(['lintian', '--fail-on', 'error,warning', str(package)], check=True)
        extracted = base / 'extracted'
        run('dpkg-deb', '-x', str(package), str(extracted))
        app = extracted / 'usr/share/cannelia-capture'
        assert (app / 'data/gschemas.compiled').is_file()
        assert (app / 'locale/pt_BR/LC_MESSAGES/cinnamon-screenshot-local.mo').is_file()
        assert not list(extracted.rglob('*.pyc'))
        launcher = (extracted / 'usr/bin/cannelia-capture').read_text()
        # Relocate only the fixed installation prefix so the exact packaged launcher
        # can be exercised without writing into the host's /usr or package database.
        launcher = launcher.replace('/usr/share/cannelia-capture', str(app))
        script = base / 'launcher.py'
        script.write_text(launcher)
        home = base / 'home'
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'),
                   XDG_CACHE_HOME=str(home / '.cache'))
        for key in ['CINNAMON_SCREENSHOT_STATE_DIR', 'CINNAMON_SCREENSHOT_CONFIG_DIR']:
            env.pop(key, None)
        assert run('/usr/bin/python3', str(script), '--version', env=env) == f'Cannelia Capture {VERSION}'
        assert not home.exists(), '--version must not create user state'
        env.pop('PYTHONDONTWRITEBYTECODE', None)
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('*') if p.is_file()}
        diagnostic = run('/usr/bin/python3', str(script), '--check', env=env)
        assert 'backend' in diagnostic, diagnostic
        after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('*') if p.is_file()}
        assert before == after, 'Runtime changed package data'
        assert (home / '.config/cinnamon-screenshot-local').is_dir()
        print(diagnostic)
        print('PASS: version, architecture, lintian, reproducibility, packaged launch and read-only assets')


if __name__ == '__main__':
    main()
