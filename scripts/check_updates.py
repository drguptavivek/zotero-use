#!/usr/bin/env python3
"""Periodically compare the installed zotero-use version with GitHub.

The default invocation is silent unless an update is available. Successful
checks schedule the next comparison 14-17 days later. No update is installed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REMOTE_VERSION_URL = (
    "https://raw.githubusercontent.com/drguptavivek/zotero-use/main/VERSION"
)
RELEASE_URL = "https://github.com/drguptavivek/zotero-use"
BASE_INTERVAL_DAYS = 14
JITTER_DAYS = 3
RETRY_INTERVAL_HOURS = 24
VERSION_PATTERN = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
FALSE_VALUES = {"0", "false", "no", "off"}


class UpdateCheckError(RuntimeError):
    """Raised when update metadata cannot be checked safely."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_version(value: str) -> tuple[int, int, int]:
    cleaned = value.strip()
    match = VERSION_PATTERN.fullmatch(cleaned)
    if not match:
        raise UpdateCheckError(f"invalid semantic version: {cleaned!r}")
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def local_version() -> str:
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    try:
        value = version_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise UpdateCheckError(f"cannot read {version_file}: {exc}") from exc
    parse_version(value)
    return value


def default_state_path() -> Path:
    override = os.environ.get("ZOTERO_USE_UPDATE_STATE")
    if override:
        return Path(override).expanduser()
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return base / "zotero-use" / "update-check.json"


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary:
            json.dump(state, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary_name = temporary.name
        os.replace(temporary_name, path)
    except OSError as exc:
        if temporary_name:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise UpdateCheckError(f"cannot write update state {path}: {exc}") from exc


def fetch_remote_version(url: str, timeout: float) -> str:
    if not url.startswith("https://"):
        raise UpdateCheckError("remote version URL must use HTTPS")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "zotero-use-update-check/2.0.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = response.read(128).decode("utf-8").strip()
    except (OSError, UnicodeError, urllib.error.URLError) as exc:
        raise UpdateCheckError(f"cannot fetch remote version: {exc}") from exc
    parse_version(value)
    return value


def next_successful_check(now: datetime) -> datetime:
    jitter_seconds = secrets.randbelow(JITTER_DAYS * 24 * 60 * 60 + 1)
    return now + timedelta(days=BASE_INTERVAL_DAYS, seconds=jitter_seconds)


def is_due(state: dict[str, Any], now: datetime) -> bool:
    next_check = parse_time(state.get("nextCheckAt"))
    return next_check is None or now >= next_check


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Check now")
    parser.add_argument("--json", action="store_true", help="Emit JSON even when not due")
    parser.add_argument("--verbose", action="store_true", help="Report non-update outcomes")
    parser.add_argument("--no-write", action="store_true", help="Do not update state")
    parser.add_argument("--strict", action="store_true", help="Fail on network/state errors")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--remote-url",
        default=os.environ.get("ZOTERO_USE_VERSION_URL", REMOTE_VERSION_URL),
    )
    parser.add_argument("--state-file", type=Path, default=default_state_path())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        installed = local_version()
    except UpdateCheckError as exc:
        if args.json:
            print(json.dumps({"checked": False, "error": str(exc)}, indent=2))
        elif args.verbose:
            print(f"zotero-use update check unavailable: {exc}", file=sys.stderr)
        return 1 if args.strict else 0
    enabled = os.environ.get("ZOTERO_USE_UPDATE_CHECK", "1").lower() not in FALSE_VALUES
    now = utc_now()
    state = load_state(args.state_file)
    due = enabled and (args.force or is_due(state, now))
    result: dict[str, Any] = {
        "enabled": enabled,
        "checked": False,
        "due": due,
        "installedVersion": installed,
        "remoteVersion": None,
        "updateAvailable": False,
        "nextCheckAt": state.get("nextCheckAt"),
        "releaseUrl": RELEASE_URL,
        "error": None,
    }

    if not due:
        if args.json:
            print(json.dumps(result, indent=2))
        elif args.verbose:
            reason = "disabled" if not enabled else f"next check: {result['nextCheckAt']}"
            print(f"zotero-use update check skipped ({reason})")
        return 0

    try:
        remote = fetch_remote_version(args.remote_url, args.timeout)
        next_check = next_successful_check(now)
        result.update(
            {
                "checked": True,
                "remoteVersion": remote,
                "updateAvailable": parse_version(remote) > parse_version(installed),
                "nextCheckAt": format_time(next_check),
            }
        )
        if not args.no_write:
            save_state(
                args.state_file,
                {
                    "lastCheckedAt": format_time(now),
                    "installedVersion": installed,
                    "remoteVersion": remote,
                    "nextCheckAt": result["nextCheckAt"],
                },
            )
    except UpdateCheckError as exc:
        result["error"] = str(exc)
        result["nextCheckAt"] = format_time(
            now + timedelta(hours=RETRY_INTERVAL_HOURS)
        )
        if not args.no_write:
            try:
                save_state(
                    args.state_file,
                    {
                        "lastAttemptAt": format_time(now),
                        "lastError": str(exc),
                        "nextCheckAt": result["nextCheckAt"],
                    },
                )
            except UpdateCheckError:
                if args.strict:
                    raise
        if args.json:
            print(json.dumps(result, indent=2))
        elif args.verbose:
            print(f"zotero-use update check unavailable: {exc}", file=sys.stderr)
        return 1 if args.strict else 0

    if args.json:
        print(json.dumps(result, indent=2))
    elif result["updateAvailable"]:
        print(
            f"zotero-use update available: {installed} -> {result['remoteVersion']}\n"
            f"Review and update: {RELEASE_URL}"
        )
    elif args.verbose:
        print(f"zotero-use {installed} is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
