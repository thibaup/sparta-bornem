"""Recovery and asset lifecycle tests for the 1.5.2 release."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import config
import utils


class ReleaseRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='editor-release-regression-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.first, self.second = self.base / 'first.html', self.base / 'second.html'
        self.first.write_bytes(b'first original')
        self.second.write_bytes(b'second original')

    def outputs(self):
        return {str(self.first): b'first changed', str(self.second): b'second changed'}

    def test_batch_success_commits_all_outputs_and_removes_recovery_journal(self):
        utils.atomic_write_many(self.outputs(), base_dir=self.base)
        self.assertEqual(self.first.read_bytes(), b'first changed')
        self.assertEqual(self.second.read_bytes(), b'second changed')
        self.assertEqual(list((self.base / '.editor-recovery').iterdir()), [])

    def test_second_file_failure_rolls_back_first_file(self):
        replace = os.replace
        def fail_second(source, destination):
            if str(source).endswith('.staged') and Path(destination) == self.second:
                raise PermissionError('second file locked')
            return replace(source, destination)
        with patch('utils.os.replace', side_effect=fail_second), self.assertRaises(PermissionError):
            utils.atomic_write_many(self.outputs(), base_dir=self.base)
        self.assertEqual(self.first.read_bytes(), b'first original')
        self.assertEqual(self.second.read_bytes(), b'second original')
        self.assertEqual(list((self.base / '.editor-recovery').iterdir()), [])

    def test_failed_rollback_retains_backups_then_next_startup_recovers(self):
        replace, write = os.replace, utils.atomic_write_bytes
        def fail_second(source, destination):
            if str(source).endswith('.staged') and Path(destination) == self.second:
                raise PermissionError('second file locked')
            return replace(source, destination)
        def fail_restore(path, content):
            if Path(path) == self.first:
                raise PermissionError('first file locked during rollback')
            return write(path, content)
        with patch('utils.os.replace', side_effect=fail_second), patch('utils.atomic_write_bytes', side_effect=fail_restore):
            with self.assertRaises(utils.EditorTransactionError) as failure:
                utils.atomic_write_many(self.outputs(), base_dir=self.base)
        journals = list((self.base / '.editor-recovery').glob('*/journal.json'))
        self.assertEqual(len(journals), 1)
        self.assertIn(str(journals[0].parent), str(failure.exception))
        self.assertEqual((journals[0].parent / '0.backup').read_bytes(), b'first original')
        utils.recover_editor_transactions(self.base)
        self.assertEqual(self.first.read_bytes(), b'first original')
        self.assertEqual(self.second.read_bytes(), b'second original')
        self.assertEqual(list((self.base / '.editor-recovery').iterdir()), [])

    def test_process_interruption_is_recovered_before_loading_next_session(self):
        replace = os.replace
        def interrupt_second(source, destination):
            if str(source).endswith('.staged') and Path(destination) == self.second:
                raise KeyboardInterrupt('simulated process interruption')
            return replace(source, destination)
        with patch('utils.os.replace', side_effect=interrupt_second), self.assertRaises(KeyboardInterrupt):
            utils.atomic_write_many(self.outputs(), base_dir=self.base)
        self.assertEqual(self.first.read_bytes(), b'first changed')
        utils.recover_editor_transactions(self.base)
        self.assertEqual(self.first.read_bytes(), b'first original')
        self.assertEqual(self.second.read_bytes(), b'second original')

    def test_recovery_does_not_overwrite_external_changes(self):
        replace = os.replace
        def interrupt_second(source, destination):
            if str(source).endswith('.staged') and Path(destination) == self.second:
                raise KeyboardInterrupt()
            return replace(source, destination)
        with patch('utils.os.replace', side_effect=interrupt_second), self.assertRaises(KeyboardInterrupt):
            utils.atomic_write_many(self.outputs(), base_dir=self.base)
        self.first.write_bytes(b'external change after interruption')
        with self.assertRaises(utils.EditorTransactionError):
            utils.recover_editor_transactions(self.base)
        self.assertEqual(self.first.read_bytes(), b'external change after interruption')
        self.assertTrue(list((self.base / '.editor-recovery').glob('*/journal.json')))

    def test_transaction_rejects_targets_outside_site_before_modifying_anything(self):
        outside = self.base.parent / (self.base.name + '-outside.html')
        with self.assertRaises(utils.EditorTransactionError):
            utils.atomic_write_many({str(outside): b'bad'}, base_dir=self.base)
        self.assertFalse(outside.exists())
        self.assertEqual(self.first.read_bytes(), b'first original')

    def test_pending_asset_cleanup_preserves_drafts_and_preexisting_assets(self):
        source = self.base / 'source.jpg'
        source.write_bytes(b'image')
        preexisting = self.base / 'images' / 'photo.jpg'
        preexisting.parent.mkdir()
        preexisting.write_bytes(b'original image')
        app = SimpleNamespace(tab_managers={})
        owner = SimpleNamespace(app=app, data={})
        with patch.object(config, 'APP_BASE_DIR', str(self.base)):
            created = Path(utils.copy_new_asset(source, preexisting, owner=owner))
            self.assertNotEqual(created, preexisting)
            owner.data = {'image': '/images/' + created.name}
            self.assertEqual(utils.cleanup_pending_assets(owner), [])
            self.assertTrue(created.exists())
            owner.data = {}
            self.assertEqual(utils.cleanup_pending_assets(owner), [])
            self.assertFalse(created.exists())
            self.assertEqual(preexisting.read_bytes(), b'original image')

    def test_metadata_save_transfers_asset_ownership_and_prevents_future_cleanup(self):
        source = self.base / 'source.jpg'
        source.write_bytes(b'image')
        app = SimpleNamespace(tab_managers={})
        owner = SimpleNamespace(app=app, downloads=[])
        with patch.object(config, 'APP_BASE_DIR', str(self.base)):
            created = Path(utils.copy_new_asset(source, self.base / 'docs' / 'photo.jpg', owner=owner))
            (self.base / 'downloads.html').write_text(f'<a href="/docs/{created.name}">Download</a>', encoding='utf-8')
            self.assertEqual(utils.cleanup_pending_assets(owner), [])
            self.assertFalse(app._pending_assets)
            (self.base / 'downloads.html').write_text('', encoding='utf-8')
            utils.cleanup_pending_assets(owner, include_drafts=False)
            self.assertTrue(created.exists())

    def test_external_asset_modification_is_never_deleted(self):
        source = self.base / 'source.jpg'
        source.write_bytes(b'image')
        owner = SimpleNamespace(app=SimpleNamespace(tab_managers={}), data={})
        with patch.object(config, 'APP_BASE_DIR', str(self.base)):
            created = Path(utils.copy_new_asset(source, self.base / 'images' / 'photo.jpg', owner=owner))
            created.write_bytes(b'changed externally')
            utils.cleanup_pending_assets(owner, include_drafts=False)
            self.assertEqual(created.read_bytes(), b'changed externally')

    def test_separate_document_save_preserves_other_pending_draft(self):
        source = self.base / 'source.pdf'
        source.write_bytes(b'document')
        owner = SimpleNamespace(app=SimpleNamespace(tab_managers={}), reports_data={}, downloads=[])
        with patch.object(config, 'APP_BASE_DIR', str(self.base)):
            created = Path(utils.copy_new_asset(source, self.base / 'docs' / 'download.pdf', owner=owner))
            owner.downloads = [{'path': '/docs/' + created.name}]
            utils.remember_editor_state(owner, owner.reports_data, '_saved_reports')
            self.assertTrue(created.exists())
            self.assertTrue(owner.app._pending_assets)
            utils.cleanup_pending_assets(owner, include_drafts=False)
            self.assertFalse(created.exists())


if __name__ == '__main__':
    unittest.main()
