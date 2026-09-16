"""Offline template-based English Pinterest pin pack generator.

Optional LLM via env vars (OPENAI_API_KEY / XAI_API_KEY) — not required.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import List, Optional, Sequence

from models.schemas import PinPack, PinVariant, ProductFields, StudioExport

# Soft-discovery CTAs (Pinterest + DM preference). Avoid hard "BUY NOW".
CTA_TEMPLATES = {
    "DM to buy": "DM us to check sizes & availability →",
    "Message us": "Message us for fit advice & current stock →",
    "Ask for sizes": "Ask us which sizes are left →",
    "Link in bio": "Tap through / link in bio for details →",
    "Save for later": "Save this pin — DM when you're ready →",
}

BOARD_TOPICS = {
    "product": "Sneaker Product Shots",
    "seo": "Running & Comfort Shoes",
    "outfit": "Sneaker Outfits & Style",
    "lifestyle": "Everyday Comfort Footwear",
    "urgency": "New Drops & Limited",
    "sizes": "Fit Guides & Size Tips",
    "story": "Sneaker Stories",
    "comparison": "Shoe Comparisons",
    "tech": "Footwear Tech & Cushioning",
}

TITLE_TEMPLATES = {
    "product": [
        "{brand} {model} — {colorway} Look",
        "{brand} {model}: Clean Product Pin",
        "Meet the {brand} {model}",
    ],
    "seo": [
        "Best {keyword} Sneakers for All-Day Comfort",
        "{brand} {model} — Comfort & Support Guide",
        "Looking for {keyword}? Start Here",
    ],
    "outfit": [
        "How to Style {brand} {model}",
        "{brand} {model} Outfit Ideas",
        "Street Style: {brand} {model}",
    ],
    "lifestyle": [
        "On-Feet Comfort: {brand} {model}",
        "From Desk to Street — {brand} {model}",
        "Daily Driver: {brand} {model}",
    ],
    "urgency": [
        "{brand} {model} — Fresh Drop",
        "Don't Miss: {brand} {model}",
        "Limited Colorway: {colorway}",
    ],
    "sizes": [
        "{brand} {model} Size Guide Notes",
        "Which Size for {brand} {model}?",
        "Fit Tips: {brand} {model}",
    ],
    "story": [
        "Why We Picked {brand} {model}",
        "The Story Behind {brand} {model}",
        "Soft Discovery: {brand} {model}",
    ],
    "comparison": [
        "{brand} {model} vs Everyday Trainers",
        "Is {brand} {model} Right for You?",
        "{brand} {model}: Comfort Checklist",
    ],
    "tech": [
        "{brand} {model} — Cushioning & Support",
        "Tech Specs: {brand} {model}",
        "Engineered Comfort: {brand} {model}",
    ],
}

DESC_OPENERS = [
    "Tired of foot fatigue after long days?",
    "Looking for sneakers that actually support your day?",
    "Want a clean look without sacrificing comfort?",
    "Building a rotation that works from office to weekend?",
    "Chasing better posture and softer landings?",
]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _pick(seq: Sequence[str], seed: str, index: int = 0) -> str:
    if not seq:
        return ""
    h = int(hashlib.md5(f"{seed}:{index}".encode()).hexdigest(), 16)
    return seq[(h + index) % len(seq)]


def _clean_hashtag_token(s: str) -> str:
    return "".join(c for c in s if c.isalnum())


def build_hashtags(product: ProductFields, extra: str = "") -> str:
    bits = ["#Sneakerness"]
    if product.brand:
        bits.append("#" + _clean_hashtag_token(product.brand))
    model = product.model or ""
    ml = model.lower()
    compounds = [
        ("hands free", "HandsFree"),
        ("slip-ins", "SlipIns"),
        ("slip ins", "SlipIns"),
        ("arch fit", "ArchFit"),
        ("max cushioning", "MaxCushioning"),
        ("air max", "AirMax"),
        ("gel-kayano", "GelKayano"),
        ("ultra boost", "Ultraboost"),
        ("cloudmonster", "Cloudmonster"),
        ("gel nimbus", "GelNimbus"),
    ]
    for needle, tag in compounds:
        if needle in ml:
            bits.append("#" + tag)
    skip = {
        "the", "and", "with", "for", "in", "of", "a", "an", "ins", "free",
        "hands", "slip", "arch", "fit",
    }
    for tok in model.replace("-", " ").split():
        clean = _clean_hashtag_token(tok)
        if len(clean) >= 4 and clean.lower() not in skip:
            bits.append("#" + clean)
    bits += [
        "#sneakers",
        "#PinterestFashion",
        "#DailyComfort",
        "#FootwearTech",
        "#SneakerStyle",
        "#ArchSupport",
    ]
    if extra:
        for t in re.findall(r"#\w+", extra):
            bits.append(t)
    seen = set()
    out = []
    for b in bits:
        k = b.lower()
        if k not in seen:
            seen.add(k)
            out.append(b)
    return " ".join(out[:12])


def _cta(product: ProductFields) -> str:
    pref = product.dm_cta_preference or "DM to buy"
    base = CTA_TEMPLATES.get(pref, CTA_TEMPLATES["DM to buy"])
    if product.destination_url:
        return f"{base} {product.destination_url}"
    wm = product.watermark or "SNEAKERNESS.EU"
    return f"{base} {wm}"


def _keyword(product: ProductFields) -> str:
    ml = (product.model or "").lower()
    if "run" in ml or "nimbus" in ml or "kayano" in ml:
        return "running"
    if "slip" in ml or "hands free" in ml:
        return "hands-free"
    if "basket" in ml or "dunk" in ml:
        return "lifestyle"
    if product.brand:
        return product.brand
    return "comfort"


def _fill_title(template: str, product: ProductFields) -> str:
    return template.format(
        brand=product.brand or "Sneaker",
        model=product.model or "Drop",
        colorway=product.colorway or "Signature Colorway",
        keyword=_keyword(product),
    ).strip()


def _description(
    variant_type: str,
    product: ProductFields,
    studio: Optional[StudioExport],
    index: int,
) -> str:
    label = product.product_label()
    opener = _pick(DESC_OPENERS, label, index)
    tech = (product.specs or "").strip()
    if not tech and studio and studio.specs:
        tech = studio.specs.strip()
    if not tech:
        tech = "posture support · all-day comfort · engineered cushioning"
    else:
        tech = " · ".join(
            p.strip() for p in tech.replace(";", ",").split(",") if p.strip()
        )[:140]

    size_line = ""
    if product.sizes:
        size_line = f"Available sizes: {product.sizes}"

    price_line = ""
    if product.price_hint:
        price_line = f"Price hint: {product.price_hint}"

    # Prefer Studio Pinterest caption as seed for first product/seo variants
    studio_seed = ""
    if studio and studio.captions_pinterest and variant_type in ("product", "seo"):
        # Strip hashtags from seed; we re-attach our own
        studio_seed = re.sub(r"#\w+", "", studio.captions_pinterest).strip()
        studio_seed = re.sub(r"\n{3,}", "\n\n", studio_seed)[:400]

    hook = ""
    if studio and studio.hooks:
        hook = studio.hooks[index % len(studio.hooks)]

    blocks: List[str] = []

    if variant_type == "product":
        if studio_seed:
            blocks.append(studio_seed)
        else:
            blocks.append(opener)
            blocks.append("")
            blocks.append(f"Discover {label}")
            blocks.append("")
            blocks.append(tech)
    elif variant_type == "seo":
        blocks.append(f"Searching for {_keyword(product)} sneakers?")
        blocks.append("")
        blocks.append(f"{label} delivers comfort-first design made for real days.")
        blocks.append("")
        blocks.append(tech)
    elif variant_type == "outfit":
        blocks.append(f"Style idea: pair {label} with clean neutrals or soft earth tones.")
        blocks.append("")
        blocks.append("Keep the silhouette simple — let the sneaker do the talking.")
        if hook:
            blocks.append("")
            blocks.append(f"Pin vibe: {hook}")
    elif variant_type == "lifestyle":
        blocks.append(opener)
        blocks.append("")
        blocks.append(f"On-feet with {label} — built for commuting, standing shifts, and weekend walks.")
        blocks.append("")
        blocks.append(tech)
    elif variant_type == "urgency":
        blocks.append(f"Fresh colorway alert: {product.colorway or label}")
        blocks.append("")
        blocks.append(f"{label} is in rotation now. Save this pin and DM for what's left.")
        if size_line:
            blocks.append("")
            blocks.append(size_line)
    elif variant_type == "sizes":
        blocks.append(f"Fit notes for {label}")
        blocks.append("")
        if size_line:
            blocks.append(size_line)
        else:
            blocks.append("True-to-size for most — DM us your usual EU size for a quick check.")
        blocks.append("")
        blocks.append("We help you match size before you commit.")
    elif variant_type == "story":
        if hook:
            blocks.append(hook)
            blocks.append("")
        blocks.append(f"We added {label} because it balances clean aesthetics with everyday support.")
        blocks.append("")
        blocks.append("Soft discovery > hard sell. Save it, try it on later, ask us anything.")
    elif variant_type == "comparison":
        blocks.append(f"Is {label} worth a pin?")
        blocks.append("")
        blocks.append("✓ Comfort-first cushioning")
        blocks.append("✓ Everyday style")
        blocks.append("✓ Authentic selection")
        blocks.append("")
        blocks.append(tech)
    elif variant_type == "tech":
        blocks.append(f"Tech focus: {label}")
        blocks.append("")
        blocks.append(tech)
        blocks.append("")
        blocks.append("Engineered for longer days on your feet.")
    else:
        blocks.append(opener)
        blocks.append("")
        blocks.append(f"Discover {label}")

    if price_line and variant_type in ("product", "urgency", "sizes"):
        blocks.append("")
        blocks.append(price_line)

    wm = product.watermark or "SNEAKERNESS.EU"
    blocks.append("")
    blocks.append(f"Learn more → {wm}")

    return "\n".join(blocks).strip()


def _aspect_for(variant_type: str, index: int) -> str:
    # Mix 2:3 (Pinterest native) and 1:1
    if variant_type in ("outfit", "lifestyle", "story"):
        return "2:3"
    if variant_type in ("product", "comparison") and index % 2 == 0:
        return "1:1"
    return "2:3"


def _board(product: ProductFields, variant_type: str) -> str:
    if product.board_suggestion:
        return product.board_suggestion
    return BOARD_TOPICS.get(variant_type, "Sneakers")


VARIANT_PLAN = [
    ("product", "2:3"),
    ("product", "1:1"),
    ("seo", "2:3"),
    ("outfit", "2:3"),
    ("lifestyle", "2:3"),
    ("tech", "1:1"),
    ("sizes", "2:3"),
    ("urgency", "2:3"),
    ("story", "2:3"),
    ("comparison", "1:1"),
]


def _optional_llm_refine(pack: PinPack) -> PinPack:
    """Optional polish if OPENAI_API_KEY or XAI_API_KEY is set. Best-effort; never required."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("XAI_API_KEY")
    if not api_key:
        return pack
    # Stub hook: MVP stays offline. Real HTTP call can be wired later without
    # changing PinPack shape. Mark generator for transparency.
    pack.generator = "templates+llm_env_detected_unused"
    return pack


def generate_pin_pack(
    product: ProductFields,
    studio: Optional[StudioExport] = None,
    count: int = 8,
) -> PinPack:
    """Generate 5–10 English pin variants from product (+ optional Studio export)."""
    count = max(5, min(10, int(count or 8)))
    if studio:
        product = studio.merge_into_product(product)

    seed = product.product_label()
    images = list(product.image_filenames or [])
    if studio and studio.image_filenames:
        for fn in studio.image_filenames:
            if fn not in images:
                images.append(fn)

    hashtags = build_hashtags(product, extra=(studio.hashtags if studio else ""))
    cta = _cta(product)
    variants: List[PinVariant] = []

    plan = VARIANT_PLAN[:count]
    for i, (vtype, default_aspect) in enumerate(plan):
        titles = TITLE_TEMPLATES.get(vtype, TITLE_TEMPLATES["product"])
        title = _fill_title(_pick(titles, seed, i), product)
        # Pinterest title soft limit ~100 chars
        if len(title) > 100:
            title = title[:97] + "…"
        aspect = default_aspect or _aspect_for(vtype, i)
        img = images[i % len(images)] if images else ""
        variants.append(
            PinVariant(
                variant_id=f"pin_{i+1:02d}",
                variant_type=vtype,
                title=title,
                description=_description(vtype, product, studio, i),
                cta=cta,
                hashtags=hashtags,
                aspect=aspect,
                board_topic=_board(product, vtype),
                image_filename=img,
                notes="English pin copy · Greek UI only",
            )
        )

    pack = PinPack(
        product=product,
        variants=variants,
        studio=studio,
        generator="templates",
        language="en",
    )
    return _optional_llm_refine(pack)
