"""Write qr.svg: a QR code that opens the venue in Google Maps. Reads maps_query from invite.js.
Usage: python3 tools/make_qr.py   (needs: pip install qrcode)"""
import json, pathlib, urllib.parse
import qrcode, qrcode.image.svg

root = pathlib.Path(__file__).resolve().parent.parent
invite = json.loads((root / "invite.js").read_text().rsplit("window.INVITE =", 1)[1].strip().rstrip(";"))
url = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(invite["maps_query"])
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0, image_factory=qrcode.image.svg.SvgPathImage)
qr.add_data(url)
qr.make(fit=True)
qr.make_image().save(root / "qr.svg")
print("qr.svg ->", url)
