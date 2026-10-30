import os
import unittest
from unittest.mock import patch

from harness import llm_config


class LlmConfigTest(unittest.TestCase):
    def test_defaults_are_openrouter_qwen_pinned_to_deepinfra(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(llm_config.base_url(), "https://openrouter.ai/api/v1")
            self.assertEqual(llm_config.model(), "qwen/qwen3.8-27b")
            self.assertEqual(llm_config.provider(), "DeepInfra")
            self.assertEqual(llm_config.api_key(), "")
            self.assertTrue(llm_config.key_required())

    def test_local_server_needs_no_key_and_no_provider(self):
        with patch.dict(os.environ, {"LLM_BASE_URL": "http://vllm:8000/v1/", "LLM_MODEL": "local/qwen"}, clear=True):
            self.assertEqual(llm_config.base_url(), "http://vllm:8000/v1")
            self.assertEqual(llm_config.model(), "local/qwen")
            self.assertIsNone(llm_config.provider())
            self.assertFalse(llm_config.key_required())

    def test_key_falls_back_to_legacy_names(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "old"}, clear=True):
            self.assertEqual(llm_config.api_key(), "old")
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "old", "LLM_API_KEY": "new"}, clear=True):
            self.assertEqual(llm_config.api_key(), "new")
        with patch.dict(os.environ, {"LLM_PROVIDER": ""}, clear=True):
            self.assertIsNone(llm_config.provider())

    def test_gateway_transport_reads_env(self):
        from harness.llm import HTTPTransport
        with patch.dict(os.environ, {"LLM_BASE_URL": "http://local:1/v1", "LLM_API_KEY": "k", "LLM_MODEL": "m"}, clear=True):
            transport = HTTPTransport()
        self.assertEqual((transport.base_url, transport.api_key, transport.model, transport.provider), ("http://local:1/v1", "k", "m", None))
