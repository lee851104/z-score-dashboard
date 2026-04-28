from flask import Flask, jsonify, render_template, request
from pathlib import Path
import yfinance as yf
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).parent
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.after_request
def no_cache(r):
    r.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    return r

MA_PERIOD    = 200
SLOPE_WINDOW = 21
BAND_SIGMA   = 1.5


def _slope_pct(window_vals):
    if np.any(np.isnan(window_vals)):
        return np.nan
    x = np.arange(len(window_vals), dtype=float)
    coeffs = np.polyfit(x, window_vals, 1)
    return (coeffs[0] * 252) / window_vals[-1] * 100


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/regime")
def regime():
    ticker = request.args.get("ticker", "SPY").strip().upper()
    start  = request.args.get("start", "") or None
    end    = request.args.get("end", "")   or None

    if not ticker:
        return jsonify({"error": "ticker required"}), 400

    try:
        raw = yf.download(ticker, start=start, end=end,
                          auto_adjust=True, progress=False)
        if raw.empty:
            return jsonify({"error": f"找不到 {ticker} 的資料，請確認代號是否正確"}), 400

        close = raw["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.squeeze()

        ma200      = close.rolling(MA_PERIOD).mean()
        std200     = close.rolling(MA_PERIOD).std()
        zscore     = (close - ma200) / std200
        upper_band = ma200 + BAND_SIGMA * std200
        lower_band = ma200 - BAND_SIGMA * std200
        slope      = ma200.rolling(SLOPE_WINDOW).apply(_slope_pct, raw=True)

        valid = ma200.notna()
        if valid.sum() == 0:
            return jsonify({"error": "資料不足 200 天，無法計算指標"}), 400

        def _ser(s):
            return [None if (v is None or (isinstance(v, float) and np.isnan(v)))
                    else round(float(v), 4)
                    for v in s[valid]]

        dates     = [str(d)[:10] for d in close[valid].index]
        close_v   = _ser(close)
        ma200_v   = _ser(ma200)
        upper_v   = _ser(upper_band)
        lower_v   = _ser(lower_band)
        zscore_v  = _ser(zscore)
        slope_v   = _ser(slope)

        last_close  = close_v[-1]
        last_ma200  = ma200_v[-1]
        last_zscore = next((v for v in reversed(zscore_v) if v is not None), 0.0)
        last_slope  = next((v for v in reversed(slope_v)  if v is not None), 0.0)

        abs_z = abs(last_zscore)
        band_label = (
            "> 2.5"      if abs_z >= 2.5 else
            "2.0 to 2.5" if abs_z >= 2.0 else
            "1.5 to 2.0" if abs_z >= 1.5 else
            "1.0 to 1.5" if abs_z >= 1.0 else
            "0 to 1.0"
        )
        slope_label = (
            "STRONG UPTREND" if last_slope > 15  else
            "UPTREND"        if last_slope > 0   else
            "DOWNTREND"
        )
        zscore_label = (
            "EXTREME"  if abs_z >= 2.5 else
            "ELEVATED" if abs_z >= 1.5 else
            "NEUTRAL"
        )

        return jsonify({
            "ticker": ticker,
            "meta": {
                "price":        last_close,
                "ma200":        last_ma200,
                "zscore":       round(last_zscore, 2),
                "zscore_label": zscore_label,
                "slope":        round(last_slope,  2),
                "slope_label":  slope_label,
                "band_label":   band_label,
            },
            "price_chart":  {"dates": dates, "close": close_v,
                             "ma200": ma200_v, "upper_band": upper_v, "lower_band": lower_v},
            "slope_chart":  {"dates": dates, "slope": slope_v},
            "zscore_chart": {"dates": dates, "zscore": zscore_v},
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
