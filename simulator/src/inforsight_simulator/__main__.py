"""Command-line entry point for fictional policy-history generation."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from pathlib import Path
from typing import Sequence

from .config import GeneratorConfig
from .generator import (
    generate_legacy_policy_histories,
    generate_policy_histories,
    generation_provenance,
    legacy_generation_provenance,
)
from .serialization import histories_to_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic fictional Inforsight policy events."
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--policy-count", type=int, default=100)
    parser.add_argument(
        "--run-namespace",
        help="Required stable namespace for corrected generation.",
    )
    parser.add_argument(
        "--simulation-start",
        default="2024-01-01T00:00:00Z",
        help="UTC ISO-8601 start for corrected generation.",
    )
    parser.add_argument(
        "--legacy-v1",
        action="store_true",
        help="Explicitly reproduce generator 0.1.0 counter-ID output.",
    )
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
        if args.legacy_v1:
            if args.run_namespace is not None:
                parser.error("--run-namespace cannot be used with --legacy-v1")
            if args.simulation_start != "2024-01-01T00:00:00Z":
                parser.error("--simulation-start cannot be changed with --legacy-v1")
            histories = generate_legacy_policy_histories(args.seed, args.policy_count)
            provenance = legacy_generation_provenance(args.seed, args.policy_count)
        else:
            if args.run_namespace is None:
                parser.error("--run-namespace is required unless --legacy-v1 is used")
            simulation_start = datetime.fromisoformat(
                args.simulation_start.replace("Z", "+00:00")
            )
            config = GeneratorConfig(
                seed=args.seed,
                policy_count=args.policy_count,
                run_namespace=args.run_namespace,
                simulation_start=simulation_start,
            )
            histories = generate_policy_histories(config)
            provenance = generation_provenance(config)
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    serialized = histories_to_jsonl(histories)
    serialized_provenance = json.dumps(provenance, sort_keys=True)

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

    print(f"generation_provenance={serialized_provenance}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
