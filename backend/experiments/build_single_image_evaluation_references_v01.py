from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json
import random

ROOT = Path("data/research_single_image_documents_v01")
PLAN = ROOT / "dataset_design_plan_v01.json"
LOCK = ROOT / "extractor_lock_v02.json"
OUT = ROOT / "evaluation_references_v01"

EXPECTED_PLAN_SHA256 = "e452d213c846362a31d80a14f6f29064b50f008562367c89f5c3f975068443cf"
EXPECTED_LOCK_SHA256 = "a40da0a6a54c8812486ca8929d5f526120b5a8117eff10a4c64fd1789d1b0c45"

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert sha256(PLAN) == EXPECTED_PLAN_SHA256, "Design plan changed"
assert sha256(LOCK) == EXPECTED_LOCK_SHA256, "Extractor lock changed"

lock = json.loads(LOCK.read_text(encoding="utf-8"))
for filename, expected_hash in lock["files_sha256"].items():
    path = Path(filename)
    assert path.is_file(), f"Missing locked file: {filename}"
    assert sha256(path) == expected_hash, f"Locked file changed: {filename}"

if OUT.exists():
    raise SystemExit(f"STOP: {OUT} already exists; nothing overwritten.")

plan = json.loads(PLAN.read_text(encoding="utf-8"))
families = [f for f in plan["families"] if f["split"] == "evaluation"]

assert len(families) == 8
assert Counter(f["layout"] for f in families) == {"D": 4, "E": 4}
assert {f["family_id"] for f in families} == {
    f"fictional_document_{n:02d}" for n in range(13, 21)
}

def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    return (
        ImageFont.truetype(str(path), size)
        if path.exists()
        else ImageFont.load_default()
    )

PALETTES = {
    "navy_cream": ("#23465f", "#fff8e8"),
    "teal_white": ("#246b70", "#ffffff"),
    "plum_sand": ("#68476a", "#fff4e8"),
    "slate_blue": ("#435b78", "#f2f7ff"),
    "olive_ivory": ("#56664d", "#ffffef"),
}

def field(draw, x, y, label, value):
    draw.text((x, y), label, font=font(16, True), fill="#526372")
    draw.text((x, y + 27), value, font=font(27, True), fill="#172e40")

def avatar(draw, box, rng):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=12, fill="#dce8ee")
    draw.text(
        (x1 + 12, y1 + 10),
        "DRAWN AVATAR",
        font=font(12),
        fill="#314d60",
    )
    cx = (x1 + x2) // 2
    skin = rng.choice(["#ad8069", "#c59476", "#8e6d61", "#d5a88a"])
    draw.ellipse(
        (cx - 38, y1 + 47, cx + 38, y1 + 123),
        fill=skin,
    )
    draw.rounded_rectangle(
        (x1 + 25, y1 + 137, x2 - 25, y2 - 14),
        radius=27,
        fill=rng.choice(["#537a99", "#89729c", "#527d70"]),
    )

def fictional_mark(draw, box, text):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=8, outline="#7894a6", width=3)
    draw.text(
        (x1 + 15, y1 + 16),
        "FICTIONAL MARK",
        font=font(14, True),
        fill="#45667d",
    )
    draw.text(
        (x1 + 15, y1 + 46),
        text,
        font=font(17, True),
        fill="#45667d",
    )

def render(family):
    rng = random.Random(family["design_seed"])
    accent, paper = PALETTES[family["palette"]]
    number = int(family["family_id"].split("_")[-1])

    image = Image.new("RGB", (1200, 760), "#e3e9ef")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((30, 30, 1170, 730), radius=18, fill=paper)

    name = f"FICTIONAL PERSON {number:02d}"
    code = f"SPEC-{number:04d}"
    birth = f"200{number % 10}-02-14"
    expiry = f"203{number % 10}-08-21"
    mark_text = rng.choice(["SAMPLE ONLY", "TEST MARK", "SPECIMEN"])

    if family["layout"] == "D":
        # Broad top header, portrait and mark on the left,
        # four vertically stacked fields on the right.
        draw.rectangle((30, 30, 1170, 130), fill=accent)
        draw.text(
            (65, 60), "FICTIONAL TRAVEL RECORD",
            font=font(34, True), fill="white",
        )
        avatar(draw, (85, 175, 335, 465), rng)
        fictional_mark(draw, (80, 515, 325, 615), mark_text)

        field(draw, 410, 165, "NAME", name)
        field(draw, 410, 280, "DOCUMENT CODE", code)
        field(draw, 410, 395, "DATE OF BIRTH", birth)
        field(draw, 410, 510, "EXPIRY DATE", expiry)

    else:
        # Fields in an upper two-column arrangement;
        # portrait lower right and mark lower left.
        draw.rectangle((30, 30, 1170, 130), fill=accent)
        draw.text(
            (65, 61), "FICTIONAL IDENTIFICATION RECORD",
            font=font(30, True), fill="white",
        )

        field(draw, 70, 170, "NAME", name)
        field(draw, 70, 295, "DOCUMENT CODE", code)
        field(draw, 485, 170, "DATE OF BIRTH", birth)
        field(draw, 485, 295, "EXPIRY DATE", expiry)

        avatar(draw, (870, 380, 1100, 635), rng)
        fictional_mark(draw, (70, 525, 315, 625), mark_text)

    draw.text(
        (70, 678), "SYNTHETIC RESEARCH IMAGE - NOT AN ID",
        font=font(21, True), fill="#a04d4d",
    )

    return image, expiry

OUT.mkdir(parents=True)

inventory = {
    "status": "SET_ASIDE_REFERENCES_GENERATED_NOT_SCORED",
    "design_plan_sha256": sha256(PLAN),
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

print("\nEVALUATION REFERENCES CREATED:", len(inventory["references"]))
print("INVENTORY SHA256:", sha256(inventory_path))
print("LOCATION:", OUT.resolve())
print("No OCR, extractor, or detector scoring performed.")
print("Production app, models, and UI unchanged.")
