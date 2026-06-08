import tree_sitter_languages
from tree_sitter import Parser, Node
from languages import registry

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

def get_provider(language_name: str = None, file_path: str = None):
    """
    Retrieves the corresponding LanguageProvider based on file path or language name.
    Falls back to the first registered provider (Python) if none match.
    """
    if file_path:
        provider = registry.get_provider_for_file(file_path)
        if provider:
            return provider
    if language_name:
        for p in registry.providers:
            if p.language_name == language_name or language_name in p.extensions:
                return p
    # Default fallback to Python provider
    return registry.providers[0]

def extract_functions(code_bytes: bytes, language_name: str = "python", file_path: str = None) -> dict:
    """
    Parses code and extracts function names with their 1-indexed start and end line ranges.
    Returns a dict mapping function name -> (start_line, end_line).
    """
    provider = get_provider(language_name, file_path)
    return provider.extract_functions(code_bytes, file_path)

def find_functions_using_symbol(code_bytes: bytes, symbol: str, language_name: str = "python", file_path: str = None) -> list:
    """
    Scans a file's AST for function definitions that contain the specified symbol name
    inside their body text. Returns a list of function names that are at risk.
    """
    provider = get_provider(language_name, file_path)
    return provider.find_functions_using_symbol(code_bytes, symbol, file_path)

def extract_api_routes(code_bytes: bytes, language_name: str = "python", file_path: str = None) -> dict:
    """
    Parses code to find functions decorated or defined as HTTP route entrypoints.
    Returns a dict mapping function name to {"method": "HTTP_METHOD", "path": "/url/path"}.
    """
    provider = get_provider(language_name, file_path)
    return provider.extract_api_routes(code_bytes, file_path)
