"""Render card-<theme>.png for every design (and card.png for the default theme), then check each QR decodes.
Usage: python3 tools/render_cards.py [theme,theme,...]   (needs: pip install playwright opencv-python; a Chrome/Chromium)"""
import json, pathlib, shutil, sys
import io
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

TEXT = ".content [data-f], .content [data-t], .content .rsvp a, .content .qr a, .content .date .side"


def ink_overlaps(page, gap=2):
    """Render each text line on its own and compare the pixels it actually paints.
    Font boxes are useless for Nastaliq (huge ascent/descent), so this checks real ink, with a small safety gap."""
    def shot(css):
        page.add_style_tag(content=css)
        return np.asarray(Image.open(io.BytesIO(page.locator(".card").screenshot(animations="disabled"))).convert("RGB"), dtype=np.int16)
    page.evaluate(f"document.querySelectorAll('{TEXT}').forEach((e,i)=>e.dataset.ink=i)")
    n = page.evaluate("document.querySelectorAll('[data-ink]').length")
    names = page.evaluate("[...document.querySelectorAll('[data-ink]')].map(e=>e.textContent.trim().slice(0,24))")
    shown = [sel for sel in [".branch", ".frame", ".thread", ".seal"]
             if page.evaluate(f"[...document.querySelectorAll('.card {sel}')].some(e=>getComputedStyle(e).display!=='none')")]
    quiet = ".card *,.card::before{visibility:hidden!important;animation:none!important;transition:none!important}"
    base = shot(quiet)
    masks = []
    for i in range(n):
        img = shot(f"[data-ink='{i}'],[data-ink='{i}'] *{{visibility:visible!important}}")
        m = np.abs(img - base).max(axis=2) > 24
        if gap:  # grow each mask so lines that merely touch also fail
            g = m.copy()
            for dy in range(-gap, gap + 1):
                for dx in range(-gap, gap + 1):
                    g |= np.roll(np.roll(m, dy, 0), dx, 1)
            m = g
        masks.append(m)
        page.evaluate("document.querySelectorAll('style').forEach((s,k,a)=>{if(k==a.length-1)s.remove()})")
    # decorations the text must keep clear of
    decor = []
    for sel in shown:
        if True:
            img = shot(f".card {sel},.card {sel} *{{visibility:visible!important}}")
            decor.append((sel, np.abs(img - base).max(axis=2) > 14))
            page.evaluate("document.querySelectorAll('style').forEach((s,k,a)=>{if(k==a.length-1)s.remove()})")
    h = base.shape[0]
    bad = [f"{names[i]} <> {names[j]}" for i in range(n) for j in range(i + 1, n)
           if (masks[i] & masks[j]).sum() > 3]
    bad += [f"{names[i]} <> decoration {sel}" for i in range(n) for sel, d in decor if (masks[i] & d).sum() > 3]
    bad += [f"below frame: {names[i]}" for i in range(n) if masks[i][int(h * .965):].any()]
    return bad

root = pathlib.Path(__file__).resolve().parent.parent
THEMES = ["midnight", "lacquer", "thread", "breeze", "blush"]
themes = sys.argv[1].split(",") if len(sys.argv) > 1 else THEMES
chrome = shutil.which("google-chrome") or shutil.which("chromium")

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=chrome) if chrome else p.chromium.launch()
    for th in themes:
        page = browser.new_page(viewport={"width": 600, "height": 1100}, device_scale_factor=2)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"file://{root}/index.html#{th}")
        page.add_style_tag(content=".envelope{display:none!important}")
        page.wait_for_timeout(6500)  # let the red thread finish drawing and petals spread
        page.locator(".card").screenshot(path=str(root / f"card-{th}.png"))
        overlaps = ink_overlaps(page)
        assert not overlaps, (th, overlaps)
        assert not errors, (th, errors)
        page.close()
    browser.close()

default = json.loads((root / "invite.js").read_text().rsplit("window.INVITE =", 1)[1].strip().rstrip(";"))["theme"]
if default in themes:
    shutil.copy(root / f"card-{default}.png", root / "card.png")

try:
    import cv2
    for th in themes:
        text = cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(root / f"card-{th}.png")))[0]
        assert text.startswith("https://www.google.com/maps"), f"QR did not decode on {th}"
    print("rendered + QR ok:", ", ".join(themes))
except ImportError:
    print("rendered:", ", ".join(themes), "(install opencv-python to check the QR codes)")
