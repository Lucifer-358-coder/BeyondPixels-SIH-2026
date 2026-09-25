"""Isolated CPU-only, tensor-only deepfake inference; no remote code or networks."""
from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--images", nargs="*", default=[])
    args = parser.parse_args()
    import torch
    from torchvision import models
    from PIL import Image
    import numpy as np

    torch.set_num_threads(2)
    state = torch.load(args.model, map_location="cpu", weights_only=True)
    if (not isinstance(state, dict) or not state or
            not all(isinstance(k, str) and isinstance(v, torch.Tensor) for k, v in state.items())):
        raise ValueError("Expected a tensor-only state dictionary")
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, 2)
    model.load_state_dict(state, strict=True)
    model.eval()
    if args.smoke:
        with torch.inference_mode():
            test_logits = model(torch.zeros((1, 3, 224, 224), dtype=torch.float32))
        if tuple(test_logits.shape) != (1, 2) or not torch.isfinite(test_logits).all().item():
            raise ValueError("Model forward check failed")
        print(json.dumps({"status": "model_forward_ok", "architecture": "efficientnet_b0"}))
        return 0
    if not 1 <= len(args.images) <= 3:
        raise ValueError("Expected 1-3 face crops")
    batch = []
    for filename in args.images:
        with Image.open(filename) as im:
            im = im.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
            pixels = np.asarray(im, dtype=np.float32).transpose(2, 0, 1).copy() / 255.0
        batch.append(torch.from_numpy(pixels))
    with torch.inference_mode():
        probabilities = torch.softmax(model(torch.stack(batch)), dim=1)[:, 1].tolist()
    print(json.dumps({"scores": [round(float(p), 6) for p in probabilities]}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("Model unavailable: " + type(error).__name__, file=sys.stderr)
        sys.exit(1)
