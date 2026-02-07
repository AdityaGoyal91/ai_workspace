# Stock Picker Data Pipeline

This repo now includes a minimal ingestion pipeline for hourly OHLCV data:

- `scripts/backfill_hourly.py`: one-time historical load from `2024-01-01` onward.
- `scripts/update_daily.py`: daily incremental refresh for freshest data.
- `scripts/update_universe.py`: monthly universe refresh for top-volume stocks + largest ETFs.

## 1) Create virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.lock.txt
python -m pip install -e .
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock.txt
python -m pip install -e .
```

Optional setup helper scripts:

- Windows: `powershell -ExecutionPolicy Bypass -File scripts/setup_venv.ps1`
- macOS/Linux: `bash scripts/setup_venv.sh`

If your shell enforces offline pip (`PIP_NO_INDEX=1`) or forced proxies, unset those vars before installation.

## 2) Build ticker universe (monthly)

```bash
python scripts/update_universe.py
```

This regenerates `tickers.txt` using:

- top 20 stocks by average daily share volume over the latest 2 years
- top 20 ETFs by latest total assets (AUM proxy)

Inputs:

- `universe/stock_candidates.txt`
- `universe/etf_candidates.txt`

Audit outputs:

- `local_data/audit/universe_stocks_ranked.csv`
- `local_data/audit/universe_etfs_ranked.csv`

## 3) Run historical backfill (hourly)

```bash
python scripts/backfill_hourly.py --start-date 2024-01-01
```

Default output dataset:

- `local_data/parquet/hourly_prices.parquet`

## 4) Run daily incremental update

```bash
python scripts/update_daily.py
```

This script reads existing data and refetches an overlap window (`--lookback-hours`, default `72`) to absorb revisions, then deduplicates by `symbol,timestamp`.

## 5) Schedule tasks (Windows Task Scheduler)

Monthly universe refresh action:

- Program/script: `C:\Users\Aditya Goyal\Documents\Github\ai_workspace\.venv\Scripts\python.exe`
- Add arguments: `scripts/update_universe.py`
- Trigger: Monthly (for example, first trading day at 6:00 AM)
- Start in: `C:\Users\Aditya Goyal\Documents\Github\ai_workspace`

Daily prices refresh action:

Example action:

- Program/script: `C:\Users\Aditya Goyal\Documents\Github\ai_workspace\.venv\Scripts\python.exe`
- Add arguments: `scripts/update_daily.py`
- Start in: `C:\Users\Aditya Goyal\Documents\Github\ai_workspace`

Pipeline scripts (recommended for scheduler):

- Backfill pipeline: `powershell -ExecutionPolicy Bypass -File scripts/backfill_pipeline.ps1 -StartDate 2024-01-01`
- Daily update pipeline: `powershell -ExecutionPolicy Bypass -File scripts/daily_update_pipeline.ps1`

Both scripts clear common proxy environment variables by default (`-ClearProxyEnv`) to avoid local proxy misconfiguration issues.
Both scripts also write timestamped logs to `local_data/logs` by default (override with `-LogDir`).
`backfill_pipeline.ps1` keeps the most recent 2 logs by default, and `daily_update_pipeline.ps1` keeps the most recent 14 logs (override either with `-MaxLogs`).

## Notes

- Data source is Yahoo Finance via `yfinance`.
- Some providers may limit how far intraday (`1h`) history goes. If that happens, the scripts will still run and store the maximum returned range.
- If package install fails, check environment variables (`PIP_NO_INDEX`, `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`) in your shell.
