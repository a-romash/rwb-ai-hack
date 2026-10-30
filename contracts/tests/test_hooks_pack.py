import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from contracts.hooks import HooksFile, load_hooks
from contracts.pack import load_pack

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "contracts" / "fixtures" / "tickets" / "hooks.json"
PACK = ROOT / "templates" / "product" / "pack.json"


class HooksPackTests(unittest.TestCase):
    def test_fixture_and_manifest(self):
        hooks = load_hooks(FIXTURE)
        pack = load_pack(PACK)
        self.assertEqual(
            [hook.id for hook in hooks],
            ["SlaDeadline", "ResolutionRequired"],
        )
        self.assertIn("mobile-web/src/app/custom", pack.write_roots)
        self.assertIsNotNone(pack.targets.pwa)
        build = pack.targets.backend.build
        self.assertIsNotNone(build)
        assert build is not None
        self.assertEqual(build[0], "dotnet")
        self.assertIn("backend/tests", pack.readonly)

    def test_sandbox_accepts_manifest(self):
        """Every target command is a non-empty list the Docker sandbox can run."""
        pack = load_pack(PACK).model_dump(exclude_none=True)
        for name, target in pack["targets"].items():
            for kind in ("restore", "build", "test", "e2e", "up", "smoke", "down"):
                if kind in target:
                    self.assertTrue(target[kind] and all(isinstance(v, str) and v for v in target[kind]), (name, kind))

    def test_missing_signature_rejected(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        del raw[0]["signature"]
        with self.assertRaises(ValidationError):
            HooksFile.model_validate(raw)
