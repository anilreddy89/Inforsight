"""Command-line entry point for fictional policy-history generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .config import GeneratorConfig
from .generator import generate_policy_histories, generation_provenance
from .serialization import histories_to_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic fictional Inforsight policy events."
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--policy-count", type=int, default=100)
    parser.add_argument(
        "--output",
        default="-",
        help="Output JSONL path, or '-' for standard output (default).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = GeneratorConfig(seed=args.seed, policy_count=args.policy_count)
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    histories = generate_policy_histories(config.seed, config.policy_count)
    serialized = histories_to_jsonl(histories)
    provenance = json.dumps(generation_provenance(config), sort_keys=True)

    if args.output == "-":
        sys.stdout.write(serialized)
    else:
        output_path = Path(args.output)
        try:
            with output_path.open("x", encoding="utf-8", newline="\n") as output:
                output.write(serialized)
        except FileExistsError:
            parser.error(f"output already exists: {output_path}")
        except OSError as error:
            parser.error(f"could not write output {output_path}: {error}")

    print(f"generation_provenance={provenance}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
