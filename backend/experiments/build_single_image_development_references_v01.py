from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json
import random

ROOT = Path("data/research_single_image_documents_v01")
PLAN = ROOT / "dataset_design_plan_v01.json"
OUT = ROOT / "development_references"
EXPECTED_PLAN_HASH = "e452d213c846362a31d80a14f6f29064b50f008562367c89f5c3f975068443cf"

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert sha256(PLAN) == EXPECTED_PLAN_HASH, "Design plan changed"
if OUT.exists():
    raise SystemExit(f"STOP: {OUT} already exists. No files overwritten.")

plan = json.loads(PLAN.read_text(encoding="utf-8"))
families = [f for f in plan["families"] if f["split"] == "development"]
assert len(families) == 12
assert {f["layout"] for f in families} == {"A", "B", "C"}

def font(size, bold=False):
    filename = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / filename
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()

PALETTES = {
    "navy_cream": ("#23465f", "#fff8e8"),
    "teal_white": ("#246b70", "#ffffff"),
    "plum_sand": ("#68476a", "#fff4e8"),
    "slate_blue": ("#435b78", "#f2f7ff"),
    "olive_ivory": ("#56664d", "#ffffef"),
}

def field(draw, x, y, label, value, value_size=26):
    draw.text((x, y), label, font=font(15, True), fill="#526372")
    draw.text((x, y + 24), value, font=font(value_size, True), fill="#172e40")

def avatar(draw, box, rng):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=12, fill="#dce8ee")
    draw.text((x1 + 12, y1 + 9), "DRAWN AVATAR", font=font(12), fill="#314d60")
    cx = (x1 + x2) // 2
    skin = rng.choice(["#ad8069", "#c59476", "#8e6d61", "#d5a88a"])
    draw.ellipse((cx - 37, y1 + 47, cx + 37, y1 + 121), fill=skin)
    draw.rounded_rectangle(
        (x1 + 26, y1 + 135, x2 - 26, y2 - 12),
        radius=28, fill=rng.choice(["#537a99", "#89729c", "#527d70"])
    )

def fictional_mark(draw, box):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=8, outline="#7894a6", width=3)
    draw.text((x1 + 16, y1 + 18), "FICTIONAL MARK",
              font=font(14, True), fill="#45667d")
    draw.text((x1 + 16, y1 + 45), "SAMPLE ONLY",
              font=font(17, True), fill="#45667d")

def render(family):
    rng = random.Random(family["design_seed"])
    accent, paper = PALETTES[family["palette"]]
    image = Image.new("RGB", (1200, 760), "#dfe8ef")
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((30, 30, 1170, 730), radius=18, fill=paper)

    layout = family["layout"]
    number = int(family["family_id"].split("_")[-1])
    name = f"FICTIONAL PERSON {number:02d}"
    code = f"SPEC-{number:04d}"

    if layout == "A":
        # Horizontal header; portrait on the right.
        d.rectangle((30, 30, 1170, 158), fill=accent)
        d.text((70, 60), "FICTIONAL DOCUMENT",
               font=font(37, True), fill="white")
        d.text((72, 115), "RESEARCH SAMPLE - NOT VALID",
               font=font(19, True), fill="#ffdfa1")
        field(d, 85, 215, "NAME", name)
        field(d, 85, 320, "DOCUMENT CODE", code)
        field(d, 85, 425, "DATE OF BIRTH", f"200{number % 10}-02-14")
        field(d, 85, 530, "EXPIRY DATE", f"203{number % 10}-08-21")
        avatar(d, (870, 215, 1090, 475), rng)
        fictional_mark(d, (865, 520, 1090, 620))

    elif layout == "B":
        # Vertical sidebar; portrait on the left.
        d.rectangle((30, 30, 345, 730), fill=accent)
        d.text((65, 80), "FICTIONAL", font=font(30, True), fill="white")
        d.text((65, 123), "DOCUMENT", font=font(30, True), fill="white")
        d.text((65, 174), "NOT VALID", font=font(21, True), fill="#ffdfa1")
        avatar(d, (85, 235, 290, 465), rng)
        fictional_mark(d, (77, 510, 304, 615))
        field(d, 395, 150, "NAME", name)
        field(d, 395, 262, "DOCUMENT CODE", code)
        field(d, 395, 374, "DATE OF BIRTH", f"200{number % 10}-02-14")
        field(d, 395, 486, "EXPIRY DATE", f"203{number % 10}-08-21")

    else:
        # Compact top bar; centered portrait; fields in two columns.
        d.rectangle((30, 30, 1170, 120), fill=accent)
        d.text((67, 55), "FICTIONAL DOCUMENT / RESEARCH SAMPLE",
               font=font(29, True), fill="white")
        avatar(d, (475, 155, 675, 390), rng)
        field(d, 75, 190, "NAME", name, 22)
        field(d, 75, 315, "DOCUMENT CODE", code)
        field(d, 745, 190, "DATE OF BIRTH", f"200{number % 10}-02-14")
        field(d, 745, 315, "EXPIRY DATE", f"203{number % 10}-08-21")
        fictional_mark(d, (465, 435, 690, 535))
        d.rectangle((30, 610, 1170, 730), fill=accent)
        d.text((75, 655), "SYNTHETIC IMAGE - NOT AN ID",
               font=font(27, True), fill="white")

    if layout != "C":
        d.text((72 if layout == "A" else 395, 675),
               "SYNTHETIC IMAGE - NOT AN ID",
               font=font(20, True), fill="#a04d4d")

    return image

OUT.mkdir(parents=True)
inventory = {
    "status": "DEVELOPMENT_REFERENCES_ONLY",
    "design_plan_sha256": sha256(PLAN),
    "references": []
}

for family in families:
    image = render(family)
    path = OUT / f"{family['family_id']}_reference.png"
    image.save(path)

    inventory["references"].append({
        "family_id": family["family_id"],
        "layout": family["layout"],
        "file": path.name,
        "sha256": sha256(path),
        "size": list(image.size)
    })
    print(f"CREATED: {path.name} | layout={family['layout']}")

inventory_path = OUT / "inventory.json"
inventory_path.write_text(json.dumps(inventory, indent=2) + "\n",
                          encoding="utf-8")

print("\nDEVELOPMENT REFERENCES:", len(inventory["references"]))
print("INVENTORY SHA256:", sha256(inventory_path))
print("LOCATION:", OUT.resolve())
print("Evaluation images, detectors, models, and UI were not changed.")
