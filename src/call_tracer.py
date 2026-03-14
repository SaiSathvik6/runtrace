"""
Traces which files and functions are executed during a run,
and which files each file depends on (cross-file call tracking).

Uses sys.settrace. Only files inside project_root are recorded.
"""

import sys
import threading
from typing import Dict, Set, List, Any

from .utils import normalize_path, is_in_project


class CallTracer:
    """
    Records dynamic file-level dependencies:
      - which project files were executed
      - which functions were called in each file (in execution order)
      - which other project files each file called into (depends_on)
    """

    def __init__(self, project_root: str):
        self.project_root = normalize_path(project_root)

        self._functions: Dict[str, List] = {}
        self._functions_seen: Dict[str, Set[str]] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._dependencies_seen: Dict[str, Set[str]] = {}
        self._file_order: List[str] = []
        self._path_cache: Dict[str, bool] = {}
        self._previous_trace = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_project_file(self, path: str) -> bool:
        """Cached is_in_project check to avoid repeated path operations."""
        if path not in self._path_cache:
            self._path_cache[path] = is_in_project(path, self.project_root)
        return self._path_cache[path]

    # ------------------------------------------------------------------
    # sys.settrace hook
    # ------------------------------------------------------------------

    def _trace(self, frame, event, arg):
        """Called by Python for every function-call event."""
        if event != 'call':
            return self._trace

        filename = frame.f_code.co_filename
        if not filename or filename.startswith('<'):
            return None

        filename = normalize_path(filename)
        if not self._is_project_file(filename):
            return None

        func_name = frame.f_code.co_name
        line_no   = frame.f_code.co_firstlineno

        # Ensure this file is tracked (even if only module-level code runs)
        if filename not in self._functions:
            self._functions[filename]          = []
            self._functions_seen[filename]     = set()
            self._dependencies[filename]       = []
            self._dependencies_seen[filename]  = set()
            self._file_order.append(filename)

        # --- Record cross-file dependency ---
        caller_frame = frame.f_back
        try:
            while caller_frame is not None:
                caller_file = caller_frame.f_code.co_filename
                if caller_file and not caller_file.startswith('<'):
                    caller_file = normalize_path(caller_file)
                    if self._is_project_file(caller_file):
                        if caller_file != filename:
                            if caller_file not in self._dependencies:
                                self._dependencies[caller_file]      = []
                                self._dependencies_seen[caller_file] = set()
                                self._functions[caller_file]         = []
                                self._functions_seen[caller_file]    = set()
                                self._file_order.append(caller_file)
                            if filename not in self._dependencies_seen[caller_file]:
                                self._dependencies[caller_file].append(filename)
                                self._dependencies_seen[caller_file].add(filename)
                        break  # stop at the first project-file caller
                caller_frame = caller_frame.f_back
        finally:
            del caller_frame

        # Module-level code: dependency recorded above, skip per-line tracing
        if func_name == '<module>':
            return None

        # --- Record function execution ---
        if func_name not in self._functions_seen[filename]:
            self._functions[filename].append({'name': func_name, 'line': line_no})
            self._functions_seen[filename].add(func_name)

        return self._trace

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        self._previous_trace = sys.gettrace()
        sys.settrace(self._trace)
        threading.settrace(self._trace)

    def stop(self):
        sys.settrace(self._previous_trace)
        threading.settrace(self._previous_trace)
        self._previous_trace = None

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def get_results(self) -> Dict[str, Any]:
        results = {}
        for filepath in self._file_order:
            results[filepath] = {
                "functions": self._functions.get(filepath, []),
                "depends_on": self._dependencies.get(filepath, []),
            }
        return results