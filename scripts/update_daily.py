from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from data_ingestion import fetch_many, load_tickers, read_existing, write_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incrementally update hourly stock prices.")
    parser.add_argument("--tickers-file", type=Path, default=Path("tickers.txt"))
    parser.add_argument("--dataset", type=Path, default=Path("local_data/parquet/hourly_prices.parquet"))
    parser.add_argument("--initial-start-date", type=str, default="2024-01-01")
    parser.add_argument(
        "--lookback-hours",
        type=int,
        default=72,
        help="Overlap window to refetch recent bars and absorb data corrections.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = load_tickers(args.tickers_file)
    existing = read_existing(args.dataset)
    now = pd.Timestamp.now(tz="UTC")

    if existing.empty:
        start = pd.Timestamp(args.initial_start_date, tz="UTC")
        print(f"No existing dataset found. Running first-load from {start} to {now}.")
    else:
        latest = existing.groupby("symbol")["timestamp"].max()
        earliest_last_bar = latest.min()
        start = earliest_last_bar - pd.Timedelta(hours=args.lookback_hours)
        print(f"Existing rows: {len(existing)}. Refreshing from {start} to {now}.")

    fresh, stats = fetch_many(tickers=tickers, start=start, end=now)
    merged = pd.concat([existing, fresh], ignore_index=True)
    write_dataset(args.dataset, merged)

    print(f"Wrote {len(merged.drop_duplicates(subset=['symbol', 'timestamp']))} total deduped rows to {args.dataset}")
    for stat in stats:
        if stat.rows == 0:
            print(f"{stat.symbol}: no new data")
            continue
        print(f"{stat.symbol}: {stat.rows} rows ({stat.first_timestamp} -> {stat.last_timestamp})")


if __name__ == "__main__":
    main()
