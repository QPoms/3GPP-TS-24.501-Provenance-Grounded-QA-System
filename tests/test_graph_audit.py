from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from telecom_agent.graph.audit import audit_graphml


SAMPLE_GRAPHML = """<?xml version="1.0" encoding="utf-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="n0" for="node" attr.name="entity_type" attr.type="string"/>
  <key id="n1" for="node" attr.name="source_file" attr.type="string"/>
  <key id="e0" for="edge" attr.name="keywords" attr.type="string"/>
  <key id="e1" for="edge" attr.name="file_path" attr.type="string"/>
  <graph edgedefault="directed">
    <node id="UE">
      <data key="n0">Concept</data>
      <data key="n1">Rel-19/24_series/24501-j20/graph.graphml</data>
    </node>
    <node id="AMF"><data key="n0">Technology</data></node>
    <edge id="e1" source="UE" target="AMF">
      <data key="e0">Reference&lt;SEP&gt;Condition</data>
      <data key="e1">../Rel-19/24_series/24501-j20.md5.5.1.2</data>
    </edge>
  </graph>
</graphml>
"""


class GraphAuditTests(unittest.TestCase):
    def test_counts_and_spec_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.graphml"
            path.write_text(SAMPLE_GRAPHML, encoding="utf-8")
            result = audit_graphml(path)

        self.assertTrue(result.directed)
        self.assertEqual(result.nodes, 2)
        self.assertEqual(result.edges, 1)
        self.assertEqual(result.matching_spec_nodes, 1)
        self.assertEqual(result.matching_spec_edges, 1)
        self.assertEqual(result.matching_spec_sections, ("5.5.1.2",))
        self.assertEqual(result.relation_keywords["Reference"], 1)
        self.assertEqual(result.relation_keywords["Condition"], 1)


if __name__ == "__main__":
    unittest.main()

