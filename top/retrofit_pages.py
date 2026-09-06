#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Retrofit archived HTML pages for mobile: ensure a viewport meta tag
(with viewport-fit=cover for edge-to-edge standalone display) and flip
any apple-mobile-web-app-status-bar-style from default to
black-translucent. Idempotent; dry-run by default, --apply to write."""

import argparse
import os
import sys

from common import BASE_PATH

SKIP_DIRS = {'js', 'css', 'img', 'fonts'}

VIEWPORT_TAG = (b'\n    <meta name="viewport" content='
                b'"width=device-width, initial-scale=1, viewport-fit=cover">')
VIEWPORT_MARKER = b'name="viewport"'
VIEWPORT_FIT = b'viewport-fit'
VIEWPORT_PLAIN = (b'<meta name="viewport" content='
                  b'"width=device-width, initial-scale=1">')
VIEWPORT_COVER = (b'<meta name="viewport" content='
                  b'"width=device-width, initial-scale=1, viewport-fit=cover">')
STATUS_BAR_DEFAULT = (b'<meta name="apple-mobile-web-app-status-bar-style" '
                      b'content="default">')
STATUS_BAR_E2E = (b'<meta name="apple-mobile-web-app-status-bar-style" '
                  b'content="black-translucent">')
ANCHOR_CHARSET = b'<meta charset="UTF-8">'
ANCHOR_HEAD = b'<head>'


def retrofit_file(path, apply):
    """Process a single HTML file.

    Returns one of:
        'ok'        - nothing to do
        'modified'  - changes made (or would be, in dry-run)
        'no_anchor' - viewport missing and no insertion anchor found
        'variant'   - viewport present in an unrecognized form; left alone
    """
    with open(path, 'rb') as f:
        data = f.read()

    new_data = data

    if VIEWPORT_MARKER not in new_data:
        idx = new_data.find(ANCHOR_CHARSET)
        if idx != -1:
            insert_pos = idx + len(ANCHOR_CHARSET)
        else:
            idx = new_data.find(ANCHOR_HEAD)
            if idx != -1:
                insert_pos = idx + len(ANCHOR_HEAD)
            else:
                return 'no_anchor'
        new_data = new_data[:insert_pos] + VIEWPORT_TAG + new_data[insert_pos:]
    elif VIEWPORT_FIT not in new_data:
        if VIEWPORT_PLAIN not in new_data:
            # unexpected viewport shape; don't guess at rewriting it
            return 'variant'
        new_data = new_data.replace(VIEWPORT_PLAIN, VIEWPORT_COVER, 1)

    new_data = new_data.replace(STATUS_BAR_DEFAULT, STATUS_BAR_E2E, 1)

    if new_data == data:
        return 'ok'

    if apply:
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
    variant = []

    for path in html_files:
        result = retrofit_file(path, args.apply)
        if result == 'ok':
            already_ok += 1
        elif result == 'modified':
            modified.append(path)
        elif result == 'no_anchor':
            no_anchor.append(path)
        elif result == 'variant':
            variant.append(path)

    action = 'modified' if args.apply else 'would modify'
    print('%s %d, already ok %d, no anchor %d, variant %d'
          % (action, len(modified), already_ok, len(no_anchor), len(variant)))

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

    if variant:
        sample = variant[:20]
        print('\nUnrecognized viewport%s:' % (' (first 20)' if len(variant) > 20 else ''))
        for p in sample:
            print('  %s' % p)


if __name__ == '__main__':
    main()
