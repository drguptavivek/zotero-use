#!/usr/bin/env python3
"""Download and install the platform-specific zotero-go-cli release.

This installer intentionally uses only the Python standard library.  It never
runs the downloaded program; it verifies the release checksum, extracts only
the expected executable, and installs it atomically into this skill's ``bin``
directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Iterable


DEFAULT_REPOSITORY = "drguptavivek/zotero-go-cli"
GITHUB_API = "https://api.github.com"
USER_AGENT = "zotero-use-cli-installer/1.0"
EXPECTED_TEAM_ID = "2M5AS49SM7"
EXPECTED_SIGNING_AUTHORITY = "Developer ID Application: ALL INDIA INSTITUTE OF MEDICAL SCIENCES (2M5AS49SM7)"
CODESIGN_PATH = Path("/usr/bin/codesign")
CHECKSUM_RE = re.compile(r"^([0-9a-fA-F]{64})\s+(?:\*|)?(.+?)\s*$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class InstallerError(RuntimeError):
    """A user-actionable installation failure."""


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _https_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise InstallerError(f"refusing non-HTTPS URL: {url}")
    return url


def fetch_bytes(url: str, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(
        _https_url(url), headers={"Accept": "application/octet-stream", "User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except (OSError, urllib.error.URLError) as exc:
        raise InstallerError(f"download failed for {url}: {exc}") from exc


def fetch_json(url: str, timeout: float = 30.0) -> Any:
    request = urllib.request.Request(
        _https_url(url), headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, UnicodeError, json.JSONDecodeError) as exc:
        raise InstallerError(f"could not read release metadata from {url}: {exc}") from exc


def normalize_version(value: str) -> str:
    value = value.strip()
    if value.startswith("v"):
        value = value[1:]
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", value):
        raise InstallerError(f"invalid release version: {value!r}")
    return value


def _release_version(release: dict[str, Any]) -> str:
    tag = release.get("tag_name")
    if not isinstance(tag, str):
        raise InstallerError("GitHub release metadata has no tag_name")
    return normalize_version(tag)


def select_release(
    releases: Iterable[dict[str, Any]],
    version: str | None = None,
    allow_prerelease: bool = False,
) -> dict[str, Any]:
    candidates = []
    requested = normalize_version(version) if version else None
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        try:
            release_version = _release_version(release)
        except InstallerError:
            continue
        if requested is not None and release_version != requested:
            continue
        if release.get("prerelease") and requested is None and not allow_prerelease:
            continue
        candidates.append(release)
    if requested is not None:
        if not candidates:
            raise InstallerError(f"release v{requested} was not found (or is a draft)")
        return candidates[0]
    if not candidates:
        qualifier = " (with --allow-prerelease)" if not allow_prerelease else ""
        raise InstallerError(f"no suitable non-draft release found{qualifier}")
    return candidates[0]


def detect_target(system: str | None = None, machine: str | None = None) -> tuple[str, str, str]:
    system = (system or sys.platform).lower()
    machine = (machine or platform.machine()).lower()
    if system.startswith("darwin"):
        os_name = "darwin"
    elif system.startswith("linux"):
        os_name = "linux"
    elif system.startswith(("win", "msys", "cygwin")):
        os_name = "windows"
    else:
        raise InstallerError(f"unsupported operating system: {system}")
    arch_aliases = {
        "arm64": "arm64",
        "aarch64": "arm64",
        "x86_64": "amd64",
        "amd64": "amd64",
        "x64": "amd64",
    }
    try:
        arch = arch_aliases[machine]
    except KeyError as exc:
        raise InstallerError(f"unsupported CPU architecture: {machine}") from exc
    if (os_name, arch) not in {("darwin", "arm64"), ("linux", "amd64"), ("linux", "arm64"), ("windows", "amd64")}:
        raise InstallerError(f"unsupported platform/architecture: {os_name}-{arch}")
    extension = ".zip" if os_name == "windows" else ".tar.gz"
    return os_name, arch, f"zotero-go-cli-{os_name}-{arch}{extension}"


def release_asset(release: dict[str, Any], name: str) -> str:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise InstallerError("release metadata has no assets")
    for asset in assets:
        if isinstance(asset, dict) and asset.get("name") == name:
            url = asset.get("browser_download_url")
            if isinstance(url, str):
                return _https_url(url)
    raise InstallerError(f"release does not contain required asset {name}")


def checksum_for(checksum_text: str, asset_name: str) -> str:
    for line in checksum_text.splitlines():
        match = CHECKSUM_RE.match(line.strip())
        if match and Path(match.group(2)).name == asset_name:
            return match.group(1).lower()
    raise InstallerError(f"SHA256SUMS has no checksum for {asset_name}")


def verify_checksum(data: bytes, expected: str, asset_name: str) -> None:
    actual = hashlib.sha256(data).hexdigest()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected) or actual != expected.lower():
        raise InstallerError(f"SHA-256 mismatch for {asset_name}: expected {expected}, got {actual}")


def _safe_member_name(name: str) -> PurePosixPath:
    if "\\" in name:
        raise InstallerError(f"archive contains unsafe path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise InstallerError(f"archive contains unsafe path: {name!r}")
    return path


def _expected_paths(executable_name: str) -> tuple[str, str]:
    return "zotero-use/bin/" + executable_name, executable_name


def _validate_archive_member(name: str, executable_name: str) -> None:
    path = _safe_member_name(name.rstrip("/"))
    expected, bare = _expected_paths(executable_name)
    # Releases may be either the complete skill bundle or an archive rooted at
    # the executable.  We extract one exact executable and ignore other safe
    # bundle files; any unsafe member still fails closed.
    if str(path) in (expected, bare):
        return
    if str(path).startswith("zotero-use/") or len(path.parts) == 1:
        return
    raise InstallerError(f"archive contains unexpected path: {name!r}")


def _read_tar(data: bytes, executable_name: str) -> bytes:
    import tarfile

    try:
        with tarfile.open(fileobj=__import__("io").BytesIO(data), mode="r:gz") as archive:
            matches = []
            for member in archive.getmembers():
                _validate_archive_member(member.name, executable_name)
                if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                    raise InstallerError(f"archive contains unsupported link/device: {member.name!r}")
                if member.isfile() and PurePosixPath(member.name).name == executable_name:
                    if member.name not in _expected_paths(executable_name):
                        raise InstallerError(f"executable has unexpected path: {member.name!r}")
                    matches.append(member)
            if len(matches) != 1:
                raise InstallerError(f"archive must contain exactly one {executable_name}")
            extracted = archive.extractfile(matches[0])
            if extracted is None:
                raise InstallerError(f"could not read {executable_name} from archive")
            return extracted.read()
    except tarfile.TarError as exc:
        raise InstallerError(f"invalid tar archive: {exc}") from exc


def _read_zip(data: bytes, executable_name: str) -> bytes:
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(data)) as archive:
            matches = []
            for info in archive.infolist():
                _validate_archive_member(info.filename, executable_name)
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise InstallerError(f"archive contains symlink: {info.filename!r}")
                if not info.is_dir() and PurePosixPath(info.filename).name == executable_name:
                    if info.filename not in _expected_paths(executable_name):
                        raise InstallerError(f"executable has unexpected path: {info.filename!r}")
                    matches.append(info)
            if len(matches) != 1:
                raise InstallerError(f"archive must contain exactly one {executable_name}")
            return archive.read(matches[0])
    except (zipfile.BadZipFile, OSError) as exc:
        raise InstallerError(f"invalid zip archive: {exc}") from exc


def extract_executable(data: bytes, asset_name: str, executable_name: str) -> bytes:
    if asset_name.endswith(".zip"):
        return _read_zip(data, executable_name)
    if asset_name.endswith(".tar.gz"):
        return _read_tar(data, executable_name)
    raise InstallerError(f"unsupported release archive: {asset_name}")


def check_existing(target: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(target), "installed": target.is_file()}
    if target.is_file():
        result["size"] = target.stat().st_size
        result["executable"] = os.access(target, os.X_OK)
    return result


def _verify_macos_signature(target: Path) -> None:
    if not CODESIGN_PATH.is_file():
        raise InstallerError("macOS signature verification requires /usr/bin/codesign")
    try:
        subprocess.run(
            [str(CODESIGN_PATH), "--verify", "--strict", "--verbose=2", str(target)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        details = subprocess.run(
            [str(CODESIGN_PATH), "-dvvv", str(target)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InstallerError(f"macOS code-signature verification failed for {target}") from exc
    signature = details.stdout + details.stderr
    if f"TeamIdentifier={EXPECTED_TEAM_ID}" not in signature or f"Authority={EXPECTED_SIGNING_AUTHORITY}" not in signature:
        raise InstallerError(
            f"macOS binary is not signed by the expected Developer ID team {EXPECTED_TEAM_ID}"
        )


def install_executable(payload: bytes, target: Path, force: bool = False, verify_macos: bool = False) -> None:
    if target.exists() and not force:
        raise InstallerError(f"destination already exists; use --force to replace: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", delete=False) as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fchmod(temporary.fileno(), 0o755)
            temporary_name = temporary.name
        temporary_path = Path(temporary_name)
        if verify_macos:
            _verify_macos_signature(temporary_path)
        os.replace(temporary_path, target)
    except OSError as exc:
        raise InstallerError(f"could not install {target}: {exc}") from exc
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="release version/tag to install, for example v0.1.0-rc.2")
    parser.add_argument("--allow-prerelease", action="store_true", help="allow the latest prerelease when --version is omitted")
    parser.add_argument("--force", action="store_true", help="replace an existing installed executable")
    parser.add_argument("--dry-run", action="store_true", help="resolve the release and asset without downloading or installing")
    parser.add_argument("--check", "--status", dest="check", action="store_true", help="show whether the local executable is installed")
    parser.add_argument("--skill-root", type=Path, default=skill_root(), help=argparse.SUPPRESS)
    parser.add_argument("--repo", default=DEFAULT_REPOSITORY, help=argparse.SUPPRESS)
    parser.add_argument("--timeout", type=float, default=30.0, help=argparse.SUPPRESS)
    return parser


def run(args: argparse.Namespace) -> int:
    os_name, arch, asset_name = detect_target()
    executable_name = "zotero-go-cli.exe" if os_name == "windows" else "zotero-go-cli"
    target = args.skill_root / "bin" / executable_name
    if args.check:
        print(json.dumps(check_existing(target), indent=2))
        return 0
    if not REPOSITORY_RE.fullmatch(args.repo):
        raise InstallerError(f"invalid GitHub repository: {args.repo!r}")
    releases_url = f"{GITHUB_API}/repos/{args.repo}/releases?per_page=100"
    releases = fetch_json(releases_url, args.timeout)
    if not isinstance(releases, list):
        raise InstallerError("GitHub releases response was not a list")
    release = select_release(releases, args.version, args.allow_prerelease)
    release_version = _release_version(release)
    checksum_name = "SHA256SUMS"
    asset_url = release_asset(release, asset_name)
    checksum_url = release_asset(release, checksum_name)
    details = {"version": "v" + release_version, "platform": f"{os_name}-{arch}", "asset": asset_name, "target": str(target)}
    if args.dry_run:
        print(json.dumps(details, indent=2))
        return 0
    archive = fetch_bytes(asset_url, args.timeout)
    checksums = fetch_bytes(checksum_url, args.timeout).decode("utf-8")
    verify_checksum(archive, checksum_for(checksums, asset_name), asset_name)
    payload = extract_executable(archive, asset_name, executable_name)
    install_executable(payload, target, args.force, verify_macos=os_name == "darwin")
    if os_name != "windows":
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Installed {executable_name} v{release_version} to {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except InstallerError as exc:
        print(f"zotero-use installer: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
