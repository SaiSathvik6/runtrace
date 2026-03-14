# runtrace

A lightweight Python tool that traces **dynamic file-level dependencies** during execution. It shows exactly which files were executed, which functions were called, and which files each file depended on at runtime — based on actual execution, not static analysis.

## Installation

```bash
pip install git+https://github.com/<SaiSathvik6>/runtrace.git
```

## Usage

```bash
# Trace a script
runtrace --project-root <project_root> <path_to_script>

# Trace pytest
runtrace --project-root <project_root> -m pytest <path_to_test_file>

# Trace unittest
runtrace --project-root <project_root> -m unittest discover -s tests

# Custom output file
runtrace --project-root <project_root> --out report.json <path_to_script>
```

### Options

| Option | Default | Description |
|---|---|---|
| `--project-root` | `.` | Root directory to scope dependency tracking |
| `--out` | `./report.json` | Output JSON report file path |
| `-m MODULE` | — | Run a module as `__main__` (e.g. `pytest`, `unittest`) |

## Output

The report is written as JSON to `./report.json` (or the path given with `--out`).

```json
{
  "project_root": "/abs/path/to/project",
  "total_files": 3,
  "file_dependencies": {
    "/abs/path/to/project/main.py": {
      "functions": [
        {"name": "run", "line": 5}
      ],
      "depends_on": [
        "/abs/path/to/project/db.py"
      ],
      "unused_imports": []
    }
  }
}
```

### Output fields

| Field | Description |
|---|---|
| `total_files` | Number of project files executed during the run |
| `file_dependencies` | Every project file touched during the run, in execution order |
| `functions` | Functions called in that file, in first-call order (`name`, `line`) |
| `depends_on` | Other project files this file called into at runtime (via function calls or dynamic imports) |
| `unused_imports` | Project files that were statically imported but never actually used at runtime |
