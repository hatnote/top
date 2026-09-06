"""Generate per-language web app manifests (static/manifest-{lang}.json).

Run from top/ like the other scripts:

    python gen_manifests.py

For every language in LOCAL_LANG_MAP, writes a manifest whose
id/start_url open that language's index, so an
install from /ar/ opens /ar/ instead of the English root. Localized
name/short_name come from templates/strings/{lang}_strings.yaml when
present (index_title/title), else English fallbacks.

Root static/manifest.json is hand-maintained and stays the manifest for
the root/English pages; description/display/colors/icons here are copied
from it verbatim. Rerun this script when adding a language or changing
those shared fields.
"""

import json
import os

import yaml

from common import LOCAL_LANG_MAP

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(os.path.dirname(CUR_PATH), 'static')
STRINGS_PATH = os.path.join(CUR_PATH, 'templates', 'strings')

RTL_LANGS = ('ar', 'fa', 'ur')

# Shared fields, verbatim from static/manifest.json
DESCRIPTION = 'The most-visited Wikipedia articles, updated daily.'
DISPLAY = 'standalone'
BACKGROUND_COLOR = '#dfe0e2'
THEME_COLOR = '#0d0f05'
ICONS = [
    {'src': '/img/icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
    {'src': '/img/icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
    {'src': '/img/icon-maskable-512.png', 'sizes': '512x512',
     'type': 'image/png', 'purpose': 'maskable'},
]


def load_strings(lang):
    path = os.path.join(STRINGS_PATH, lang + '_strings.yaml')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def main():
    written = []
    for lang in sorted(LOCAL_LANG_MAP):
        # No static/{lang}/ existence check: lang dirs are server-side
        # build artifacts and absent from dev checkouts; the map is the
        # authoritative list of served languages.
        strings = load_strings(lang)
        manifest = {
            'id': '/%s/' % lang,
            'name': (strings.get('index_title') or 'Wikipedia Top 100').strip(),
            'short_name': (strings.get('title') or 'Top 100').strip(),
            'description': DESCRIPTION,
            'lang': lang,
            'dir': 'rtl' if lang in RTL_LANGS else 'ltr',
            'start_url': '/%s/?src=homescreen' % lang,
            'scope': '/',
            'display': DISPLAY,
            'background_color': BACKGROUND_COLOR,
            'theme_color': THEME_COLOR,
            'icons': ICONS,
        }
        out_path = os.path.join(STATIC_PATH, 'manifest-%s.json' % lang)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            f.write('\n')
        written.append(lang)
    print('wrote %d manifests: %s' % (len(written), ' '.join(written)))


if __name__ == '__main__':
    main()
