#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Retrofit archived HTML pages with a viewport meta tag for mobile."""

import argparse
import os
import sys

from common import BASE_PATH

SKIP_DIRS = {'js', 'css', 'img', 'fonts'}

VIEWPORT_TAG = b'\n    <meta name="viewport" content="width=device-width, initial-scale=1">'
VIEWPORT_MARKER = b'name="viewport"'
ANCHOR_CHARSET = b'<meta charset="UTF-8">'
ANCHOR_HEAD = b'<head>'


def retrofit_file(path, apply):
    """Process a single HTML file.

    Returns one of:
        'ok'        - already has viewport meta
        'modified'  - viewport inserted (or would be, in dry-run)
        'no_anchor' - neither charset nor head anchor found
    """
    with open(path, 'rb') as f:
        data = f.read()

    if VIEWPORT_MARKER in data:
        return 'ok'

    idx = data.find(ANCHOR_CHARSET)
    if idx != -1:
        insert_pos = idx + len(ANCHOR_CHARSET)
    else:
        idx = data.find(ANCHOR_HEAD)
        if idx != -1:
            insert_pos = idx + len(ANCHOR_HEAD)
        else:
            return 'no_anchor'

    if apply:
        new_data = data[:insert_pos] + VIEWPORT_TAG + data[insert_pos:]
        tmp_path = path + '.tmp'
        with open(tmp_path, 'wb') as f:
            f.write(new_data)
        os.rename(tmp_path, path)

    return 'modified'


def collect_html_files(root):
    """Walk root collecting *.html paths, skipping SKIP_DIRS."""
    html_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skipped directories in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if fname.endswith('.html'):
                html_files.append(os.path.join(dirpath, fname))
    return html_files


def main():
    parser = argparse.ArgumentParser(
        description='Retrofit archived HTML pages with viewport meta tag.')
    parser.add_argument('--apply', action='store_true',
                        help='Actually write changes (default is dry-run)')
    parser.add_argument('--root', default=None,
                        help='Root directory to walk (default: BASE_PATH from common.py)')
    args = parser.parse_args()

    root = args.root if args.root else BASE_PATH

    if not os.path.isdir(root):
        print('Error: root directory does not exist: %s' % root)
        sys.exit(1)

    html_files = collect_html_files(root)

    modified = []
    already_ok = 0
    no_anchor = []

    for path in html_files:
        result = retrofit_file(path, args.apply)
        if result == 'ok':
            already_ok += 1
        elif result == 'modified':
            modified.append(path)
        elif result == 'no_anchor':
            no_anchor.append(path)

    action = 'modified' if args.apply else 'would modify'
    print('%s %d, already ok %d, no anchor %d' % (action, len(modified), already_ok, len(no_anchor)))

    if modified:
        sample = modified[:20]
        print('\n%s files%s:' % (action.capitalize(), ' (first 20)' if len(modified) > 20 else ''))
        for p in sample:
            print('  %s' % p)

    if no_anchor:
        sample = no_anchor[:20]
        print('\nNo anchor found%s:' % (' (first 20)' if len(no_anchor) > 20 else ''))
        for p in sample:
            print('  %s' % p)


if __name__ == '__main__':
    main()
