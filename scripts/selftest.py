#!/usr/bin/env python3
"""Check whether the local environment is ready for zotero-use.

This diagnostic is read-only, installs nothing, and uses only the Python
standard library.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


MINIMUM_PYTHON = (3, 8)
PROFILE_PATH = Path.home() / ".config" / "zotcli" / "config.ini"
PROFILE_ENVIRONMENT = (
    "ZOTERO_API_KEY",
    "ZOTERO_LIBRARY_ID",
    "ZOTERO_LIBRARY_TYPE",
)
ZOTSEEK_ENDPOINT = os.environ.get(
    "ZOTSEEK_MCP_URL", "http://localhost:23119/zotseek/mcp"
)


def add_check(
    checks: list[dict[str, Any]], name: str, status: str, detail: str
) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def sanitize(message: str) -> str:
    cleaned = " ".join(message.strip().split())
    for variable in PROFILE_ENVIRONMENT:
        value = os.environ.get(variable)
        if value:
            cleaned = cleaned.replace(value, "***")
    return cleaned[:500]


def run_command(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def command_version(
    checks: list[dict[str, Any]], name: str, path: str, command: list[str], timeout: float
) -> bool:
    try:
        result = run_command(command, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        add_check(checks, name, "WARN", f"found at {path}, but version check failed: {exc}")
        return False
    if result.returncode != 0:
        detail = sanitize(result.stderr or result.stdout or "no diagnostic output")
        add_check(checks, name, "WARN", f"found at {path}, but version check failed: {detail}")
        return False
    version = sanitize(result.stdout or result.stderr or "version reported successfully")
    add_check(checks, name, "PASS", f"{path}: {version}")
    return True


def check_python(checks: list[dict[str, Any]]) -> None:
    version = sys.version_info[:3]
    rendered = ".".join(str(value) for value in version)
    if version < MINIMUM_PYTHON:
        minimum = ".".join(str(value) for value in MINIMUM_PYTHON)
        add_check(checks, "python", "FAIL", f"Python {rendered}; requires {minimum}+")
    else:
        add_check(checks, "python", "PASS", f"Python {rendered} at {sys.executable}")

    required_modules = (
        "argparse",
        "json",
        "pathlib",
        "subprocess",
        "urllib.request",
        "xml.etree.ElementTree",
        "zipfile",
    )
    failures = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError as exc:
            failures.append(f"{module}: {exc}")
    if failures:
        add_check(checks, "python-standard-library", "FAIL", "; ".join(failures))
    else:
        add_check(
            checks,
            "python-standard-library",
            "PASS",
            "all required standard-library modules are available",
        )


def check_validator(checks: list[dict[str, Any]], timeout: float) -> None:
    validator = Path(__file__).with_name("validate_zotero_docx.py")
    if not validator.is_file():
        add_check(checks, "docx-validator", "FAIL", f"missing: {validator}")
        return
    try:
        compile(validator.read_text(encoding="utf-8"), str(validator), "exec")
    except (OSError, SyntaxError, UnicodeError) as exc:
        add_check(checks, "docx-validator", "FAIL", f"cannot compile: {exc}")
        return
    try:
        result = run_command(
            [sys.executable, "-I", "-S", str(validator), "--help"], timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        add_check(checks, "docx-validator", "FAIL", f"isolated invocation failed: {exc}")
        return
    if result.returncode != 0:
        detail = sanitize(result.stderr or result.stdout or "no diagnostic output")
        add_check(checks, "docx-validator", "FAIL", f"isolated invocation failed: {detail}")
    else:
        add_check(
            checks,
            "docx-validator",
            "PASS",
            "present, compilable, and runnable with Python -I -S",
        )


def check_update_checker(checks: list[dict[str, Any]], timeout: float) -> None:
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    checker = Path(__file__).with_name("check_updates.py")
    if not version_file.is_file():
        add_check(checks, "update-checker", "FAIL", f"missing: {version_file}")
        return
    version = version_file.read_text(encoding="utf-8").strip()
    version_parts = version.split(".")
    if len(version_parts) != 3 or any(not part.isdigit() for part in version_parts):
        add_check(checks, "update-checker", "FAIL", f"invalid VERSION: {version!r}")
        return
    if not checker.is_file():
        add_check(checks, "update-checker", "FAIL", f"missing: {checker}")
        return
    try:
        compile(checker.read_text(encoding="utf-8"), str(checker), "exec")
        result = run_command(
            [sys.executable, "-I", "-S", str(checker), "--help"], timeout
        )
    except (OSError, SyntaxError, UnicodeError, subprocess.TimeoutExpired) as exc:
        add_check(checks, "update-checker", "FAIL", f"isolated check failed: {exc}")
        return
    if result.returncode != 0:
        detail = sanitize(result.stderr or result.stdout or "no diagnostic output")
        add_check(checks, "update-checker", "FAIL", detail)
    else:
        add_check(
            checks,
            "update-checker",
            "PASS",
            f"version {version}; present, compilable, and runnable with Python -I -S",
        )


def check_zot(
    checks: list[dict[str, Any]], strict: bool, skip_local: bool, timeout: float
) -> None:
    zot = shutil.which("zot")
    uv = shutil.which("uv")
    uvx = shutil.which("uvx")

    if uv:
        command_version(checks, "uv", uv, [uv, "--version"], timeout)
    else:
        add_check(checks, "uv", "SKIP", "not found; optional when zot is installed")
    if uvx:
        command_version(checks, "uvx", uvx, [uvx, "--version"], timeout)
    else:
        add_check(checks, "uvx", "SKIP", "not found; ephemeral zot fallback unavailable")

    if not zot:
        status = "FAIL" if strict else "WARN"
        fallback = "uvx is available" if uvx else "uvx is also unavailable"
        add_check(checks, "zot", status, f"not found on PATH; {fallback}")
        add_check(checks, "zotero-local-read", "SKIP", "requires the zot command")
        return

    version_ok = command_version(checks, "zot", zot, [zot, "--version"], timeout)
    if not version_ok:
        if strict:
            checks[-1]["status"] = "FAIL"
        add_check(checks, "zotero-local-read", "SKIP", "zot version check failed")
        return
    if skip_local:
        add_check(checks, "zotero-local-read", "SKIP", "disabled by --skip-local")
        return

    command = [
        zot,
        "--local",
        "--library-id",
        "0",
        "--library-type",
        "user",
        "items",
        "list",
        "--limit",
        "1",
        "--output",
        "keys",
    ]
    try:
        result = run_command(command, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        status = "FAIL" if strict else "WARN"
        add_check(checks, "zotero-local-read", status, f"read-only query failed: {exc}")
        return
    if result.returncode == 0:
        add_check(
            checks,
            "zotero-local-read",
            "PASS",
            "read-only local query succeeded; library contents were not printed",
        )
    else:
        status = "FAIL" if strict else "WARN"
        detail = sanitize(result.stderr or "Zotero may be closed or local API access disabled")
        add_check(checks, "zotero-local-read", status, detail)


def check_profiles(checks: list[dict[str, Any]]) -> None:
    present = [name for name in PROFILE_ENVIRONMENT if os.environ.get(name)]
    if len(present) == len(PROFILE_ENVIRONMENT):
        add_check(
            checks,
            "zotero-api-environment",
            "PASS",
            "all API environment variable names are present; values were not printed",
        )
    elif present:
        missing = [name for name in PROFILE_ENVIRONMENT if name not in present]
        add_check(
            checks,
            "zotero-api-environment",
            "WARN",
            f"partial configuration; missing: {', '.join(missing)}",
        )
    else:
        add_check(checks, "zotero-api-environment", "SKIP", "not configured")

    if PROFILE_PATH.is_file():
        add_check(
            checks,
            "zot-profile",
            "PASS",
            f"profile file exists at {PROFILE_PATH}; contents were not read",
        )
    else:
        add_check(checks, "zot-profile", "SKIP", f"no profile file at {PROFILE_PATH}")


def check_optional_tools(checks: list[dict[str, Any]], timeout: float) -> None:
    git = shutil.which("git")
    if git:
        command_version(checks, "git", git, [git, "--version"], timeout)
    else:
        add_check(checks, "git", "SKIP", "not found; only needed for git-based rollback")

    mcp = shutil.which("zotero-mcp")
    if mcp:
        command_version(checks, "zotero-mcp", mcp, [mcp, "version"], timeout)
    else:
        add_check(checks, "zotero-mcp", "SKIP", "not found; optional integration")


def check_zotseek(
    checks: list[dict[str, Any]], timeout: float, require_zotseek: bool
) -> None:
    client = Path(__file__).with_name("zotseek_mcp.py")
    if not client.is_file():
        add_check(checks, "zotseek-mcp", "FAIL", f"missing client: {client}")
        return
    try:
        result = run_command(
            [
                sys.executable,
                "-I",
                "-S",
                str(client),
                "--endpoint",
                ZOTSEEK_ENDPOINT,
                "tools",
                "--names-only",
            ],
            timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        status = "FAIL" if require_zotseek else "WARN"
        add_check(checks, "zotseek-mcp", status, f"discovery failed: {exc}")
        return
    if result.returncode != 0:
        status = "FAIL" if require_zotseek else "WARN"
        detail = sanitize(result.stderr or result.stdout or "no diagnostic output")
        add_check(checks, "zotseek-mcp", status, detail)
        return
    names = [name for name in result.stdout.splitlines() if name]
    rendered = ", ".join(names) if names else "no tools"
    add_check(
        checks,
        "zotseek-mcp",
        "PASS",
        f"live discovery at {ZOTSEEK_ENDPOINT}: {rendered}",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when zot or local Zotero read access is unavailable",
    )
    parser.add_argument(
        "--skip-local",
        action="store_true",
        help="Do not run the read-only local Zotero query",
    )
    parser.add_argument(
        "--require-zotseek",
        action="store_true",
        help="Fail when the ZOTseek MCP endpoint or tool discovery is unavailable",
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    checks: list[dict[str, Any]] = []
    check_python(checks)
    check_validator(checks, args.timeout)
    check_update_checker(checks, args.timeout)
    check_zot(checks, args.strict, args.skip_local, args.timeout)
    check_profiles(checks)
    check_optional_tools(checks, args.timeout)
    check_zotseek(checks, args.timeout, args.require_zotseek)

    failed = [check for check in checks if check["status"] == "FAIL"]
    warnings = [check for check in checks if check["status"] == "WARN"]
    result = {
        "ready": not failed,
        "strict": args.strict,
        "checks": checks,
        "summary": {
            "passed": sum(check["status"] == "PASS" for check in checks),
            "warnings": len(warnings),
            "failed": len(failed),
            "skipped": sum(check["status"] == "SKIP" for check in checks),
        },
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for check in checks:
            print(f"[{check['status']}] {check['name']}: {check['detail']}")
        summary = result["summary"]
        print(
            "Summary: "
            f"{summary['passed']} passed, {summary['warnings']} warning(s), "
            f"{summary['failed']} failed, {summary['skipped']} skipped"
        )
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
