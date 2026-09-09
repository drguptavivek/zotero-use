import importlib.util
import io
import os
import stat
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_cli.py"
SPEC = importlib.util.spec_from_file_location("install_cli", SCRIPT)
INSTALL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(INSTALL)


class InstallerTests(unittest.TestCase):
    def test_target_matrix(self):
        self.assertEqual(
            INSTALL.detect_target("darwin", "arm64"),
            ("darwin", "arm64", "zotero-go-cli-darwin-arm64.tar.gz"),
        )
        self.assertEqual(
            INSTALL.detect_target("linux", "x86_64"),
            ("linux", "amd64", "zotero-go-cli-linux-amd64.tar.gz"),
        )
        self.assertEqual(
            INSTALL.detect_target("win32", "AMD64"),
            ("windows", "amd64", "zotero-go-cli-windows-amd64.zip"),
        )
        with self.assertRaises(INSTALL.InstallerError):
            INSTALL.detect_target("darwin", "x86_64")

    def test_release_selection_excludes_prerelease_by_default(self):
        releases = [
            {"tag_name": "v0.2.0-rc.1", "prerelease": True, "draft": False},
            {"tag_name": "v0.1.0", "prerelease": False, "draft": False},
            {"tag_name": "v0.3.0", "prerelease": False, "draft": True},
        ]
        self.assertEqual(INSTALL.select_release(releases)["tag_name"], "v0.1.0")
        self.assertEqual(INSTALL.select_release(releases, allow_prerelease=True)["tag_name"], "v0.2.0-rc.1")
        self.assertEqual(INSTALL.select_release(releases, version="v0.2.0-rc.1")["tag_name"], "v0.2.0-rc.1")
        with self.assertRaises(INSTALL.InstallerError):
            INSTALL.select_release(releases, version="v0.3.0")

    def test_checksum_parser_and_verification(self):
        payload = b"signed test binary"
        digest = INSTALL.hashlib.sha256(payload).hexdigest()
        checksums = f"{digest}  other-file.zip\n{digest}  zotero-go-cli-linux-amd64.tar.gz\n"
        expected = INSTALL.checksum_for(checksums, "zotero-go-cli-linux-amd64.tar.gz")
        INSTALL.verify_checksum(payload, expected, "zotero-go-cli-linux-amd64.tar.gz")
        with self.assertRaises(INSTALL.InstallerError):
            INSTALL.verify_checksum(b"tampered", expected, "zotero-go-cli-linux-amd64.tar.gz")

    def _tar(self, name="zotero-use/bin/zotero-go-cli", payload=b"binary"):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        return stream.getvalue()

    def _zip(self, name="zotero-use/bin/zotero-go-cli.exe", payload=b"binary"):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr(name, payload)
        return stream.getvalue()

    def test_extracts_only_expected_executable_from_tar_and_zip(self):
        self.assertEqual(
            INSTALL.extract_executable(self._tar(), "zotero-go-cli-linux-amd64.tar.gz", "zotero-go-cli"),
            b"binary",
        )
        self.assertEqual(
            INSTALL.extract_executable(self._zip(), "zotero-go-cli-windows-amd64.zip", "zotero-go-cli.exe"),
            b"binary",
        )

    def test_archive_traversal_and_symlink_are_rejected(self):
        with self.assertRaises(INSTALL.InstallerError):
            INSTALL.extract_executable(self._tar("zotero-use/bin/../evil", b"x"), "zotero-go-cli-linux-amd64.tar.gz", "zotero-go-cli")

        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            link = tarfile.TarInfo("zotero-use/bin/zotero-go-cli")
            link.type = tarfile.SYMTYPE
            link.linkname = "/tmp/evil"
            archive.addfile(link)
        with self.assertRaises(INSTALL.InstallerError):
            INSTALL.extract_executable(stream.getvalue(), "zotero-go-cli-linux-amd64.tar.gz", "zotero-go-cli")

    def test_install_is_atomic_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "bin" / "zotero-go-cli"
            INSTALL.install_executable(b"first", target)
            self.assertEqual(target.read_bytes(), b"first")
            self.assertTrue(target.stat().st_mode & stat.S_IXUSR)
            with self.assertRaises(INSTALL.InstallerError):
                INSTALL.install_executable(b"second", target)
            INSTALL.install_executable(b"second", target, force=True)
            self.assertEqual(target.read_bytes(), b"second")
            self.assertEqual(list(target.parent.glob(".*")), [])

    def test_macos_signature_requires_expected_team(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "zotero-go-cli"
            target.write_bytes(b"binary")
            valid = mock.Mock(stdout="", stderr=(
                "Authority=Developer ID Application: ALL INDIA INSTITUTE OF MEDICAL SCIENCES (2M5AS49SM7)\n"
                "TeamIdentifier=2M5AS49SM7\n"
            ))
            with mock.patch.object(INSTALL, "CODESIGN_PATH", Path(__file__)), mock.patch.object(
                INSTALL.subprocess, "run", side_effect=[mock.Mock(stdout="", stderr=""), valid]
            ):
                INSTALL._verify_macos_signature(target)

            wrong_team = mock.Mock(
                stdout="",
                stderr="Authority=Developer ID Application: Someone Else (BADTEAM123)\nTeamIdentifier=BADTEAM123\n",
            )
            with mock.patch.object(INSTALL, "CODESIGN_PATH", Path(__file__)), mock.patch.object(
                INSTALL.subprocess, "run", side_effect=[mock.Mock(stdout="", stderr=""), wrong_team]
            ), self.assertRaises(INSTALL.InstallerError):
                INSTALL._verify_macos_signature(target)

    def test_macos_signature_fails_closed_without_codesign(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "codesign"
            with mock.patch.object(INSTALL, "CODESIGN_PATH", missing), self.assertRaises(INSTALL.InstallerError):
                INSTALL._verify_macos_signature(Path(directory) / "zotero-go-cli")

    def test_dry_run_resolves_release_without_downloading_asset(self):
        release = {
            "tag_name": "v0.1.0",
            "draft": False,
            "prerelease": False,
            "assets": [
                {"name": "zotero-go-cli-darwin-arm64.tar.gz", "browser_download_url": "https://example.invalid/cli"},
                {"name": "SHA256SUMS", "browser_download_url": "https://example.invalid/sums"},
            ],
        }
        args = INSTALL.build_parser().parse_args(["--dry-run", "--skill-root", "/tmp/skill"])
        with mock.patch.object(INSTALL, "detect_target", return_value=("darwin", "arm64", "zotero-go-cli-darwin-arm64.tar.gz")), mock.patch.object(INSTALL, "fetch_json", return_value=[release]), mock.patch.object(INSTALL, "fetch_bytes") as fetch:
            self.assertEqual(INSTALL.run(args), 0)
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
