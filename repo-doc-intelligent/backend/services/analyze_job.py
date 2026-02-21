import json
import os
from datetime import datetime
from config import JOBS_DIR
from services.url_validator import validate_github_url
from services.clone import clone_repo
from services.scanner import scan_repo
from services.language_detector import detect_languages
from services.framework_detector import detect_frameworks
from services.symbol_index import build_symbol_index
from services.import_graph import build_import_graph
from services.call_graph import build_call_graph
from services.entry_points import detect_entry_points
from services.diagram import (
    generate_representative_call_flow,
    generate_module_dependency_clean,
    generate_layer_diagram_abstract,
)
from services.graph_metrics import compute_call_graph_metrics
from services.graph_abstraction import should_abstract_call_graph, get_abstract_layer_edges
from services.architecture_inference import infer_architecture, _build_file_to_layer
from services.responsibility_classification import classify_responsibilities
from services.report_data import compute_metrics, get_component_units, get_file_categories
from services.report_template import build_code_wiki_markdown, build_architecture_wiki_markdown
from services.llm_pipeline import run_multi_pass_pipeline, generate_executive_summary
from services.llm_documenter import (
    _folder_structure,
    _dependency_files_content,
    _repo_name_from_url,
)
from services.rag_vectors import build_and_save_vectors


def run_analyze_job(job_id: str, repo_url: str) -> None:
    if not validate_github_url(repo_url):
        raise ValueError("Invalid GitHub URL. Use https://github.com/owner/repo")

    job_dir = os.path.join(JOBS_DIR, job_id)
    repo_dir = os.path.join(job_dir, "repo")
    os.makedirs(job_dir, exist_ok=True)

    try:
        clone_repo(repo_url, repo_dir)
    except RuntimeError as e:
        if os.path.isdir(repo_dir):
            try:
                import shutil
                shutil.rmtree(repo_dir, ignore_errors=True)
            except Exception:
                pass
        raise RuntimeError(str(e)) from e

    file_entries = scan_repo(repo_dir)
    languages = detect_languages(file_entries)
    frameworks = detect_frameworks(repo_dir, file_entries)
    symbol_index = build_symbol_index(file_entries)
    importgraph = build_import_graph(symbol_index, repo_dir)
    callgraph = build_call_graph(file_entries, symbol_index)
    entry_points = detect_entry_points(repo_dir, file_entries, symbol_index)

    with open(os.path.join(job_dir, "callgraph.json"), "w", encoding="utf-8") as f:
        json.dump(callgraph, f, indent=2)
    with open(os.path.join(job_dir, "importgraph.json"), "w", encoding="utf-8") as f:
        json.dump(importgraph, f, indent=2)

    file_to_layer = _build_file_to_layer(importgraph, symbol_index)
    graph_metrics = compute_call_graph_metrics(callgraph, entry_points=entry_points, file_to_layer=file_to_layer)
    with open(os.path.join(job_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(graph_metrics, f, indent=2)

    responsibilities = classify_responsibilities(
        callgraph,
        graph_metrics["in_degree"],
        graph_metrics["out_degree"],
        entry_points,
        file_to_layer,
        symbol_index,
    )
    architecture = {
        "languages": languages,
        "frameworks": frameworks,
        "entry_points": entry_points,
        "symbol_index": symbol_index,
        "responsibilities": responsibilities,
    }
    with open(os.path.join(job_dir, "architecture.json"), "w", encoding="utf-8") as f:
        json.dump(architecture, f, indent=2)

    architecture_summary = infer_architecture(
        callgraph, importgraph, graph_metrics, symbol_index, entry_points, frameworks
    )
    with open(os.path.join(job_dir, "architecture_summary.json"), "w", encoding="utf-8") as f:
        json.dump(architecture_summary, f, indent=2)

    metadata = {
        "file_count": len(file_entries),
        "languages": languages,
        "frameworks": frameworks,
        "entry_points": entry_points,
    }
    with open(os.path.join(job_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    gen_date = datetime.utcnow().strftime("%B %d, %Y")
    metrics_report = compute_metrics(file_entries, symbol_index)
    repo_name = _repo_name_from_url(repo_url)

    use_abstracted = should_abstract_call_graph(
        graph_metrics["node_count"], graph_metrics["edge_count"]
    )
    file_to_layer = _build_file_to_layer(importgraph, symbol_index)
    layer_edges = get_abstract_layer_edges(importgraph, file_to_layer)

    mermaid_layer = generate_layer_diagram_abstract(architecture_summary, layer_edges)
    mermaid_module_dep = generate_module_dependency_clean(
        importgraph, file_to_layer=file_to_layer, max_nodes=20
    )
    mermaid_call_flow = generate_representative_call_flow(
        callgraph, graph_metrics, use_abstracted, max_nodes=15
    )
    if mermaid_layer:
        with open(os.path.join(job_dir, "diagram_layer.mmd"), "w", encoding="utf-8") as f:
            f.write(mermaid_layer)
    if mermaid_module_dep:
        with open(os.path.join(job_dir, "diagram_module.mmd"), "w", encoding="utf-8") as f:
            f.write(mermaid_module_dep)
    if mermaid_call_flow:
        with open(os.path.join(job_dir, "diagram_callflow.mmd"), "w", encoding="utf-8") as f:
            f.write(mermaid_call_flow)
    diagram_mmd = mermaid_layer or mermaid_module_dep or mermaid_call_flow or ""
    if diagram_mmd:
        with open(os.path.join(job_dir, "diagram.mmd"), "w", encoding="utf-8") as f:
            f.write(diagram_mmd)

    try:
        pipeline_result = run_multi_pass_pipeline(
            repo_url=repo_url,
            repo_name=repo_name,
            architecture_summary=architecture_summary,
            metrics=graph_metrics,
            symbol_index=symbol_index,
            callgraph=callgraph,
            importgraph=importgraph,
            entry_points=entry_points,
            frameworks=frameworks,
            responsibilities=responsibilities,
        )
        pass1_md = pipeline_result.get("pass1", "")
        pass2_md = pipeline_result.get("pass2", "")
        pass3_md = pipeline_result.get("pass3", "")

        folder_structure = _folder_structure(repo_dir)
        executive_summary_md = generate_executive_summary(
            repo_url=repo_url,
            repo_name=repo_name,
            entry_points=entry_points,
            frameworks=frameworks,
            architecture_summary=architecture_summary,
            folder_structure=folder_structure,
            file_count=metrics_report.get("total_files", 0),
            total_lines=metrics_report.get("total_lines", 0),
        )

        documentation = build_architecture_wiki_markdown(
            repo_url=repo_url,
            repo_name=repo_name,
            gen_date=gen_date,
            frameworks=frameworks,
            executive_summary_md=executive_summary_md,
            pass1_architecture_md=pass1_md,
            pass2_module_md=pass2_md,
            pass3_executive_md=pass3_md,
            mermaid_call_flow=mermaid_call_flow,
            mermaid_module_dependency=mermaid_module_dep,
            mermaid_layer=mermaid_layer,
            architecture_summary=architecture_summary,
            entry_points=entry_points,
            metrics_report=metrics_report,
            graph_metrics=graph_metrics,
        )
    except ConnectionError as e:
        documentation = f"""# {repo_name}

**Repository**: {repo_url} · **Generated**: {gen_date}

---

Ollama was unavailable for documentation generation: {e}

Run the analysis again with Ollama running (`ollama serve` and `ollama pull qwen2.5-coder:7b`) to generate CodeWiki-level documentation.
"""

    with open(os.path.join(job_dir, "documentation.md"), "w", encoding="utf-8") as f:
        f.write(documentation)

    try:
        build_and_save_vectors(job_dir)
    except Exception:
        pass
