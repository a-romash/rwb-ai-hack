import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from contracts.stage import ContractError


class ManifestTest(unittest.TestCase):
    def test_all_manifest_files_protected_and_wrong_hash_rejected(self):
        from app.test_integrity import accept_manifest
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'product').mkdir(); (root/'reports').mkdir()
            (root/'product'/'helper.txt').write_text('protected')
            manifest=root/'reports/tests.json'
            manifest.write_text(json.dumps({'schema_version':1,'hashes':{'product/helper.txt':hashlib.sha256(b'protected').hexdigest()}}))
            session=MagicMock()
            accept_manifest(session,'run',root,'reports/tests.json')
            self.assertEqual(session.add.call_args.args[0].path,'product/helper.txt')
            (root/'product'/'helper.txt').write_text('changed')
            with self.assertRaises(ContractError):
                accept_manifest(session,'run',root,'reports/tests.json')
