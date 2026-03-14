"""
Import dependency tracer using import hooks
"""

import sys
import ast
import inspect
from typing import Dict, Set, List, Optional
from importlib.abc import MetaPathFinder
from collections import defaultdict

from .utils import is_in_project, normalize_path


class ImportTracer(MetaPathFinder):
    """Traces runtime imports by hooking into the import system."""

    def __init__(self, project_root: str):
        self.project_root = project_root

        # module_name -> [caller_file, ...]
        self.runtime_imports: Dict[str, List[str]] = defaultdict(list)

        # file_path -> set of imported module names (from AST)
        self.static_imports: Dict[str, Set[str]] = defaultdict(set)

        # files already analyzed for static imports
        self.analyzed_files: Set[str] = set()

    def find_spec(self, fullname: str, path: Optional[List[str]] = None, target=None):
        """
        Hook called on every import statement.
        Records which project file triggered the import.
        Returns None to let the normal import system handle loading.
        """
        frame = inspect.currentframe()
        caller_file = None

        try:
            while frame is not None:
                frame = frame.f_back
                if frame and frame.f_code.co_filename:
                    filename = frame.f_code.co_filename
                    if 'importlib' not in filename and '<frozen' not in filename:
                        caller_file = filename
                        break
        finally:
            del frame

        if self.should_trace_import(fullname, caller_file):
            self.runtime_imports[fullname].append(caller_file)

        return None

    def should_trace_import(self, module_name: str, caller_file: Optional[str]) -> bool:
        if not module_name:
            return False
        if module_name.startswith('runtrace'):
            return False
        if caller_file and is_in_project(caller_file, self.project_root):
            return True
        return False

    def analyze_static_imports(self, file_path: str):
        """Parse a Python file with AST to collect its import statements."""
        if file_path in self.analyzed_files:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.static_imports[file_path].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self.static_imports[file_path].add(node.module)
                        for alias in node.names:
                            self.static_imports[file_path].add(f"{node.module}.{alias.name}")
            self.analyzed_files.add(file_path)
        except Exception:
            pass

    def _resolve_module_file(self, module_name: str) -> Optional[str]:
        """
        Resolve a module name to its absolute .py file path via sys.modules.
        Returns None if the module is not loaded or has no file (e.g. built-ins).
        """
        module = sys.modules.get(module_name)
        if module is None:
            return None
        module_file = getattr(module, '__file__', None)
        if not module_file:
            return None
        if module_file.endswith('.pyc'):
            module_file = module_file[:-1]
        return normalize_path(module_file)

    def start(self):
        sys.meta_path.insert(0, self)

    def stop(self):
        if self in sys.meta_path:
            sys.meta_path.remove(self)

    def get_results(self) -> Dict:
        # Analyze all project modules currently loaded for static imports
        for module in list(sys.modules.values()):
            module_file = getattr(module, '__file__', None)
            if not module_file:
                continue
            if module_file.endswith('.pyc'):
                module_file = module_file[:-1]
            module_file = normalize_path(module_file)
            if module_file.endswith('.py') and is_in_project(module_file, self.project_root):
                self.analyze_static_imports(module_file)

        # Unused imports: statically declared but not triggered at runtime
        unused_imports = {}
        for file_path, static_mods in self.static_imports.items():
            runtime_mods = {
                module
                for module, caller_files in self.runtime_imports.items()
                for caller_file in caller_files
                if caller_file == file_path
            }
            unused = static_mods - runtime_mods
            if unused:
                unused_files = [
                    mod_file
                    for mod_name in unused
                    if (mod_file := self._resolve_module_file(mod_name))
                    and is_in_project(mod_file, self.project_root)
                ]
                if unused_files:
                    unused_imports[file_path] = unused_files

        # Runtime-only imports: imported dynamically, no static import statement
        runtime_only_imports = {}
        for module, caller_files in self.runtime_imports.items():
            module_file = self._resolve_module_file(module)
            if not module_file or not is_in_project(module_file, self.project_root):
                continue
            for file_path in caller_files:
                if file_path and file_path not in self.static_imports:
                    continue
                if file_path and module not in self.static_imports.get(file_path, set()):
                    if file_path not in runtime_only_imports:
                        runtime_only_imports[file_path] = []
                    if module_file not in runtime_only_imports[file_path]:
                        runtime_only_imports[file_path].append(module_file)

        return {
            'unused_imports': unused_imports,
            'runtime_only_imports': runtime_only_imports,
        }