"""
CLI entry point for runtrace
"""

import sys
import argparse
from .tracer import RuntimeTracer


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='runtrace',
        description='Trace dynamic file dependencies during Python execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--version', action='version', version='0.1.0')

    parser.add_argument(
        '-m',
        dest='module',
        metavar='MODULE',
        help='Module to run as __main__ (e.g. pytest, unittest)'
    )
    parser.add_argument(
        '--project-root',
        default='.',
        metavar='DIR',
        help='Root directory to scope dependency tracking (default: current dir)'
    )
    parser.add_argument(
        '--out',
        default='./report.json',
        metavar='FILE',
        help='Output JSON file path (default: ./report.json)'
    )

    args, remaining = parser.parse_known_args()

    if args.module:
        args.target = None
        args.extra_args = remaining
    else:
        if remaining:
            args.target = remaining[0]
            args.extra_args = remaining[1:]
        else:
            args.target = None
            args.extra_args = []

    if not args.module and not args.target:
        parser.print_help()
        sys.exit(1)

    tracer = RuntimeTracer(project_root=args.project_root)

    exit_code = 0
    try:
        if args.module:
            exit_code = tracer.trace_module(args.module, args.extra_args)
        else:
            exit_code = tracer.trace_script(args.target, args.extra_args)
    except Exception as e:
        import traceback
        traceback.print_exc()
        exit_code = 1

    tracer.generate_reports(output_file=args.out)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()