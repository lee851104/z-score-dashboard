# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
uv run --frozen python server.py
```

Opens at `http://127.0.0.1:5050`. No build step required.

Install dependencies (first time only):
```bash
uv sync --frozen
```

## Architecture

Layered Flask package under `src/zscore_dashboard/` plus the existing single-file frontend. Dependencies are defined in `pyproject.toml` and locked in `uv.lock`. See `docs/architecture.md` for boundaries and `MODEL_CARD.md` for methods and limits.

**`server.py`** — compatibility entry point. `src/zscore_dashboard/serving/app.py` defines the application factory and routes:
- `GET /` → renders `src/zscore_dashboard/serving/templates/index.html`
- `GET /api/regime?ticker=NVDA&start=YYYY-MM-DD&end=YYYY-MM-DD` → JSON with all chart data

Pure calculations live in `src/zscore_dashboard/features/indicators.py`; HTTP serialization lives in `serving/schemas.py`. Parameters come from `configs/dashboard.toml`:
- `MA_PERIOD = 200` — rolling mean window for the 200 DMA
- `SLOPE_WINDOW = 21` — lookback days for the annualized slope regression (`numpy.polyfit`)
- `BAND_SIGMA = 1.5` — standard deviation multiplier for the price band
- Slope formula: `(polyfit_slope * 252) / current_ma200 * 100` (annualized %)
- Z-Score: `(price - ma200) / rolling_200day_std`
- All series are trimmed to `ma200.notna()` rows before serialization; `np.nan` → JSON `null`

**`src/zscore_dashboard/serving/templates/index.html`** — Inline CSS + JS, Plotly.js from CDN. No external JS dependencies.
- Design tokens are CSS variables at the top of `<style>` (dark theme, `--bg-*`, `--accent-*`)
- Plotly charts use `dragmode: 'pan'` and `scrollZoom: true` (drag to pan, scroll to zoom)
- The `±1.5σ Band` on the price chart uses two overlapping Plotly traces with `fill: 'tonexty'`
- `plotLayout()` function defines shared chart styling — pass overrides as an object argument

## API Response Shape

```json
{
  "ticker": "NVDA",
  "meta": { "price", "last_date", "ma200", "zscore", "zscore_label", "slope", "slope_label", "band_label" },
  "price_chart":  { "dates", "close", "ma200", "upper_band", "lower_band" },
  "slope_chart":  { "dates", "slope" },
  "zscore_chart": { "dates", "zscore" }
}
```

Labels: `zscore_label` ∈ {NEUTRAL, ELEVATED, EXTREME}; `slope_label` ∈ {DOWNTREND, UPTREND, STRONG UPTREND}.

`data/market.py` implements `GET /api/search?q=...` search ranking via `yf.Search()`, re-ranked with `difflib.SequenceMatcher`. Returns up to 8 results: `[{"symbol", "name", "type"}, ...]`. Used by the autocomplete dropdown in the frontend.

## Building the Executable

```bash
py -m PyInstaller regime_dashboard.spec --clean
```

Output: `dist/RegimeDashboard.exe` (~72 MB, single-file). Double-clicking it starts Flask in a background thread and opens the default browser at `http://127.0.0.1:5050`.

**`launcher.py`** — entry point for the exe. Handles two concerns:
1. Path resolution: when frozen, sets `BASE_DIR = sys._MEIPASS` (PyInstaller's temp extraction folder) so Flask can find `templates/`.
2. Startup sequencing: starts Flask in a daemon thread, polls the port until it accepts connections, then calls `webbrowser.open()`. Falls back to the next available port if 5050 is occupied.

**`regime_dashboard.spec`** — PyInstaller spec. Key settings: `console=False` (no terminal window), `src/zscore_dashboard/serving/templates/index.html` bundled as a data file, yfinance data files collected via `collect_data_files("yfinance")`.

## Key Behaviour Notes

- Template serving uses `render_template_string` + `.read_text()` instead of `render_template` to bypass Flask's template cache — changes to `index.html` are picked up on every request without a server restart.
- yfinance may return a MultiIndex DataFrame for `Close` — `data/market.py` normalizes it without collapsing a one-row Series to a scalar.
- The `annualized_slope` function is passed to `rolling().apply(raw=True)`, so it receives a numpy array directly.
- Taiwan stocks use Yahoo Finance suffix format: `2330.TW` (TWSE listed), `6488.TWO` (OTC). The search endpoint returns these suffixes automatically.
- The exe bundles a frozen copy of `src/zscore_dashboard/serving/templates/index.html` — editing the file has no effect on the exe; rebuild with PyInstaller to update it.
- **Server restart required** for Python or TOML changes; the exe must be rebuilt for any changes to take effect in the packaged version.

## Frontend Architecture (`src/zscore_dashboard/serving/templates/index.html`)

All CSS, JS, and HTML are in a single file. Key frontend pieces:

- **Autocomplete**: `input#ctrl-ticker` → debounced `GET /api/search` → dropdown rendered via `innerHTML`. Keyboard nav (↑↓ Enter Esc) handled inside `DOMContentLoaded`.
- **Bell curve**: SVG drawn by `buildBellPath()` using the standard normal PDF. `updateBell(zscore)` moves the needle and sets its color. ±1σ/±2σ dashed marker lines are fixed at init.
- **Slope gauge**: CSS gradient bar (`left: red → center: sand → right: green`) with an absolutely-positioned needle div. Color and position set directly in `renderCards()`.
- **Color logic**: Z-Score green(|z|<1.5) / sand(1.5–2.5) / rose(>2.5). Slope green(>5%) / sand(−5–5%) / rose(<−5%). Both the KPI value text and the indicator needle use the same color.
- **Mobile UI**: a 760px media query controls compact cards, collapsible dates and chart tabs; mobile CSS follows base rules. Match this breakpoint in `mobileQuery` when changing layout.
- **Plotly**: `Plotly.react` renders the active mobile chart; desktop shows all three. Chart gestures are opt-in on mobile to preserve page scrolling. See `reports/mobile-ui.md` for verification scope.

## Deployment

- **Railway**: connected to the GitHub repo (`main` branch). Push to `main` triggers auto-deploy. Previously deployed at `https://web-production-a1ed8.up.railway.app/`; verify the integration before publishing.
- **Procfile**: `web: env HOST=0.0.0.0 python server.py` — Railway uses this to start the app.

## Refactor checks

- `uv run --frozen pytest` runs deterministic offline tests, including no-lookahead checks.
- `uv run --frozen ruff check .` and `uv run --frozen ruff format --check .` check Python style.
- `uv build` then `uv run --frozen python scripts/check_wheel.py` validates installed resources.
- `uv run --frozen python scripts/smoke.py --live` is a separate real Yahoo request.
- HF Docker uses the locked `serve` extra and `zscore_dashboard.serving.app:create_app()` on port 7860.
- Exclude only root `/data/` and `/models/` in `.gitignore`; do not exclude the source package's `data/` module.
- Preserve the user's frontend changes when refactoring or moving files.
