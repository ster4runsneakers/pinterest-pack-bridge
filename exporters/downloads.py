"""Build downloadable .txt / .csv / .zip for a PinPack."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime
from typing import Optional

from models.schemas import PinPack


def _safe_name(product_label: str, ext: str) -> str:
    base = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in product_label)
    base = base.strip("_") or "pin_pack"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{stamp}.{ext}"


def pack_to_txt(pack: PinPack) -> tuple[str, str]:
    """Return (filename, text content)."""
    lines = [
        "Pinterest Pack Bridge — English pin pack",
        f"Product: {pack.product.product_label()}",
        f"Generator: {pack.generator}",
        f"Variants: {len(pack.variants)}",
        "",
    ]
    p = pack.product
    lines.append("--- Product fields ---")
    lines.append(f"Brand: {p.brand}")
    lines.append(f"Model: {p.model}")
    lines.append(f"Colorway: {p.colorway}")
    lines.append(f"Sizes: {p.sizes}")
    lines.append(f"Price hint: {p.price_hint}")
    lines.append(f"Destination URL: {p.destination_url}")
    lines.append(f"Board suggestion: {p.board_suggestion}")
    lines.append(f"DM CTA: {p.dm_cta_preference}")
    if p.image_filenames:
        lines.append(f"Images: {', '.join(p.image_filenames)}")
    lines.append("")
    for v in pack.variants:
        lines.append(v.copy_block())
        lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    return _safe_name(pack.product.product_label(), "txt"), text


def pack_to_csv(pack: PinPack) -> tuple[str, str]:
    """Return (filename, csv text)."""
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "variant_id",
            "variant_type",
            "title",
            "description",
            "cta",
            "hashtags",
            "aspect",
            "board_topic",
            "image_filename",
            "brand",
            "model",
            "colorway",
            "sizes",
            "price_hint",
            "destination_url",
        ],
    )
    writer.writeheader()
    p = pack.product
    for v in pack.variants:
        writer.writerow(
            {
                "variant_id": v.variant_id,
                "variant_type": v.variant_type,
                "title": v.title,
                "description": v.description,
                "cta": v.cta,
                "hashtags": v.hashtags,
                "aspect": v.aspect,
                "board_topic": v.board_topic,
                "image_filename": v.image_filename,
                "brand": p.brand,
                "model": p.model,
                "colorway": p.colorway,
                "sizes": p.sizes,
                "price_hint": p.price_hint,
                "destination_url": p.destination_url,
            }
        )
    return _safe_name(pack.product.product_label(), "csv"), buf.getvalue()


def pack_to_zip(
    pack: PinPack,
    include_manifest: bool = True,
) -> tuple[str, bytes]:
    """ZIP with pin_pack.txt, pin_pack.csv, manifest.json noting image filenames.

    Does not embed uploaded binary images (keeps ZIP light); lists filenames
    so the user can match Studio / local assets.
    """
    txt_name, txt_body = pack_to_txt(pack)
    csv_name, csv_body = pack_to_csv(pack)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pin_pack.txt", txt_body)
        zf.writestr("pin_pack.csv", csv_body)
        if include_manifest:
            manifest = {
                "product": pack.product.to_dict(),
                "variant_count": len(pack.variants),
                "image_filenames": pack.product.image_filenames,
                "variants": [
                    {
                        "variant_id": v.variant_id,
                        "aspect": v.aspect,
                        "image_filename": v.image_filename,
                        "board_topic": v.board_topic,
                    }
                    for v in pack.variants
                ],
                "note": "Images are referenced by filename only — attach the matching Studio/product files when publishing.",
            }
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
        # Per-variant quick copy files
        for v in pack.variants:
            zf.writestr(f"variants/{v.variant_id}.txt", v.copy_block() + "\n")
    filename = _safe_name(pack.product.product_label(), "zip")
    return filename, buf.getvalue()
