from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from data_ingestion import fetch_many, load_tickers, write_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill hourly stock prices.")
    parser.add_argument("--tickers-file", type=Path, default=Path("tickers.txt"))
    parser.add_argument("--output", type=Path, default=Path("local_data/parquet/hourly_prices.parquet"))
    parser.add_argument("--start-date", type=str, default="2024-01-01")
    parser.add_argument("--end-date", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = load_tickers(args.tickers_file)
    start = pd.Timestamp(args.start_date, tz="UTC")
    end = pd.Timestamp(args.end_date, tz="UTC") if args.end_date else pd.Timestamp.now(tz="UTC")

    frame, stats = fetch_many(tickers=tickers, start=start, end=end)
    write_dataset(args.output, frame)

    print(f"Wrote {len(frame)} rows to {args.output}")
    for stat in stats:
        if stat.rows == 0:
            print(f"{stat.symbol}: no data returned")
            continue
        print(f"{stat.symbol}: {stat.rows} rows ({stat.first_timestamp} -> {stat.last_timestamp})")


if __name__ == "__main__":
    main()
