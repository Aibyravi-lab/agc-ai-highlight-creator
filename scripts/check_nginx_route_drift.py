#!/usr/bin/env python3
"""OPS-001 — Nginx route-drift check for nginx/agc.conf.

Vedzovi has twice shipped an Nginx config where a public API path (first
/admin/mission-control/summary, then /feedback) fell through to the Next.js
catch-all instead of FastAPI, because the old model required a hand-maintained
location block per backend router. The fix adopted in nginx/agc.conf is
architectural: api.vedzovi.com owns one dedicated server block whose only
location is a catch-all straight to the FastAPI upstream, so no route prefix
list needs to stay in sync with backend/app/routers/ ever again.

This script guards that invariant. It fails if:
  1. There isn't exactly one dedicated proxying server block for an "api.*"
     hostname (i.e. api.* is not sharing a server block with the frontend
     hostnames).
  2. That block's "location /" proxies to the same upstream as the frontend's
     "location /" (the exact regression: api.* silently routed to Next.js).
  3. That block contains any location other than "/" (reintroducing the
     per-route location-block pattern that caused both incidents).

No third-party dependencies — stdlib only. Run from the repo root:
    python scripts/check_nginx_route_drift.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CONF_PATH = Path(__file__).resolve().parent.parent / "nginx" / "agc.conf"


def extract_blocks(text: str, header_pattern: str) -> list[tuple[re.Match, str]]:
    """Return (header match, body) for each brace-delimited block matching header_pattern."""
    blocks = []
    for match in re.finditer(header_pattern + r"\s*\{", text):
        open_brace = match.end() - 1
        depth = 0
        i = open_brace
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        else:
            raise ValueError(f"Unbalanced braces starting at offset {open_brace}")
        blocks.append((match, text[open_brace + 1 : i]))
    return blocks


def server_names(body: str) -> list[str]:
    m = re.search(r"server_name\s+([^;]+);", body)
    if not m:
        return []
    return m.group(1).split()


def locations(body: str) -> list[tuple[str, str]]:
    return [
        (match.group(1).strip(), loc_body)
        for match, loc_body in extract_blocks(body, r"location\s+([^\{]+)")
    ]


def proxy_target(body: str) -> str | None:
    m = re.search(r"proxy_pass\s+([^;]+);", body)
    return m.group(1).strip() if m else None


def main() -> int:
    if not CONF_PATH.exists():
        print(f"FAIL: {CONF_PATH} not found")
        return 1

    text = CONF_PATH.read_text(encoding="utf-8")
    server_blocks = extract_blocks(text, r"server")

    # Only look at server blocks that actually reverse-proxy somewhere;
    # the plain HTTP->HTTPS redirect block shares server_name but has no
    # proxy_pass and is irrelevant to routing drift.
    proxying_blocks = [
        (server_names(body), body) for _, body in server_blocks if "proxy_pass" in body
    ]

    api_blocks = [
        (names, body)
        for names, body in proxying_blocks
        if any(name.startswith("api.") for name in names)
    ]
    frontend_blocks = [
        (names, body)
        for names, body in proxying_blocks
        if not any(name.startswith("api.") for name in names)
    ]

    errors = []

    if len(api_blocks) != 1:
        errors.append(
            f"expected exactly 1 dedicated proxying server block for an api.* "
            f"hostname, found {len(api_blocks)}"
        )
    if len(frontend_blocks) != 1:
        errors.append(
            f"expected exactly 1 dedicated proxying server block for the "
            f"frontend hostname(s), found {len(frontend_blocks)}"
        )

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1

    api_names, api_body = api_blocks[0]
    if any(not name.startswith("api.") for name in api_names):
        print(
            f"FAIL: api server block also serves non-api hostname(s) {api_names} "
            f"— api.* must be isolated in its own server block"
        )
        return 1

    front_names, front_body = frontend_blocks[0]

    api_locations = locations(api_body)
    non_root = [path.strip() for path, _ in api_locations if path.strip() != "/"]
    if non_root:
        print(
            f"FAIL: api server block defines location(s) other than '/': {non_root} "
            f"— this reintroduces the per-route drift pattern that caused the "
            f"/admin and /feedback incidents. Route everything through the "
            f"catch-all instead."
        )
        return 1

    root_api = next((body for path, body in api_locations if path.strip() == "/"), None)
    if root_api is None:
        print("FAIL: api server block has no 'location /' catch-all")
        return 1

    front_root = next(
        (body for path, body in locations(front_body) if path.strip() == "/"), None
    )
    if front_root is None:
        print("FAIL: frontend server block has no 'location /' catch-all")
        return 1

    api_target = proxy_target(root_api)
    front_target = proxy_target(front_root)

    if not api_target or not front_target:
        print("FAIL: could not resolve proxy_pass target for one of the catch-alls")
        return 1

    if api_target == front_target:
        print(
            f"FAIL: api.* catch-all proxies to the same upstream as the frontend "
            f"catch-all ({api_target}) — api traffic would fall through to Next.js"
        )
        return 1

    print("OK: nginx/agc.conf keeps api.* and frontend hostnames on isolated")
    print(f"    server blocks with single catch-alls ({api_target} vs {front_target}).")
    print("    No per-route location drift detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
