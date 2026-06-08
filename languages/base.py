from abc import ABC, abstractmethod
from tree_sitter import Parser, Node
import tree_sitter_languages

class LanguageProvider(ABC):
    
    @property
    @abstractmethod
    def extensions(self) -> list[str]:
        """Returns the list of file extensions supported by this language (e.g. ['.py'])."""
        pass
        
    @property
    @abstractmethod
    def language_name(self) -> str:
        """Returns the tree-sitter language identifier (e.g. 'python', 'javascript')."""
        pass

    def get_parser(self, file_path: str = None) -> Parser:
        """Instantiates and returns the Tree-sitter parser for this language."""
        return tree_sitter_languages.get_parser(self.language_name)

    def parse_code(self, code_bytes: bytes, file_path: str = None) -> Node:
        """Parses raw bytes of a file and returns the root node of the AST."""
        parser = self.get_parser(file_path)
        tree = parser.parse(code_bytes)
        return tree.root_node

    @abstractmethod
    def extract_functions(self, code_bytes: bytes, file_path: str = None) -> dict[str, tuple[int, int]]:
        """
        Parses file and returns a dict mapping:
        function_name -> (start_line_1_indexed, end_line_1_indexed)
        """
        pass

    @abstractmethod
    def find_functions_using_symbol(self, code_bytes: bytes, symbol: str, file_path: str = None) -> list[str]:
        """
        Scans a file's AST for function definitions that contain the specified symbol name
        inside their body text. Returns a list of function names that are at risk.
        """
        pass

    @abstractmethod
    def extract_imports(self, code_bytes: bytes, file_path: str = None) -> list[str]:
        """
        Extracts raw import statements / dependency targets from the file.
        """
        pass

    @abstractmethod
    def resolve_import_to_file(self, imported_ref: str, current_file: str, files_data: dict[str, bytes]) -> list[str]:
        """
        Resolves a raw import string to actual file paths in the workspace.
        Returns a list of matching file paths (since a package import in Go can map to multiple files).
        """
        pass

    @abstractmethod
    def extract_api_routes(self, code_bytes: bytes, file_path: str = None) -> dict[str, dict]:
        """
        Parses code to find functions decorated or defined as HTTP route entrypoints.
        Returns a dict mapping function name to {"method": "HTTP_METHOD", "path": "/url/path"}.
        """
        pass
