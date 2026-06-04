from graph_engine import build_dependency_graph, get_impacted_files
from parser import extract_functions

# Step 6 Action Step 1 & 2: Define mock base repository snapshot
base_repo = {
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

# Step 6 Action Step 3: Define mock head repository snapshot with modifications in file_b.py
head_repo = {
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

def get_function_source(code_bytes: bytes, start_line: int, end_line: int) -> bytes:
    lines = code_bytes.splitlines()
    return b"\n".join(lines[start_line - 1 : end_line])

def run_sandbox_integration_test():
    print("Initializing Sandbox Integration Test...\n")
    
    # 1. Build base dependency graph
    print("[1/4] Building dependency graph from Base snapshot...")
    graph = build_dependency_graph(base_repo)
    print(f"Registered Modules: {list(graph.nodes)}")
    print(f"Dependency Edges (Supplier -> Consumer): {list(graph.edges)}")
    
    # 2. Check for modified functions
    print("\n[2/4] Scanning for modified functions between Base and Head...")
    modified_files = []
    modified_functions = {}
    
    for file_path, base_code in base_repo.items():
        if file_path not in head_repo:
            print(f"  - File deleted: {file_path}")
            modified_files.append(file_path)
            modified_functions[file_path] = [("All", "deleted")]
            continue
            
        head_code = head_repo[file_path]
        if base_code != head_code:
            base_funcs = extract_functions(base_code, "python")
            head_funcs = extract_functions(head_code, "python")
            
            changed_funcs = []
            
            # Check for modifications or deletions
            for f_name, range_b in base_funcs.items():
                if f_name not in head_funcs:
                    changed_funcs.append((f_name, "deleted"))
                else:
                    range_h = head_funcs[f_name]
                    if get_function_source(base_code, *range_b) != get_function_source(head_code, *range_h):
                        changed_funcs.append((f_name, "modified"))
                        
            # Check for additions
            for f_name in head_funcs:
                if f_name not in base_funcs:
                    changed_funcs.append((f_name, "added"))
                    
            if changed_funcs:
                print(f"  - Modified file: {file_path} (Detected: {changed_funcs})")
                modified_files.append(file_path)
                modified_functions[file_path] = changed_funcs

    # 3. Resolve architectural blast radius via Graph solver
    print("\n[3/4] Tracing architectural blast radius...")
    all_impacted_files = set()
    for m_file in modified_files:
        impacted = get_impacted_files(graph, m_file)
        all_impacted_files.update(impacted)
        print(f"  - Changes in '{m_file}' impact upstream: {impacted}")
        
    # 4. Assertions and verification
    print("\n[4/4] Running assertions verification...")
    
    # Assert file_b.py is detected as modified
    assert "file_b.py" in modified_files, "file_b.py should be detected as modified"
    # Assert compute_value is the modified function
    file_b_changes = [f[0] for f in modified_functions["file_b.py"]]
    assert "compute_value" in file_b_changes, "compute_value should be detected as modified"
    
    # Assert that file_a.py is impacted by changes in file_b.py
    assert "file_a.py" in all_impacted_files, "file_a.py should be in the blast radius of file_b.py"
    
    print("\n✓ Sandbox Integration Test passed successfully!")

if __name__ == "__main__":
    run_sandbox_integration_test()
