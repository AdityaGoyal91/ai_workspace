from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yfinance as yf


def load_symbols(path: Path) -> list[str]:
    symbols: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().upper()
        if not line or line.startswith("#"):
            continue
        symbols.append(line)
    return list(dict.fromkeys(symbols))


@dataclass
class ReturnScore:
    symbol: str
    trailing_return: float
    first_date: pd.Timestamp
    last_date: pd.Timestamp


def compute_trailing_return(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> ReturnScore | None:
    try:
        history = yf.Ticker(symbol).history(
            start=start,
            end=end,
            interval="1d",
            auto_adjust=False,
            actions=False,
        )
    except Exception:
        return None

    if history.empty:
        return None

    price_col = "Adj Close" if "Adj Close" in history.columns else "Close"
    prices = history[price_col].dropna()
    if len(prices) < 2:
        return None

    first = float(prices.iloc[0])
    last = float(prices.iloc[-1])
    if first <= 0:
        return None

    trailing_return = (last / first) - 1.0
    return ReturnScore(
        symbol=symbol,
        trailing_return=trailing_return,
        first_date=pd.Timestamp(prices.index[0]),
        last_date=pd.Timestamp(prices.index[-1]),
    )


def fetch_stock_sector(symbol: str) -> str | None:
    try:
        info = yf.Ticker(symbol).info
    except Exception:
        return None
    sector = info.get("sector")
    if not sector:
        return None
    return str(sector)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build top-5 ETF and stock benchmarks by sector.")
    parser.add_argument("--sectors-file", type=Path, default=Path("universe/sectors.csv"))
    parser.add_argument("--sector-etf-candidates-file", type=Path, default=Path("universe/sector_etf_candidates.csv"))
    parser.add_argument("--stock-candidates-file", type=Path, default=Path("universe/stock_candidates.txt"))
    parser.add_argument("--output-dir", type=Path, default=Path("local_data/audit"))
    parser.add_argument("--lookback-days", type=int, default=252)
    parser.add_argument("--top-n", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(days=args.lookback_days)

    sectors_df = pd.read_csv(args.sectors_file)
    required_sector_cols = {"sector", "benchmark_etf"}
    if not required_sector_cols.issubset(sectors_df.columns):
        missing = required_sector_cols - set(sectors_df.columns)
        raise ValueError(f"Missing required columns in {args.sectors_file}: {sorted(missing)}")

    etf_candidates = pd.read_csv(args.sector_etf_candidates_file)
    required_etf_cols = {"sector", "ticker"}
    if not required_etf_cols.issubset(etf_candidates.columns):
        missing = required_etf_cols - set(etf_candidates.columns)
        raise ValueError(f"Missing required columns in {args.sector_etf_candidates_file}: {sorted(missing)}")

    stock_candidates = load_symbols(args.stock_candidates_file)

    etf_scores: list[dict] = []
    for row in etf_candidates.itertuples(index=False):
        symbol = str(row.ticker).upper()
        score = compute_trailing_return(symbol=symbol, start=start, end=end)
        if score is None:
            continue
        etf_scores.append(
            {
                "sector": row.sector,
                "symbol": score.symbol,
                "trailing_return": score.trailing_return,
                "first_date": score.first_date,
                "last_date": score.last_date,
            }
        )

    stock_scores: list[dict] = []
    for symbol in stock_candidates:
        sector = fetch_stock_sector(symbol)
        if sector is None:
            continue
        score = compute_trailing_return(symbol=symbol, start=start, end=end)
        if score is None:
            continue
        stock_scores.append(
            {
                "sector": sector,
                "symbol": score.symbol,
                "trailing_return": score.trailing_return,
                "first_date": score.first_date,
                "last_date": score.last_date,
            }
        )

    etf_frame = pd.DataFrame(etf_scores)
    stock_frame = pd.DataFrame(stock_scores)

    if etf_frame.empty:
        raise RuntimeError("No ETF return data found. Check candidate list and network access.")
    if stock_frame.empty:
        raise RuntimeError("No stock return data found. Check candidate list and network access.")

    etf_top = (
        etf_frame.sort_values(["sector", "trailing_return"], ascending=[True, False])
        .groupby("sector", as_index=False)
        .head(args.top_n)
        .reset_index(drop=True)
    )
    stock_top = (
        stock_frame.sort_values(["sector", "trailing_return"], ascending=[True, False])
        .groupby("sector", as_index=False)
        .head(args.top_n)
        .reset_index(drop=True)
    )

    summary_rows: list[dict] = []
    for row in sectors_df.itertuples(index=False):
        sector = row.sector
        summary_rows.append(
            {
                "sector": sector,
                "benchmark_etf": row.benchmark_etf,
                "etf_candidates": int((etf_candidates["sector"] == sector).sum()),
                "etfs_scored": int((etf_frame["sector"] == sector).sum()),
                "etf_top_count": int((etf_top["sector"] == sector).sum()),
                "stock_candidates": len(stock_candidates),
                "stocks_scored_in_sector": int((stock_frame["sector"] == sector).sum()),
                "stock_top_count": int((stock_top["sector"] == sector).sum()),
            }
        )
    summary = pd.DataFrame(summary_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    etf_out = args.output_dir / "sector_etf_top.csv"
    stock_out = args.output_dir / "sector_stock_top.csv"
    summary_out = args.output_dir / "sector_benchmark_summary.csv"

    etf_top.to_csv(etf_out, index=False)
    stock_top.to_csv(stock_out, index=False)
    summary.to_csv(summary_out, index=False)

    print(f"Universe sectors: {len(sectors_df)}")
    print(f"Wrote ETF top list: {etf_out}")
    print(f"Wrote stock top list: {stock_out}")
    print(f"Wrote summary: {summary_out}")
    print("Strategy assumption: one buy/sell decision window per day.")


if __name__ == "__main__":
    main()
