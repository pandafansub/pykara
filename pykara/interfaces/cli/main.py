"""CLI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

from pykara.errors import (
    DocumentReadError,
    PykaraError,
    ValidationError,
)
from pykara.interfaces.cli.args import build_parser
from pykara.interfaces.cli.pipeline import (
    load_declarations,
    load_document,
    run_engine,
    run_validation,
    write_output,
)


def _paths_target_same_file(input_path: Path, output_path: Path) -> bool:
    """Return whether the input and output paths point to the same file."""

    return input_path.resolve(strict=False) == output_path.resolve(strict=False)


def _confirm_overwrite_same_file() -> bool:
    """Ask whether overwriting the input file should proceed."""

    try:
        response = input(
            "warning: input and output are the same file. Overwrite it? [y/N]: "
        )
    except EOFError, KeyboardInterrupt:
        return False
    return response.strip().lower() in {"y", "yes"}


def _preflight_output_paths(
    input_path: Path,
    output_path: Path,
    *,
    generated_only: bool,
) -> int | None:
    """Validate risky input/output path combinations before processing."""

    if not _paths_target_same_file(input_path, output_path):
        return None

    if generated_only:
        print(
            "error: --generated-only cannot be used when input and output "
            "are the same file because templates and source karaoke lines "
            "would be lost.",
            file=sys.stderr,
        )
        return 1

    if _confirm_overwrite_same_file():
        return None

    print("error: operation cancelled by user.", file=sys.stderr)
    return 1


def main() -> int:
    """Run the CLI and return the process exit code.

    Returns:
        Process exit code compatible with shell execution.
    """

    args = build_parser().parse_args()
    preflight_result = _preflight_output_paths(
        args.input,
        args.output,
        generated_only=args.generated_only,
    )
    if preflight_result is not None:
        return preflight_result

    try:
        document = load_document(args.input)
        declarations = load_declarations(document)
        report = run_validation(document, declarations)
    except DocumentReadError as error:
        print(
            f"error: could not read '{error.path}': {error}",
            file=sys.stderr,
        )
        return 1
    except PykaraError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if report.has_errors and not args.warn_only:
        for violation in report.errors:
            message = (
                f"[{violation.code}] {violation.message}  ({violation.context})"
            )
            print(
                message,
                file=sys.stderr,
            )
        return 2

    if report.has_errors and args.warn_only:
        for violation in report.errors:
            print(
                f"warning [{violation.code}]: {violation.message}",
                file=sys.stderr,
            )

    for violation in report.warnings:
        print(
            f"warning [{violation.code}]: {violation.message}",
            file=sys.stderr,
        )

    try:
        fx_events = run_engine(
            document,
            declarations,
            seed=args.seed,
            font_dirs=tuple(path.resolve() for path in args.font_dir),
        )
        write_output(
            document,
            fx_events,
            args.output,
            args.json,
            generated_only=args.generated_only,
        )
    except ValidationError as error:
        for violation in error.report.errors:
            print(
                f"[{violation.code}] {violation.message}",
                file=sys.stderr,
            )
        return 2
    except PykaraError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"ok: {len(fx_events)} fx line(s) written to '{args.output}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
