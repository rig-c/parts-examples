#!/usr/bin/env python3
"""Bind the new shared neck/shoulder boundary to one accepted chest frame.

Only existing named chest bind coordinates are reused. No art, bone, physics,
motion, UV or topology is changed; ordinary official build/check follows.
"""
import hashlib
import json
import pathlib

family = pathlib.Path(__file__).resolve().parents[1]
home = family / "outfits/homewear/naru"
target = home / "out/rig/rig.json"
before = target.read_bytes()
rig = json.loads(before)
parts = {p["name"]: p for p in json.loads((home / "out/parts.json").read_text())["parts"]}
rows = []
for name, threshold, lower in [("neck", 625, True), ("topwear", 705, False)]:
    attachment = rig["skins"]["default"][name][name]
    record = parts[name]
    changed = []
    for i, weights in enumerate(attachment["weights"]):
        # Four transparent pixels are added on every side by public rig-parts.
        source_y = record["y"] - 4 + attachment["uvs"][2 * i + 1] * attachment["height"]
        if not (source_y >= threshold if lower else source_y <= threshold):
            continue
        chest = next((w for w in weights if w["bone"] == "chest"), None)
        if chest is None:
            raise RuntimeError("HOMEWEAR_EXISTING_CHEST_BIND_REQUIRED " + name + " vertex=" + str(i))
        bound = [{**chest, "weight": 1}]
        if bound != weights:
            changed.append({"vertex": i, "sourceY": source_y,
                            "before": [{"bone": w["bone"], "weight": w["weight"]} for w in weights]})
        attachment["weights"][i] = bound
    rows.append({"part": name, "sourceYThreshold": threshold,
                 "side": "atOrBelow" if lower else "atOrAbove", "changed": changed})
text = json.dumps(rig, indent=2) + "\n"
target.write_text(text)
(home / "out/neck-seam-stitch.json").write_text(json.dumps({
    "spec": "family-homewear-neck-seam/1", "beforeRigSHA256": hashlib.sha256(before).hexdigest(),
    "afterRigSHA256": hashlib.sha256(text.encode()).hexdigest(), "rows": rows,
    "scope": "Existing chest bind coordinates only. New neck lower edge and upper camisole/cardigan use the same chest affine transform. Original common bones/constraints/motion/attachments and every art pixel, UV and triangle remain unchanged.",
    "reason": "Native dark motion closeup exposed independently weighted shared skin edge despite a green zero-fold check."
}, indent=2) + "\n")
print(json.dumps({"status": "AUTHOR_WEIGHTS_STITCHED_PENDING_GATE",
                  "verticesChanged": {r["part"]: len(r["changed"]) for r in rows}}))
