"""
Generates the dependency report from traced execution data.
"""

import json
import os
from typing import Dict, Any


class Reporter:
    """Writes the JSON report to a direct file path."""

    def __init__(self, results: Dict[str, Any], output_path: str):
        self.results = results
        self.output_path = output_path

    def generate_json_report(self):
        """Write the dependency report directly to output_path."""
        # Ensure parent directory exists
        parent = os.path.dirname(os.path.abspath(self.output_path))
        os.makedirs(parent, exist_ok=True)

        executed = self.results.get('executed_files', {})
        import_data = self.results.get('import_data', {})
        unused_imports = import_data.get('unused_imports', {})
        runtime_only = import_data.get('runtime_only_imports', {})

        output = {
            'project_root': self.results.get('project_root', ''),
            'total_files': len(executed),
            'file_dependencies': {
                filepath: {
                    'functions': data['functions'],
                    'depends_on': list(dict.fromkeys(
                        data['depends_on'] + runtime_only.get(filepath, [])
                    )),
                    'unused_imports': unused_imports.get(filepath, []),
                }
                for filepath, data in executed.items()
            }
        }

        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
