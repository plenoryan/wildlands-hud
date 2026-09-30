# SPDX-License-Identifier: GPL-2.0-or-later
"""Portable app controller tests use small synthetic archives in a temp folder."""
import hashlib
import importlib
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
import zipfile

import portable_hud as app
import build_portable
import phoenix_hud as backend


class PortableControllerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="portable_hud_test_")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.game = self.root / "game"
        self.cache = self.root / "cache"
        self.game.mkdir()
        self.originals = {name: ("original " + name).encode() for name in app.ARCHIVES}
        for name, data in self.originals.items():
            (self.game / name).write_bytes(data)
        mock.patch.object(backend, "require_game_closed").start()
        mock.patch("sys.stdout", new_callable=io.StringIO).start()
        self.addCleanup(mock.patch.stopall)
        self.prepares = []

        def prepare(variant):
            def operation(game, package, previous=None):
                self.prepares.append((variant, game, package, previous))
                package.mkdir(parents=True)
                rows = []
                for name in app.ARCHIVES:
                    patched = (variant + " patched " + name).encode()
                    (package / name).write_bytes(patched)
                    rows.append({"name": name, "original_sha256": hashlib.sha256(self.originals[name]).hexdigest(),
                                 "patched_sha256": hashlib.sha256(patched).hexdigest()})
                (package / "manifest.json").write_text(json.dumps({"version": 1, "archives": rows}), encoding="utf8")
            return operation

        self.hud = types.SimpleNamespace(**{name: getattr(backend, name) for name in
            ("require_game_closed", "load_manifest", "sha256", "install", "restore", "upgrade", "BACKUP_SUFFIX")})
        self.hud.prepare_v3 = prepare("v3")
        self.hud.prepare_v4 = prepare("v4")
        mock.patch.object(app.importlib, "import_module", return_value=self.hud).start()

    def run_app(self, action, **options):
        return app.run_operation(action, self.game, cache=self.cache, emit=lambda text: None, **options)

    def test_local_prepare_install_and_restore_roundtrip(self):
        result = self.run_app("install")
        self.assertEqual(result["variant"], "v4")
        self.assertIsNone(self.prepares[0][3])
        self.assertTrue((self.cache / "active.json").is_file())
        for name in app.ARCHIVES:
            self.assertEqual((self.game / (name + backend.BACKUP_SUFFIX)).read_bytes(), self.originals[name])
            self.assertTrue((self.game / name).read_bytes().startswith(b"v4 patched"))
        self.run_app("restore")
        for name in app.ARCHIVES:
            self.assertEqual((self.game / name).read_bytes(), self.originals[name])

    def test_upgrade_from_v3_retains_exact_pre_mod_originals(self):
        old = self.run_app("install", variant="v3")
        new = self.run_app("install", variant="v4")
        self.assertEqual(self.prepares[-1][3], Path(old["package"]))
        self.assertNotEqual(old["package"], new["package"])
        for name in app.ARCHIVES:
            self.assertEqual((self.game / (name + backend.BACKUP_SUFFIX)).read_bytes(), self.originals[name])
            self.assertTrue((self.game / name).read_bytes().startswith(b"v4 patched"))

    def test_missing_v4_never_silently_applies_v3(self):
        del self.hud.prepare_v4
        with self.assertRaisesRegex(RuntimeError, "não inclui a V4"):
            self.run_app("install")
        self.assertEqual(self.prepares, [])
        for name in app.ARCHIVES:
            self.assertEqual((self.game / name).read_bytes(), self.originals[name])
        self.run_app("install", variant="v3")
        self.assertEqual(self.prepares[0][0], "v3")

    def test_existing_backup_without_matching_manifest_is_preserved(self):
        name = app.ARCHIVES[0]
        backup = self.game / (name + backend.BACKUP_SUFFIX)
        backup.write_bytes(b"unrecognized earlier backup")
        with self.assertRaisesRegex(ValueError, "instalação anterior"):
            self.run_app("install")
        self.assertEqual(backup.read_bytes(), b"unrecognized earlier backup")
        self.assertEqual(self.prepares, [])

    def test_restore_refuses_external_live_changes(self):
        self.run_app("install")
        (self.game / app.ARCHIVES[1]).write_bytes(b"unrelated newer modification")
        before = {p.name: p.read_bytes() for p in self.game.iterdir()}
        with self.assertRaises(ValueError):
            self.run_app("restore")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.game.iterdir()})

    def test_pending_receipt_recovers_commit_before_active_receipt(self):
        real = app._write_receipt

        def fail_active(path, *args):
            if path.name == "active.json":
                raise OSError("simulated app interruption after install")
            return real(path, *args)

        with mock.patch.object(app, "_write_receipt", side_effect=fail_active):
            with self.assertRaisesRegex(OSError, "app interruption"):
                self.run_app("install")
        self.assertTrue((self.cache / "pending.json").is_file())
        self.run_app("restore")
        for name in app.ARCHIVES:
            self.assertEqual((self.game / name).read_bytes(), self.originals[name])

    def test_recovery_allows_absent_live_file_with_original_backup(self):
        self.run_app("install")
        (self.game / app.ARCHIVES[0]).unlink()
        self.run_app("restore")
        for name in app.ARCHIVES:
            self.assertEqual((self.game / name).read_bytes(), self.originals[name])

    def test_unknown_prepared_resource_failure_never_installs(self):
        self.hud.prepare_v4 = mock.Mock(side_effect=ValueError("unsupported resource hash"))
        self.hud.install = mock.Mock()
        with self.assertRaisesRegex(ValueError, "resource hash"):
            self.run_app("install")
        self.hud.install.assert_not_called()

    def test_partial_staging_keeps_recovery_receipt_and_originals(self):
        self.cache.mkdir()
        receipt = self.cache / "pending.json"
        journal = b'{"version": 1, "recovery": "preserve this interrupted-copy record"}'
        receipt.write_bytes(journal)
        staged = self.game / (app.ARCHIVES[0] + ".phoenixhud.pending")
        staged.write_bytes(b"partial interrupted copy")
        with self.assertRaisesRegex(ValueError, "interrompida"):
            self.run_app("install")
        self.assertEqual(receipt.read_bytes(), journal)
        self.assertEqual(staged.read_bytes(), b"partial interrupted copy")
        self.assertEqual(self.prepares, [])
        for name in app.ARCHIVES:
            self.assertEqual((self.game / name).read_bytes(), self.originals[name])

    def test_cache_is_user_local_and_rejects_the_game_directory(self):
        with mock.patch.dict(app.os.environ, {"LOCALAPPDATA": str(self.root / "profile")}):
            path = app.default_cache(self.game)
            self.assertTrue(str(path).startswith(str(self.root / "profile")))
            self.assertEqual(path.parent, self.root / "profile" / "WildlandsHUD")
        with self.assertRaisesRegex(ValueError, "fora da pasta"):
            app.run_operation("install", self.game, cache=self.game / "cache", emit=lambda text: None)


class PortableDistributionTests(unittest.TestCase):
    def test_source_allowlist_never_contains_game_or_analysis_files(self):
        files = build_portable.source_files()
        self.assertIn("phoenix_friendly_patch.py", {path.name for path in files})
        self.assertIn("minilzo.dll", {path.name for path in files})
        self.assertFalse(any(".forge" in path.name or path.name.startswith("test_") for path in files))
        self.assertTrue(all(path.suffix in (".py", ".dll") for path in files))

    def test_shareable_source_zip_contains_code_and_licenses_only(self):
        with tempfile.TemporaryDirectory(prefix="portable_hud_dist_test_") as directory:
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                archive = build_portable.build(Path(directory), "source")
            with zipfile.ZipFile(archive) as zipped:
                names = zipped.namelist()
                self.assertTrue(any(name.endswith("portable_hud.py") for name in names))
                self.assertTrue(any(name.endswith("COPYING") for name in names))
                self.assertTrue(any(name.endswith("Abrir_WildlandsHUD.cmd") for name in names))
                self.assertFalse(any(".forge" in name or "analysis_" in name or "prepared_" in name for name in names))
                self.assertLess(archive.stat().st_size, 2 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
