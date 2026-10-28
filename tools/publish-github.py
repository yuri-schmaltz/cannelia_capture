#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 yuri-schmaltz. See NOTICE.md.
"""Publish this committed checkout and apply the reviewed GitHub About metadata."""
import argparse
import json
from pathlib import Path
import subprocess


def run(*args, capture=False):
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Show publication metadata without network writes')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    metadata = json.loads((root / '.github/repository.json').read_text())
    repository = metadata['owner'] + '/' + metadata['name']
    url = 'https://github.com/' + repository
    if args.dry_run:
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return
    if run('git', '-C', str(root), 'status', '--porcelain', capture=True).strip():
        raise RuntimeError('Commit the reviewed source tree before publishing.')
    owner = run('gh', 'api', 'user', '--jq', '.login', capture=True).strip()
    if owner != metadata['owner']:
        raise RuntimeError('Authenticate gh as ' + metadata['owner'] + ' before publishing.')
    branch = run('git', '-C', str(root), 'branch', '--show-current', capture=True).strip()
    if branch != 'main':
        raise RuntimeError('Publish the main branch.')
    remotes = run('git', '-C', str(root), 'remote', capture=True).splitlines()
    if 'origin' in remotes:
        remote = run('git', '-C', str(root), 'remote', 'get-url', 'origin', capture=True).strip()
        if remote not in (url + '.git', url, 'git@github.com:' + repository + '.git'):
            raise RuntimeError('origin points to another repository; refusing to publish there.')
    check = subprocess.run(['gh', 'repo', 'view', repository, '--json', 'visibility'],
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check.returncode:
        run('gh', 'repo', 'create', repository, '--public', '--description', metadata['description'])
    elif json.loads(check.stdout)['visibility'] != 'PUBLIC':
        raise RuntimeError('An existing private repository has this name. Inspect it before making it public.')
    if 'origin' not in remotes:
        run('git', '-C', str(root), 'remote', 'add', 'origin', url + '.git')
    run('git', '-C', str(root), 'push', '-u', 'origin', 'main')
    command = ['gh', 'repo', 'edit', repository, '--description', metadata['description'],
               '--homepage', metadata['homepage']]
    for topic in metadata['topics']:
        command.extend(['--add-topic', topic])
    run(*command)
    details = json.loads(run('gh', 'api', 'repos/' + repository, capture=True))
    if details['private'] or details['owner']['login'] != metadata['owner']:
        raise RuntimeError('The published repository metadata did not match the request.')
    print(json.dumps({'url': details['html_url'], 'public': not details['private'],
                      'description': details['description'], 'homepage': details['homepage'],
                      'topics': details['topics'], 'license': (details.get('license') or {}).get('spdx_id')},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc))
