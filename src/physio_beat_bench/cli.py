"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .bench import Layout, run_entries, run_modern
from .compare import compare_runs
from .fetch import fetch
from .report import (
    add_official_scores,
    comparisons,
    figure,
    healthy_looking_mismatches,
    method_selection,
    official_agreement,
    outcomes_figure,
    reproduction_map,
    reproduction_table,
    reproduction_tiers,
    summarise,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="physio-beat-bench", description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--work", type=Path, default=Path("work"))
    parser.add_argument("--results", type=Path, default=Path("results"))
    commands = parser.add_subparsers(dest="command", required=True)
    fetcher = commands.add_parser(
        "fetch", help="download the published Challenge archive, or unpack a local copy"
    )
    fetcher.add_argument(
        "--archive", type=Path, help="use this local copy of the archive; no download"
    )
    entries = commands.add_parser("entries", help="build and run archived Challenge entries")
    entries.add_argument("--jobs", type=int, default=8)
    entries.add_argument("--timeout", type=float, default=120)
    entries.add_argument("--only", nargs="*")
    modern = commands.add_parser("modern", help="run current open-source detectors")
    modern.add_argument("--jobs", type=int, default=8)
    commands.add_parser("report", help="summarise results")
    comparer = commands.add_parser(
        "compare", help="compare --results (the candidate) with another run, record by record"
    )
    comparer.add_argument("--baseline", type=Path, required=True)
    comparer.add_argument("--out", type=Path, help="write per-record and per-detector CSVs here")
    args = parser.parse_args()

    layout = Layout(args.data.resolve())
    results = args.results.resolve()
    if args.command == "fetch":
        report = fetch(args.data.resolve(), archive=args.archive)
        print(f"Archive: {report['archive']}\nSHA-256: {report['sha256']}")
        if report["verified_against_known_checksum"]:
            print("Matches the archive behind the published results.")
        else:
            print("WARNING: differs from the archive behind the published results.")
    elif args.command == "entries":
        run_entries(
            layout, args.work.resolve(), results / "entries.csv", args.jobs, args.timeout, args.only
        )
    elif args.command == "modern":
        run_modern(layout, results / "modern.csv", args.jobs)
    elif args.command == "compare":
        rows, detectors = compare_runs(args.baseline.resolve(), results)
        print(rows.groupby(["kind", "outcome"]).size().unstack(fill_value=0).to_string())
        print(detectors[detectors["identical"] < detectors["rows"]].to_string(index=False))
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            rows.to_csv(args.out / "rows.csv", index=False)
            detectors.to_csv(args.out / "detectors.csv", index=False)
    else:
        names = ("entries.csv", "modern.csv")
        frames = [pd.read_csv(results / name) for name in names if (results / name).exists()]
        combined = pd.concat(frames)
        summary = add_official_scores(summarise(combined), layout.data / "rankings-20150413")
        # The README's figures come from the default results; any other run keeps its own.
        figures = Path("docs") if results == Path("results").resolve() else results
        figure(summary, figures / "scores.png")
        outcomes_figure(summary, figures / "outcomes.png")
        print(reproduction_tiers(summary))
        print({"healthy_looking_mismatches": healthy_looking_mismatches(summary)})
        print(official_agreement(summary))
        paired = comparisons(combined)
        paired.to_csv(results / "comparisons.csv", index=False)
        print(paired.to_string(index=False))
        summary.to_csv(results / "summary.csv", index=False)
        reproduction_table(summary).to_csv(results / "reproduction.csv", index=False)
        reproduction_map(combined, summary, figures / "reproduction_map.png")
        selection = method_selection(combined, summary)
        selection.to_csv(results / "selection.csv", index=False)
        print(selection.to_string(index=False))
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
