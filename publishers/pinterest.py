"""Pinterest publisher stub — dry-run logs payload; no live API calls in MVP."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger("publishers.pinterest")


@dataclass
class PinterestConfig:
    """Config shape for future auto-publish.

    Keep secrets in env / Streamlit secrets — never commit tokens.
    """

    access_token: str = ""  # from env PINTEREST_ACCESS_TOKEN
    board_id: str = ""
    default_board_id: str = ""
    schedule_at: Optional[str] = None  # ISO-8601 or None for immediate
    dry_run: bool = True
    api_base: str = "https://api.pinterest.com/v5"
    extra: Dict[str, Any] = field(default_factory=dict)

    def resolved_board_id(self) -> str:
        return self.board_id or self.default_board_id


def publish_pin(
    *,
    title: str,
    description: str,
    link: str = "",
    board_id: str = "",
    image_path: str = "",
    image_url: str = "",
    alt_text: str = "",
    schedule_at: Optional[str] = None,
    config: Optional[PinterestConfig] = None,
    hashtags: str = "",
    cta: str = "",
) -> Dict[str, Any]:
    """Publish (or dry-run) a single pin.

    MVP: always dry-run unless config.dry_run is explicitly False AND a token
    is present. Live API is intentionally not implemented yet — this stub
    defines the payload contract for a future merge.
    """
    cfg = config or PinterestConfig()
    board = board_id or cfg.resolved_board_id()
    when = schedule_at or cfg.schedule_at

    full_description = description
    if cta and cta not in description:
        full_description = f"{description}\n\n{cta}".strip()
    if hashtags and hashtags not in full_description:
        full_description = f"{full_description}\n\n{hashtags}".strip()

    payload = {
        "board_id": board,
        "title": title[:100],
        "description": full_description[:800],
        "link": link or None,
        "alt_text": (alt_text or title)[:500],
        "media": {
            "image_path": image_path or None,
            "image_url": image_url or None,
        },
        "schedule_at": when,
        "dry_run": True,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    # Force dry-run in MVP — live publish requires a dedicated implementation.
    live_requested = (not cfg.dry_run) and bool(cfg.access_token) and bool(board)
    if live_requested:
        payload["dry_run"] = False
        payload["status"] = "not_implemented"
        payload["message"] = (
            "Live Pinterest API publish is stubbed. Payload logged only. "
            "Set dry_run=True or implement v5 pins endpoint."
        )
        logger.warning("Pinterest live publish requested but not implemented: %s", payload)
        return payload

    payload["status"] = "dry_run"
    payload["message"] = "Dry-run OK — payload logged, nothing sent to Pinterest."
    logger.info("Pinterest dry-run pin payload:\n%s", json.dumps(payload, indent=2))
    print(f"[pinterest.publish_pin] DRY-RUN\n{json.dumps(payload, indent=2)}")
    return payload


def config_from_env() -> PinterestConfig:
    """Build config from environment (no secrets written to disk)."""
    import os

    return PinterestConfig(
        access_token=os.environ.get("PINTEREST_ACCESS_TOKEN", ""),
        default_board_id=os.environ.get("PINTEREST_BOARD_ID", ""),
        dry_run=os.environ.get("PINTEREST_DRY_RUN", "1") not in ("0", "false", "False"),
    )


def config_schema() -> Dict[str, Any]:
    """Documented config shape for INTEGRATION.md / future UI."""
    return asdict(
        PinterestConfig(
            access_token="<from env PINTEREST_ACCESS_TOKEN>",
            board_id="<board id per pin or default>",
            default_board_id="<from env PINTEREST_BOARD_ID>",
            schedule_at="<ISO-8601 or null>",
            dry_run=True,
        )
    )
