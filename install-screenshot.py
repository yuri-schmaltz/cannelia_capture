#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
"""Install just the screenshot app for the current user, independently of the clone."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess


APP_PATH = Path('files/usr/share/cinnamon/cinnamon-screenshot')
SHORTCUTS = [('Captura: desktop inteiro', '<Super><Shift>a', ''),
             ('Captura: seleção', '<Super><Shift>s', ' --area'),
             ('Captura: janela atual', '<Super><Shift>d', ' --window')]


def custom_settings(ident):
    from gi.repository import Gio
    return Gio.Settings.new_with_path('org.cinnamon.desktop.keybindings.custom-keybinding',
        '/org/cinnamon/desktop/keybindings/custom-keybindings/' + ident + '/')


def install_shortcuts(launcher, original=None):
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gio, Gtk
    settings = Gio.Settings.new('org.cinnamon.desktop.keybindings')
    ids = list(settings.get_strv('custom-list'))
    managed = {ident for ident in ids if custom_settings(ident).get_string('name') in {x[0] for x in SHORTCUTS}}
    targets = {Gtk.accelerator_parse(x[1]) for x in SHORTCUTS}
    source = Gio.SettingsSchemaSource.get_default()
    conflicts = []
    checks = [(name, Gio.Settings.new(name)) for name in source.list_schemas(True)[0]
              if name.startswith('org.cinnamon.desktop.keybindings')]
    checks += [(ident, custom_settings(ident)) for ident in ids if ident not in managed]
    for name, item in checks:
        for key in item.props.settings_schema.list_keys():
            value = item.get_value(key).unpack()
            values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
            if any(isinstance(v, str) and '<' in v and Gtk.accelerator_parse(v) in targets for v in values):
                conflicts.append(name + ':' + key)
    if conflicts:
        raise RuntimeError('Conflito de atalhos: ' + ', '.join(conflicts))
    backup = original or {'entries': {}, 'created': []}
    for name, binding, argument in SHORTCUTS:
        ident = next((i for i in ids if custom_settings(i).get_string('name') == name), None)
        if ident is None:
            index = 0
            while 'custom' + str(index) in ids:
                index += 1
            ident = 'custom' + str(index)
            ids.append(ident)
            backup['created'].append(ident)
        item = custom_settings(ident)
        if ident not in backup['entries']:
            backup['entries'][ident] = {key: item.get_value(key).unpack() for key in ('name', 'command', 'binding')}
        item.set_string('name', name)
        item.set_string('command', shlex.quote(str(launcher)) + argument)
        item.set_strv('binding', [binding])
    settings.set_strv('custom-list', ids)
    Gio.Settings.sync()
    return backup


def restore_shortcuts(launcher, backup):
    from gi.repository import Gio
    settings = Gio.Settings.new('org.cinnamon.desktop.keybindings')
    ids = list(settings.get_strv('custom-list'))
    for ident, values in backup.get('entries', {}).items():
        item = custom_settings(ident)
        if not item.get_string('command').startswith(shlex.quote(str(launcher))):
            continue  # Preserve shortcuts the user edited after installation.
        if ident in backup.get('created', []):
            ids = [i for i in ids if i != ident]
            for key in ('name', 'command', 'binding'):
                item.reset(key)
        else:
            item.set_string('name', values['name'])
            item.set_string('command', values['command'])
            item.set_strv('binding', values['binding'])
    settings.set_strv('custom-list', ids)
    Gio.Settings.sync()


def install(prefix, configure_shortcuts=True, isolated=False):
    source = Path(__file__).resolve().parent
    destination = prefix / 'share/cinnamon-screenshot-local'
    launcher = prefix / 'bin/cinnamon-screenshot-local'
    desktop = prefix / 'share/applications/cinnamon-screenshot-local.desktop'
    manifest = destination / 'install-manifest.json'
    old = json.loads(manifest.read_text()) if manifest.exists() else {}
    if destination.exists() and not old:
        raise RuntimeError('Pasta de destino já existe e não pertence a esta instalação: ' + str(destination))
    config = (prefix / 'config' if isolated else
              Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'cinnamon-screenshot-local')
    cache = (prefix / 'cache' if isolated else
             Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'cinnamon-screenshot-local')
    config.mkdir(parents=True, exist_ok=True)
    # Keep the preferences already configured in this checkout on first install.
    saved = source / '.local-screenshot/config/glib-2.0/settings/keyfile'
    target = config / 'glib-2.0/settings/keyfile'
    if saved.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(saved, target)
    if source != destination:
        (destination / APP_PATH).mkdir(parents=True, exist_ok=True)
        shutil.copytree(source / APP_PATH, destination / APP_PATH, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (destination / 'data').mkdir(exist_ok=True)
        shutil.copy2(source / 'data/org.cinnamon.gschema.xml', destination / 'data/org.cinnamon.gschema.xml')
        for filename in ('run-screenshot.py', 'install-screenshot.py', 'SCREENSHOT-DEVELOPMENT.md',
                         'COPYING', 'LICENSE', 'NOTICE.md', 'AUTHORS.md', 'README.md'):
            shutil.copy2(source / filename, destination / filename)
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text('#!/usr/bin/python3\nimport os, runpy\n'
        + 'os.environ["CINNAMON_SCREENSHOT_STATE_DIR"] = ' + repr(str(cache)) + '\n'
        + 'os.environ["CINNAMON_SCREENSHOT_CONFIG_DIR"] = ' + repr(str(config)) + '\n'
        + 'runpy.run_path(' + repr(str(destination / 'run-screenshot.py')) + ', run_name="__main__")\n')
    launcher.chmod(0o755)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    executable = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
    desktop.write_text('[Desktop Entry]\nType=Application\nVersion=1.0\n'
        'Name=Cannelia Capture\nName[pt_BR]=Cannelia Capture\n'
        'Comment=Capture your screen, windows or regions\nComment[pt_BR]=Capture telas, janelas ou regiões\n'
        + 'Exec="' + executable + '" --interactive\n'
        + 'Icon=applets-screenshooter\nTerminal=false\nCategories=GTK;Utility;\nStartupNotify=false\n')
    result = subprocess.run([str(launcher), '--help'], stdout=subprocess.DEVNULL)
    if result.returncode:
        raise RuntimeError('O lançador instalado não iniciou corretamente.')
    backup = old.get('shortcuts')
    manifest.write_text(json.dumps({'prefix': str(prefix), 'config': str(config), 'cache': str(cache),
                                   'shortcuts': backup}, indent=2) + '\n')
    if configure_shortcuts:
        backup = install_shortcuts(launcher, backup)
        manifest.write_text(json.dumps({'prefix': str(prefix), 'config': str(config), 'cache': str(cache),
                                       'shortcuts': backup}, indent=2) + '\n')
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(desktop.parent)], check=True)
    print('Instalado:', launcher)
    print('Menu: Cannelia Capture')
    return destination


def uninstall(prefix):
    destination = prefix / 'share/cinnamon-screenshot-local'
    manifest = destination / 'install-manifest.json'
    if not manifest.is_file():
        raise RuntimeError('Instalação não encontrada: ' + str(destination))
    details = json.loads(manifest.read_text())
    launcher = prefix / 'bin/cinnamon-screenshot-local'
    if details.get('shortcuts'):
        restore_shortcuts(launcher, details['shortcuts'])
    for path in (launcher, prefix / 'share/applications/cinnamon-screenshot-local.desktop'):
        if path.exists():
            path.unlink()
    shutil.rmtree(destination)
    print('Aplicativo removido. Preferências preservadas em:', details['config'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Instalar o aplicativo de captura para este usuário')
    parser.add_argument('--prefix', type=Path, help='Instalação isolada para validação')
    parser.add_argument('--no-shortcuts', action='store_true')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    prefix = (args.prefix or Path.home() / '.local').expanduser().resolve()
    try:
        if args.uninstall:
            uninstall(prefix)
        else:
            install(prefix, not args.no_shortcuts, args.prefix is not None)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, str(exc) + '\n')
