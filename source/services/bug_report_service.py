import io
import math
import os
import random
import re
from datetime import datetime, timezone


def build_bug_report_markdown(
    *,
    summary,
    details,
    now_text,
    app_version,
    theme_variant,
    selected_path,
    last_json_error,
    last_highlight_note,
    python_version,
    platform_text,
    include_diag=True,
    diag_tail="",
    crash_tail="",
    discord_contact="",
    screenshot_url="",
    screenshot_filename="",
    screenshot_note="",
):
    # Assemble the final issue body used by API submission and browser fallback.
    crash_tail = str(crash_tail or "").strip()
    discord_contact = str(discord_contact or "").strip()
    parts = [
        "## In-App Bug Report",
        "",
        "### Summary",
        str(summary or "").strip(),
        "",
        "### Reporter Notes",
        str(details or "").strip() or "(no extra notes)",
        "",
        "### Runtime Context",
        f"- Time: {now_text}",
        f"- App Version: {app_version}",
        f"- Theme: {theme_variant}",
        f"- Selected Path: {selected_path}",
        f"- Last JSON Error: {last_json_error or 'none'}",
        f"- Last Highlight Note: {last_highlight_note or 'none'}",
        f"- Python: {python_version}",
        f"- Platform: {platform_text}",
    ]
    if discord_contact:
        parts.append(f"- Discord: {discord_contact}")
    if include_diag:
        parts.extend(
            [
                "",
                "### Diagnostics Tail",
                "```text",
                str(diag_tail or "").strip() or "(diagnostics log is empty)",
                "```",
            ]
        )
    if crash_tail:
        parts.extend(
            [
                "",
                "### Crash Log Tail",
                "```text",
                crash_tail,
                "```",
            ]
        )
    if screenshot_url:
        parts.extend(
            [
                "",
                "### Screenshot",
                f"![{(screenshot_filename or 'bug-screenshot').strip()}]({screenshot_url})",
                "",
                f"Direct link: {screenshot_url}",
            ]
        )
    elif screenshot_filename:
        parts.extend(
            [
                "",
                "### Screenshot",
                (
                    f"Selected file: `{screenshot_filename}` "
                    "(attach manually in browser issue form if needed)."
                ),
            ]
        )
    if screenshot_note:
        parts.extend(
            [
                "",
                "### Screenshot Upload Note",
                str(screenshot_note).strip(),
            ]
        )
    return "\n".join(parts).strip()


def sanitize_bug_screenshot_slug(value):
    # Keep screenshot path segments filesystem/URL safe.
    text = str(value or "").strip().lower()
    if not text:
        return "screenshot"
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return "screenshot"
    return text[:40]


def build_bug_screenshot_repo_path(source_filename, summary="", uploads_dir="bug-uploads"):
    # Build a collision-resistant repo path under bug-uploads/YYYY/MM/.
    base_name = os.path.basename(str(source_filename or "").strip())
    stem, ext = os.path.splitext(base_name)
    ext = str(ext or "").lower()
    if not ext:
        ext = ".png"
    slug_source = stem if stem else summary
    slug = sanitize_bug_screenshot_slug(slug_source)
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y%m%dT%H%M%SZ")
    short_id = f"{random.getrandbits(24):06x}"
    year = now_utc.strftime("%Y")
    month = now_utc.strftime("%m")
    use_uploads_dir = str(uploads_dir or "bug-uploads").strip("/")
    return f"{use_uploads_dir}/{year}/{month}/{ts}_{short_id}_{slug}{ext}"


def detect_bug_screenshot_magic_ext(source_path):
    # Validate file signature instead of trusting extension alone.
    try:
        with open(source_path, "rb") as fh:
            header = fh.read(16)
    except Exception:
        return ""
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return ".webp"
    return ""


def validate_bug_screenshot_dimensions(source_path, max_dimension=4096):
    max_dim = int(max_dimension or 0)
    if max_dim <= 0:
        return
    try:
        from PIL import Image

        with Image.open(source_path) as img:
            width = int(img.width or 0)
            height = int(img.height or 0)
    except Exception as exc:
        raise RuntimeError("Unable to inspect screenshot dimensions.") from exc
    if width <= 0 or height <= 0:
        raise RuntimeError("Selected screenshot has invalid image dimensions.")
    if width > max_dim or height > max_dim:
        raise RuntimeError(
            f"Screenshot dimensions exceed limit ({max_dim}px max width/height)."
        )


def validate_bug_screenshot_file(
    path,
    *,
    allowed_extensions=(".png", ".jpg", ".jpeg", ".webp"),
    max_bytes=5 * 1024 * 1024,
    max_dimension=4096,
):
    # Enforce extension/signature/size/dimension guardrails before upload prep.
    src = str(path or "").strip()
    if not src:
        return ""
    if not os.path.isfile(src):
        raise RuntimeError("Selected screenshot file does not exist.")
    ext = os.path.splitext(src)[1].lower()
    allowed = {str(item).lower() for item in allowed_extensions}
    if ext not in allowed:
        raise RuntimeError(
            "Unsupported screenshot format. Allowed: " + ", ".join(sorted(allowed))
        )
    detected_ext = detect_bug_screenshot_magic_ext(src)
    if not detected_ext:
        raise RuntimeError("Selected file is not a valid supported image.")
    jpeg_exts = {".jpg", ".jpeg"}
    ext_matches = (ext == detected_ext) or ({ext, detected_ext} <= jpeg_exts)
    if not ext_matches:
        raise RuntimeError("Screenshot extension does not match actual file format.")
    use_max_bytes = int(max_bytes or 0)
    size_bytes = int(os.path.getsize(src))
    if use_max_bytes > 0 and size_bytes > use_max_bytes:
        raise RuntimeError(
            f"Screenshot exceeds size limit ({use_max_bytes // (1024 * 1024)} MB max)."
        )
    validate_bug_screenshot_dimensions(src, max_dimension=max_dimension)
    return src


def prepare_bug_screenshot_upload_bytes(source_path, detected_ext, max_bytes=5 * 1024 * 1024):
    # Re-encode image to strip metadata and normalize upload payload.
    from PIL import Image

    save_ext = str(detected_ext or "").lower()
    format_map = {
        ".png": ("PNG", "image/png"),
        ".jpg": ("JPEG", "image/jpeg"),
        ".jpeg": ("JPEG", "image/jpeg"),
        ".webp": ("WEBP", "image/webp"),
    }
    save_format, mime_type = format_map.get(save_ext, ("PNG", "image/png"))
    with Image.open(source_path) as img:
        working = img
        if save_format == "JPEG" and img.mode not in ("RGB", "L"):
            working = img.convert("RGB")
        out = io.BytesIO()
        save_kwargs = {}
        if save_format == "JPEG":
            save_kwargs["quality"] = 92
            save_kwargs["optimize"] = True
        if save_format == "WEBP":
            save_kwargs["quality"] = 90
            save_kwargs["method"] = 6
        working.save(out, format=save_format, **save_kwargs)
        raw_bytes = out.getvalue()
    use_max_bytes = int(max_bytes or 0)
    if use_max_bytes > 0 and len(raw_bytes) > use_max_bytes:
        raise RuntimeError(
            f"Processed screenshot exceeds size limit ({use_max_bytes // (1024 * 1024)} MB max)."
        )
    return raw_bytes, mime_type


def build_bug_report_new_issue_url(owner, repo, labels, title, body_markdown, include_body=True):
    use_owner = str(owner or "").strip()
    use_repo = str(repo or "").strip()
    if not use_owner or not use_repo:
        raise RuntimeError("Bug report repo is not configured.")
    labels_csv = ",".join(str(label).strip() for label in labels if str(label).strip())
    from urllib import parse

    payload = {
        "title": str(title or "").strip(),
        "labels": labels_csv,
    }
    # Browser fallback privacy mode can omit body= so diagnostics/crash text is not placed in URL query.
    if include_body:
        payload["body"] = str(body_markdown or "").strip()
    query = parse.urlencode(payload)
    return f"https://github.com/{use_owner}/{use_repo}/issues/new?{query}"


def bug_report_submit_cooldown_remaining(last_submit_monotonic, cooldown_seconds, now_monotonic):
    # Returns seconds remaining before another submit is allowed.
    cooldown = int(cooldown_seconds or 0)
    if cooldown <= 0:
        return 0
    last_submit = float(last_submit_monotonic or 0.0)
    if last_submit <= 0:
        return 0
    now_val = float(now_monotonic)
    remaining = (last_submit + float(cooldown)) - now_val
    if remaining <= 0:
        return 0
    return int(math.ceil(remaining))
