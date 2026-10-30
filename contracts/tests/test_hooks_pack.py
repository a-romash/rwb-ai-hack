import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from contracts.hooks import HooksFile, load_hooks
from contracts.pack import load_pack

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "contracts" / "fixtures" / "tickets" / "hooks.json"
PACK = ROOT / "templates" / "product" / "pack.yaml"


class HooksPackTests(unittest.TestCase):
    def test_fixture_and_manifest(self):
        hooks = load_hooks(FIXTURE)
        pack = load_pack(PACK)
        self.assertEqual(
            [hook.id for hook in hooks],
            ["SlaDeadline", "ResolutionRequired"],
        )
        self.assertIn("mobile/app/src/main/java/app/hooks", pack.write_roots)
        build = pack.targets.backend.build
        self.assertIsNotNone(build)
        assert build is not None
        self.assertEqual(build[0], "dotnet")
        self.assertIn("backend/tests", pack.readonly)

    def test_missing_signature_rejected(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        del raw[0]["signature"]
        with self.assertRaises(ValidationError):
            HooksFile.model_validate(raw)
