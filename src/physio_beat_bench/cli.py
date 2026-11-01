"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .bench import Layout, run_entries, run_modern
from .fetch import fetch
from .report import (
    add_official_scores,
    comparisons,
    figure,
    official_agreement,
    reproduction_tiers,
    summarise,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="physio-beat-bench", description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--work", type=Path, default=Path("work"))
    parser.add_argument("--results", type=Path, default=Path("results"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch", help="download the published Challenge archive")
    entries = commands.add_parser("entries", help="build and run archived Challenge entries")
    entries.add_argument("--jobs", type=int, default=8)
    entries.add_argument("--timeout", type=float, default=120)
    entries.add_argument("--only", nargs="*")
    modern = commands.add_parser("modern", help="run current open-source detectors")
    modern.add_argument("--jobs", type=int, default=8)
    commands.add_parser("report", help="summarise results")
    args = parser.parse_args()

    layout = Layout(args.data.resolve())
    results = args.results.resolve()
    if args.command == "fetch":
        fetch(args.data.resolve())
    elif args.command == "entries":
        run_entries(
            layout, args.work.resolve(), results / "entries.csv", args.jobs, args.timeout, args.only
        )
    elif args.command == "modern":
        run_modern(layout, results / "modern.csv", args.jobs)
    else:
        names = ("entries.csv", "modern.csv")
        frames = [pd.read_csv(results / name) for name in names if (results / name).exists()]
        combined = pd.concat(frames)
        summary = add_official_scores(summarise(combined), layout.data / "rankings-20150413")
        figure(summary, Path("docs/scores.png"))
        print(reproduction_tiers(summary))
        print(official_agreement(summary))
        paired = comparisons(combined)
        paired.to_csv(results / "comparisons.csv", index=False)
        print(paired.to_string(index=False))
        summary.to_csv(results / "summary.csv", index=False)
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
