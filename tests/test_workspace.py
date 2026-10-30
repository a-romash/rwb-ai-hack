import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from contracts.stage import ContractError
from harness.workspace import create_workspace, commit, describe, restore

class WorkspaceTest(unittest.TestCase):
    def test_isolation_commit_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = create_workspace(root, uuid4(), uuid4(), 'требования')
            (a / 'x').write_text('один')
            rev = commit(a, 'stage')
            (a / 'x').write_text('два')
            (a / 'new').write_text('new')
            restore(a, rev)
            self.assertEqual((a / 'x').read_text(), 'один')
            self.assertFalse((a / 'new').exists())
            self.assertEqual(describe(a, 'x')[1], len('один'.encode()))
            with self.assertRaises(ContractError):
                describe(a, '../outside')

    def test_directory_hash_skips_restored_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = create_workspace(Path(tmp), uuid4(), uuid4(), 'требования')
            (a / 'product' / 'web').mkdir(parents=True)
            (a / 'product' / 'web' / 'app.ts').write_text('code')
            before = describe(a, 'product')
            (a / 'product' / 'web' / 'node_modules' / 'pkg').mkdir(parents=True)
            (a / 'product' / 'web' / 'node_modules' / 'pkg' / 'index.js').write_text('dependency')
            (a / 'product' / '.publish').mkdir()
            (a / 'product' / '.publish' / 'App.Api.dll').write_bytes(b'compiled')
            self.assertEqual(describe(a, 'product'), before)
