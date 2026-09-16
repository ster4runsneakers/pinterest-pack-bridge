"""Pinterest Pack Bridge — Streamlit MVP.

Greek UI · English pin copy · offline templates.
Bridge AFTER Sneaker Image Studio → Pinterest-ready packs.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import streamlit as st

from exporters.downloads import pack_to_csv, pack_to_txt, pack_to_zip
from generators.pin_templates import generate_pin_pack
from models.schemas import ProductFields, StudioExport
from parsers.studio_export import parse_studio_export
from publishers.pinterest import PinterestConfig, publish_pin

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="Pinterest Pack Bridge",
    page_icon="📌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Greek UI strings (pin copy stays English)
# ---------------------------------------------------------------------------
UI = {
    "title": "📌 Pinterest Pack Bridge",
    "subtitle": "Μετά το Sneaker Image Studio → έτοιμα English pin packs για Pinterest",
    "sidebar_help": "Ανέβασε εικόνες προϊόντος + προαιρετικό export από το Image Studio. Τα κείμενα των pins είναι πάντα Αγγλικά.",
    "studio_link": "Sneaker Image Studio",
    "section_images": "1. Εικόνες προϊόντος",
    "images_help": "JPG / PNG / WEBP — μία ή περισσότερες",
    "section_studio": "2. Export από Image Studio (προαιρετικό)",
    "studio_help": ".txt ή .zip από το Sneaker Image Studio (captions, hooks, prompts, meta.json)",
    "section_fields": "3. Στοιχεία προϊόντος",
    "brand": "Μάρκα (Brand)",
    "model": "Μοντέλο",
    "colorway": "Χρώμα / Colorway",
    "sizes": "Μεγέθη (π.χ. EU 40–45)",
    "price": "Ένδειξη τιμής (προαιρετικό)",
    "dm_cta": "Προτίμηση CTA (DM)",
    "url": "URL προορισμού",
    "board": "Πρόταση board",
    "specs": "Specs / χαρακτηριστικά (EN καλύτερα)",
    "watermark": "Watermark / site",
    "count": "Αριθμός pin variants",
    "generate": "🚀 Δημιουργία Pin Pack",
    "parse_ok": "Διαβάστηκε το Studio export",
    "parse_fail": "Δεν ήταν δυνατή η ανάγνωση του export — χρησιμοποιούνται τα χειροκίνητα πεδία.",
    "need_product": "Συμπλήρωσε τουλάχιστον μάρκα ή μοντέλο, ή ανέβασε Studio export.",
    "results": "4. Αποτελέσματα — English pin packs",
    "download_txt": "⬇️ Λήψη .txt",
    "download_csv": "⬇️ Λήψη .csv",
    "download_zip": "⬇️ Λήψη .zip (με manifest εικόνων)",
    "dry_run": "🧪 Dry-run publish (stub)",
    "dry_run_help": "Καταγράφει το payload τοπικά — δεν στέλνει τίποτα στο Pinterest.",
    "copy_hint": "Επίλεξε το κείμενο στο πλαίσιο και Ctrl/Cmd+C για αντιγραφή.",
    "variant": "Variant",
    "aspect": "Aspect",
    "board_topic": "Board",
    "title_en": "Title (EN)",
    "desc_en": "Description (EN)",
    "cta_en": "CTA (EN)",
    "hashtags_en": "Hashtags (EN)",
    "image_ref": "Αρχείο εικόνας",
    "footer": "MVP · offline templates · χωρίς υποχρεωτικό API key · publishers/pinterest.py = dry-run stub",
}

DM_OPTIONS = [
    "DM to buy",
    "Message us",
    "Ask for sizes",
    "Link in bio",
    "Save for later",
]


def _init_state() -> None:
    defaults = {
        "pin_pack": None,
        "studio_export": None,
        "last_dry_runs": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _parse_uploaded_studio(uploaded) -> Optional[StudioExport]:
    if not uploaded:
        return None
    try:
        data = uploaded.getvalue()
        return parse_studio_export(data, uploaded.name)
    except Exception as exc:  # noqa: BLE001 — show friendly Greek message
        st.warning(f"{UI['parse_fail']} ({exc})")
        return None


def _product_from_form(
    brand: str,
    model: str,
    colorway: str,
    sizes: str,
    price_hint: str,
    dm_cta: str,
    url: str,
    board: str,
    specs: str,
    watermark: str,
    image_names: List[str],
) -> ProductFields:
    return ProductFields(
        brand=brand.strip(),
        model=model.strip(),
        colorway=colorway.strip(),
        sizes=sizes.strip(),
        price_hint=price_hint.strip(),
        dm_cta_preference=dm_cta,
        destination_url=url.strip(),
        board_suggestion=board.strip(),
        specs=specs.strip(),
        watermark=watermark.strip() or "SNEAKERNESS.EU",
        image_filenames=image_names,
    )


def main() -> None:
    _init_state()

    st.title(UI["title"])
    st.markdown(
        f"{UI['subtitle']} · "
        f"[{UI['studio_link']}](https://sneakernessimagestudio.streamlit.app/)"
    )
    st.caption(UI["sidebar_help"])

    with st.sidebar:
        st.header("ℹ️ Οδηγίες")
        st.markdown(
            """
1. Ανέβασε **εικόνες** προϊόντος  
2. (Προαιρετικά) ανέβασε **Studio .txt / .zip**  
3. Συμπλήρωσε μάρκα / μοντέλο αν λείπουν  
4. Πάτα **Δημιουργία Pin Pack**  
5. Κατέβασε `.txt` / `.csv` / `.zip`

Τα **titles, descriptions, CTAs, hashtags** είναι πάντα **Αγγλικά**.
            """
        )
        st.divider()
        st.markdown("**Επόμενα βήματα**")
        st.caption("Auto-publish Pinterest · συνένωση με Image Studio · LLM polish")
        st.divider()
        count = st.slider(UI["count"], min_value=5, max_value=10, value=8)

    # --- Images ---
    st.subheader(UI["section_images"])
    images = st.file_uploader(
        UI["images_help"],
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="product_images",
    )
    image_names: List[str] = []
    if images:
        cols = st.columns(min(4, len(images)))
        for i, img in enumerate(images):
            image_names.append(img.name)
            with cols[i % len(cols)]:
                st.image(img, caption=img.name, use_container_width=True)

    # --- Studio export ---
    st.subheader(UI["section_studio"])
    studio_file = st.file_uploader(
        UI["studio_help"],
        type=["txt", "zip"],
        accept_multiple_files=False,
        key="studio_export_file",
    )

    studio: Optional[StudioExport] = None
    if studio_file is not None:
        studio = _parse_uploaded_studio(studio_file)
        if studio:
            st.session_state["studio_export"] = studio
            st.success(
                f"{UI['parse_ok']}: `{studio.source_name}` — "
                f"{studio.brand or '—'} / {studio.model or '—'}"
            )
            with st.expander("Προεπισκόπηση Studio export", expanded=False):
                st.json(
                    {
                        "brand": studio.brand,
                        "model": studio.model,
                        "colorway": studio.colorway,
                        "specs": studio.specs,
                        "hooks": studio.hooks[:5],
                        "prompts_count": len(studio.prompts),
                        "hashtags": studio.hashtags,
                        "captions_pinterest_preview": (studio.captions_pinterest or "")[:300],
                        "image_filenames": studio.image_filenames,
                    }
                )
            for fn in studio.image_filenames:
                if fn not in image_names:
                    image_names.append(fn)

    # Prefill from studio if fields empty
    pre = st.session_state.get("studio_export") or studio
    default_brand = (pre.brand if pre else "") or ""
    default_model = (pre.model if pre else "") or ""
    default_colorway = (pre.colorway if pre else "") or ""
    default_specs = (pre.specs if pre else "") or ""

    # --- Manual fields ---
    st.subheader(UI["section_fields"])
    c1, c2, c3 = st.columns(3)
    with c1:
        brand = st.text_input(UI["brand"], value=default_brand)
        model = st.text_input(UI["model"], value=default_model)
        colorway = st.text_input(UI["colorway"], value=default_colorway)
    with c2:
        sizes = st.text_input(UI["sizes"], value="")
        price_hint = st.text_input(UI["price"], value="")
        dm_cta = st.selectbox(UI["dm_cta"], DM_OPTIONS, index=0)
    with c3:
        url = st.text_input(UI["url"], value="", placeholder="https://…")
        board = st.text_input(UI["board"], value="", placeholder="Sneaker Product Shots")
        watermark = st.text_input(UI["watermark"], value="SNEAKERNESS.EU")

    specs = st.text_area(UI["specs"], value=default_specs, height=80)

    gen = st.button(UI["generate"], type="primary", use_container_width=True)

    if gen:
        product = _product_from_form(
            brand,
            model,
            colorway,
            sizes,
            price_hint,
            dm_cta,
            url,
            board,
            specs,
            watermark,
            image_names,
        )
        studio_use = studio or st.session_state.get("studio_export")
        if not product.brand and not product.model and not (
            studio_use and (studio_use.brand or studio_use.model or studio_use.raw_text)
        ):
            st.error(UI["need_product"])
        else:
            with st.spinner("Δημιουργία English pin variants…"):
                pack = generate_pin_pack(product, studio=studio_use, count=count)
            st.session_state["pin_pack"] = pack
            st.success(f"Έτοιμο — {len(pack.variants)} pin variants (EN)")

    pack = st.session_state.get("pin_pack")
    if not pack:
        st.info("Συμπλήρωσε τα πεδία και πάτα **Δημιουργία Pin Pack** για αποτελέσματα.")
        st.caption(UI["footer"])
        return

    # --- Results ---
    st.subheader(UI["results"])
    st.caption(UI["copy_hint"])

    txt_name, txt_body = pack_to_txt(pack)
    csv_name, csv_body = pack_to_csv(pack)
    zip_name, zip_bytes = pack_to_zip(pack)

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.download_button(
            UI["download_txt"],
            data=txt_body,
            file_name=txt_name,
            mime="text/plain",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            UI["download_csv"],
            data=csv_body,
            file_name=csv_name,
            mime="text/csv",
            use_container_width=True,
        )
    with d3:
        st.download_button(
            UI["download_zip"],
            data=zip_bytes,
            file_name=zip_name,
            mime="application/zip",
            use_container_width=True,
            help="Περιλαμβάνει pin_pack.txt, pin_pack.csv, manifest.json με ονόματα εικόνων",
        )
    with d4:
        if st.button(UI["dry_run"], use_container_width=True, help=UI["dry_run_help"]):
            results = []
            cfg = PinterestConfig(dry_run=True, board_id=pack.product.board_suggestion)
            for v in pack.variants:
                results.append(
                    publish_pin(
                        title=v.title,
                        description=v.description,
                        link=pack.product.destination_url,
                        board_id=v.board_topic,
                        image_path=v.image_filename,
                        hashtags=v.hashtags,
                        cta=v.cta,
                        config=cfg,
                    )
                )
            st.session_state["last_dry_runs"] = results
            st.success(f"Dry-run: {len(results)} payloads καταγράφηκαν (δες παρακάτω / terminal).")

    if st.session_state.get("last_dry_runs"):
        with st.expander("Dry-run payloads", expanded=False):
            st.json(st.session_state["last_dry_runs"][:3])
            st.caption(f"… σύνολο {len(st.session_state['last_dry_runs'])} (εμφανίζονται τα 3 πρώτα)")

    # Variant cards
    for v in pack.variants:
        with st.expander(
            f"{v.variant_id} · {v.variant_type} · {v.aspect} · {v.title[:60]}",
            expanded=(v.variant_id == "pin_01"),
        ):
            m1, m2, m3 = st.columns(3)
            m1.markdown(f"**{UI['aspect']}:** `{v.aspect}`")
            m2.markdown(f"**{UI['board_topic']}:** {v.board_topic}")
            m3.markdown(f"**{UI['image_ref']}:** `{v.image_filename or '—'}`")

            st.text_input(
                UI["title_en"],
                value=v.title,
                key=f"title_{v.variant_id}",
            )
            st.text_area(
                UI["desc_en"],
                value=v.description,
                height=180,
                key=f"desc_{v.variant_id}",
            )
            st.text_input(UI["cta_en"], value=v.cta, key=f"cta_{v.variant_id}")
            st.text_input(
                UI["hashtags_en"],
                value=v.hashtags,
                key=f"tags_{v.variant_id}",
            )
            st.text_area(
                "Copy block (όλο μαζί)",
                value=v.copy_block(),
                height=160,
                key=f"copy_{v.variant_id}",
            )

    st.caption(UI["footer"])


if __name__ == "__main__":
    main()
