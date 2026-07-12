from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from telecom_agent.agent import AgentTools, OpenAIResponsesAgent
from telecom_agent.graph import GraphRepository

from test_bm25 import chunk
from test_graph_audit import SAMPLE_GRAPHML


class FakeResponses:
    def __init__(self, responses):
        self.queue = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        graph_path = Path(self.temp_dir.name) / "graph.graphml"
        graph_path.write_text(SAMPLE_GRAPHML, encoding="utf-8")
        self.tools = AgentTools(
            GraphRepository.from_graphml(graph_path),
            [chunk("c1", "5.5.1.2", "Registration", "The UE initiates registration.")],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_executes_tool_and_continues_response(self) -> None:
        first = SimpleNamespace(
            id="resp-1",
            output=[
                SimpleNamespace(
                    type="function_call",
                    name="search_spec",
                    arguments=json.dumps(
                        {"query": "UE registration", "top_k": 3, "section_prefix": None}
                    ),
                    call_id="call-1",
                )
            ],
            output_text="",
        )
        second = SimpleNamespace(
            id="resp-2",
            output=[],
            output_text=(
                "Answer\nThe UE initiates registration.\n\nCitations\n"
                "3GPP TS 24.501 v19.2.0, section 5.5.1.2, chunk_id: c1"
            ),
        )
        responses = FakeResponses([first, second])
        client = SimpleNamespace(responses=responses)
        result = OpenAIResponsesAgent(client, "test-model", self.tools).ask(
            "When does the UE register?"
        )

        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(result.response_id, "resp-2")
        self.assertEqual(result.trace[0].name, "search_spec")
        self.assertEqual(result.cited_chunk_ids, ("c1",))
        self.assertEqual(responses.calls[1]["previous_response_id"], "resp-1")
        tool_output = json.loads(responses.calls[1]["input"][0]["output"])
        self.assertTrue(tool_output["ok"])
        self.assertEqual(tool_output["result"]["hits"][0]["chunk_id"], "c1")

    def test_extracts_markdown_bold_chunk_id_citations(self) -> None:
        first = SimpleNamespace(
            id="resp-1",
            output=[
                SimpleNamespace(
                    type="function_call",
                    name="search_spec",
                    arguments=json.dumps(
                        {"query": "UE registration", "top_k": 3, "section_prefix": None}
                    ),
                    call_id="call-1",
                )
            ],
            output_text="",
        )
        second = SimpleNamespace(
            id="resp-2",
            output=[],
            output_text=(
                "Citations\n"
                "3GPP TS 24.501 v19.2.0, section 5.5.1.2, chunk_id **c1**"
            ),
        )
        responses = FakeResponses([first, second])
        client = SimpleNamespace(responses=responses)
        result = OpenAIResponsesAgent(client, "test-model", self.tools).ask(
            "When does the UE register?"
        )

        self.assertEqual(result.cited_chunk_ids, ("c1",))

    def test_retries_tool_output_without_previous_response_id_for_stateful_proxy_error(self) -> None:
        first = SimpleNamespace(
            id="resp-1",
            output=[
                SimpleNamespace(
                    id="fc-resource-id",
                    type="function_call",
                    name="search_spec",
                    arguments=json.dumps(
                        {"query": "UE registration", "top_k": 3, "section_prefix": None}
                    ),
                    call_id="call-1",
                    status="completed",
                )
            ],
            output_text="",
        )
        final = SimpleNamespace(
            id="resp-2",
            output=[],
            output_text=(
                "Answer\nThe UE initiates registration.\n\nCitations\n"
                "3GPP TS 24.501 v19.2.0, section 5.5.1.2, chunk_id: c1"
            ),
        )
        responses = FakeResponses(
            [
                first,
                RuntimeError(
                    "The requested item was created under a different Azure OpenAI resource."
                ),
                final,
            ]
        )
        client = SimpleNamespace(responses=responses)
        result = OpenAIResponsesAgent(client, "test-model", self.tools).ask(
            "When does the UE register?"
        )

        self.assertEqual(result.response_id, "resp-2")
        self.assertEqual(len(responses.calls), 3)
        self.assertEqual(responses.calls[1]["previous_response_id"], "resp-1")
        self.assertNotIn("previous_response_id", responses.calls[2])
        retry_input = responses.calls[2]["input"]
        self.assertEqual(retry_input[0]["type"], "function_call")
        self.assertEqual(retry_input[0]["name"], "search_spec")
        self.assertEqual(retry_input[0]["call_id"], "call-1")
        self.assertNotIn("id", retry_input[0])
        self.assertEqual(retry_input[1]["type"], "function_call_output")

    def test_enforces_tool_call_limit(self) -> None:
        call = SimpleNamespace(
            type="function_call",
            name="resolve_entities",
            arguments=json.dumps({"query": "UE", "limit": 3}),
            call_id="call-1",
        )
        response = SimpleNamespace(id="resp-1", output=[call, call], output_text="")
        client = SimpleNamespace(responses=FakeResponses([response]))
        with self.assertRaisesRegex(RuntimeError, "maximum"):
            OpenAIResponsesAgent(client, "test-model", self.tools, max_tool_calls=1).ask("UE")

    def test_rejects_invented_chunk_id(self) -> None:
        response = SimpleNamespace(
            id="resp-1",
            output=[],
            output_text="Citations: chunk_id: invented-chunk",
        )
        client = SimpleNamespace(responses=FakeResponses([response]))
        with self.assertRaisesRegex(RuntimeError, "not returned by tools"):
            OpenAIResponsesAgent(client, "test-model", self.tools).ask("UE")


if __name__ == "__main__":
    unittest.main()
