import argparse
import gc
import gzip
import json
import re
import time
import tracemalloc
from pathlib import Path


EMAIL_FIELD_PATTERN = re.compile(r'"(email|from|to)"\s*:\s*"([^"]*)"')


def _load_payload_text(path: Path) -> str:
    # Accept either plain JSON or .hhsav gzip payloads.
    raw = path.read_bytes()
    if raw.startswith(b"\x1f\x8b"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def _build_synthetic_payload(records: int) -> str:
    # Deterministic synthetic payload for repeatable local/CI perf checks.
    records = max(20, int(records))
    users = []
    mails = []
    files = []
    for idx in range(records):
        users.append(
            {
                "id": f"user-{idx}",
                "name": f"User {idx}",
                "email": f"user{idx}@gmail.com",
                "stats": {"level": idx % 60, "xp": idx * 17},
                "flags": [idx % 2 == 0, idx % 3 == 0, idx % 5 == 0],
            }
        )
        mails.append(
            {
                "from": f"sender{idx}@gomail.com",
                "to": f"recipient{idx}@gmx.com",
                "subject": f"Subject {idx}",
                "body": "x" * 120,
            }
        )
        files.append(
            {
                "name": f"file_{idx}.txt",
                "isFolder": False,
                "meta": {"size": 1024 + idx, "locked": idx % 11 == 0},
            }
        )

    payload = {
        "users": users,
        "mails": mails,
        "files": files,
        "terminal": {"installedPackages": ["bettercap", "hashcat", "wireshark"]},
    }
    return json.dumps(payload, separators=(",", ":"))


def _count_nodes(root) -> tuple[int, int]:
    count = 0
    max_depth = 0
    stack = [(root, 1)]
    while stack:
        value, depth = stack.pop()
        count += 1
        if depth > max_depth:
            max_depth = depth
        if isinstance(value, dict):
            for item in value.values():
                stack.append((item, depth + 1))
        elif isinstance(value, list):
            for item in value:
                stack.append((item, depth + 1))
    return count, max_depth


def _run_once(payload_text: str) -> dict:
    parse_start = time.perf_counter()
    data = json.loads(payload_text)
    parse_ms = (time.perf_counter() - parse_start) * 1000.0

    total_start = time.perf_counter()
    node_count, max_depth = _count_nodes(data)
    email_count = sum(1 for _ in EMAIL_FIELD_PATTERN.finditer(payload_text))
    json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    total_ms = (time.perf_counter() - total_start) * 1000.0

    return {
        "parse_ms": parse_ms,
        "total_ms": total_ms,
        "node_count": node_count,
        "max_depth": max_depth,
        "email_count": email_count,
    }


def _fmt_bytes(num_bytes: int) -> str:
    mib = float(num_bytes) / (1024.0 * 1024.0)
    return f"{mib:.2f} MiB"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Quick performance/memory smoke check for release builds."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to .hhsav or JSON file. If omitted, synthetic payload is used.",
    )
    parser.add_argument("--synthetic-records", type=int, default=1200)
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Lower-impact local profile (smaller payload + fewer iterations + pacing sleep).",
    )
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument(
        "--iteration-pause-ms",
        type=float,
        default=0.0,
        help="Optional sleep between measured iterations to reduce CPU spikes.",
    )
    # Strict gate exits non-zero when perf/memory thresholds regress.
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--max-parse-ms", type=float, default=300.0)
    parser.add_argument("--max-total-ms", type=float, default=900.0)
    parser.add_argument("--max-peak-mib", type=float, default=256.0)
    parser.add_argument("--max-growth-kib", type=float, default=1024.0)
    args = parser.parse_args()

    if args.safe_mode:
        # Safe mode keeps checks lightweight for shared runners and dev machines.
        if not args.input:
            args.synthetic_records = min(int(args.synthetic_records), 800)
        args.iterations = min(int(args.iterations), 3)
        args.warmup = min(int(args.warmup), 1)
        args.iteration_pause_ms = max(float(args.iteration_pause_ms), 25.0)

    if args.input:
        if not args.input.exists():
            print(f"ERROR: input not found: {args.input}")
            return 2
        source = str(args.input)
        try:
            payload_text = _load_payload_text(args.input)
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as exc:
            print(f"ERROR: failed to load input payload: {exc}")
            return 2
    else:
        source = f"synthetic:{max(20, int(args.synthetic_records))}"
        payload_text = _build_synthetic_payload(args.synthetic_records)

    iterations = max(1, int(args.iterations))
    warmup = max(0, int(args.warmup))

    parse_samples = []
    total_samples = []
    node_counts = []
    depth_counts = []
    email_counts = []
    current_samples = []
    peak_samples = []

    tracemalloc.start()
    try:
        for idx in range(warmup + iterations):
            gc.collect()
            metrics = _run_once(payload_text)
            gc.collect()
            current_bytes, peak_bytes = tracemalloc.get_traced_memory()
            if float(args.iteration_pause_ms) > 0:
                time.sleep(max(0.0, float(args.iteration_pause_ms)) / 1000.0)
            if idx < warmup:
                continue
            parse_samples.append(metrics["parse_ms"])
            total_samples.append(metrics["total_ms"])
            node_counts.append(metrics["node_count"])
            depth_counts.append(metrics["max_depth"])
            email_counts.append(metrics["email_count"])
            current_samples.append(current_bytes)
            peak_samples.append(peak_bytes)
    finally:
        tracemalloc.stop()

    avg_parse = sum(parse_samples) / len(parse_samples)
    max_total = max(total_samples)
    peak_bytes = max(peak_samples)
    growth_bytes = 0
    if len(current_samples) >= 2:
        growth_bytes = current_samples[-1] - current_samples[0]

    print("perf_smoke summary")
    print(f"- source: {source}")
    print(f"- iterations: {iterations} (warmup={warmup})")
    print(f"- iteration pause: {max(0.0, float(args.iteration_pause_ms)):.2f} ms")
    print(f"- payload size: {len(payload_text):,} bytes")
    print(f"- avg parse: {avg_parse:.2f} ms")
    print(f"- max total: {max_total:.2f} ms")
    print(f"- max nodes: {max(node_counts):,}")
    print(f"- max depth: {max(depth_counts)}")
    print(f"- email fields scanned: {max(email_counts):,}")
    print(f"- peak traced memory: {_fmt_bytes(peak_bytes)}")
    print(f"- traced memory growth: {_fmt_bytes(growth_bytes)}")

    if not args.strict:
        return 0

    failures = []
    if avg_parse > float(args.max_parse_ms):
        failures.append(f"avg parse {avg_parse:.2f} ms > {args.max_parse_ms:.2f} ms")
    if max_total > float(args.max_total_ms):
        failures.append(f"max total {max_total:.2f} ms > {args.max_total_ms:.2f} ms")
    if peak_bytes > int(float(args.max_peak_mib) * 1024 * 1024):
        failures.append(
            f"peak traced memory {_fmt_bytes(peak_bytes)} > {args.max_peak_mib:.2f} MiB"
        )
    if growth_bytes > int(float(args.max_growth_kib) * 1024):
        failures.append(
            f"traced growth {_fmt_bytes(growth_bytes)} > {float(args.max_growth_kib) / 1024.0:.2f} MiB"
        )

    if failures:
        print("perf_smoke strict gate: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("perf_smoke strict gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
