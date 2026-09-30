# SPDX-License-Identifier: GPL-2.0-or-later
"""Installer transaction tests use arbitrary bytes in temporary directories only."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import phoenix_hud as hud


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="phoenix_installer_test_")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.game = self.root / "game"
        self.package = self.root / "package"
        self.game.mkdir()
        self.package.mkdir()
        self.originals = {}
        self.patched = {}
        rows = []
        for index, name in enumerate(hud.ARCHIVES):
            original = (f"original live archive {index}:\n".encode() + bytes(range(256))) * 3
            patched = (f"prepared experimental archive {index}:\n".encode() + bytes(reversed(range(256)))) * 4
            self.originals[name] = original
            self.patched[name] = patched
            (self.game / name).write_bytes(original)
            (self.package / name).write_bytes(patched)
            rows.append({"name": name,
                         "original_sha256": hashlib.sha256(original).hexdigest(),
                         "patched_sha256": hashlib.sha256(patched).hexdigest()})
        self.manifest = {"version": 1, "experimental": True, "archives": rows}
        (self.package / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf8")
        self.game_check = mock.patch.object(hud, "require_game_closed").start()
        self.addCleanup(mock.patch.stopall)
        mock.patch("sys.stdout", new_callable=io.StringIO).start()

    def snapshot(self):
        return {path.name: path.read_bytes() for path in self.game.iterdir()}

    def assert_original_live_files(self):
        for name in hud.ARCHIVES:
            self.assertEqual((self.game / name).read_bytes(), self.originals[name])

    def assert_no_pending(self):
        for name in hud.ARCHIVES:
            self.assertFalse((self.game / (name + hud.PENDING_SUFFIX)).exists())

    def test_install_then_restore_exact_current_originals(self):
        hud.install(self.game, self.package)
        for name in hud.ARCHIVES:
            self.assertEqual((self.game / name).read_bytes(), self.patched[name])
            self.assertEqual((self.game / (name + hud.BACKUP_SUFFIX)).read_bytes(), self.originals[name])
        self.assert_no_pending()
        hud.restore(self.game, self.package)
        self.assert_original_live_files()
        for name in hud.ARCHIVES:
            self.assertFalse((self.game / (name + hud.BACKUP_SUFFIX)).exists())
        self.assertGreaterEqual(self.game_check.call_count, 3)

    def test_second_package_hash_mismatch_refuses_all_edits(self):
        (self.package / hud.ARCHIVES[1]).write_bytes(b"package changed since preparation")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Pacote alterado"):
            hud.install(self.game, self.package)
        self.assertEqual(self.snapshot(), before)

    def test_second_live_hash_mismatch_refuses_all_edits(self):
        (self.game / hud.ARCHIVES[1]).write_bytes(b"unrelated patch installed later")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "O jogo mudou"):
            hud.install(self.game, self.package)
        self.assertEqual(self.snapshot(), before)

    def test_second_staged_copy_corruption_keeps_both_originals_and_no_backups(self):
        real_copy = hud.shutil.copyfileobj
        copy_count = 0

        def corrupt_second(source, target, length):
            nonlocal copy_count
            copy_count += 1
            real_copy(source, target, length)
            if copy_count == 2:
                target.write(b"simulated bad staged write")

        with mock.patch.object(hud.shutil, "copyfileobj", side_effect=corrupt_second):
            with self.assertRaisesRegex(ValueError, "verificacao da copia"):
                hud.install(self.game, self.package)
        self.assertEqual(self.snapshot(), self.originals)

    def test_package_disappears_after_preflight_leaves_no_orphan_pending(self):
        real_sha256 = hud.sha256
        last_package = self.package / hud.ARCHIVES[1]

        def source_disappears(path):
            digest = real_sha256(path)
            if Path(path) == last_package:
                last_package.unlink()  # Simulate removal after preflight hashes.
            return digest

        with mock.patch.object(hud, "sha256", side_effect=source_disappears):
            with self.assertRaises(FileNotFoundError):
                hud.install(self.game, self.package)
        self.assertEqual(self.snapshot(), self.originals)

    def test_second_file_install_failure_rolls_back_first_and_second(self):
        real_replace = hud.os.replace
        failed = False

        def fail_second(source, destination):
            nonlocal failed
            if Path(source).name == hud.ARCHIVES[1] + hud.PENDING_SUFFIX and not failed:
                failed = True
                # Both originals must remain exact backups when committing fails.
                for name in hud.ARCHIVES:
                    self.assertEqual((self.game / (name + hud.BACKUP_SUFFIX)).read_bytes(), self.originals[name])
                raise OSError("simulated second-file replacement failure")
            return real_replace(source, destination)

        with mock.patch.object(hud.os, "replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "second-file"):
                hud.install(self.game, self.package)
        self.assertTrue(failed)
        self.assertEqual(self.snapshot(), self.originals)

    def test_live_change_after_staging_preserves_external_change(self):
        changed = b"external game update while staging"

        def game_check():
            if self.game_check.call_count == 2:
                (self.game / hud.ARCHIVES[1]).write_bytes(changed)

        self.game_check.side_effect = game_check
        with self.assertRaisesRegex(ValueError, "mudou durante"):
            hud.install(self.game, self.package)
        self.assertEqual((self.game / hud.ARCHIVES[0]).read_bytes(), self.originals[hud.ARCHIVES[0]])
        self.assertEqual((self.game / hud.ARCHIVES[1]).read_bytes(), changed)
        self.assert_no_pending()
        self.assertEqual(len(self.snapshot()), 2)

    def test_restore_preserves_unrelated_changed_live_files_and_all_backups(self):
        hud.install(self.game, self.package)
        (self.game / hud.ARCHIVES[1]).write_bytes(b"another mod after Phoenix")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "alterado depois"):
            hud.restore(self.game, self.package)
        # In particular, the first archive must not already have been restored.
        self.assertEqual(self.snapshot(), before)

    def test_restore_checks_every_backup_before_consuming_any_original(self):
        hud.install(self.game, self.package)
        second_backup = self.game / (hud.ARCHIVES[1] + hud.BACKUP_SUFFIX)
        second_backup.write_bytes(b"corrupt original backup")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Backup diferente"):
            hud.restore(self.game, self.package)
        self.assertEqual(self.snapshot(), before)

    def test_existing_original_backup_never_overwritten_by_install(self):
        backup = self.game / (hud.ARCHIVES[1] + hud.BACKUP_SUFFIX)
        backup.write_bytes(b"prior original: do not overwrite")
        before = self.snapshot()
        with self.assertRaises(FileExistsError):
            hud.install(self.game, self.package)
        self.assertEqual(self.snapshot(), before)

    def test_interrupted_install_missing_live_can_restore(self):
        name = hud.ARCHIVES[0]
        (self.game / name).rename(self.game / (name + hud.BACKUP_SUFFIX))
        hud.restore(self.game, self.package)
        self.assertEqual(self.snapshot(), self.originals)

    def test_second_restore_failure_can_resume_without_losing_originals(self):
        hud.install(self.game, self.package)
        real_replace = hud.os.replace

        def fail_second(source, destination):
            if Path(source).name == hud.ARCHIVES[1] + hud.BACKUP_SUFFIX:
                raise OSError("simulated restore interruption")
            return real_replace(source, destination)

        with mock.patch.object(hud.os, "replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "restore interruption"):
                hud.restore(self.game, self.package)
        for name in hud.ARCHIVES:
            live, backup = self.game / name, self.game / (name + hud.BACKUP_SUFFIX)
            self.assertTrue(live.read_bytes() == self.originals[name] or
                            (backup.exists() and backup.read_bytes() == self.originals[name]))
        hud.restore(self.game, self.package)
        self.assertEqual(self.snapshot(), self.originals)

    def test_restore_cleans_verified_pending_files_from_interrupted_staging(self):
        # A hard interruption after staging leaves no backups, but both pending
        # files exist. Recovery must clear known staged files so reinstall works.
        for name in hud.ARCHIVES:
            (self.game / (name + hud.PENDING_SUFFIX)).write_bytes(self.patched[name])
        hud.restore(self.game, self.package)
        self.assert_original_live_files()
        self.assert_no_pending()
        hud.install(self.game, self.package)

    def test_restore_does_not_delete_unrecognized_pending_content(self):
        # A pending filename alone does not prove ownership of its contents.
        pending = self.game / (hud.ARCHIVES[0] + hud.PENDING_SUFFIX)
        pending.write_bytes(b"unrecognized pending bytes: retain for inspection")
        before = self.snapshot()
        try:
            hud.restore(self.game, self.package)
        except (OSError, ValueError, RuntimeError):
            pass
        self.assertEqual(self.snapshot(), before)

    def v2_package(self):
        new_package = self.root / "package_v2"
        new_package.mkdir()
        manifest = json.loads(json.dumps(self.manifest))
        for row in manifest["archives"]:
            data = self.patched[row["name"]] + b"V2 visual scaling"
            (new_package / row["name"]).write_bytes(data)
            row["patched_sha256"] = hashlib.sha256(data).hexdigest()
        (new_package / "manifest.json").write_text(json.dumps(manifest), encoding="utf8")
        return new_package

    def test_upgrade_then_restore_recovers_original_before_v1(self):
        hud.install(self.game, self.package)
        v2 = self.v2_package()
        hud.upgrade(self.game, v2, self.package)
        for name in hud.ARCHIVES:
            self.assertEqual((self.game / name).read_bytes(), (v2 / name).read_bytes())
            self.assertEqual((self.game / (name + hud.BACKUP_SUFFIX)).read_bytes(), self.originals[name])
        hud.restore(self.game, v2)
        self.assertEqual(self.snapshot(), self.originals)

    def test_bad_v2_package_leaves_v1_untouched(self):
        hud.install(self.game, self.package)
        v2 = self.v2_package()
        (v2 / hud.ARCHIVES[1]).write_bytes(b"corrupt v2")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Pacote novo alterado"):
            hud.upgrade(self.game, v2, self.package)
        self.assertEqual(self.snapshot(), before)

    def test_v2_staging_failure_leaves_true_originals(self):
        hud.install(self.game, self.package)
        v2 = self.v2_package()
        with mock.patch.object(hud.shutil, "copyfileobj", side_effect=OSError("staging failure")):
            with self.assertRaisesRegex(OSError, "staging failure"):
                hud.upgrade(self.game, v2, self.package)
        self.assertEqual(self.snapshot(), self.originals)

    def test_upgrade_different_originals_refused_before_restore(self):
        hud.install(self.game, self.package)
        v2 = self.v2_package()
        manifest = json.loads((v2 / "manifest.json").read_text())
        manifest["archives"][1]["original_sha256"] = "wrong original"
        (v2 / "manifest.json").write_text(json.dumps(manifest))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "mesmos arquivos"):
            hud.upgrade(self.game, v2, self.package)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
