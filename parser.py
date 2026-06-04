import tree_sitter_languages
from tree_sitter import Parser, Node

def get_ast_parser(language_name: str = "python") -> Parser:
    """
    Instantiates and returns a Tree-sitter parser for the specified language.
    """
    return tree_sitter_languages.get_parser(language_name)

def parse_code(code_bytes: bytes, parser: Parser) -> Node:
    """
    Parses raw bytes of a file and returns the root node of the AST.
    """
    tree = parser.parse(code_bytes)
    return tree.root_node

def extract_functions(code_bytes: bytes, language_name: str = "python") -> dict:
    """
    Parses code and extracts function names with their 1-indexed start and end line ranges.
    Returns a dict mapping function name -> (start_line, end_line).
    """
    parser = get_ast_parser(language_name)
    root = parse_code(code_bytes, parser)
    
    lang = tree_sitter_languages.get_language(language_name)
    
    # Python-specific query to find function definitions
    if language_name == "python":
        query_str = "(function_definition name: (identifier) @function_name)"
    else:
        # Fallback / placeholder for other languages if needed
        query_str = "(function_definition name: (identifier) @function_name)"
        
    query = lang.query(query_str)
    captures = query.captures(root)
    functions = {}
    
    for node, capture_name in captures:
        if capture_name == "function_name":
            # Extract function name from raw bytes
            func_name = code_bytes[node.start_byte:node.end_byte].decode("utf-8")
            
            # The function definition block is the parent node of the identifier name
            func_def_node = node.parent
            if func_def_node and func_def_node.type == "function_definition":
                start_line = func_def_node.start_point[0] + 1
                end_line = func_def_node.end_point[0] + 1
                functions[func_name] = (start_line, end_line)
                
    return functions

def find_functions_using_symbol(code_bytes: bytes, symbol: str, language_name: str = "python") -> list:
    """
    Scans a file's AST for function definitions that contain the specified symbol name
    inside their body text. Returns a list of function names that are at risk.
    """
    parser = get_ast_parser(language_name)
    root = parse_code(code_bytes, parser)
    lang = tree_sitter_languages.get_language(language_name)
    
    if language_name == "python":
        query_str = "(function_definition name: (identifier) @func_name)"
    else:
        query_str = "(function_definition name: (identifier) @func_name)"
        
    query = lang.query(query_str)
    captures = query.captures(root)
    at_risk = []
    
    for node, capture_name in captures:
        if capture_name == "func_name":
            func_name = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
            # Get the full text of the function definition
            func_def_node = node.parent
            if func_def_node and func_def_node.type == "function_definition":
                func_text = code_bytes[func_def_node.start_byte:func_def_node.end_byte].decode("utf-8", errors="ignore")
                # Simple string matching inside the function body
                if symbol in func_text:
                    at_risk.append(func_name)
                    
    # Maintain insertion order but remove duplicates
    return list(dict.fromkeys(at_risk))
