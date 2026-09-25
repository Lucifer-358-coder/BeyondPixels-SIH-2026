from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json
import random

ROOT = Path("data/research_single_image_documents_v01")
PLAN = ROOT / "v03_new_evaluation_design_v01.json"
LOCK = ROOT / "extractor_lock_v03.json"
OUT = ROOT / "v03_new_evaluation_references"

EXPECTED_PLAN = "6e27a589ab7117b9b13c90e77a9690203e99f1644bf2b9f7271a222329a29116"
EXPECTED_LOCK = "7bd93c59e8d03add6a259dea03d86b357e7bce421a8bd59549c157bd7b850701"

def sha256(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert sha256(PLAN) == EXPECTED_PLAN, "Evaluation plan changed"
assert sha256(LOCK) == EXPECTED_LOCK, "V03 extractor lock changed"

lock = json.loads(LOCK.read_text(encoding="utf-8"))
for filename, expected in lock["files_sha256"].items():
    assert sha256(Path(filename)) == expected, f"Locked file changed: {filename}"

if OUT.exists():
    raise SystemExit(f"STOP: {OUT} already exists. Nothing overwritten.")

plan = json.loads(PLAN.read_text(encoding="utf-8"))
families = plan["families"]

assert len(families) == 8
assert Counter(f["layout"] for f in families) == {"F": 4, "G": 4}
assert {f["family_id"] for f in families} == {
    f"fictional_document_{n:02d}" for n in range(21, 29)
}

def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()

PALETTES = [
    ("#244d61", "#fffaf0"),
    ("#53634c", "#fcfff4"),
    ("#644b70", "#fff8fc"),
    ("#405a7c", "#f5f9ff"),
]

def field(draw, x, y, label, value):
    draw.text((x, y), label, font=font(16, True), fill="#526372")
    draw.text((x, y + 29), value, font=font(27, True), fill="#172e40")

def avatar(draw, box, rng):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=12, fill="#dce8ee")
    draw.text((x1 + 12, y1 + 9), "DRAWN AVATAR",
              font=font(12), fill="#314d60")

    cx = (x1 + x2) // 2
    face = rng.choice(["#ae816a", "#c7977c", "#997563"])
    shirt = rng.choice(["#567d9b", "#846b94", "#527b72"])

    draw.ellipse((cx - 38, y1 + 45, cx + 38, y1 + 121), fill=face)
    draw.rounded_rectangle(
        (x1 + 28, y1 + 140, x2 - 28, y2 - 12),
        radius=28, fill=shirt
    )

def mark(draw, box, text):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=8, outline="#718b9e", width=3)
    draw.text((x1 + 12, y1 + 14), "FICTIONAL MARK",
              font=font(13, True), fill="#45667d")
    draw.text((x1 + 12, y1 + 43), text,
              font=font(17, True), fill="#45667d")

def render(family):
    rng = random.Random(family["design_seed"])
    number = int(family["family_id"].split("_")[-1])
    accent, paper = PALETTES[number % len(PALETTES)]

    image = Image.new("RGB", (1200, 760), "#e2e9ef")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((30, 30, 1170, 730), radius=18, fill=paper)

    name = f"FICTIONAL PERSON {number:02d}"
    code = f"SPEC-{number:04d}"
    birth = f"200{number % 10}-02-14"
    expiry = f"203{number % 10}-08-21"
    stamp_text = rng.choice(["SAMPLE ONLY", "TEST MARK", "SPECIMEN"])

    if family["layout"] == "F":
        # Asymmetric: a vertical identity panel and an offset expiry field.
        draw.rectangle((30, 30, 285, 730), fill=accent)
        draw.text((55, 68), "FICTIONAL", font=font(25, True), fill="white")
        draw.text((55, 108), "RECORD", font=font(25, True), fill="white")
        draw.text((55, 157), "NOT VALID", font=font(17, True), fill="#ffe1a3")

        avatar(draw, (60, 230, 255, 450), rng)

        field(draw, 340, 170, "NAME", name)
        field(draw, 340, 300, "DATE OF BIRTH", birth)
        field(draw, 750, 300, "DOCUMENT CODE", code)
        field(draw, 750, 440, "EXPIRY DATE", expiry)
        mark(draw, (340, 525, 585, 625), stamp_text)

    else:
        # Sectioned arrangement with expiry in a lower two-column row.
        draw.rectangle((30, 30, 1170, 135), fill=accent)
        draw.text((65, 63), "FICTIONAL RESEARCH DOCUMENT",
                  font=font(33, True), fill="white")

        draw.rounded_rectangle((55, 158, 820, 370),
                               radius=12, outline="#a9bcc8", width=2)
        field(draw, 85, 180, "NAME", name)
        field(draw, 85, 285, "DOCUMENT CODE", code)

        avatar(draw, (870, 165, 1090, 415), rng)

        draw.line((70, 465, 1120, 465), fill=accent, width=3)
        field(draw, 85, 485, "DATE OF BIRTH", birth)
        field(draw, 525, 485, "EXPIRY DATE", expiry)
        mark(draw, (85, 590, 330, 675), stamp_text)

    draw.text((345 if family["layout"] == "F" else 385, 690),
              "SYNTHETIC IMAGE - NOT AN ID",
              font=font(19, True), fill="#a04d4d")

    return image, expiry

OUT.mkdir(parents=True)

inventory = {
    "status": "NEW_SET_ASIDE_REFERENCES_GENERATED_NOT_SCORED",
    "evaluation_plan_sha256": sha256(PLAN),
    "extractor_lock_sha256": sha256(LOCK),
    "references": [],
}

for family in families:
    image, expiry = render(family)
    path = OUT / f"{family['family_id']}_reference.png"
    image.save(path)

    inventory["references"].append({
        "family_id": family["family_id"],
        "layout": family["layout"],
        "file": path.name,
        "sha256": sha256(path),
        "size": list(image.size),
        "expected_reference_expiry": expiry,
    })

    print(f"CREATED: {path.name} | layout={family['layout']}")

inventory_path = OUT / "inventory.json"
inventory_path.write_text(
    json.dumps(inventory, indent=2) + "\n",
    encoding="utf-8",
)

print("\nNEW EVALUATION REFERENCES:", len(inventory["references"]))
print("INVENTORY SHA256:", sha256(inventory_path))
print("LOCATION:", OUT.resolve())
print("No OCR or detector scoring performed.")
print("Locked extractor, production app, models, and UI unchanged.")
