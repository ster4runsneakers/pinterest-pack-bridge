"""Flexible parser for Sneaker Image Studio .txt / .zip exports."""

from __future__ import annotations

import io
import json
import re
import zipfile
from typing import BinaryIO, List, Optional, Union

from models.schemas import StudioExport

BytesLike = Union[bytes, BinaryIO]


def _read_bytes(data: BytesLike) -> bytes:
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    return data.read()


def _safe_decode(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_kv(text: str, keys: List[str]) -> dict:
    """Pull Brand:/Model: style lines from free-form text."""
    out = {}
    for key in keys:
        # Match "Brand: Nike" or "**Brand:** Nike" or "brand = Nike"
        pattern = re.compile(
            rf"(?im)^(?:\*\*)?\s*{re.escape(key)}\s*(?:\*\*)?\s*[:=]\s*(.+)$"
        )
        m = pattern.search(text)
        if m:
            out[key.lower()] = m.group(1).strip().strip("*").strip()
    return out


def _extract_section(text: str, headers: List[str]) -> str:
    """Extract body under a markdown-ish section header until next === or ##."""
    for header in headers:
        pattern = re.compile(
            rf"(?is)(?:^|\n)(?:#+\s*|{re.escape('===')}\s*)?{re.escape(header)}\s*"
            rf"(?:{re.escape('===')})?\s*\n+(.*?)(?=\n(?:#+\s*|{re.escape('===')})|\Z)"
        )
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return ""


def _extract_hooks(text: str) -> List[str]:
    hooks: List[str] = []
    # Lines like "Hook 1:" or "HOOK:" or bullet hooks
    for m in re.finditer(r"(?im)^(?:hook\s*\d*|hook)\s*[:=]\s*(.+)$", text):
        val = m.group(1).strip()
        if val:
            hooks.append(val)
    # Also grab short quoted lines under a Hooks section
    section = _extract_section(text, ["Hooks", "HOOKS", "Video Hooks", "hooks"])
    if section:
        for line in section.splitlines():
            line = line.strip().lstrip("-•* ").strip('"\'')
            if 8 <= len(line) <= 120 and line not in hooks:
                hooks.append(line)
    return hooks[:12]


def _extract_prompts(text: str) -> List[str]:
    prompts: List[str] = []
    # === slideN === blocks
    for m in re.finditer(
        r"(?is)===\s*slide\s*(\d+)\s*===\s*\n(.*?)(?=\n===\s*slide|\Z)", text
    ):
        body = m.group(2).strip()
        if body:
            prompts.append(body)
    # Prompt 1: / Visual prompt:
    for m in re.finditer(
        r"(?im)^(?:visual\s*)?prompt\s*\d*\s*[:=]\s*(.+)$", text
    ):
        val = m.group(1).strip()
        if val and val not in prompts:
            prompts.append(val)
    section = _extract_section(text, ["Prompts", "Grok Prompts", "Image Prompts", "prompts"])
    if section and not prompts:
        chunks = re.split(r"\n{2,}", section)
        prompts.extend(c.strip() for c in chunks if len(c.strip()) > 20)
    return prompts[:20]


def _extract_hashtags(text: str) -> str:
    tags = re.findall(r"#\w+", text)
    seen = set()
    out = []
    for t in tags:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(t)
    return " ".join(out[:20])


def parse_txt(text: str, source_name: str = "export.txt") -> StudioExport:
    """Parse a free-form Studio content-pack .txt."""
    kv = _extract_kv(
        text,
        ["Brand", "Model", "Colorway", "Specs", "Price", "Watermark", "Goal", "Aspect"],
    )
    pin = _extract_section(
        text,
        [
            "Pinterest EN",
            "Pinterest Caption",
            "Pinterest",
            "📌 Pinterest",
            "pinterest_caption",
        ],
    )
    meta_cap = _extract_section(
        text,
        ["FB / IG", "Meta Caption", "Instagram", "Facebook", "meta_caption", "Captions"],
    )
    tiktok = _extract_section(text, ["TikTok", "tiktok_caption", "TikTok Caption"])

    # If no sections, treat whole file as raw captions
    if not meta_cap and not pin and len(text.strip()) > 40:
        # Prefer first non-empty paragraph as caption
        paras = [p.strip() for p in re.split(r"\n{2,}", text.strip()) if p.strip()]
        if paras:
            meta_cap = paras[0]

    return StudioExport(
        source_name=source_name,
        brand=kv.get("brand", ""),
        model=kv.get("model", ""),
        colorway=kv.get("colorway", ""),
        specs=kv.get("specs", ""),
        goal=kv.get("goal", ""),
        aspect=kv.get("aspect", ""),
        captions_meta=meta_cap,
        captions_tiktok=tiktok,
        captions_pinterest=pin,
        hooks=_extract_hooks(text),
        prompts=_extract_prompts(text),
        hashtags=_extract_hashtags(text),
        raw_text=text,
        meta=dict(kv),
    )


def parse_zip(data: bytes, source_name: str = "export.zip") -> StudioExport:
    """Parse Studio ZIP (captions_*.txt, prompts.txt, meta.json, images)."""
    export = StudioExport(source_name=source_name)
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        lower_map = {n.lower(): n for n in names}

        def read_named(*candidates: str) -> str:
            for c in candidates:
                # exact or basename match
                if c.lower() in lower_map:
                    return _safe_decode(zf.read(lower_map[c.lower()]))
                for ln, real in lower_map.items():
                    if ln.endswith("/" + c.lower()) or ln.rsplit("/", 1)[-1] == c.lower():
                        return _safe_decode(zf.read(real))
            return ""

        meta_json_raw = read_named("meta.json")
        if meta_json_raw:
            try:
                meta = json.loads(meta_json_raw)
                if isinstance(meta, dict):
                    export.meta = meta
                    export.brand = str(meta.get("brand") or "")
                    export.model = str(meta.get("model") or "")
                    export.colorway = str(meta.get("colorway") or "")
                    export.specs = str(meta.get("specs") or "")
                    export.goal = str(meta.get("goal") or "")
                    export.lang = str(meta.get("lang") or "")
                    export.aspect = str(meta.get("aspect") or "")
            except json.JSONDecodeError:
                pass

        export.captions_meta = read_named(
            "captions_meta.txt", "meta_caption.txt", "captions.txt"
        )
        export.captions_tiktok = read_named("captions_tiktok.txt", "tiktok.txt")
        export.captions_pinterest = read_named(
            "captions_pinterest.txt", "pinterest.txt", "pinterest_en.txt"
        )
        prompts_txt = read_named("prompts.txt", "visual_prompts.txt", "grok_prompts.txt")
        if prompts_txt:
            export.prompts = _extract_prompts(prompts_txt) or [
                p.strip() for p in re.split(r"\n{2,}", prompts_txt) if p.strip()
            ]
            export.raw_text = (export.raw_text + "\n\n" + prompts_txt).strip()

        # Any other .txt — merge hooks/hashtags/brand fields
        for n in names:
            if not n.lower().endswith(".txt"):
                continue
            body = _safe_decode(zf.read(n))
            export.raw_text = (export.raw_text + "\n\n" + body).strip()
            if not export.captions_pinterest and "pinterest" in n.lower():
                export.captions_pinterest = body.strip()
            for h in _extract_hooks(body):
                if h not in export.hooks:
                    export.hooks.append(h)
            kv = _extract_kv(body, ["Brand", "Model", "Colorway", "Specs"])
            if not export.brand and kv.get("brand"):
                export.brand = kv["brand"]
            if not export.model and kv.get("model"):
                export.model = kv["model"]
            if not export.colorway and kv.get("colorway"):
                export.colorway = kv["colorway"]
            if not export.specs and kv.get("specs"):
                export.specs = kv["specs"]

        # Image filenames inside zip
        for n in names:
            low = n.lower()
            if any(low.endswith(ext) for ext in image_exts) and not n.endswith("/"):
                export.image_filenames.append(n.rsplit("/", 1)[-1])

        # Hashtags from captions
        blob = "\n".join(
            filter(
                None,
                [
                    export.captions_meta,
                    export.captions_tiktok,
                    export.captions_pinterest,
                    export.raw_text,
                ],
            )
        )
        export.hashtags = _extract_hashtags(blob)

        # If still no brand/model, try parsing concatenated text as txt pack
        if not export.brand and not export.model and export.raw_text:
            fallback = parse_txt(export.raw_text, source_name)
            export.brand = export.brand or fallback.brand
            export.model = export.model or fallback.model
            export.colorway = export.colorway or fallback.colorway
            export.specs = export.specs or fallback.specs
            if not export.hooks:
                export.hooks = fallback.hooks
            if not export.prompts:
                export.prompts = fallback.prompts
            if not export.captions_meta:
                export.captions_meta = fallback.captions_meta
            if not export.captions_pinterest:
                export.captions_pinterest = fallback.captions_pinterest

    return export


def parse_studio_export(
    data: BytesLike,
    filename: str,
) -> StudioExport:
    """Auto-detect .txt vs .zip and parse."""
    raw = _read_bytes(data)
    name = (filename or "export").lower()
    if name.endswith(".zip") or raw[:2] == b"PK":
        try:
            return parse_zip(raw, source_name=filename)
        except zipfile.BadZipFile:
            # Fall through to text
            pass
    return parse_txt(_safe_decode(raw), source_name=filename)
