#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
"""Measure startup and PNG capture paths. Screenshots are deleted after each run."""
import argparse
import json
from pathlib import Path
import runpy
import statistics
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=5)
    parser.add_argument('--full-screen', action='store_true', help='Measure full images instead of a single pixel')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('--samples must be positive')
    root = Path(__file__).resolve().parents[1]
    startup = []
    for _ in range(args.samples):
        started = time.perf_counter()
        subprocess.run([str(root / 'run-screenshot.py'), '--help'], check=True, stdout=subprocess.DEVNULL)
        startup.append((time.perf_counter()-started)*1000)
    runpy.run_path(str(root / 'run-screenshot.py'))['prepare']()
    import application
    import prefs
    import util
    from gi.repository import GLib, GdkPixbuf
    backend = application.screenshot_backend.Backend()
    if not backend.is_available():
        raise RuntimeError('No compositor screenshot service is available for the direct path')
    prefs.get_use_flash = lambda: False
    results = {'roundtrip_ms': [], 'direct_ms': []}
    dimensions = []
    with tempfile.TemporaryDirectory() as temp:
        for sample in range(args.samples):
            for route in ('roundtrip_ms', 'direct_ms'):
                loop = GLib.MainLoop()
                path = str(Path(temp) / f'{route}-{sample}.png')
                completed, errors = [], []
                started = time.perf_counter()

                def done(result):
                    try:
                        if result is None:
                            raise RuntimeError(backend.error() or 'capture failed')
                        if route == 'roundtrip_ms':
                            util.save_pixbuf(result, path)
                        completed.append((time.perf_counter()-started)*1000)
                    except Exception as exc:
                        errors.append(exc)
                    finally:
                        loop.quit()

                def expired():
                    errors.append(RuntimeError('capture timeout'))
                    loop.quit()
                    return GLib.SOURCE_REMOVE

                timer = GLib.timeout_add_seconds(10, expired)
                if route == 'roundtrip_ms':
                    if args.full_screen:
                        backend.screenshot(False, done)
                    else:
                        backend.screenshot_area(0, 0, 1, 1, False, done)
                else:
                    backend.capture_file('screen', path, False, False, done,
                                         area_rect=None if args.full_screen else (0, 0, 1, 1))
                if not completed and not errors:
                    loop.run()
                if completed:
                    GLib.source_remove(timer)
                if errors:
                    raise errors[0]
                image = GdkPixbuf.Pixbuf.new_from_file(path)
                dimensions.append([image.get_width(), image.get_height()])
                results[route].append(completed[0])
                Path(path).unlink()
    report = {'backend': type(backend._active()).__name__, 'dimensions': dimensions[0],
              'help_ms': startup, 'help_median_ms': statistics.median(startup), **results}
    for key in results:
        report[key.replace('_ms', '_median_ms')] = statistics.median(results[key])
    report['capture_reduction_percent'] = 100*(1-report['direct_median_ms']/report['roundtrip_median_ms'])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
