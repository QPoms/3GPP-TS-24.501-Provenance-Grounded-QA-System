"""Command-line entry point for deterministic project operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from telecom_agent.alignment import align_graph_to_chunks
from telecom_agent.agent import AgentTools, OpenAIResponsesAgent
from telecom_agent.config import Settings, create_openai_client
from telecom_agent.evaluation import evaluate_bm25
from telecom_agent.graph import GraphRepository, audit_graphml, build_spec_graph, export_spec_subgraph
from telecom_agent.ingestion import ingest_docx
from telecom_agent.retrieval import (
    BM25Index,
    SentenceTransformerEmbedder,
    VectorIndex,
    load_chunks,
    reciprocal_rank_fusion,
)


DEFAULT_GRAPH = Path("data/tkg/rel19_3gpp_telecom_kg.graphml")
DEFAULT_WORKING_GRAPH = Path("data/processed/graph/ts24501_working_subgraph.graphml")
DEFAULT_CHUNKS = Path("data/processed/chunks/ts24501_v19_2_0.jsonl")
DEFAULT_ALIGNMENTS = Path("data/processed/alignments/ts24501_lexical.jsonl")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kg-agent",
        description="3GPP TS 24.501 provenance-grounded QA tools",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit-graph", help="Audit GraphML structure and TS 24.501 coverage")
    audit.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    audit.add_argument("--spec-token", default="24501")
    audit.add_argument("--source-token", default="24501-j20")
    audit.add_argument("--output", type=Path)

    export = subparsers.add_parser(
        "export-subgraph", help="Export graph elements with explicit specification provenance"
    )
    export.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    export.add_argument("--spec-token", default="24501")
    export.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/graph/ts24501_working_subgraph.graphml"),
    )

    build_graph = subparsers.add_parser(
        "build-graph", help="Build a document-first TS 24.501 GraphML knowledge graph"
    )
    build_graph.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    build_graph.add_argument("--output", type=Path, default=DEFAULT_WORKING_GRAPH)

    ingest = subparsers.add_parser("ingest-spec", help="Parse a TS 24.501 DOCX into JSONL")
    ingest.add_argument("--source", type=Path, required=True)
    ingest.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/chunks/ts24501_v19_2_0.jsonl"),
    )
    ingest.add_argument("--spec-id", default="3GPP TS 24.501")
    ingest.add_argument("--release", default="Rel-19")
    ingest.add_argument("--version", default="19.2.0")
    ingest.add_argument("--max-chars", type=int, default=2400)

    search = subparsers.add_parser("search-spec", help="Search the parsed specification with BM25")
    search.add_argument("query")
    search.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("--section")
    search.add_argument("--max-text-chars", type=int, default=700)

    resolve = subparsers.add_parser("resolve", help="Resolve text to graph entities")
    resolve.add_argument("query")
    resolve.add_argument("--graph", type=Path, default=DEFAULT_WORKING_GRAPH)
    resolve.add_argument("--limit", type=int, default=10)

    inspect = subparsers.add_parser("inspect", help="Inspect a graph entity and its degree")
    inspect.add_argument("entity")
    inspect.add_argument("--graph", type=Path, default=DEFAULT_WORKING_GRAPH)

    neighbors = subparsers.add_parser("neighbors", help="Return bounded neighboring relations")
    neighbors.add_argument("entity")
    neighbors.add_argument("--graph", type=Path, default=DEFAULT_WORKING_GRAPH)
    neighbors.add_argument("--direction", choices=("in", "out", "both"), default="both")
    neighbors.add_argument("--relation")
    neighbors.add_argument("--limit", type=int, default=20)

    path = subparsers.add_parser("path", help="Find bounded graph paths between two entities")
    path.add_argument("source")
    path.add_argument("target")
    path.add_argument("--graph", type=Path, default=DEFAULT_WORKING_GRAPH)
    path.add_argument("--max-hops", type=int, default=3)
    path.add_argument("--limit", type=int, default=5)

    align = subparsers.add_parser("align", help="Align graph items to specification chunks")
    align.add_argument("--graph", type=Path, default=DEFAULT_WORKING_GRAPH)
    align.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    align.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/alignments/ts24501_lexical.jsonl"),
    )
    align.add_argument("--max-per-item", type=int, default=3)

    evaluate = subparsers.add_parser("eval-retrieval", help="Evaluate BM25 section retrieval")
    evaluate.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    evaluate.add_argument(
        "--questions", type=Path, default=Path("examples/retrieval_eval.json")
    )
    evaluate.add_argument("--top-k", type=int, default=5)
    evaluate.add_argument("--output", type=Path)

    build_vector = subparsers.add_parser("build-vector", help="Build the optional local vector index")
    build_vector.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    build_vector.add_argument(
        "--output", type=Path, default=Path("data/indexes/vector/ts24501.npy")
    )
    build_vector.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")

    hybrid = subparsers.add_parser("search-hybrid", help="Search BM25 and vector indexes with RRF")
    hybrid.add_argument("query")
    hybrid.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    hybrid.add_argument("--vectors", type=Path, default=Path("data/indexes/vector/ts24501.npy"))
    hybrid.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    hybrid.add_argument("--top-k", type=int, default=5)
    hybrid.add_argument("--candidate-k", type=int, default=20)
    hybrid.add_argument("--max-text-chars", type=int, default=700)

    ask = subparsers.add_parser("ask", help="Ask the provenance-grounded QA runtime")
    ask.add_argument("question")
    ask.add_argument("--graph", type=Path, default=DEFAULT_WORKING_GRAPH)
    ask.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    ask.add_argument("--alignments", type=Path, default=DEFAULT_ALIGNMENTS)
    ask.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "audit-graph":
        result = audit_graphml(
            args.graph,
            spec_token=args.spec_token,
            source_token=args.source_token,
        )
        rendered = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0
    if args.command == "export-subgraph":
        result = export_spec_subgraph(args.graph, args.output, spec_token=args.spec_token)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "build-graph":
        result = build_spec_graph(load_chunks(args.chunks), args.output)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "ingest-spec":
        result = ingest_docx(
            args.source,
            args.output,
            spec_id=args.spec_id,
            release=args.release,
            version=args.version,
            max_chars=args.max_chars,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "search-spec":
        index = BM25Index(load_chunks(args.chunks))
        hits = index.search(args.query, top_k=args.top_k, section_prefix=args.section)
        values = []
        for hit in hits:
            value = hit.to_dict()
            text = str(value["text"])
            value["text"] = text[: args.max_text_chars] + ("..." if len(text) > args.max_text_chars else "")
            values.append(value)
        print(json.dumps(values, ensure_ascii=False, indent=2))
        return 0
    if args.command in {"resolve", "inspect", "neighbors", "path"}:
        repository = GraphRepository.from_graphml(args.graph)
        if args.command == "resolve":
            values = [match.to_dict() for match in repository.resolve_entities(args.query, limit=args.limit)]
        elif args.command == "inspect":
            match = _best_entity(repository, args.entity)
            values = repository.node_view(match.node.node_id)
            values["resolution"] = {"score": match.score, "method": match.method}
        elif args.command == "neighbors":
            match = _best_entity(repository, args.entity)
            edges = repository.neighbors(
                match.node.node_id,
                direction=args.direction,
                relation=args.relation,
                limit=args.limit,
            )
            values = {
                "resolved_entity": match.to_dict(),
                "edges": [_edge_with_labels(repository, edge) for edge in edges],
            }
        else:
            source = _best_entity(repository, args.source)
            target = _best_entity(repository, args.target)
            paths = repository.find_paths(
                source.node.node_id,
                target.node.node_id,
                max_hops=args.max_hops,
                limit=args.limit,
            )
            values = {
                "source": source.to_dict(),
                "target": target.to_dict(),
                "paths": [
                    [_edge_with_labels(repository, edge) for edge in graph_path]
                    for graph_path in paths
                ],
            }
        print(json.dumps(values, ensure_ascii=False, indent=2))
        return 0
    if args.command == "align":
        result = align_graph_to_chunks(
            GraphRepository.from_graphml(args.graph),
            load_chunks(args.chunks),
            args.output,
            max_per_item=args.max_per_item,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "eval-retrieval":
        result = evaluate_bm25(
            BM25Index(load_chunks(args.chunks)), args.questions, top_k=args.top_k
        )
        rendered = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0
    if args.command == "build-vector":
        chunks = load_chunks(args.chunks)
        index = VectorIndex.build(chunks, SentenceTransformerEmbedder(args.model))
        index.save(args.output)
        print(
            json.dumps(
                {
                    "output": str(args.output.resolve()),
                    "model": args.model,
                    "chunks": len(chunks),
                    "dimensions": int(index.embeddings.shape[1]),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "search-hybrid":
        chunks = load_chunks(args.chunks)
        embedder = SentenceTransformerEmbedder(args.model)
        lexical = BM25Index(chunks).search(args.query, top_k=args.candidate_k)
        vector = VectorIndex.load(args.vectors, chunks).search(
            args.query, embedder, top_k=args.candidate_k
        )
        hits = reciprocal_rank_fusion(lexical, vector, top_k=args.top_k)
        values = []
        for hit in hits:
            text = hit.chunk.text
            values.append(
                {
                    "chunk_id": hit.chunk.chunk_id,
                    "rrf_score": round(hit.score, 6),
                    "lexical_rank": hit.lexical_rank,
                    "vector_rank": hit.vector_rank,
                    "section": hit.chunk.section,
                    "section_title": hit.chunk.section_title,
                    "page_start": hit.chunk.page_start,
                    "text": text[: args.max_text_chars]
                    + ("..." if len(text) > args.max_text_chars else ""),
                }
            )
        print(json.dumps(values, ensure_ascii=False, indent=2))
        return 0
    if args.command == "ask":
        settings = Settings.from_env()
        tools = AgentTools(
            GraphRepository.from_graphml(args.graph),
            load_chunks(args.chunks),
            alignments_path=args.alignments,
        )
        result = OpenAIResponsesAgent(
            create_openai_client(settings),
            settings.openai_model,
            tools,
            max_tool_calls=settings.max_tool_calls,
        ).ask(args.question)
        if args.as_json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(result.answer)
            print("\nTool trace:")
            print(json.dumps([item.to_dict() for item in result.trace], ensure_ascii=False, indent=2))
        return 0
    return 2


def _best_entity(repository: GraphRepository, query: str):
    matches = repository.resolve_entities(query, limit=1)
    if not matches or matches[0].score < 0.5:
        raise ValueError(f"No confident graph entity match for: {query}")
    return matches[0]


def _edge_with_labels(repository: GraphRepository, edge) -> dict[str, object]:
    value = edge.to_dict()
    value["source_label"] = repository.nodes[edge.source].label
    value["target_label"] = repository.nodes[edge.target].label
    return value


if __name__ == "__main__":
    raise SystemExit(main())
