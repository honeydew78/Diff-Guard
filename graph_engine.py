import networkx as nx
import tree_sitter_languages
from parser import get_ast_parser, parse_code

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
    module_to_file = {}
    
    # 1. Register file paths as nodes and build module map
    for file_path in files_data.keys():
        graph.add_node(file_path)
        
        normalized = file_path.replace("\\", "/")
        if normalized.endswith(".py"):
            normalized = normalized[:-3]
        if normalized.endswith("/__init__"):
            normalized = normalized[:-9]
            
        module_name = normalized.replace("/", ".")
        # Strip leading dots or directory indicators
        if module_name.startswith("."):
            module_name = module_name.lstrip(".")
            
        module_to_file[module_name] = file_path

    # 2. Extract and resolve imports
    parser = get_ast_parser("python")
    import_query_str = """
    (import_statement name: (dotted_name) @import_name)
    (import_from_statement module_name: [(dotted_name) (relative_import)] @import_from_name)
    """
    lang = tree_sitter_languages.get_language("python")
    query = lang.query(import_query_str)
    
    for file_path, code_bytes in files_data.items():
        root = parse_code(code_bytes, parser)
        captures = query.captures(root)
        
        for node, capture_name in captures:
            raw_import = code_bytes[node.start_byte:node.end_byte].decode("utf-8")
            
            if capture_name == "import_from_name" and raw_import.startswith("."):
                resolved_module = resolve_relative_import(file_path, raw_import)
            else:
                resolved_module = raw_import
                
            dep_file = find_matching_file(resolved_module, module_to_file)
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
