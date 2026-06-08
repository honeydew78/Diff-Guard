import os
import tree_sitter_languages
from languages.base import LanguageProvider

class GoLanguageProvider(LanguageProvider):
    
    @property
    def extensions(self) -> list[str]:
        return [".go"]
        
    @property
    def language_name(self) -> str:
        return "go"

    def extract_functions(self, code_bytes: bytes, file_path: str = None) -> dict[str, tuple[int, int]]:
        root = self.parse_code(code_bytes, file_path)
        lang = tree_sitter_languages.get_language(self.language_name)
        
        query_str = """
        (function_declaration name: (identifier) @function_name)
        (method_declaration name: (field_identifier) @function_name)
        """
        query = lang.query(query_str)
        captures = query.captures(root)
        
        functions = {}
        for node, capture_name in captures:
            if capture_name == "function_name":
                func_name = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                func_def_node = node.parent
                if func_def_node and func_def_node.type in ("function_declaration", "method_declaration"):
                    start_line = func_def_node.start_point[0] + 1
                    end_line = func_def_node.end_point[0] + 1
                    functions[func_name] = (start_line, end_line)
                    
        return functions

    def find_functions_using_symbol(self, code_bytes: bytes, symbol: str, file_path: str = None) -> list[str]:
        root = self.parse_code(code_bytes, file_path)
        lang = tree_sitter_languages.get_language(self.language_name)
        
        query_str = """
        (function_declaration name: (identifier) @func_name)
        (method_declaration name: (field_identifier) @func_name)
        """
        query = lang.query(query_str)
        captures = query.captures(root)
        
        at_risk = []
        for node, capture_name in captures:
            if capture_name == "func_name":
                func_name = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                func_def_node = node.parent
                if func_def_node and func_def_node.type in ("function_declaration", "method_declaration"):
                    func_text = code_bytes[func_def_node.start_byte:func_def_node.end_byte].decode("utf-8", errors="ignore")
                    if symbol in func_text:
                        at_risk.append(func_name)
                        
        return list(dict.fromkeys(at_risk))

    def extract_imports(self, code_bytes: bytes, file_path: str = None) -> list[str]:
        root = self.parse_code(code_bytes, file_path)
        lang = tree_sitter_languages.get_language(self.language_name)
        
        query_str = "(import_spec path: _ @import_path)"
        query = lang.query(query_str)
        captures = query.captures(root)
        
        imports = []
        for node, _ in captures:
            raw_import = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore").strip("\"'`")
            imports.append(raw_import)
            
        return imports

    def resolve_import_to_file(self, imported_ref: str, current_file: str, files_data: dict[str, bytes]) -> list[str]:
        # Try to find module path from go.mod
        module_name = ""
        go_mod_path = next((k for k in files_data.keys() if os.path.basename(k) == "go.mod"), None)
        if go_mod_path:
            content = files_data[go_mod_path].decode("utf-8", errors="ignore")
            for line in content.splitlines():
                if line.strip().startswith("module "):
                    parts = line.strip().split()
                    if len(parts) > 1:
                        module_name = parts[1]
                    break

        suffix = ""
        if module_name and imported_ref.startswith(module_name + "/"):
            suffix = imported_ref[len(module_name) + 1:]
        elif module_name and imported_ref == module_name:
            suffix = "."  # Root module level
        else:
            # Fallback if no module name matches, treat last segment as potential package dir name
            suffix = imported_ref.split("/")[-1]

        matching_files = []
        for f in files_data.keys():
            if f.endswith(".go"):
                dir_path = os.path.dirname(f.replace("\\", "/"))
                # Match suffix exactly, or if suffix is package directory
                if dir_path == suffix or dir_path.endswith("/" + suffix) or (suffix == "." and dir_path == ""):
                    matching_files.append(f)
                    
        return matching_files

    def extract_api_routes(self, code_bytes: bytes, file_path: str = None) -> dict[str, dict]:
        root = self.parse_code(code_bytes, file_path)
        lang = tree_sitter_languages.get_language(self.language_name)
        
        query_str = """
        (call_expression
          function: (selector_expression
            field: (field_identifier) @method)
          arguments: (argument_list [(interpreted_string_literal) (raw_string_literal)] @path (identifier) @func_name))
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
                current_path = text.strip("\"'`")
            elif capture_name == "func_name":
                if current_method in ("GET", "POST", "PUT", "DELETE", "PATCH") and current_path:
                    routes[text] = {"method": current_method, "path": current_path}
                current_method = None
                current_path = None
                
        return routes
