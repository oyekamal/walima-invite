"""Render card-<theme>.png for every design (and card.png for the default theme), then check each QR decodes.
Usage: python3 tools/render_cards.py [theme,theme,...]   (needs: pip install playwright opencv-python; a Chrome/Chromium)"""
import json, pathlib, shutil, sys
from playwright.sync_api import sync_playwright

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
