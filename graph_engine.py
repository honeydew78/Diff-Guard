import networkx as nx
from languages import registry

def resolve_relative_import(current_file_path: str, import_from_name: str) -> str:
    """
    Resolves a relative import (e.g. '.module' or '..module') to a full module path
    based on the current file path.
    """
    dots_count = 0
    for char in import_from_name:
        if char == '.':
            dots_count += 1
        else:
            break
            
    if dots_count == 0:
        return import_from_name
        
    remainder = import_from_name[dots_count:]
    parts = current_file_path.replace("\\", "/").split("/")
    parts = parts[:-1]  # Remove filename, keep directories
    
    levels_up = dots_count - 1
    if levels_up > 0:
        parts = parts[:-levels_up]
        
    if remainder:
        parts.append(remainder)
        
    return ".".join(parts)

def find_matching_file(imported_module: str, module_to_file: dict) -> str:
    """
    Finds the file path that corresponds to the imported module name.
    Matches exact names and sub-modules (e.g. imported 'pkg.mod.sub' matches 'pkg/mod.py').
    """
    if imported_module in module_to_file:
        return module_to_file[imported_module]
        
    # Match parent modules (e.g., imported_module="pkg.mod.sub" -> matches key "pkg.mod")
    for mod, file_path in module_to_file.items():
        if imported_module.startswith(mod + "."):
            return file_path
            
    return None

def build_dependency_graph(files_data: dict) -> nx.DiGraph:
    """
    Builds a directed dependency graph.
    files_data: dict mapping file_path (str) -> code_bytes (bytes)
    
    Edges point from the dependency target (supplier) to the file importing it (consumer).
    """
    graph = nx.DiGraph()
    
    # 1. Register supported files as nodes
    for file_path in files_data.keys():
        if registry.is_supported(file_path):
            graph.add_node(file_path)

    # 2. Extract and resolve imports using registered language providers
    for file_path, code_bytes in files_data.items():
        if not registry.is_supported(file_path):
            continue
            
        provider = registry.get_provider_for_file(file_path)
        if not provider:
            continue
            
        raw_imports = provider.extract_imports(code_bytes, file_path)
        for imp in raw_imports:
            dep_files = provider.resolve_import_to_file(imp, file_path, files_data)
            for dep_file in dep_files:
                if dep_file and dep_file != file_path:
                    # Add edge from supplier -> consumer
                    graph.add_edge(dep_file, file_path)
                    
    return graph

def get_impacted_files(graph: nx.DiGraph, changed_file: str) -> set:
    """
    Finds all files upstream that import/depend on the changed_file.
    """
    if not graph.has_node(changed_file):
        return set()
    return nx.descendants(graph, changed_file)
