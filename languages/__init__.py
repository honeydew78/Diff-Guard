import os
from languages.python import PythonLanguageProvider
from languages.javascript import JavaScriptLanguageProvider
from languages.go import GoLanguageProvider

class LanguageRegistry:
    def __init__(self):
        self.providers = [
            PythonLanguageProvider(),
            JavaScriptLanguageProvider(),
            GoLanguageProvider(),
        ]
        self.extension_map = {}
        for provider in self.providers:
            for ext in provider.extensions:
                self.extension_map[ext] = provider

    def get_provider_for_file(self, file_path: str):
        """Finds the correct LanguageProvider based on the file extension."""
        _, ext = os.path.splitext(file_path.lower())
        return self.extension_map.get(ext)

    def is_supported(self, file_path: str) -> bool:
        """Checks if Diff-Guard can parse this file type."""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.extension_map

# Export a global instance
registry = LanguageRegistry()
