from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import hashlib
import json

ROOT = Path("data/research_single_image_documents_v01")
REFS = ROOT / "v03_new_evaluation_references"
OUT = ROOT / "v03_new_evaluation_variants"
PLAN = ROOT / "v03_new_evaluation_design_v01.json"
LOCK = ROOT / "extractor_lock_v03.json"
INVENTORY = REFS / "inventory.json"

EXPECTED = {
    PLAN: "6e27a589ab7117b9b13c90e77a9690203e99f1644bf2b9f7271a222329a29116",
    LOCK: "7bd93c59e8d03add6a259dea03d86b357e7bce421a8bd59549c157bd7b850701",
    INVENTORY: "7be4ea4c5f141217ac1b013b19801e76c09275dcf466d60cffeae47ae4bbbd37",
}

def sha256(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()

if OUT.exists():
    raise SystemExit(f"STOP: {OUT} already exists. Nothing overwritten.")

for path, expected in EXPECTED.items():
    assert sha256(path) == expected, f"Hash mismatch: {path}"

lock = json.loads(LOCK.read_text(encoding="utf-8"))
for filename, expected in lock["files_sha256"].items():
    assert sha256(Path(filename)) == expected, f"Locked file changed: {filename}"

plan = json.loads(PLAN.read_text(encoding="utf-8"))
inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))

families = {f["family_id"]: f for f in plan["families"]}
references = inventory["references"]

assert len(families) == len(references) == 8
assert Counter(r["layout"] for r in references) == {"F": 4, "G": 4}
assert set(families) == {r["family_id"] for r in references}

def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    return (
        ImageFont.truetype(str(path), size)
        if path.exists()
        else ImageFont.load_default()
    )

# All boxes have exclusive right and bottom coordinates.
REGIONS = {
    "F": {
        "expiry_value": (745, 465, 1100, 515),
        "expiry_label": (745, 435, 1000, 465),
        "expiry_field": (745, 435, 1100, 515),
        "portrait": (60, 230, 256, 451),
        "stamp": (340, 525, 586, 626),
        "expiry_x": 750,
        "expiry_value_y": 469,
    },
    "G": {
        "expiry_value": (520, 510, 900, 560),
        "expiry_label": (520, 480, 790, 510),
        "expiry_field": (520, 480, 900, 560),
        "portrait": (870, 165, 1091, 416),
        "stamp": (85, 590, 331, 676),
        "expiry_x": 525,
        "expiry_value_y": 514,
    },
}

def mask_for(size, box):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle(
        (box[0], box[1], box[2] - 1, box[3] - 1),
        fill=255,
    )
    assert mask.getbbox() == box
    return mask

def clear_rectangle(image, box):
    x1, y1, x2, y2 = box
    # Sample blank paper from the right edge of the field.
    paper = image.getpixel((x2 - 5, y1 + 5))
    ImageDraw.Draw(image).rectangle(
        (x1, y1, x2 - 1, y2 - 1),
        fill=paper,
    )

def create_variant(reference, layout, kind, number):
    config = REGIONS[layout]
    image = reference.copy()
    draw = ImageDraw.Draw(image)

    if kind == "expiry_value_edit":
        box = config["expiry_value"]
        clear_rectangle(image, box)
        draw = ImageDraw.Draw(image)
        draw.text(
            (config["expiry_x"], config["expiry_value_y"]),
            f"204{number % 10}-11-25",
            font=font(27, True),
            fill="#172e40",
        )

    elif kind == "portrait_edit":
        box = config["portrait"]
        x1, y1, x2, y2 = box
        draw.rounded_rectangle(
            (x1, y1, x2 - 1, y2 - 1),
            radius=12,
            fill="#dce8ee",
        )
        draw.text(
            (x1 + 12, y1 + 9),
            "DRAWN AVATAR",
            font=font(12),
            fill="#314d60",
        )
        cx = (x1 + x2) // 2
        draw.ellipse(
            (cx - 38, y1 + 45, cx + 38, y1 + 121),
            fill="#b87962",
        )
        draw.polygon(
            [
                (x1 + 18, y2 - 13),
                (cx - 32, y1 + 138),
                (cx + 32, y1 + 138),
                (x2 - 18, y2 - 13),
            ],
            fill="#8b677f",
        )

    elif kind == "fictional_mark_edit":
        box = config["stamp"]
        x1, y1, x2, y2 = box
        paper = reference.getpixel((x1 + 120, y1 + 34))
        draw.rectangle(
            (x1 + 9, y1 + 39, x2 - 10, y1 + 73),
            fill=paper,
        )
        draw.text(
            (x1 + 12, y1 + 43),
            "DEMO ENTRY",
            font=font(17, True),
            fill="#45667d",
        )

    elif kind == "birth_date_only_no_expiry_label":
        # Remove both the expiry label and expiry value.
        # The existing date of birth remains visible.
        box = config["expiry_field"]
        clear_rectangle(image, box)

    elif kind == "unlabelled_date_no_expiry_label":
        # Remove only the label; retain the expiry-like date.
        box = config["expiry_label"]
        clear_rectangle(image, box)

    else:
        raise ValueError(kind)

    observed = ImageChops.difference(reference, image).getbbox()
    assert observed is not None, f"No pixels changed for {kind}"
    assert (
        box[0] <= observed[0]
        and box[1] <= observed[1]
        and observed[2] <= box[2]
        and observed[3] <= box[3]
    ), f"Unexpected changes outside {kind} region: {observed}"

    return image, mask_for(reference.size, box), observed, box

# Prepare and validate all images in memory before creating output files.
prepared = []
for record in references:
    family_id = record["family_id"]
    layout = record["layout"]
    number = int(family_id.split("_")[-1])
    planned = families[family_id]

    assert layout == planned["layout"]
    assert len(planned["cases"]) == 9
    assert sha256(REFS / record["file"]) == record["sha256"]

    with Image.open(REFS / record["file"]) as source:
        reference = source.convert("RGB")

    assert reference.size == (1200, 760)

    variants = []
    for kind in (
        "expiry_value_edit",
        "portrait_edit",
        "fictional_mark_edit",
        "birth_date_only_no_expiry_label",
        "unlabelled_date_no_expiry_label",
    ):
        image, mask, observed, box = create_variant(
            reference, layout, kind, number
        )
        variants.append((kind, image, mask, observed, box))

    controls = [
        ("unchanged_copy", reference.copy(), ".png"),
        (
            "jpeg_recompression",
            reference.copy(),
            ".jpg",
        ),
        (
            "mild_blur",
            reference.filter(ImageFilter.GaussianBlur(radius=0.6)),
            ".png",
        ),
    ]
    prepared.append((record, variants, controls))

OUT.mkdir(parents=True)

manifest = {
    "name": "beyondpixels_v03_new_evaluation_variants",
    "status": "GENERATED_NOT_SCORED",
    "plan_sha256": sha256(PLAN),
    "extractor_lock_sha256": sha256(LOCK),
    "reference_inventory_sha256": sha256(INVENTORY),
    "families": [],
}

for record, variants, controls in prepared:
    family_id = record["family_id"]
    folder = OUT / family_id
    folder.mkdir()

    family_manifest = {
        "family_id": family_id,
        "layout": record["layout"],
        "reference_file": record["file"],
        "reference_sha256": record["sha256"],
        "reference_expected_expiry": record["expected_reference_expiry"],
        "cases": [],
    }

    for kind, image, mask, observed, box in variants:
        filename = f"{kind}.png"
        mask_name = f"{kind}_region_mask.png"
        image.save(folder / filename)
        mask.save(folder / mask_name)

        expected_expiry = (
            f"204{int(family_id[-2:]) % 10}-11-25"
            if kind == "expiry_value_edit"
            else None if "no_expiry_label" in kind
            else record["expected_reference_expiry"]
        )

        family_manifest["cases"].append({
            "category": kind,
            "file": filename,
            "sha256": sha256(folder / filename),
            "expected_expiry": expected_expiry,
            "annotated_region_xyxy": list(box),
            "observed_difference_xyxy": list(observed),
            "region_mask": mask_name,
            "mask_sha256": sha256(folder / mask_name),
        })

    for kind, image, extension in controls:
        filename = kind + extension
        path = folder / filename

        if kind == "jpeg_recompression":
            image.save(path, quality=80)
        else:
            image.save(path)

        family_manifest["cases"].append({
            "category": kind,
            "file": filename,
            "sha256": sha256(path),
            "expected_expiry": record["expected_reference_expiry"],
        })

    assert len(family_manifest["cases"]) == 8
    manifest["families"].append(family_manifest)

    print(
        f"CREATED: {family_id} | layout={record['layout']} | "
        "3 edits + 3 controls + 2 negative cases"
    )

manifest_path = OUT / "manifest.json"
manifest_path.write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
)

print("\nTOTAL: 8 references + 64 variants = 72 planned images")
print("MANIFEST SHA256:", sha256(manifest_path))
print("LOCATION:", OUT.resolve())
print("No OCR scoring, model training, or app/UI changes.")
