#!/usr/bin/env python3
"""Admit only fixed-mask RGBA from an inspected generated hidden-cloth repair.

Every RGBA pixel outside the explicit consumer mask is held equal
to the reviewed input. The original artwork and accepted head are not edited.
"""
import hashlib
import argparse
import json
import pathlib
import shutil
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt,label

family = pathlib.Path(__file__).resolve().parents[1]
home = family / "outfits/homewear/naru"
repair = home / "hidden-repair"
before = home / "prepared-base"
parser=argparse.ArgumentParser();parser.add_argument("--candidate",default="prepared");parser.add_argument("--feather",type=float,default=1);args=parser.parse_args()
out = home / args.candidate
if out.exists():
    raise RuntimeError("HOMEWEAR_REPAIR_FRESH_OUTPUT_REQUIRED")
shutil.copytree(before, out)
mask = np.array(Image.open(repair / "consumer-mask.png")) > 0
generated = Image.open(repair / "generated-upper-body.png").convert("RGBA")
target = Image.open(repair / "edit-target.png").convert("RGBA")
def solid_box(im):
    components,n = label(np.array(im)[:,:,3]>128, np.ones((3,3),dtype=bool))
    if n == 0: return None
    counts=np.bincount(components.ravel());counts[0]=0
    ys,xs=np.nonzero(components==counts.argmax())
    return (int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
source_box = solid_box(generated)
target_box = solid_box(target)
if source_box is None or target_box is None:
    raise RuntimeError("HOMEWEAR_REPAIR_NONEMPTY_ALPHA_REQUIRED")
registered = Image.new("RGBA", target.size)
registered.alpha_composite(generated.crop(source_box).resize(
    (target_box[2] - target_box[0], target_box[3] - target_box[1]), Image.Resampling.LANCZOS), target_box[:2])
patch = np.array(registered.crop((52, 332, 972, 692)).resize((460, 180), Image.Resampling.LANCZOS))
mapped = np.zeros((2284, 800, 4), dtype=np.uint8)
mapped[560:740, 160:620] = patch
unsupported_alpha = int(np.count_nonzero(mask & (mapped[:, :, 3] < 128)))
meta = json.loads((out / "prototype.json").read_text())
pieces = {}
records = {r["name"]: r for r in meta["parts"]}
for name, row in records.items():
    a = np.zeros((2284, 800, 4), dtype=np.uint8)
    a[row["y"]:row["y"] + row["h"], row["x"]:row["x"] + row["w"]] = np.array(Image.open(before / "parts" / (name + ".png")).convert("RGBA"))
    pieces[name] = a
order = [r["name"] for r in meta["parts"]]
owner = np.full(mask.shape, -1, dtype=np.int16)
for i, name in enumerate(order):
    owner[pieces[name][:, :, 3] > 0] = i
unowned_mask_pixels = int(np.count_nonzero(mask & (owner < 0)))
# Feather only inward from the fixed mask. No outside-mask output is admitted.
weight = np.minimum(1, distance_transform_edt(mask) / args.feather)
proof = []
for i, name in enumerate(order):
    old = pieces[name]
    new = old.copy()
    take = mask & (owner == i)
    mix = weight[take, None]
    old_alpha=old[take,3:4].astype(np.float32)/255
    patch_alpha=mapped[take,3:4].astype(np.float32)/255
    alpha=mix*patch_alpha+(1-mix)*old_alpha
    premul=mix*mapped[take,:3]*patch_alpha+(1-mix)*old[take,:3]*old_alpha
    new[take,:3]=np.rint(np.divide(premul,alpha,out=np.zeros_like(premul),where=alpha>0)).astype(np.uint8)
    new[take,3]=np.rint(alpha[:,0]*255).astype(np.uint8)
    if not np.array_equal(new[~mask], old[~mask]):
        raise RuntimeError("HOMEWEAR_REPAIR_OUTSIDE_MASK_OR_ALPHA_CHANGED " + name)
    row = records[name]
    # Alpha may change inside the admitted hidden repair. Re-measure after it,
    # rather than carrying the pre-repair opaque count into downstream inputs.
    row["opaque_px"] = int(np.count_nonzero(new[:, :, 3] > 8))
    Image.fromarray(new).crop((row["x"], row["y"], row["x"] + row["w"], row["y"] + row["h"])).save(out / "parts" / (name + ".png"))
    changed = np.any(new != old, axis=2)
    proof.append({"part": name, "changedPixels": int(changed.sum()), "outsideMaskChangedPixels": 0, "alphaChangedInsideMask": int(np.count_nonzero(new[:,:,3]!=old[:,:,3])), "outsideMaskAlphaMaxDelta": 0})
    pieces[name] = new
baseline = json.loads((family / "naru/out/parts.json").read_text())
common = [r for r in baseline["parts"] if r["name"] not in ["shoes", "legwear", "bottomwear", "neck", "topwear"]]
canvas = Image.new("RGBA", (800, 2284))
def accepted(row):
    return Image.open(family / "naru/out/parts" / (row["name"] + ".png")).convert("RGBA")
back = next(r for r in common if r["name"] == "hair_back")
canvas.alpha_composite(accepted(back), (back["x"], back["y"]))
for name in order:
    canvas.alpha_composite(Image.fromarray(pieces[name]))
for row in common:
    if row["name"] != "hair_back":
        canvas.alpha_composite(accepted(row), (row["x"], row["y"]))
canvas.save(out / "assembled.png")
flat = Image.new("RGBA", canvas.size, "white"); flat.alpha_composite(canvas); flat.convert("RGB").save(out / "assembled-white.png")
dark = Image.new("RGBA", canvas.size, "#202630"); dark.alpha_composite(canvas)
dark.resize((400, 1142), Image.Resampling.LANCZOS).save(home / ("docs/" + args.candidate + "-dark.png"))
dark.crop((160, 590, 620, 710)).resize((920, 240), Image.Resampling.NEAREST).save(home / ("docs/" + args.candidate + "-neck.png"))
record = {"spec": "family-homewear-hidden-repair-admission/1", "tool": "built-in image_gen",
    "generatedSHA256": hashlib.sha256((repair / "generated-upper-body.png").read_bytes()).hexdigest(),
    "maskSHA256": hashlib.sha256((repair / "consumer-mask.png").read_bytes()).hexdigest(),
    "maskPixels": int(mask.sum()), "emptyMaskPixelsLeftUnchanged": unowned_mask_pixels, "maskPixelsWhereGeneratedSurfaceIsTransparent": unsupported_alpha, "sourceBox": source_box, "targetBox": target_box,
    "registration": "Largest connected alpha>128 body bounding box fitted to original edit-target alpha box, then original 2x crop transform inverted. RGBA only inside fixed source-occluded mask. Transparent generated pixels remove floating material above actual shoulder contour.",
    "maskFeatherInwardPx": args.feather, "proof": proof,
    "scope": "Generated hidden material, not original source pixels. Original visible garment, all outside-mask RGBA, and exact accepted head assets are protected by the consumer composite mask."}
(repair / "admission.json").write_text(json.dumps(record, indent=2) + "\n")
meta["hiddenRepair"] = "hidden-repair/admission.json; built-in generated RGBA admitted only in the fixed original-hair-occluded mask"
(out / "prototype.json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps(record))
