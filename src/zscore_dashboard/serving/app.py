"""Application factory; accepts a data provider for offline API tests."""

import os
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

from zscore_dashboard.data.market import YahooMarketData, normalize_close
from zscore_dashboard.features.indicators import compute_indicators
from zscore_dashboard.serving.schemas import build_response
from zscore_dashboard.settings import Settings, load_settings


def create_app(settings: Settings | None = None, provider=None) -> Flask:
    settings = settings or load_settings()
    provider = provider if provider is not None else YahooMarketData(settings.market)
    template_dir = Path(__file__).parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["DASHBOARD_SETTINGS"] = settings

    @app.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response

    @app.get("/")
    def index():
        return render_template_string(
            (template_dir / "index.html").read_text(encoding="utf-8"),
            indicators=settings.indicators,
        )

    @app.get("/api/search")
    def search():
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify([])
        try:
            return jsonify(provider.search(query))
        except Exception:
            app.logger.exception("Ticker search failed")
            # Preserve the autocomplete API's empty-list fallback.
            return jsonify([])

    @app.get("/api/regime")
    def regime():
        ticker = request.args.get("ticker", "SPY").strip().upper()
        start = request.args.get("start", "") or None
        end = request.args.get("end", "") or None
        if not ticker:
            return jsonify(error="ticker required"), 400
        try:
            start_date = date.fromisoformat(start) if start else None
            end_date = date.fromisoformat(end) if end else None
            if start_date and end_date and start_date >= end_date:
                raise ValueError("start must precede end")
        except ValueError:
            return jsonify(error="日期格式需為 YYYY-MM-DD，且開始日期須早於結束日期"), 400
        try:
            raw = provider.download(ticker, start=start, end=end)
        except Exception:
            app.logger.exception("Market data request failed for %s", ticker)
            return jsonify(error="行情服務暫時無法使用，請稍後重試"), 502
        if raw.empty:
            return jsonify(error=f"找不到 {ticker} 的資料，請確認代號是否正確"), 400
        try:
            close = normalize_close(raw)
            frame = compute_indicators(close, settings.indicators)
            return jsonify(build_response(ticker, frame, settings.indicators))
        except ValueError as error:
            return jsonify(error=str(error)), 400
        except Exception:
            app.logger.exception("Indicator calculation failed for %s", ticker)
            return jsonify(error="指標計算失敗，請稍後重試"), 500

    return app


def main():
    settings = load_settings()
    default_host = "0.0.0.0" if "PORT" in os.environ else settings.server.host
    create_app(settings).run(
        host=os.environ.get("HOST", default_host),
        port=int(os.environ.get("PORT", settings.server.port)),
        debug=False,
    )
