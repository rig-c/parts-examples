#!/usr/bin/env python3
"""Read or update bust_r / bust_l contour regions across ALL outfits (office, homewear, swimwear) for a character."""
import argparse
import hashlib
import json
import math
import pathlib
import shutil
import subprocess
import tempfile

CHARACTERS = ["roa", "luna", "jinni", "naru", "nova"]
OUTFITS = ["office", "homewear", "swimwear"]

TOPWEAR_STITCH_THRESHOLD = {
    "homewear": {"roa": 520, "luna": 645, "jinni": 625, "naru": 705, "nova": 625},
    "swimwear": {"roa": 520, "luna": 645, "jinni": 625, "naru": 705, "nova": 625},
}


def config_path_for(family: pathlib.Path, char: str, outfit: str) -> pathlib.Path:
    if outfit == "office":
        return family / char / "config.json"
    return family / "outfits" / outfit / char / "authoring/config.json"


def out_dir_for(family: pathlib.Path, char: str, outfit: str) -> pathlib.Path:
    if outfit == "office":
        return family / char / "out"
    return family / "outfits" / outfit / char / "out"


def read_all_regions(family: pathlib.Path) -> dict:
    result = {}
    for ch in CHARACTERS:
        base_cfg = json.loads((family / ch / "config.json").read_text())
        chest_bone = next((b for b in base_cfg["bones"] if b.get("name") == "chest"), {"at": [400, 750]})
        ch_entry = {"chest": chest_bone["at"], "outfits": {}}
        for outfit in OUTFITS:
            cpath = config_path_for(family, ch, outfit)
            if not cpath.is_file():
                cpath = family / ch / "config.json"
            cfg = json.loads(cpath.read_text())
            regs = cfg.get("meshes", {}).get("topwear", {}).get("contour", {}).get("regions", [])
            by_name = {}
            for r in regs:
                if r.get("name") in ("bust_r", "bust_l"):
                    by_name[r["name"]] = {
                        "cx": int(round(r["cx"])),
                        "cy": int(round(r["cy"])),
                        "r": int(round(r["r"])),
                        "band": int(round(r["band"])),
                    }
            ch_entry["outfits"][outfit] = by_name
        result[ch] = ch_entry
    return result


def clamp_non_overlapping(bust_r: dict, bust_l: dict, margin: float = 2.0) -> tuple[dict, dict, bool]:
    r_out = {k: int(round(float(bust_r[k]))) for k in ("cx", "cy", "r", "band")}
    l_out = {k: int(round(float(bust_l[k]))) for k in ("cx", "cy", "r", "band")}
    r_out["r"] = max(6, min(120, r_out["r"]))
    l_out["r"] = max(6, min(120, l_out["r"]))
    r_out["band"] = max(4, min(120, r_out["band"]))
    l_out["band"] = max(4, min(120, l_out["band"]))

    dist = math.hypot(l_out["cx"] - r_out["cx"], l_out["cy"] - r_out["cy"])
    avail = max(16.0, dist - margin)
    clamped = False
    if r_out["r"] + l_out["r"] + 8 > avail:
        scale = max(0.25, (avail - 8.0) / max(1.0, r_out["r"] + l_out["r"]))
        r_out["r"] = max(6, int(math.floor(r_out["r"] * scale)))
        l_out["r"] = max(6, int(math.floor(l_out["r"] * scale)))
        clamped = True
    max_band_sum = max(8, int(math.floor(avail - (r_out["r"] + l_out["r"]))))
    cur_band_sum = r_out["band"] + l_out["band"]
    if cur_band_sum > max_band_sum:
        ratio = max_band_sum / max(1, cur_band_sum)
        r_out["band"] = max(4, int(math.floor(r_out["band"] * ratio)))
        l_out["band"] = max(4, max_band_sum - r_out["band"])
        clamped = True
    return r_out, l_out, clamped


def rebuild_single_outfit_topwear(
    family: pathlib.Path,
    live_family: pathlib.Path | None,
    char: str,
    outfit: str,
    r_clean: dict,
    l_clean: dict,
) -> tuple[dict, dict]:
    cfg_path = config_path_for(family, char, outfit)
    out_dir = out_dir_for(family, char, outfit)
    parts_doc = json.loads((out_dir / "parts.json").read_text())
    top_part_rec = next(p for p in parts_doc["parts"] if p["name"] == "topwear")
    top_png_path = out_dir / "parts/topwear.png"

    cfg_init = json.loads(cfg_path.read_text())
    has_cardigan = "cardigan" in cfg_init.get("meshes", {}) and any(
        p["name"] == "cardigan" for p in parts_doc["parts"]
    )
    target_parts = ["topwear", "cardigan"] if has_cardigan else ["topwear"]

    with tempfile.TemporaryDirectory(prefix=f"bust-{char}-{outfit}-") as tmp:
        tmp_dir = pathlib.Path(tmp)
        inputs_dir = tmp_dir / "inputs"
        (inputs_dir / "parts").mkdir(parents=True)
        clean_part_recs = []
        for pname in target_parts:
            prec = next(p for p in parts_doc["parts"] if p["name"] == pname)
            shutil.copy2(out_dir / f"parts/{pname}.png", inputs_dir / f"parts/{pname}.png")
            clean_part_recs.append({
                **{k: prec[k] for k in ("name", "x", "y", "w", "h", "opaque_px")},
                "from": f"full:author:{pname}",
                "projected_core_px": 0,
                "source_px_taken": 0,
                "refused_drift_px": 0,
                "merged_px": 0,
                "seam_override_px": 0,
            })
        (inputs_dir / "parts.json").write_text(
            json.dumps(
                {
                    "rig_size": [800, 2284],
                    "scale_rig_per_source": 1,
                    "ghost_px": {},
                    "parts": clean_part_recs,
                },
                indent=2,
            )
            + "\n"
        )

        cur_r, cur_l = dict(r_clean), dict(l_clean)
        for margin in (2.0, 8.0, 14.0, 20.0):
            if margin > 2.0:
                cur_r, cur_l, _ = clamp_non_overlapping(r_clean, l_clean, margin=margin)
            cfg = json.loads(cfg_path.read_text())
            for reg in cfg["meshes"]["topwear"]["contour"].get("regions", []):
                if reg["name"] == "bust_r":
                    reg.update(cur_r)
                elif reg["name"] == "bust_l":
                    reg.update(cur_l)
            if has_cardigan:
                cfg["meshes"]["cardigan"]["contour"]["regions"] = json.loads(
                    json.dumps(cfg["meshes"]["topwear"]["contour"].get("regions", []))
                )
            cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")

            mini_cfg = json.loads(json.dumps(cfg))
            mini_cfg.pop("seethrough", None)
            mini_cfg["assemble"] = {
                "rig_scale": 1,
                "plan": [[pname, "full", f"author:{pname}"] for pname in target_parts],
            }
            mini_cfg["motion"].pop("blink", None)
            mini_cfg["meshes"] = {pname: mini_cfg["meshes"][pname] for pname in target_parts}
            mini_cfg["regions"] = {}
            mini_cfg_path = tmp_dir / "config.json"
            mini_cfg_path.write_text(json.dumps(mini_cfg, indent=2) + "\n")

            rig_out = tmp_dir / "rig"
            if rig_out.exists():
                shutil.rmtree(rig_out)
            rig_parts_bin = (
                "/Users/firejune/Workspace/Firejune/rig-parts-naru-369/bin/rig-parts.cjs"
                if pathlib.Path("/Users/firejune/Workspace/Firejune/rig-parts-naru-369/bin/rig-parts.cjs").is_file()
                else "/Users/firejune/Workspace/Firejune/rig-parts/bin/rig-parts.cjs"
            )
            import os
            env = dict(os.environ)
            env["PATH"] = "/Users/firejune/Workspace/Firejune/rig-parts/node_modules/.bin:" + env.get("PATH", "")
            proc = subprocess.run(
                [
                    "node",
                    rig_parts_bin,
                    "rig",
                    "--config",
                    str(mini_cfg_path),
                    "--parts",
                    str(inputs_dir),
                    "--out",
                    str(rig_out),
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                break
            if "RIG_CONTOUR_REGIONS_OVERLAP" not in (proc.stdout + proc.stderr):
                raise RuntimeError(f"[{char}/{outfit}] {(proc.stderr or proc.stdout).strip()}")
        else:
            raise RuntimeError(f"[{char}/{outfit}] Bust regions still overlap after automatic band reduction")

        new_rig = json.loads((rig_out / "rig.json").read_text())
        new_reports = json.loads((rig_out / "mesh_report.json").read_text())
        new_rep_by_part = {r.get("part"): r for r in new_reports if r.get("part") in target_parts}

        for rep_path in [
            out_dir / "rig/mesh_report.json",
            (family / "outfits" / outfit / char / "authoring/rig/mesh_report.json") if outfit != "office" else None,
        ]:
            if rep_path and rep_path.is_file() and new_rep_by_part:
                reps = json.loads(rep_path.read_text())
                reps = [new_rep_by_part.get(r.get("part"), r) for r in reps]
                rep_path.write_text(json.dumps(reps, indent=2) + "\n")

        target_rig_path = out_dir / "rig/rig.json"
        rig = json.loads(target_rig_path.read_text())
        for pname in target_parts:
            rig["skins"]["default"][pname] = new_rig["skins"]["default"][pname]
            for attachment in rig["skins"]["default"][pname].values():
                shutil.copy2(rig_out / "images" / attachment["image"], out_dir / "rig/images" / attachment["image"])

        if outfit in TOPWEAR_STITCH_THRESHOLD:
            threshold = TOPWEAR_STITCH_THRESHOLD[outfit][char]
            for pname in target_parts:
                prec = next(p for p in parts_doc["parts"] if p["name"] == pname)
                attachment = rig["skins"]["default"][pname][pname]
                for i, weights in enumerate(attachment["weights"]):
                    source_y = prec["y"] - 4 + attachment["uvs"][2 * i + 1] * attachment["height"]
                    if source_y <= threshold:
                        chest = next((w for w in weights if w["bone"] == "chest"), None)
                        if chest is not None:
                            attachment["weights"][i] = [{**chest, "weight": 1}]

        target_rig_text = json.dumps(rig, indent=2) + "\n"
        target_rig_path.write_text(target_rig_text)

        if outfit != "office":
            stitch_path = out_dir / "neck-seam-stitch.json"
            if stitch_path.is_file():
                stitch_doc = json.loads(stitch_path.read_text())
                stitch_doc["afterRigSHA256"] = hashlib.sha256(target_rig_text.encode()).hexdigest()
                stitch_path.write_text(json.dumps(stitch_doc, indent=2) + "\n")

    build_dir = out_dir / "check/build"
    build_dir.mkdir(parents=True, exist_ok=True)
    bproc = subprocess.run(
        [
            "node",
            "/Users/firejune/Workspace/Firejune/rigc/bin/rigc.cjs",
            "build",
            "--rig",
            str(out_dir / "rig/rig.json"),
            "--motion",
            str(out_dir / "rig/motion.json"),
            "--out",
            str(build_dir),
            "--profile",
            "spine-html",
            "--pack",
            "--page-edges",
            "free",
            "--pack-shape",
            "polygon",
        ],
        capture_output=True,
        text=True,
    )
    if bproc.returncode != 0:
        raise RuntimeError(f"[{char}/{outfit}] {(bproc.stderr or bproc.stdout).strip()}")

    if live_family is not None and live_family.resolve() != family.resolve():
        live_out = out_dir_for(live_family, char, outfit)
        live_build = live_out / "check/build"
        live_build.mkdir(parents=True, exist_ok=True)
        for item in build_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, live_build / item.name)
        live_cfg = config_path_for(live_family, char, outfit)
        if live_cfg.parent.is_dir():
            shutil.copy2(cfg_path, live_cfg)

    return cur_r, cur_l


def sync_integrity_manifests(family: pathlib.Path, char: str):
    manifest_path = family / "accepted-inputs.json"
    if manifest_path.is_file():
        doc = json.loads(manifest_path.read_text())
        for rel in list(doc.get("files", {}).keys()):
            if rel.startswith(f"{char}/") or rel.startswith("viewer/"):
                p = family / rel
                if p.is_file():
                    raw = p.read_bytes()
                    doc["files"][rel] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        manifest_path.write_text(json.dumps(doc, indent=2) + "\n")

    for outfit in ("homewear", "swimwear"):
        pb_path = family / "outfits" / outfit / char / "protected-baseline.json"
        if pb_path.is_file():
            pb = json.loads(pb_path.read_text())
            for rel in list(pb.get("files", {}).keys()):
                p = family / rel
                if p.is_file():
                    pb["files"][rel] = hashlib.sha256(p.read_bytes()).hexdigest()
            pb_path.write_text(json.dumps(pb, indent=2) + "\n")


def rebuild_all_outfits_for_character(
    family: pathlib.Path,
    live_family: pathlib.Path | None,
    char: str,
    bust_r: dict,
    bust_l: dict,
) -> dict:
    r_clean, l_clean, clamped = clamp_non_overlapping(bust_r, bust_l, margin=2.0)
    rebuilt_outfits = []
    final_r, final_l = r_clean, l_clean
    for outfit in OUTFITS:
        cpath = config_path_for(family, char, outfit)
        odir = out_dir_for(family, char, outfit)
        if not cpath.is_file() or not (odir / "rig/rig.json").is_file():
            continue
        final_r, final_l = rebuild_single_outfit_topwear(family, live_family, char, outfit, final_r, final_l)
        rebuilt_outfits.append(outfit)

    sync_integrity_manifests(family, char)
    return {
        "ok": True,
        "character": char,
        "outfits": rebuilt_outfits,
        "bust_r": final_r,
        "bust_l": final_l,
        "clamped": clamped or (final_r != r_clean or final_l != l_clean),
    }


def parse_region_arg(text: str) -> dict:
    parts = [float(x.strip()) for x in text.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Expected cx,cy,r,band (got {text})")
    return {"cx": parts[0], "cy": parts[1], "r": parts[2], "band": parts[3]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["get", "set"], required=True)
    parser.add_argument("--family-dir", default="/Users/firejune/Workspace/Firejune/parts-examples-naru-homewear/family")
    parser.add_argument("--live-family-dir", default="/Users/firejune/Workspace/Firejune/spine-parts-examples/family")
    parser.add_argument("--character", choices=CHARACTERS)
    parser.add_argument("--outfit", choices=OUTFITS, default="swimwear")
    parser.add_argument("--bust-r")
    parser.add_argument("--bust-l")
    args = parser.parse_args()

    family = pathlib.Path(args.family_dir)
    live_family = pathlib.Path(args.live_family_dir) if args.live_family_dir else None

    if args.action == "get":
        print(json.dumps(read_all_regions(family)))
        return

    if not args.character or not args.bust_r or not args.bust_l:
        raise SystemExit("--character, --bust-r, and --bust-l are required for --action set")
    res = rebuild_all_outfits_for_character(
        family,
        live_family,
        args.character,
        parse_region_arg(args.bust_r),
        parse_region_arg(args.bust_l),
    )
    print(json.dumps(res))


if __name__ == "__main__":
    main()
