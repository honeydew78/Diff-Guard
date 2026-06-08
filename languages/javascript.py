import os
import tree_sitter_languages
from tree_sitter import Parser
from languages.base import LanguageProvider

class JavaScriptLanguageProvider(LanguageProvider):
    
    @property
    def extensions(self) -> list[str]:
        return [".js", ".jsx", ".ts", ".tsx"]
        
    @property
    def language_name(self) -> str:
        return "javascript"

    def get_parser(self, file_path: str = None) -> Parser:
        if file_path:
            _, ext = os.path.splitext(file_path.lower())
            if ext == ".ts":
                return tree_sitter_languages.get_parser("typescript")
            elif ext == ".tsx":
                return tree_sitter_languages.get_parser("tsx")
        return tree_sitter_languages.get_parser("javascript")

    def get_tree_sitter_language(self, file_path: str = None):
        if file_path:
            _, ext = os.path.splitext(file_path.lower())
            if ext == ".ts":
                return tree_sitter_languages.get_language("typescript")
            elif ext == ".tsx":
                return tree_sitter_languages.get_language("tsx")
        return tree_sitter_languages.get_language("javascript")

    def extract_functions(self, code_bytes: bytes, file_path: str = None) -> dict[str, tuple[int, int]]:
        root = self.parse_code(code_bytes, file_path)
        lang = self.get_tree_sitter_language(file_path)
        
        query_str = """
        (function_declaration name: (identifier) @function_name)
        (method_definition name: (property_identifier) @function_name)
        (variable_declarator name: (identifier) @function_name value: [(arrow_function) (function)])
        """
        query = lang.query(query_str)
        captures = query.captures(root)
        
        functions = {}
        for node, capture_name in captures:
            if capture_name == "function_name":
                func_name = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                
                # Resolve the node range
                func_def_node = node.parent
                if func_def_node:
                    if func_def_node.parent and func_def_node.parent.type in ("variable_declaration", "lexical_declaration"):
                        func_def_node = func_def_node.parent
                        
                    start_line = func_def_node.start_point[0] + 1
                    end_line = func_def_node.end_point[0] + 1
                    functions[func_name] = (start_line, end_line)
                    
        return functions

    def find_functions_using_symbol(self, code_bytes: bytes, symbol: str, file_path: str = None) -> list[str]:
        root = self.parse_code(code_bytes, file_path)
        lang = self.get_tree_sitter_language(file_path)
        
        query_str = """
        (function_declaration name: (identifier) @func_name)
        (method_definition name: (property_identifier) @func_name)
        (variable_declarator name: (identifier) @func_name value: [(arrow_function) (function)])
        """
        query = lang.query(query_str)
        captures = query.captures(root)
        
        at_risk = []
        for node, capture_name in captures:
            if capture_name == "func_name":
                func_name = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                
                func_def_node = node.parent
                if func_def_node:
                    if func_def_node.parent and func_def_node.parent.type in ("variable_declaration", "lexical_declaration"):
                        func_def_node = func_def_node.parent
                        
                    func_text = code_bytes[func_def_node.start_byte:func_def_node.end_byte].decode("utf-8", errors="ignore")
                    if symbol in func_text:
                        at_risk.append(func_name)
                        
        return list(dict.fromkeys(at_risk))

    def extract_imports(self, code_bytes: bytes, file_path: str = None) -> list[str]:
        root = self.parse_code(code_bytes, file_path)
        lang = self.get_tree_sitter_language(file_path)
        
        query_str = """
        (import_statement source: (string) @import_path)
        (export_statement source: (string) @import_path)
        (call_expression
          function: [(identifier) (import)] @require_or_import
          arguments: (arguments (string) @import_path))
        """
        query = lang.query(query_str)
        captures = query.captures(root)
        
        imports = []
        for node, capture_name in captures:
            if capture_name == "import_path":
                # Validate if require_name/import check is needed
                parent = node.parent
                is_valid = False
                while parent:
                    if parent.type in ("import_statement", "export_statement"):
                        is_valid = True
                        break
                    if parent.type == "call_expression":
                        func_node = parent.child_by_field_name("function")
                        if func_node:
                            if func_node.type == "import":
                                is_valid = True
                            elif func_node.type == "identifier":
                                func_name = code_bytes[func_node.start_byte:func_node.end_byte].decode("utf-8", errors="ignore")
                                if func_name == "require":
                                    is_valid = True
                        break
                    parent = parent.parent
                    
                if is_valid:
                    path_str = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore").strip("\"'")
                    imports.append(path_str)
                    
        return imports

    def resolve_import_to_file(self, imported_ref: str, current_file: str, files_data: dict[str, bytes]) -> list[str]:
        if not (imported_ref.startswith("./") or imported_ref.startswith("../")):
            return []  # Ignore absolute / library imports
            
        current_dir = os.path.dirname(current_file.replace("\\", "/"))
        raw_target = os.path.normpath(os.path.join(current_dir, imported_ref)).replace("\\", "/")
        
        # Candidate extensions and index structures
        candidates = [
            raw_target,
            raw_target + ".js",
            raw_target + ".ts",
            raw_target + ".jsx",
            raw_target + ".tsx",
            os.path.join(raw_target, "index.js").replace("\\", "/"),
            os.path.join(raw_target, "index.ts").replace("\\", "/"),
            os.path.join(raw_target, "index.jsx").replace("\\", "/"),
            os.path.join(raw_target, "index.tsx").replace("\\", "/"),
        ]
        
        # Build normalized files set for quick lookup
        normalized_files = {f.replace("\\", "/"): f for f in files_data.keys()}
        
        for candidate in candidates:
            if candidate in normalized_files:
                return [normalized_files[candidate]]
                
        return []

    def extract_api_routes(self, code_bytes: bytes, file_path: str = None) -> dict[str, dict]:
        root = self.parse_code(code_bytes, file_path)
        lang = self.get_tree_sitter_language(file_path)
        
        query_str = """
        (call_expression
          function: (member_expression
            property: (property_identifier) @method)
          arguments: (arguments (string) @path (identifier) @func_name))
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
                if current_method in ("GET", "POST", "PUT", "DELETE", "PATCH") and current_path:
                    routes[text] = {"method": current_method, "path": current_path}
                current_method = None
                current_path = None
                
        return routes
