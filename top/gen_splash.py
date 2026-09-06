"""Generate iOS startup ("splash") images and the matching <link> partial.

Run locally (Pillow is not a build-server dependency):

    uv run --with pillow python top/gen_splash.py

Re-run when the device table changes (new Apple hardware) or the artwork
changes; bump --version on artwork changes so installed pages fetch fresh
images. Device table source: apple-web-app skill references/ios-devices.md
(checked 2026-09-04).

Outputs (from repo root):
  - static/img/splash/{w}x{h}@{dpr}-{portrait|landscape}.png  (44 files)
  - top/templates/splash_links.dust                            (44 links)
"""

import argparse
import os

BACKGROUND = '#dfe0e2'  # must equal manifest background_color and body bg

# Unique (points_w, points_h, dpr) triples, portrait orientation.
DEVICE_TRIPLES = [
    # iPhone
    (320, 568, 2),
    (375, 667, 2),
    (414, 736, 3),
    (375, 812, 3),
    (414, 896, 2),
    (414, 896, 3),
    (390, 844, 3),
    (428, 926, 3),
    (393, 852, 3),
    (430, 932, 3),
    (402, 874, 3),
    (440, 956, 3),
    (420, 912, 3),
    # iPad
    (768, 1024, 2),
    (810, 1080, 2),
    (820, 1180, 2),
    (744, 1133, 2),
    (834, 1112, 2),
    (834, 1194, 2),
    (834, 1210, 2),
    (1024, 1366, 2),
    (1032, 1376, 2),
]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLASH_DIR = os.path.join(REPO_ROOT, 'static', 'img', 'splash')
ICON_PATH = os.path.join(REPO_ROOT, 'static', 'img', 'icon-512.png')
PARTIAL_PATH = os.path.join(REPO_ROOT, 'top', 'templates', 'splash_links.dust')

LINK_TMPL = ('    <link rel="apple-touch-startup-image"'
             ' href="{dir_depth}img/splash/%(name)s.png?v=%(version)s"'
             ' media="(device-width: %(mw)spx) and (device-height: %(mh)spx)'
             ' and (-webkit-device-pixel-ratio: %(dpr)s)'
             ' and (orientation: %(orientation)s)">')


def make_splash(px_w, px_h, icon):
    from PIL import Image, ImageDraw

    img = Image.new('RGB', (px_w, px_h), BACKGROUND)
    edge = int(min(px_w, px_h) * 0.20)
    scaled = icon.resize((edge, edge), Image.LANCZOS).convert('RGB')

    # Rounded-rect alpha mask, corner radius 22.5% of icon edge
    # (matches iOS app-icon corner curvature closely enough).
    mask = Image.new('L', (edge, edge), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, edge - 1, edge - 1], radius=int(edge * 0.225), fill=255)

    img.paste(scaled, ((px_w - edge) // 2, (px_h - edge) // 2), mask)
    return img


def main():
    from PIL import Image

    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='1',
                        help='cache-bust version for link hrefs (default: 1)')
    args = parser.parse_args()

    os.makedirs(SPLASH_DIR, exist_ok=True)
    icon = Image.open(ICON_PATH)

    links = []
    written = 0
    for w, h, dpr in DEVICE_TRIPLES:
        for orientation in ('portrait', 'landscape'):
            pw, ph = (w * dpr, h * dpr)
            if orientation == 'landscape':
                pw, ph = ph, pw
            name = '%dx%d@%d-%s' % (w, h, dpr, orientation)
            path = os.path.join(SPLASH_DIR, name + '.png')
            img = make_splash(pw, ph, icon)
            assert img.size == (pw, ph), (
                'size mismatch for %s: %r' % (name, img.size))
            img.save(path, optimize=True)
            written += 1
            mw, mh = (w, h) if orientation == 'portrait' else (h, w)
            links.append(LINK_TMPL % {
                'name': name, 'version': args.version,
                'mw': mw, 'mh': mh, 'dpr': dpr, 'orientation': orientation})

    assert written == len(DEVICE_TRIPLES) * 2, written
    assert len(links) == 44, len(links)

    with open(PARTIAL_PATH, 'w') as f:
        f.write('\n'.join(links) + '\n')

    print('wrote %d splash images to %s' % (written, SPLASH_DIR))
    print('wrote %d links to %s' % (len(links), PARTIAL_PATH))


if __name__ == '__main__':
    main()
