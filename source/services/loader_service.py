import random


_LOADER_LINES_LOADING = (
    "/buffering startup core sectors...",
    "/buffering dual-theme texture cache...",
    "/buffering render bus channels...",
    "/buffering command shell context...",
    "/protocol siindbad online...",
    "/protocol kamue online...",
    "/cross-theme cache linking...",
    "/fusion handshake in progress...",
    "/render lattice alignment...",
    "/toolbar sprite channels synced...",
    "/decrypting frame atlas segments...",
    "/routing neon signal through core bus...",
    "/indexing hover sweep vectors...",
    "/calibrating titlebar lightfield...",
    "/binding cypher grid to editor shell...",
    "/warming dual-theme shader palette...",
    "/syncing search frame geometry...",
    "/activating command rail telemetry...",
    "/loading tactical ui signatures...",
    "/patching live glyph stream...",
    "/arming selective glitch dampeners...",
    "/resolving border harmonics...",
    "/allocating memory lanes for overlays...",
    "/validating cyber route checksum...",
    "/optimizing hover cadence map...",
    "/decoding darknet mirror packets...",
    "/injecting stealth tracer signatures...",
    "/forging zero-trace handshake keys...",
    "/probing firewall ghost apertures...",
    "/spinning up phantom relay nodes...",
    "/compiling neon intrusion macros...",
    "/mapping black-ice bypass lanes...",
    "/tuning pulse-drive timing offsets...",
    "/authorizing root-shell decoys...",
    "/cross-linking cobalt threat graphs...",
    "/seeding sandbox decoy artifacts...",
    "/sampling packet-noise spectrogram...",
    "/aligning quantum nonce ring...",
    "/routing shadowbus failover path...",
    "/validating opsec checksum lattice...",
    "/arming silent breakpoint sentries...",
    "/fusing dual-core command vectors...",
    "/tempering signal bloom threshold...",
    "/normalizing tactical clock skew...",
    "/indexing exploit telemetry shards...",
    "/backfilling cold-cache glyph maps...",
    "/hushing watchdog interrupt spikes...",
)

_LOADER_LINES_READY = (
    "/full-load complete // stabilizing matrix...",
    "/sync fence engaged // holding viewport...",
    "/dual cache confirmed // finalizing handoff...",
    "/hacker shell primed // user entry incoming...",
    "/siindbad control lane // signal locked...",
    "/kamue shadow lane // spectrum stable...",
    "/fusion corridor // no packet loss...",
    "/neural ui bridge // handshake green...",
    "/clock drift audit // threshold nominal...",
    "/quantum glyph cache // persistence high...",
    "/threat monitor // passive silent mode...",
    "/signal entropy map // variance contained...",
    "/terminal ghost channels // muted clean...",
    "/cold-path watchers // heartbeat stable...",
    "/runtime cloak // low-noise profile...",
    "/final cinematic hold // awaiting operator...",
)


def startup_loader_lines(ready=False):
    return list(_LOADER_LINES_READY if ready else _LOADER_LINES_LOADING)


def pop_startup_loader_line(ready=False, pool=None, shuffle_fn=None):
    lines = startup_loader_lines(ready=ready)
    if not lines:
        return "", []
    next_pool = list(pool) if isinstance(pool, (list, tuple)) else []
    if not next_pool:
        next_pool = list(lines)
        shuffler = shuffle_fn if callable(shuffle_fn) else random.shuffle
        shuffler(next_pool)
    if not next_pool:
        return "", []
    return str(next_pool.pop()), next_pool


def normalize_title_variant(variant):
    name = str(variant or "SIINDBAD").upper()
    if name not in ("SIINDBAD", "KAMUE"):
        return "SIINDBAD"
    return name


def next_title_variant(current_variant):
    current = normalize_title_variant(current_variant)
    return "KAMUE" if current == "SIINDBAD" else "SIINDBAD"


def title_color_for_variant(variant, siindbad_palette=None, kamue_palette=None):
    name = normalize_title_variant(variant)
    if name == "KAMUE":
        palette = kamue_palette if isinstance(kamue_palette, dict) else {}
        return str(palette.get("find_border", "#cfb5ee"))
    palette = siindbad_palette if isinstance(siindbad_palette, dict) else {}
    return str(palette.get("logo_border_outer", "#349fc7"))


def compute_loader_fill_dimensions(track_width, track_height, pct):
    pct = max(0.0, min(100.0, float(pct or 0.0)))
    track_w = max(2, int(track_width or 0))
    track_h = max(2, int(track_height or 0))
    fill_w = int(round(float(max(0, track_w - 2)) * (pct / 100.0)))
    fill_h = max(1, track_h - 2)
    return fill_w, fill_h
