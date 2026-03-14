"""
Main runtime tracer orchestrator
"""

import sys
import os
import runpy
import importlib.util

from .call_tracer import CallTracer
from .import_tracer import ImportTracer
from .reporter import Reporter
from .utils import normalize_path


class RuntimeTracer:
    """Orchestrates tracing of a script or module execution."""

    def __init__(self, project_root: str = "."):
        self.project_root = normalize_path(project_root)
        self.call_tracer = CallTracer(project_root=self.project_root)
        self.import_tracer = ImportTracer(project_root=self.project_root)

    def trace_script(self, script_path: str, args: list = None) -> int:
        """Trace execution of a Python script. Returns the exit code."""
        script_path = normalize_path(script_path)
        script_dir = os.path.dirname(os.path.abspath(script_path))

        old_argv = sys.argv
        old_path = sys.path[:]
        sys.argv = [script_path] + list(args or [])
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)

        self.call_tracer.start()
        self.import_tracer.start()
        exit_code = 0
        try:
            runpy.run_path(script_path, run_name='__main__')
        except SystemExit as e:
            exit_code = e.code if e.code is not None else 0
        finally:
            self.call_tracer.stop()
            self.import_tracer.stop()
            sys.argv = old_argv
            sys.path = old_path

        return exit_code

    def trace_module(self, module_name: str, args: list = None) -> int:
        """
        Trace execution of a Python module (e.g. pytest, unittest).
        Returns the exit code of the module.
        """
        old_argv = sys.argv
        old_path = sys.path[:]

        try:
            spec = importlib.util.find_spec(f'{module_name}.__main__') or \
                   importlib.util.find_spec(module_name)
            argv0 = spec.origin if (spec and spec.origin) else module_name
        except Exception:
            argv0 = module_name

        sys.argv = [argv0] + list(args or [])
        if '' not in sys.path:
            sys.path.insert(0, '')

        self.call_tracer.start()
        self.import_tracer.start()
        exit_code = 0
        try:
            runpy.run_module(module_name, run_name='__main__', alter_sys=True)
        except SystemExit as e:
            exit_code = e.code if e.code is not None else 0
        finally:
            self.call_tracer.stop()
            self.import_tracer.stop()
            sys.argv = old_argv
            sys.path = old_path

        return exit_code

    def generate_reports(self, output_file: str = "./report.json"):
        """Write the JSON report to the given file path."""
        results = {
            'project_root': self.project_root,
            'executed_files': self.call_tracer.get_results(),
            'import_data': self.import_tracer.get_results(),
        }
        reporter = Reporter(results, output_file)
        reporter.generate_json_report()