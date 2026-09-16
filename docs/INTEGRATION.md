# Integration: Sneaker Image Studio ↔ Pinterest Pack Bridge

This document describes how the two Streamlit apps should share data today and
how they can merge later.

## Roles

| App | Role |
|-----|------|
| [Sneaker Image Studio](https://sneakernessimagestudio.streamlit.app/) | Analyze product images, generate prompts/captions, export `.txt` / `.zip` packs |
| **Pinterest Pack Bridge** (this repo) | Consume Studio export + product images → **English** Pinterest pin packs (titles, descriptions, CTAs, hashtags, aspects, boards) |

Greek UI stays in the Bridge for operators; **all pin copy is English**.

## Stable models

Defined in `models/schemas.py`:

### `StudioExport`
Parsed from Studio `.txt` or `.zip`:

- `brand`, `model`, `colorway`, `specs`
- `captions_meta`, `captions_tiktok`, `captions_pinterest`
- `hooks[]`, `prompts[]`, `hashtags`
- `image_filenames[]`, `meta{}`, `raw_text`

### `ProductFields`
Manual / enriched fields from the Bridge UI (sizes, price hint, DM CTA preference, destination URL, board suggestion, watermark).

### `PinVariant` / `PinPack`
One product → 5–10 English variants:

- `title`, `description`, `cta`, `hashtags`
- `aspect` (`2:3` or `1:1`)
- `board_topic`, `image_filename`
- `variant_type`: product | seo | outfit | lifestyle | urgency | sizes | story | comparison | tech

## Current Studio ZIP shape (supported)

As produced by Image Studio / engine packs:

```
captions_meta.txt
captions_tiktok.txt
prompts.txt
meta.json          # brand, model, colorway, specs, goal, lang, aspect, …
[optional images]
```

`.txt` content packs with `Brand:`, `Model:`, section headers (`Pinterest`, `Hooks`, …) are also accepted.

## Merge path (future)

1. **Shared package** — extract `models/schemas.py` + `parsers/studio_export.py` into a small shared module both apps import.
2. **In-process handoff** — Studio “Send to Pinterest Bridge” button writes `StudioExport` into `st.session_state` or a temp JSON; Bridge reads it without file upload.
3. **Combined app** — single Streamlit multipage: `pages/1_Studio.py` + `pages/2_Pinterest_Pack.py`.
4. **Auto-publish** — wire `publishers/pinterest.py` to Pinterest API v5 using env secrets (`PINTEREST_ACCESS_TOKEN`, `PINTEREST_BOARD_ID`). Keep dry-run default.

## Publisher config shape

See `publishers/pinterest.py` → `PinterestConfig` / `config_schema()`:

```json
{
  "access_token": "<env PINTEREST_ACCESS_TOKEN>",
  "board_id": "<per pin or empty>",
  "default_board_id": "<env PINTEREST_BOARD_ID>",
  "schedule_at": "<ISO-8601 or null>",
  "dry_run": true,
  "api_base": "https://api.pinterest.com/v5"
}
```

**Never commit tokens.** Use `.env` (gitignored) or Streamlit Secrets.

## Contract checklist for Studio exporters

When changing Studio export format, keep at least one of:

- `meta.json` with `brand` / `model` / `colorway` / `specs`
- OR plain-text lines `Brand:` / `Model:`
- Captions in `captions_*.txt` or clearly headed sections
- Image files with stable filenames if you want Bridge ZIP manifests to match

Bridge parsers are intentionally **flexible** — missing fields fall back to manual UI inputs.
