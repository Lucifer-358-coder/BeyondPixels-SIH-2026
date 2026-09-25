from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import hashlib
import json

ROOT = Path("data/research_single_image_documents_v01")
REFERENCES = ROOT / "development_references"
OUT = ROOT / "development_variants_v01"

EXPECTED_INVENTORY_SHA256 = (
    "1214c7455a5964bb98f4e6db6afdb720dc66985668b1fc0f5a1bed84be289e0b"
)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if OUT.exists():
    raise SystemExit(f"STOP: {OUT} already exists; nothing will be overwritten.")

inventory_path = REFERENCES / "inventory.json"
assert sha256(inventory_path) == EXPECTED_INVENTORY_SHA256, "Reference inventory changed"
inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
assert len(inventory["references"]) == 12

def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()

# Coordinates match the already-generated development layouts.
REGIONS = {
    "A": {
        "expiry": (80, 550, 390, 605),
        "portrait": (870, 215, 1090, 475),
        "stamp": (865, 520, 1090, 620),
    },
    "B": {
        "expiry": (390, 505, 755, 560),
        "portrait": (85, 235, 290, 465),
        "stamp": (77, 510, 304, 615),
    },
    "C": {
        "expiry": (739, 335, 1105, 390),
        "portrait": (475, 155, 675, 390),
        "stamp": (465, 435, 690, 535),
    },
}

def create_edit(reference, layout, kind, family_number):
    image = reference.copy()
    draw = ImageDraw.Draw(image)
    box = REGIONS[layout][kind]
    x1, y1, x2, y2 = box

    if kind == "expiry":
        # Replace only the printed value, retaining the field label.
        paper = reference.getpixel((x1 + 2, y1 + 2))
        draw.rectangle((x1, y1, x2 - 1, y2 - 1), fill=paper)
        new_date = f"204{family_number % 10}-11-25"
        value_x = {"A": 85, "B": 395, "C": 745}[layout]
        value_y = {"A": 554, "B": 510, "C": 339}[layout]
        draw.text(
            (value_x, value_y),
            new_date,
            font=font(26, True),
            fill="#172e40",
        )

    elif kind == "portrait":
        # Replace the fictional drawing, not a real person's photograph.
        draw.rounded_rectangle(box, radius=12, fill="#dce8ee")
        draw.text(
            (x1 + 12, y1 + 9),
            "DRAWN AVATAR",
            font=font(12),
            fill="#314d60",
        )
        cx = (x1 + x2) // 2
        draw.ellipse(
            (cx - 37, y1 + 47, cx + 37, y1 + 121),
            fill="#b87962",
        )
        draw.polygon(
            [
                (x1 + 20, y2 - 12),
                (cx - 31, y1 + 138),
                (cx + 31, y1 + 138),
                (x2 - 20, y2 - 12),
            ],
            fill="#8b677f",
        )

    elif kind == "stamp":
        # Change the fictional mark's second line only.
        paper = reference.getpixel((x1 + 12, y1 + 40))
        draw.rectangle(
            (x1 + 12, y1 + 41, x2 - 8, y1 + 79),
            fill=paper,
        )
        draw.text(
            (x1 + 16, y1 + 45),
            "TEST MARK",
            font=font(17, True),
            fill="#45667d",
        )

    else:
        raise ValueError(kind)

    observed = ImageChops.difference(reference, image).getbbox()
    assert observed is not None, f"No difference for {kind}"
    assert (
        x1 <= observed[0] and y1 <= observed[1]
        and observed[2] <= x2 and observed[3] <= y2
    ), f"{kind} changed pixels outside its region: {observed}"

    mask = Image.new("L", reference.size, 0)
    ImageDraw.Draw(mask).rectangle(
        (x1, y1, x2 - 1, y2 - 1),
        fill=255,
    )
    assert mask.getbbox() == box

    return image, mask, observed, box

OUT.mkdir(parents=True)

manifest = {
    "name": "single_image_development_variants_v01",
    "status": "DEVELOPMENT_ONLY_NOT_EVALUATION",
    "reference_inventory_sha256": sha256(inventory_path),
    "purpose": "Controlled fictional edits and benign processing examples",
    "limitations": [
        "All source images come from an internal synthetic generator",
        "Editing artifacts may differ from those in real photographs",
        "Reference images and masks are ground truth, never detector inputs",
        "No evaluation-family images were generated or accessed",
    ],
    "families": [],
}

for record in inventory["references"]:
    family_id = record["family_id"]
    layout = record["layout"]
    number = int(family_id.split("_")[-1])

    assert layout in REGIONS
    reference_path = REFERENCES / record["file"]
    assert sha256(reference_path) == record["sha256"]

    with Image.open(reference_path) as source:
        reference = source.convert("RGB")

    folder = OUT / family_id
    folder.mkdir()

    family = {
        "family_id": family_id,
        "layout": layout,
        "reference_file": str(reference_path.as_posix()),
        "reference_sha256": record["sha256"],
        "edits": [],
        "benign_controls": [],
    }

    for kind in ("expiry", "portrait", "stamp"):
        image, mask, observed, box = create_edit(
            reference, layout, kind, number
        )

        image_name = f"edit_{kind}.png"
        mask_name = f"edit_{kind}_region_mask.png"

        image.save(folder / image_name)
        mask.save(folder / mask_name)

        family["edits"].append({
            "file": image_name,
            "type": kind,
            "label": "controlled_synthetic_edit",
            "annotated_region_xyxy": list(box),
            "observed_difference_xyxy": list(observed),
            "region_mask": mask_name,
            "sha256": sha256(folder / image_name),
            "mask_sha256": sha256(folder / mask_name),
        })

    controls = [
        ("control_copy.png", "unchanged"),
        ("control_jpeg_80.jpg", "jpeg_recompression"),
        ("control_blur_0_6.png", "blur"),
    ]

    reference.save(folder / controls[0][0])
    reference.save(folder / controls[1][0], quality=80)
    reference.filter(
        ImageFilter.GaussianBlur(radius=0.6)
    ).save(folder / controls[2][0])

    for filename, label in controls:
        family["benign_controls"].append({
            "file": filename,
            "label": label,
            "sha256": sha256(folder / filename),
        })

    manifest["families"].append(family)
    print(
        f"CREATED: {family_id} | layout={layout} | "
        "3 edits + 3 benign controls + 3 masks"
    )

manifest_path = OUT / "manifest.json"
manifest_path.write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
)

print("\nTOTAL: 12 development families, 36 edits, 36 controls, 36 masks")
print("MANIFEST SHA256:", sha256(manifest_path))
print("LOCATION:", OUT.resolve())
print("No evaluation images, detectors, models, or UI files changed.")
