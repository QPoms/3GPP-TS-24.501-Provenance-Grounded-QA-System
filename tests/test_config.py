from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from telecom_agent.config import Settings


class SettingsTests(unittest.TestCase):
    def test_from_env_loads_utf8_bom_dotenv_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\ufeffOPENAI_API_KEY=test-key\n"
                "OPENAI_MODEL=test-model\n"
                "OPENAI_BASE_URL=https://example.test/v1\n",
                encoding="utf-8",
            )
            old_cwd = Path.cwd()
            old_values = {
                name: os.environ.get(name)
                for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL")
            }
            for name in old_values:
                os.environ.pop(name, None)
            try:
                os.chdir(temp_dir)
                settings = Settings.from_env()
            finally:
                os.chdir(old_cwd)
                for name, value in old_values.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value

        self.assertEqual(settings.openai_api_key, "test-key")
        self.assertEqual(settings.openai_model, "test-model")
        self.assertEqual(settings.openai_base_url, "https://example.test/v1")
