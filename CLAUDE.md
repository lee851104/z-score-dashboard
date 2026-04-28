# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
py server.py
```

Opens at `http://127.0.0.1:5050`. No build step required.

Install dependencies (first time only):
```bash
pip install -r requirements.txt
```

## Architecture

Single-file Flask backend + single-file frontend SPA. No framework, no bundler.

**`server.py`** — Flask app with two routes:
- `GET /` → renders `templates/index.html`
- `GET /api/regime?ticker=NVDA&start=YYYY-MM-DD&end=YYYY-MM-DD` → JSON with all chart data

All financial calculations happen in `server.py` using pandas/numpy:
- `MA_PERIOD = 200` — rolling mean window for the 200 DMA
- `SLOPE_WINDOW = 21` — lookback days for the annualized slope regression (`numpy.polyfit`)
- `BAND_SIGMA = 1.5` — standard deviation multiplier for the price band
- Slope formula: `(polyfit_slope * 252) / current_ma200 * 100` (annualized %)
- Z-Score: `(price - ma200) / rolling_200day_std`
- All series are trimmed to `ma200.notna()` rows before serialization; `np.nan` → JSON `null`

**`templates/index.html`** — Inline CSS + JS, Plotly.js from CDN. No external JS dependencies.
- Design tokens are CSS variables at the top of `<style>` (dark theme, `--bg-*`, `--accent-*`)
- Plotly charts use `dragmode: 'pan'` and `scrollZoom: true` (drag to pan, scroll to zoom)
- The `±1.5σ Band` on the price chart uses two overlapping Plotly traces with `fill: 'tonexty'`
- `plotLayout()` function defines shared chart styling — pass overrides as an object argument

## API Response Shape

```json
{
  "ticker": "NVDA",
  "meta": { "price", "ma200", "zscore", "zscore_label", "slope", "slope_label", "band_label" },
  "price_chart":  { "dates", "close", "ma200", "upper_band", "lower_band" },
  "slope_chart":  { "dates", "slope" },
  "zscore_chart": { "dates", "zscore" }
}
```

Labels: `zscore_label` ∈ {NEUTRAL, ELEVATED, EXTREME}; `slope_label` ∈ {DOWNTREND, UPTREND, STRONG UPTREND}.

## Building the Executable

```bash
py -m PyInstaller regime_dashboard.spec --clean
```

Output: `dist/RegimeDashboard.exe` (~72 MB, single-file). Double-clicking it starts Flask in a background thread and opens the default browser at `http://127.0.0.1:5050`.

**`launcher.py`** — entry point for the exe. Handles two concerns:
1. Path resolution: when frozen, sets `BASE_DIR = sys._MEIPASS` (PyInstaller's temp extraction folder) so Flask can find `templates/`.
2. Startup sequencing: starts Flask in a daemon thread, polls the port until it accepts connections, then calls `webbrowser.open()`. Falls back to the next available port if 5050 is occupied.

**`regime_dashboard.spec`** — PyInstaller spec. Key settings: `console=False` (no terminal window), `templates/index.html` bundled as a data file, yfinance data files collected via `collect_data_files("yfinance")`.

## Key Behaviour Notes

- `TEMPLATES_AUTO_RELOAD = True` and a `no_cache` after-request hook are set so template changes appear immediately without restarting the server.
- yfinance may return a MultiIndex DataFrame for `Close` — the backend handles this with `.squeeze()` / `isinstance` check.
- The `_slope_pct` function is passed to `rolling().apply(raw=True)`, so it receives a numpy array directly.
