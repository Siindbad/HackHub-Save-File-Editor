"""Manual-update fallback prompt/open helpers."""
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def offer_manual_update_fallback(owner: Any, pretty_error: Any, askyesno_fn: Any, no_value: Any, open_url_fn: Any) -> Any:
    """Prompt for manual update fallback and open release page when accepted."""
    error_text = str(pretty_error or "").strip() or "Update failed."
    prompt = (
        f"{error_text}\n\n"
        "Would you like to open the manual update download page now?"
    )
    wants_open = bool(
        askyesno_fn(
            "Update",
            prompt,
            default=no_value,
        )
    )
    if not wants_open:
        return False
    url = owner._manual_update_download_url()
    if not url:
        return False
    try:
        open_url_fn(url)
        owner._set_status("Opened manual update download page.")
        return True
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        owner._set_status("Could not open browser for manual update download.")
        return False
