import pytest
import networkx as nx
from graph_engine import resolve_relative_import, build_dependency_graph, get_impacted_files
from parser import get_ast_parser, parse_code, extract_functions, find_functions_using_symbol

# ---------------------------------------------------------------------------
# Existing unit tests
# ---------------------------------------------------------------------------

def test_resolve_relative_import():
    assert resolve_relative_import("src/flask/app.py", ".testing") == "src.flask.testing"
    assert resolve_relative_import("src/flask/app.py", "..utils") == "src.utils"

def test_build_dependency_graph():
    files_data = {
        "file_b.py": b"def compute(): pass",
        "file_a.py": b"from file_b import compute",
        "file_c.py": b"import file_a"
    }
    graph = build_dependency_graph(files_data)
    
    # Nodes
    assert graph.has_node("file_b.py")
    assert graph.has_node("file_a.py")
    assert graph.has_node("file_c.py")
    
    # Edges (supplier -> consumer)
    assert graph.has_edge("file_b.py", "file_a.py")
    assert graph.has_edge("file_a.py", "file_c.py")

def test_get_impacted_files():
    graph = nx.DiGraph()
    graph.add_edge("file_b", "file_a")
    graph.add_edge("file_a", "file_c")
    
    impacted = get_impacted_files(graph, "file_b")
    assert "file_a" in impacted
    assert "file_c" in impacted
    
    impacted_a = get_impacted_files(graph, "file_a")
    assert "file_b" not in impacted_a
    assert "file_c" in impacted_a

# ---------------------------------------------------------------------------
# Tests migrated from scratch_test.py
# ---------------------------------------------------------------------------

def test_shortest_path_finding():
    """Verifies nx.shortest_path works for our graph structure."""
    graph = nx.DiGraph()
    graph.add_edge("file_b.py", "file_a.py")
    
    path = nx.shortest_path(graph, "file_b.py", "file_a.py")
    assert path == ["file_b.py", "file_a.py"]


def test_find_functions_using_symbol_via_graph():
    """Verifies that functions using a specific symbol in consumer files are detected."""
    consumer_code = b"from file_b import compute_value\n\ndef run_calculation():\n    return compute_value(10)\n"
    
    at_risk = find_functions_using_symbol(consumer_code, "compute_value")
    assert "run_calculation" in at_risk
