import os
import tree_sitter_languages
from languages.base import LanguageProvider

class PythonLanguageProvider(LanguageProvider):
    
    @property
    def extensions(self) -> list[str]:
        return [".py"]
        
    @property
    def language_name(self) -> str:
        return "python"

    def extract_functions(self, code_bytes: bytes, file_path: str = None) -> dict[str, tuple[int, int]]:
        root = self.parse_code(code_bytes, file_path)
        lang = tree_sitter_languages.get_language(self.language_name)
        
        query_str = "(function_definition name: (identifier) @function_name)"
        query = lang.query(query_str)
        captures = query.captures(root)
        
        functions = {}
        for node, capture_name in captures:
            if capture_name == "function_name":
                func_name = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                func_def_node = node.parent
                if func_def_node and func_def_node.type == "function_definition":
                    start_line = func_def_node.start_point[0] + 1
                    end_line = func_def_node.end_point[0] + 1
                    functions[func_name] = (start_line, end_line)
                    
        return functions

    def find_functions_using_symbol(self, code_bytes: bytes, symbol: str, file_path: str = None) -> list[str]:
        root = self.parse_code(code_bytes, file_path)
        lang = tree_sitter_languages.get_language(self.language_name)
        
        query_str = "(function_definition name: (identifier) @func_name)"
        query = lang.query(query_str)
        captures = query.captures(root)
        
        at_risk = []
        for node, capture_name in captures:
            if capture_name == "func_name":
                func_name = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                func_def_node = node.parent
                if func_def_node and func_def_node.type == "function_definition":
                    func_text = code_bytes[func_def_node.start_byte:func_def_node.end_byte].decode("utf-8", errors="ignore")
                    if symbol in func_text:
                        at_risk.append(func_name)
                        
        return list(dict.fromkeys(at_risk))

    def extract_imports(self, code_bytes: bytes, file_path: str = None) -> list[str]:
        root = self.parse_code(code_bytes, file_path)
        lang = tree_sitter_languages.get_language(self.language_name)
        
        query_str = """
        (import_statement name: (dotted_name) @import_name)
        (import_from_statement module_name: [(dotted_name) (relative_import)] @import_from_name)
        """
        query = lang.query(query_str)
        captures = query.captures(root)
        
        imports = []
        for node, _ in captures:
            raw_import = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
            imports.append(raw_import)
            
        return imports

    def resolve_import_to_file(self, imported_ref: str, current_file: str, files_data: dict[str, bytes]) -> list[str]:
        from graph_engine import resolve_relative_import, find_matching_file

        # Build Python module map
        module_to_file = {}
        for f in files_data.keys():
            if f.endswith(".py"):
                normalized = f.replace("\\", "/")[:-3]
                if normalized.endswith("/__init__"):
                    normalized = normalized[:-9]
                mod = normalized.replace("/", ".")
                if mod.startswith("."):
                    mod = mod.lstrip(".")
                module_to_file[mod] = f

        resolved_module = resolve_relative_import(current_file, imported_ref)
        dep_file = find_matching_file(resolved_module, module_to_file)
        if dep_file:
            return [dep_file]
        return []

    def extract_api_routes(self, code_bytes: bytes, file_path: str = None) -> dict[str, dict]:
        root = self.parse_code(code_bytes, file_path)
        lang = tree_sitter_languages.get_language(self.language_name)
        
        query_str = """
        (decorated_definition
          (decorator
            (call
              function: (attribute
                attribute: (identifier) @method)
              arguments: (argument_list
                (string) @path)))
          (function_definition
            name: (identifier) @func_name))
        """
        query = lang.query(query_str)
        captures = query.captures(root)
        
        routes = {}
        current_method = None
        current_path = None
        
        for node, capture_name in captures:
            text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
            if capture_name == "method":
                current_method = text.upper()
            elif capture_name == "path":
                current_path = text.strip("\"'")
            elif capture_name == "func_name":
                if current_method and current_path:
                    routes[text] = {"method": current_method, "path": current_path}
                current_method = None
                current_path = None
                
        return routes
