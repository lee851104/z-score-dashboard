"""Explicit live Yahoo smoke check; excluded from deterministic CI tests."""

import argparse
from datetime import date, timedelta

from zscore_dashboard.serving.app import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Fetch historical prices from Yahoo")
    parser.add_argument("--ticker", default="NVDA")
    args = parser.parse_args()
    client = create_app().test_client()
    assert client.get("/").status_code == 200
    print("Homepage OK")
    if args.live:
        today = date.today()
        response = client.get(
            "/api/regime",
            query_string={
                "ticker": args.ticker,
                "start": str(today - timedelta(days=3 * 365)),
                "end": str(today),
            },
        )
        if response.status_code != 200:
            raise SystemExit(f"Live provider failed: {response.status_code} {response.json}")
        data = response.json
        print(
            f"{data['ticker']}: {len(data['price_chart']['dates'])} points; last date {data['meta']['last_date']}"
        )


if __name__ == "__main__":
    main()
