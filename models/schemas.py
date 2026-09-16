"""Stable schemas for Studio ↔ Pinterest Pack Bridge integration.

These models are intentionally plain dataclasses so both the Image Studio
and this bridge can share them without heavy dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProductFields:
    """Manual / enriched product fields (Greek UI → English pin copy)."""

    brand: str = ""
    model: str = ""
    colorway: str = ""
    sizes: str = ""
    price_hint: str = ""
    destination_url: str = ""
    board_suggestion: str = ""
    dm_cta_preference: str = "DM to buy"  # e.g. "DM to buy", "Message us", "Ask for sizes"
    specs: str = ""
    watermark: str = "SNEAKERNESS.EU"
    image_filenames: List[str] = field(default_factory=list)

    def product_label(self) -> str:
        bits = [b.strip() for b in (self.brand, self.model, self.colorway) if b and b.strip()]
        return " · ".join(bits) if bits else "Sneaker Drop"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StudioExport:
    """Parsed Sneaker Image Studio export (.txt or .zip).

    Flexible: fields may be empty if the export only had captions/hooks.
    """

    source_name: str = ""
    brand: str = ""
    model: str = ""
    colorway: str = ""
    specs: str = ""
    goal: str = ""
    lang: str = ""
    aspect: str = ""
    captions_meta: str = ""
    captions_tiktok: str = ""
    captions_pinterest: str = ""
    hooks: List[str] = field(default_factory=list)
    prompts: List[str] = field(default_factory=list)
    hashtags: str = ""
    raw_text: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)
    image_filenames: List[str] = field(default_factory=list)

    def merge_into_product(self, product: ProductFields) -> ProductFields:
        """Fill empty product fields from Studio export."""
        if not product.brand and self.brand:
            product.brand = self.brand
        if not product.model and self.model:
            product.model = self.model
        if not product.colorway and self.colorway:
            product.colorway = self.colorway
        if not product.specs and self.specs:
            product.specs = self.specs
        if not product.image_filenames and self.image_filenames:
            product.image_filenames = list(self.image_filenames)
        return product

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PinVariant:
    """One Pinterest-ready pin variant (English copy)."""

    variant_id: str
    variant_type: str  # product | seo | outfit | lifestyle | urgency | sizes | story | comparison
    title: str
    description: str
    cta: str
    hashtags: str
    aspect: str  # "2:3" | "1:1"
    board_topic: str
    image_filename: str = ""
    notes: str = ""

    def copy_block(self) -> str:
        """Plain-text block for clipboard / .txt export."""
        lines = [
            f"=== {self.variant_id} · {self.variant_type} · {self.aspect} ===",
            f"Title: {self.title}",
            f"Description:\n{self.description}",
            f"CTA: {self.cta}",
            f"Hashtags: {self.hashtags}",
            f"Board: {self.board_topic}",
        ]
        if self.image_filename:
            lines.append(f"Image: {self.image_filename}")
        if self.notes:
            lines.append(f"Notes: {self.notes}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PinPack:
    """Full pin pack for one product (5–10 variants)."""

    product: ProductFields
    variants: List[PinVariant] = field(default_factory=list)
    studio: Optional[StudioExport] = None
    generator: str = "templates"
    language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product": self.product.to_dict(),
            "variants": [v.to_dict() for v in self.variants],
            "studio": self.studio.to_dict() if self.studio else None,
            "generator": self.generator,
            "language": self.language,
        }
