# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
"""Command line parsing without loading GTK or screenshot services."""
import argparse
from branding import APP_NAME, VERSION


def build_arg_parser():
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description='Take screenshots of your screen, windows, or selected areas',
        add_help=True,
    )
    parser.add_argument('--version', action='version', version=f'{APP_NAME} {VERSION}')
    parser.add_argument('-c', '--clipboard', action='store_true',
                        help='Send the grab directly to the clipboard')
    parser.add_argument('-w', '--window', action='store_true',
                        help='Grab the active window instead of the entire screen')
    parser.add_argument('--select-window', action='store_true', dest='select_window',
                        help='Interactively pick a window to grab')
    parser.add_argument('-a', '--area', action='store_true',
                        help='Grab a selected area of the screen')
    parser.add_argument('-m', '--monitor', type=int, default=None, metavar='INDEX',
                        help='Grab a specific monitor by 0-based index')
    parser.add_argument('-p', '--include-pointer', action='store_true',
                        help='Include the pointer in the screenshot')
    parser.add_argument('-s', '--include-shadow', action='store_true',
                        help='Include the window shadow when grabbing a window')
    parser.add_argument('-d', '--delay', type=int, default=None, metavar='SECONDS',
                        help='Take the screenshot after a delay')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Interactively set options before taking the screenshot')
    parser.add_argument('-f', '--file', metavar='PATH',
                        help='Save the screenshot directly to PATH')
    parser.add_argument('--profile', action='store_true', help='Print elapsed time to save as JSON on stderr')
    parser.add_argument('--no-notification', action='store_true', help='Disable desktop notifications')
    parser.add_argument('--check', action='store_true', help='Check dependencies and interface without capturing')
    return parser
