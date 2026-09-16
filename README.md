# Pinterest Pack Bridge

Streamlit bridge **after** [Sneaker Image Studio](https://sneakernessimagestudio.streamlit.app/): upload Studio export + product image(s) → **English** Pinterest-ready pin packs.

**UI language:** Greek · **Pin copy (titles, descriptions, CTAs, hashtags):** English always.

## Quick start

```bash
git clone https://github.com/ster4runsneakers/pinterest-pack-bridge.git
cd pinterest-pack-bridge
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL Streamlit prints (usually http://localhost:8501).

No API key required. Optional env vars (see `.env.example`) for future LLM polish / Pinterest publish.

## What the MVP does

1. **Upload** product images (JPG/PNG/WEBP)
2. **Optional** Studio `.txt` / `.zip` export (captions, hooks, prompts, `meta.json`)
3. **Manual fields:** brand, model, colorway, sizes, price hint, DM CTA preference, destination URL, board suggestion
4. **Generate** 5–10 English pin variants (product, SEO, outfit, lifestyle, tech, sizes, urgency, story, comparison)
5. **Download** `.txt`, `.csv`, and `.zip` (includes `manifest.json` with image filenames)
6. **Copy helpers** via text fields (select + Ctrl/Cmd+C)
7. **Dry-run publish** stub — logs payload, does not call Pinterest

## Project layout

```
app.py                 # Streamlit entrypoint
models/schemas.py      # StudioExport, ProductFields, PinVariant, PinPack
parsers/studio_export.py
generators/pin_templates.py   # offline English templates
exporters/downloads.py
publishers/pinterest.py       # dry-run stub
docs/INTEGRATION.md           # future merge with Image Studio
```

## MVP vs next

| Now (MVP) | Next |
|-----------|------|
| Offline template generation | Optional LLM rewrite via env key |
| Parse Studio txt/zip | In-process handoff / multipage combine with Studio |
| Dry-run `publish_pin(...)` | Live Pinterest API v5 + schedule |
| Download packs | Board picker + media upload |

See [docs/INTEGRATION.md](docs/INTEGRATION.md) for shared models and merge plan.

## Security

- Do **not** commit API tokens or `.streamlit/secrets.toml`
- `.env` is gitignored — copy from `.env.example`

## License

Private — Sneakerness / ster4runsneakers.
