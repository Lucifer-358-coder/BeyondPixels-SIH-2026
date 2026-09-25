from __future__ import annotations
from pathlib import Path
import json
import argparse

import cv2
import numpy as np


def load_bgr(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not load image: {path}")
    return image


def xyxy_area(box):
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def intersection(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)
    if x2 <= x1 or y2 <= y1:
        return 0
    return (x2 - x1) * (y2 - y1)


def iou(box_a, box_b):
    inter = intersection(box_a, box_b)
    union = xyxy_area(box_a) + xyxy_area(box_b) - inter
    return inter / union if union > 0 else 0.0


def detect_change(reference: np.ndarray, candidate: np.ndarray,
                  diff_threshold: int = 18,
                  min_component_area: int = 40):
    if reference.shape != candidate.shape:
        raise ValueError("Reference and candidate images must have identical dimensions.")

    diff = cv2.absdiff(reference, candidate)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # Mild blur to suppress isolated pixel noise.
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Binary change mask.
    _, binary = cv2.threshold(blurred, diff_threshold, 255, cv2.THRESH_BINARY)

    # Morphological cleanup.
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    kept_boxes = []
    filtered_mask = np.zeros_like(binary)

    for label_id in range(1, num_labels):
        x = int(stats[label_id, cv2.CC_STAT_LEFT])
        y = int(stats[label_id, cv2.CC_STAT_TOP])
        w = int(stats[label_id, cv2.CC_STAT_WIDTH])
        h = int(stats[label_id, cv2.CC_STAT_HEIGHT])
        area = int(stats[label_id, cv2.CC_STAT_AREA])

        if area < min_component_area:
            continue

        kept_boxes.append((x, y, x + w, y + h))
        filtered_mask[labels == label_id] = 255

    if not kept_boxes:
        return {
            "flagged": False,
            "predicted_bbox_xyxy": None,
            "changed_pixels": int(np.count_nonzero(filtered_mask)),
            "component_count": 0,
            "mask": filtered_mask,
        }

    x1 = min(box[0] for box in kept_boxes)
    y1 = min(box[1] for box in kept_boxes)
    x2 = max(box[2] for box in kept_boxes)
    y2 = max(box[3] for box in kept_boxes)

    return {
        "flagged": True,
        "predicted_bbox_xyxy": (x1, y1, x2, y2),
        "changed_pixels": int(np.count_nonzero(filtered_mask)),
        "component_count": len(kept_boxes),
        "mask": filtered_mask,
    }


def evaluate_fixture_set(root: Path):
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reference_path = root / manifest["reference"]
    reference = load_bgr(reference_path)

    print("=== REFERENCE-BASED TAMPER DETECTOR V01 ===")
    print("Root:", root)
    print("Reference:", manifest["reference"])

    pass_count = 0
    total = 0

    for item in manifest["images"]:
        total += 1
        candidate_path = root / item["file"]
        candidate = load_bgr(candidate_path)

        result = detect_change(reference, candidate)

        expected_box = tuple(item["annotated_region_xyxy"])
        predicted_box = result["predicted_bbox_xyxy"]

        overlaps = False
        score_iou = 0.0

        if predicted_box is not None:
            overlaps = intersection(predicted_box, expected_box) > 0
            score_iou = iou(predicted_box, expected_box)

        print("\nFile:", item["file"])
        print("Edit type:", item["edit_type"])
        print("Flagged:", result["flagged"])
        print("Predicted bbox:", predicted_box)
        print("Expected bbox :", expected_box)
        print("Changed pixels:", result["changed_pixels"])
        print("Components:", result["component_count"])
        print("Overlap:", overlaps)
        print("IoU:", round(score_iou, 4))

        if result["flagged"] and overlaps:
            pass_count += 1

    print("\n=== SUMMARY ===")
    print(f"Detected-and-overlapped: {pass_count}/{total}")
    if pass_count == total:
        print("RESULT: PASS")
    else:
        print("RESULT: REVIEW NEEDED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures-root",
        default="data/research_synthetic_documents_v01",
        help="Path to synthetic fixture root",
    )
    args = parser.parse_args()

    evaluate_fixture_set(Path(args.fixtures_root))


if __name__ == "__main__":
    main()
