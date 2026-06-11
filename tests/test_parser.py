import pytest
import difflib
from parser import extract_functions, find_functions_using_symbol
from graph_engine import build_dependency_graph, get_impacted_files

# ---------------------------------------------------------------------------
# Existing unit tests
# ---------------------------------------------------------------------------

def test_extract_functions():
    code = b"""
def foo():
    pass

class Bar:
    def method(self):
        pass

async def async_foo():
    pass
"""
    funcs = extract_functions(code, "python")
    
    assert "foo" in funcs
    assert "method" in funcs
    assert "async_foo" in funcs
    
    assert funcs["foo"] == (2, 3)
    assert funcs["method"] == (6, 7)
    assert funcs["async_foo"] == (9, 10)

def test_find_functions_using_symbol():
    code = b"""
def outer():
    modified_target()
    
def safe_func():
    pass
"""
    at_risk = find_functions_using_symbol(code, "modified_target", "python")
    assert "outer" in at_risk
    assert "safe_func" not in at_risk

# ---------------------------------------------------------------------------
# Integration tests (migrated from sandbox_test.py)
# ---------------------------------------------------------------------------

# Mock base and head repository snapshots
_base_repo = {
    "file_b.py": b"""
def compute_value(x):
    return x * 2
""",
    "file_a.py": b"""
from file_b import compute_value

def run_calculation():
    return compute_value(10)
"""
}

_head_repo = {
    "file_b.py": b"""
def compute_value(x):
    # Modified comment and behavior inside function
    print("Computing value...")
    return x * 3
""",
    "file_a.py": b"""
from file_b import compute_value

def run_calculation():
    return compute_value(10)
"""
}


def _get_changed_line_numbers(base_code: bytes, head_code: bytes) -> tuple[set[int], set[int]]:
    """Local helper replicating the diff utility for tests."""
    base_lines = base_code.decode("utf-8", errors="replace").splitlines()
    head_lines = head_code.decode("utf-8", errors="replace").splitlines()
    
    sm = difflib.SequenceMatcher(None, base_lines, head_lines)
    base_changed = set()
    head_changed = set()
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            for idx in range(i1, i2):
                base_changed.add(idx + 1)
        if tag in ("replace", "insert"):
            for idx in range(j1, j2):
                head_changed.add(idx + 1)
                
    return base_changed, head_changed


def _run_sandbox_analysis():
    """Helper that runs the sandbox pipeline and returns all computed data."""
    import networkx as nx
    
    graph = build_dependency_graph(_base_repo)
    
    modified_files = []
    modified_functions = {}
    
    for file_path, base_code in _base_repo.items():
        if file_path not in _head_repo:
            modified_files.append(file_path)
            modified_functions[file_path] = [("All", "deleted")]
            continue
            
        head_code = _head_repo[file_path]
        if base_code != head_code:
            base_funcs = extract_functions(base_code, "python")
            head_funcs = extract_functions(head_code, "python")
            base_changed, head_changed = _get_changed_line_numbers(base_code, head_code)
            
            changed_funcs = []
            for f_name, (start_b, end_b) in base_funcs.items():
                if f_name not in head_funcs:
                    changed_funcs.append((f_name, "deleted"))
                else:
                    start_h, end_h = head_funcs[f_name]
                    b_intersect = any(line in base_changed for line in range(start_b, end_b + 1))
                    h_intersect = any(line in head_changed for line in range(start_h, end_h + 1))
                    if b_intersect or h_intersect:
                        changed_funcs.append((f_name, "modified"))
                        
            for f_name, (start_h, end_h) in head_funcs.items():
                if f_name not in base_funcs:
                    changed_funcs.append((f_name, "added"))
                    
            if changed_funcs:
                modified_files.append(file_path)
                modified_functions[file_path] = changed_funcs
    
    all_impacted_files = set()
    impact_paths = {}
    at_risk_functions = {}
    
    for m_file in modified_files:
        impacted = get_impacted_files(graph, m_file)
        all_impacted_files.update(impacted)
        paths_dict = {}
        for imp_file in impacted:
            paths_dict[imp_file] = nx.shortest_path(graph, m_file, imp_file)
        impact_paths[m_file] = paths_dict
        
    for m_file in modified_files:
        changed_entities = modified_functions[m_file]
        for imp_file, path in impact_paths.get(m_file, {}).items():
            if len(path) == 2:
                code_bytes = _head_repo.get(imp_file)
                if code_bytes:
                    for c_func_name, c_type in changed_entities:
                        if c_type in ("modified", "deleted"):
                            found_funcs = find_functions_using_symbol(code_bytes, c_func_name)
                            if found_funcs:
                                if imp_file not in at_risk_functions:
                                    at_risk_functions[imp_file] = []
                                at_risk_functions[imp_file].extend(found_funcs)
    
    return modified_files, modified_functions, all_impacted_files, impact_paths, at_risk_functions


def test_sandbox_modified_file_detection():
    """file_b.py should be detected as modified."""
    modified_files, _, _, _, _ = _run_sandbox_analysis()
    assert "file_b.py" in modified_files


def test_sandbox_compute_value_modified():
    """compute_value should be detected as a modified function in file_b.py."""
    _, modified_functions, _, _, _ = _run_sandbox_analysis()
    file_b_changes = [f[0] for f in modified_functions["file_b.py"]]
    assert "compute_value" in file_b_changes


def test_sandbox_blast_radius():
    """file_a.py should be in the blast radius of file_b.py."""
    _, _, all_impacted_files, _, _ = _run_sandbox_analysis()
    assert "file_a.py" in all_impacted_files


def test_sandbox_impact_path():
    """The correct dependency path should be detected."""
    _, _, _, impact_paths, _ = _run_sandbox_analysis()
    assert impact_paths["file_b.py"]["file_a.py"] == ["file_b.py", "file_a.py"]


def test_sandbox_at_risk_function():
    """run_calculation should be marked at risk inside file_a.py."""
    _, _, _, _, at_risk_functions = _run_sandbox_analysis()
    assert "run_calculation" in at_risk_functions["file_a.py"]
