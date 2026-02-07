from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import yfinance as yf


EXPECTED_COLUMNS = [
    "timestamp",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
]


@dataclass
class FetchResult:
    symbol: str
    rows: int
    first_timestamp: pd.Timestamp | None
    last_timestamp: pd.Timestamp | None


def load_tickers(tickers_file: Path) -> list[str]:
    tickers: list[str] = []
    for raw_line in tickers_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().upper()
        if not line or line.startswith("#"):
            continue
        tickers.append(line)
    if not tickers:
        raise ValueError(f"No tickers found in {tickers_file}")
    return tickers


def fetch_hourly_prices(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    data = yf.download(
        tickers=symbol,
        start=start,
        end=end,
        interval="1h",
        auto_adjust=False,
        progress=False,
        prepost=False,
        multi_level_index=False,
    )
    if data.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]

    data = data.reset_index()
    datetime_col = "Datetime" if "Datetime" in data.columns else "Date"
    data = data.rename(
        columns={
            datetime_col: "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
    data["symbol"] = symbol

    if "adj_close" not in data.columns:
        data["adj_close"] = data["close"]

    output = data[["timestamp", "symbol", "open", "high", "low", "close", "adj_close", "volume"]].copy()
    volume_col = output["volume"]
    if isinstance(volume_col, pd.DataFrame):
        volume_col = volume_col.iloc[:, 0]
    output["volume"] = pd.to_numeric(volume_col, errors="coerce").fillna(0).astype("int64")
    return output.sort_values("timestamp")


def fetch_many(
    tickers: Iterable[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, list[FetchResult]]:
    frames: list[pd.DataFrame] = []
    stats: list[FetchResult] = []
    for symbol in tickers:
        frame = fetch_hourly_prices(symbol=symbol, start=start, end=end)
        frames.append(frame)
        if frame.empty:
            stats.append(FetchResult(symbol=symbol, rows=0, first_timestamp=None, last_timestamp=None))
            continue
        stats.append(
            FetchResult(
                symbol=symbol,
                rows=len(frame),
                first_timestamp=frame["timestamp"].min(),
                last_timestamp=frame["timestamp"].max(),
            )
        )
    if not frames:
        return pd.DataFrame(columns=EXPECTED_COLUMNS), stats
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["symbol", "timestamp"], keep="last")
    combined = combined.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    return combined, stats


def read_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    frame = pd.read_parquet(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame[EXPECTED_COLUMNS].copy()


def write_dataset(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = frame.copy()
    output["timestamp"] = pd.to_datetime(output["timestamp"], utc=True)
    output = output.drop_duplicates(subset=["symbol", "timestamp"], keep="last")
    output = output.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    output.to_parquet(path, index=False)
