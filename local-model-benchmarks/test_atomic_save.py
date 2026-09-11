import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import nightly

class AtomicSaveTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)/'result.json'
        nightly.atomic_json(self.path, {'old': True})

    def test_transient_windows_reader_keeps_old_file_then_replaces(self):
        original_replace = nightly.os.replace
        error = PermissionError('temporary sharing conflict')
        error.winerror = 5
        calls = []
        def replace(source, target):
            calls.append(source)
            self.assertEqual(nightly.read_json(target), {'old': True})
            if len(calls) == 1:
                raise error
            return original_replace(source, target)
        with patch('nightly.os.replace', side_effect=replace), patch('nightly.time.sleep') as sleep:
            nightly.atomic_json(self.path, {'new': True})
        self.assertEqual(nightly.read_json(self.path), {'new': True})
        self.assertEqual(len(calls), 2)
        sleep.assert_called_once_with(0.05)
        self.assertFalse(list(self.path.parent.glob('*.tmp')))

    def test_persistent_windows_denial_is_bounded_and_preserves_old_file(self):
        error = PermissionError('persistent denial')
        error.winerror = 5
        with patch('nightly.os.replace', side_effect=error) as replace, patch('nightly.time.sleep') as sleep:
            with self.assertRaises(PermissionError):
                nightly.atomic_json(self.path, {'new': True})
        self.assertEqual(replace.call_count, 6)
        self.assertAlmostEqual(sum(c.args[0] for c in sleep.call_args_list), 1.55)
        self.assertEqual(nightly.read_json(self.path), {'old': True})
        self.assertFalse(list(self.path.parent.glob('*.tmp')))

    def test_other_permission_errors_are_not_retried(self):
        with patch('nightly.os.replace', side_effect=PermissionError('denied')) as replace, patch('nightly.time.sleep') as sleep:
            with self.assertRaises(PermissionError):
                nightly.atomic_json(self.path, {'new': True})
        replace.assert_called_once()
        sleep.assert_not_called()
        self.assertEqual(nightly.read_json(self.path), {'old': True})

if __name__ == '__main__':
    unittest.main()
