import networkx as nx
from parser import get_ast_parser, parse_code, extract_functions
import tree_sitter_languages

# Mock data
base_repo = {
    "file_b.py": b"def compute_value(x):\n    return x * 2\n",
    "file_a.py": b"from file_b import compute_value\n\ndef run_calculation():\n    return compute_value(10)\n"
}

# 1. Test Path finding
graph = nx.DiGraph()
graph.add_edge("file_b.py", "file_a.py")
print("Shortest path to file_a.py:", nx.shortest_path(graph, "file_b.py", "file_a.py"))

# 2. Test finding functions at risk
def find_functions_using_symbol(code_bytes: bytes, symbol: str) -> list:
    parser = get_ast_parser("python")
    root = parse_code(code_bytes, parser)
    lang = tree_sitter_languages.get_language("python")
    
    query_str = "(function_definition name: (identifier) @func_name body: (block) @body)"
    query = lang.query(query_str)
    
    at_risk = []
    for node, name in query.captures(root):
        if name == "func_name":
            func_name = code_bytes[node.start_byte:node.end_byte].decode("utf-8")
            # The body is the next capture, but let's just get the parent function_definition's text
            func_text = code_bytes[node.parent.start_byte:node.parent.end_byte].decode("utf-8")
            if symbol in func_text:
                at_risk.append(func_name)
    return at_risk

print("Functions in file_a.py using 'compute_value':", find_functions_using_symbol(base_repo["file_a.py"], "compute_value"))
