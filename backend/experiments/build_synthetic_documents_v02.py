from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import hashlib
import json

ROOT = Path("data/research_synthetic_documents_v02")

if ROOT.exists():
    raise SystemExit(
        f"STOP: {ROOT} already exists. Do not overwrite this research set."
    )

ROOT.mkdir(parents=True)

def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def render_document(index, layout, edit=None):
    image = Image.new("RGB", (1200, 760), "#eaf0f5")
    d = ImageDraw.Draw(image)

    d.rounded_rectangle((35, 35, 1165, 725), radius=20, fill="white")
    header = "#234c69" if layout == "A" else "#405d55"
    d.rectangle((35, 35, 1165, 170), fill=header)
    d.text((70, 60), "FICTIONAL TRAVEL DOCUMENT",
           font=font(37, True), fill="white")
    d.text((72, 116), "RESEARCH SPECIMEN - NOT VALID",
           font=font(23, True), fill="#ffe2a3")

    if layout == "A":
        text_x = 85
        portrait_box = (850, 215, 1090, 480)
        expiry_x = 440
    else:
        text_x = 410
        portrait_box = (85, 215, 325, 480)
        expiry_x = 750

    expiry_y = 445
    expiry_box = (expiry_x, 474, expiry_x + 335, 520)
    stamp_box = (850, 530, 1090, 680)

    def field(label, value, x, y):
        d.text((x, y), label, font=font(17), fill="#546c7c")
        d.text((x, y + 29), value, font=font(30, True), fill="#183047")

    field("NAME", f"FICTIONAL PERSON {index:02d}", text_x, 225)
    field("DOCUMENT CODE", f"SPEC-{index:04d}", text_x, 335)
    field("DATE OF BIRTH", f"200{index}-01-15", text_x, 445)

    d.text((expiry_x, expiry_y), "EXPIRY DATE",
           font=font(17), fill="#546c7c")
    expiry = f"203{index}-06-30"
    if edit == "expiry":
        expiry = f"204{index}-09-15"
    d.text((expiry_x, expiry_y + 29), expiry,
           font=font(30, True), fill="#183047")

    px1, py1, px2, py2 = portrait_box
    d.rounded_rectangle(portrait_box, radius=12, fill="#e3eaf0")
    d.text((px1 + 18, py1 + 9), "DRAWN AVATAR",
           font=font(14), fill="#183047")

    color = "#b87962" if edit == "portrait" else "#648cb2"
    cx = (px1 + px2) // 2
    d.ellipse((cx - 48, py1 + 42, cx + 48, py1 + 138), fill=color)

    if edit == "portrait":
        d.polygon([
            (px1 + 18, py2 - 18),
            (cx - 34, py1 + 145),
            (cx + 34, py1 + 145),
            (px2 - 18, py2 - 18)
        ], fill=color)
    else:
        d.rounded_rectangle(
            (px1 + 26, py1 + 150, px2 - 26, py2 - 16),
            radius=32, fill=color
        )

    sx1, sy1, sx2, sy2 = stamp_box
    d.rectangle(stamp_box, fill="white")
    d.ellipse(
        (sx1 + 28, sy1 + 10, sx2 - 28, sy2 - 10),
        outline="#517794", width=5
    )
    stamp_text = "MARK B" if edit == "stamp" else "MARK A"
    d.text((sx1 + 48, sy1 + 54), stamp_text,
           font=font(19, True), fill="#365a77")

    d.text((75, 691), "SYNTHETIC TEST IMAGE - NO REAL IDENTITY",
           font=font(19, True), fill="#984d4d")

    boxes = {
        "expiry": expiry_box,
        "portrait": portrait_box,
        "stamp": stamp_box,
    }
    return image, boxes

manifest = {
    "purpose": "Fictional controlled document research; not an authenticity benchmark",
    "version": "v02",
    "split_policy": (
        "Four development documents with layout A; "
        "two set-aside documents with layout B. "
        "Keep reference families within one split."
    ),
    "limitations": [
        "All documents use the same synthetic generator",
        "Reference-based changes do not establish single-image tampering detection",
        "Set-aside examples are not an external independent dataset"
    ],
    "documents": []
}

for index in range(1, 7):
    split = "development" if index <= 4 else "evaluation"
    layout = "A" if index <= 4 else "B"
    folder = ROOT / split / f"document_{index:02d}"
    folder.mkdir(parents=True)

    reference, boxes = render_document(index, layout)
    reference_path = folder / "reference.png"
    reference.save(reference_path)

    record = {
        "document_id": f"fictional_{index:02d}",
        "split": split,
        "layout": layout,
        "reference": "reference.png",
        "reference_sha256": digest(reference_path),
        "edits": [],
        "benign_controls": []
    }

    for kind in ("expiry", "portrait", "stamp"):
        edited, _ = render_document(index, layout, edit=kind)
        filename = f"edit_{kind}.png"
        edited.save(folder / filename)

        observed = ImageChops.difference(reference, edited).getbbox()
        assert observed is not None, filename

        box = boxes[kind]
        assert (
            box[0] <= observed[0] and box[1] <= observed[1]
            and observed[2] <= box[2] and observed[3] <= box[3]
        ), f"Unexpected change outside {kind} region: {observed}"

        mask = Image.new("L", reference.size, 0)
        # Bounding-box coordinates are right/bottom exclusive.
        ImageDraw.Draw(mask).rectangle(
            (box[0], box[1], box[2] - 1, box[3] - 1),
            fill=255
        )
        mask_name = f"edit_{kind}_region_mask.png"
        mask.save(folder / mask_name)

        record["edits"].append({
            "file": filename,
            "type": kind,
            "label": "controlled_synthetic_edit",
            "annotated_region_xyxy": list(box),
            "observed_difference_xyxy": list(observed),
            "mask": mask_name,
            "sha256": digest(folder / filename),
            "mask_sha256": digest(folder / mask_name)
        })

    controls = [
        ("control_copy.png", "unchanged_copy"),
        ("control_jpeg_80.jpg", "benign_jpeg_recompression"),
        ("control_blur_0_6.png", "benign_mild_blur")
    ]

    reference.save(folder / "control_copy.png")
    reference.save(folder / "control_jpeg_80.jpg", quality=80)
    reference.filter(
        ImageFilter.GaussianBlur(radius=0.6)
    ).save(folder / "control_blur_0_6.png")

    for filename, label in controls:
        record["benign_controls"].append({
            "file": filename,
            "label": label,
            "sha256": digest(folder / filename)
        })

    manifest["documents"].append(record)
    print(
        f"CREATED: {split}/document_{index:02d} | "
        f"layout={layout} | 3 edits + 3 controls"
    )

manifest_path = ROOT / "manifest.json"
manifest_path.write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)

print("\nTOTAL: 6 references, 18 edits, 18 controls, 18 region masks")
print("MANIFEST SHA256:", digest(manifest_path))
print("LOCATION:", ROOT.resolve())
print("No existing models, app files, or v01 fixtures modified.")
