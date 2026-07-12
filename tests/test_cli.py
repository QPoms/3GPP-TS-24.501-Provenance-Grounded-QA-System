from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from telecom_agent.cli import main

from test_bm25 import chunk


class CliTests(unittest.TestCase):
    def test_build_graph_command_outputs_document_built_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            chunks_path = Path(temp_dir) / "chunks.jsonl"
            graph_path = Path(temp_dir) / "graph.graphml"
            chunks = [
                chunk(
                    "c1",
                    "4.4.3.2",
                    "Replay protection",
                    "Replay protection shall be supported for received NAS messages.",
                )
            ]
            chunks_path.write_text(
                "\n".join(json.dumps(item.to_dict()) for item in chunks) + "\n",
                encoding="utf-8",
            )

            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "build-graph",
                        "--chunks",
                        str(chunks_path),
                        "--output",
                        str(graph_path),
                    ]
                )

            summary = json.loads(buffer.getvalue())
            self.assertTrue(graph_path.exists())

        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["chunks"], 1)
        self.assertGreaterEqual(summary["nodes"], 2)


if __name__ == "__main__":
    unittest.main()
