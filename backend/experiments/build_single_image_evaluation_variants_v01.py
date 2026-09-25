from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import hashlib
import json

ROOT = Path("data/research_single_image_documents_v01")
REFS = ROOT / "evaluation_references_v01"
OUT = ROOT / "evaluation_variants_v01"
LOCK = ROOT / "extractor_lock_v02.json"
INVENTORY = REFS / "inventory.json"

EXPECTED_LOCK = "a40da0a6a54c8812486ca8929d5f526120b5a8117eff10a4c64fd1789d1b0c45"
EXPECTED_INVENTORY = "bcf1bfbbe35a747cb5fd4569346609de10bc37d5eca9d3851e352c10bb3c1345"

def sha256(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert sha256(LOCK) == EXPECTED_LOCK, "Extractor lock changed"
assert sha256(INVENTORY) == EXPECTED_INVENTORY, "Evaluation inventory changed"

lock = json.loads(LOCK.read_text(encoding="utf-8"))
for filename, expected in lock["files_sha256"].items():
    assert sha256(Path(filename)) == expected, f"Locked file changed: {filename}"

if OUT.exists():
    raise SystemExit(f"STOP: {OUT} already exists. No files overwritten.")

inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
references = inventory["references"]

assert len(references) == 8
assert Counter(r["layout"] for r in references) == {"D": 4, "E": 4}

def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    return (
        ImageFont.truetype(str(path), size)
        if path.exists()
        else ImageFont.load_default()
    )

# Right and bottom coordinates are exclusive.
REGIONS = {
    "D": {
        "expiry": (405, 534, 780, 580),
        "portrait": (85, 175, 335, 465),
        "stamp": (80, 515, 325, 615),
    },
    "E": {
        "expiry": (480, 319, 850, 365),
        "portrait": (870, 380, 1100, 635),
        "stamp": (70, 525, 315, 625),
    },
}

def create_edit(reference, layout, kind, number):
    image = reference.copy()
    draw = ImageDraw.Draw(image)
    box = REGIONS[layout][kind]
    x1, y1, x2, y2 = box

    if kind == "expiry":
        # Replace only the printed value; retain the field label.
        paper = reference.getpixel((x2 - 5, y2 - 5))
        draw.rectangle(
            (x1, y1, x2 - 1, y2 - 1),
            fill=paper,
        )
        value_x = 410 if layout == "D" else 485
        value_y = 537 if layout == "D" else 322
        draw.text(
            (value_x, value_y),
            f"204{number % 10}-11-25",
            font=font(27, True),
            fill="#172e40",
        )

    elif kind == "portrait":
        # Fictional drawing only; no real person's photograph.
        draw.rounded_rectangle(
            (x1, y1, x2 - 1, y2 - 1),
            radius=12,
            fill="#dce8ee",
        )
        draw.text(
            (x1 + 12, y1 + 10),
            "DRAWN AVATAR",
            font=font(12),
            fill="#314d60",
        )
        cx = (x1 + x2) // 2
        draw.ellipse(
            (cx - 38, y1 + 47, cx + 38, y1 + 123),
            fill="#b87962",
        )
        draw.polygon(
            [
                (x1 + 20, y2 - 14),
                (cx - 32, y1 + 138),
                (cx + 32, y1 + 138),
                (x2 - 20, y2 - 14),
            ],
            fill="#8b677f",
        )

    elif kind == "stamp":
        # Change only the fictional mark's lower text.
        paper = reference.getpixel((x1 + 20, y1 + 85))
        draw.rectangle(
            (x1 + 11, y1 + 43, x2 - 10, y1 + 79),
            fill=paper,
        )
        draw.text(
            (x1 + 15, y1 + 46),
            "DEMO ENTRY",
            font=font(17, True),
            fill="#45667d",
        )

    else:
        raise ValueError(kind)

    observed = ImageChops.difference(reference, image).getbbox()
    assert observed is not None, f"No change: {kind}"
    assert (
        x1 <= observed[0]
        and y1 <= observed[1]
        and observed[2] <= x2
        and observed[3] <= y2
    ), f"Change outside annotated region: {kind}: {observed}"

    mask = Image.new("L", reference.size, 0)
    ImageDraw.Draw(mask).rectangle(
        (x1, y1, x2 - 1, y2 - 1),
        fill=255,
    )
    assert mask.getbbox() == box

    return image, mask, observed, box

OUT.mkdir(parents=True)

manifest = {
    "name": "single_image_evaluation_variants_v01",
    "status": "SET_ASIDE_VARIANTS_GENERATED_NOT_SCORED",
    "evaluation_reference_inventory_sha256": sha256(INVENTORY),
    "extractor_lock_sha256": sha256(LOCK),
    "limitations": [
        "Fictional documents from an internal generator",
        "This is an OCR extraction experiment, not tampering detection",
        "References and annotations are evaluation ground truth, never extractor inputs",
        "Evaluation results must not be used to revise the locked extractor and claim fresh validation",
    ],
    "families": [],
}

for record in references:
    family_id = record["family_id"]
    layout = record["layout"]
    number = int(family_id.split("_")[-1])

    assert layout in REGIONS
    reference_path = REFS / record["file"]
    assert sha256(reference_path) == record["sha256"]

    with Image.open(reference_path) as source:
        reference = source.convert("RGB")

    folder = OUT / family_id
    folder.mkdir()

    family = {
        "family_id": family_id,
        "layout": layout,
        "reference_file": record["file"],
        "reference_sha256": record["sha256"],
        "expected_reference_expiry": record["expected_reference_expiry"],
        "edits": [],
        "benign_controls": [],
    }

    for kind in ("expiry", "portrait", "stamp"):
        edited, mask, observed, box = create_edit(
            reference, layout, kind, number
        )

        image_name = f"edit_{kind}.png"
        mask_name = f"edit_{kind}_region_mask.png"

        edited.save(folder / image_name)
        mask.save(folder / mask_name)

        family["edits"].append({
            "file": image_name,
            "type": kind,
            "label": "controlled_synthetic_edit",
            "expected_expiry": (
                f"204{number % 10}-11-25"
                if kind == "expiry"
                else record["expected_reference_expiry"]
            ),
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
            "expected_expiry": record["expected_reference_expiry"],
            "sha256": sha256(folder / filename),
        })

    manifest["families"].append(family)
    print(
        f"CREATED: {family_id} | layout={layout} | "
        "3 edits + 3 controls + 3 masks"
    )

manifest_path = OUT / "manifest.json"
manifest_path.write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
)

print("\nTOTAL: 8 evaluation families, 24 edits, 24 controls, 24 masks")
print("MANIFEST SHA256:", sha256(manifest_path))
print("LOCATION:", OUT.resolve())
print("No OCR or detector scoring performed.")
print("Locked extractor, production app, models, and UI unchanged.")
