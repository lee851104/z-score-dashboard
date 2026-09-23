# 架構重構驗證

驗證日期：2026-09-23。環境：Windows、Python 3.12、專案 uv 環境。

## 已執行

| 檢查 | 結果與範圍 |
| --- | --- |
| `pytest -q` | 36 passed；公式、暖機、缺值、JSON、行情格式、API、TOML、未來資料洩漏 |
| `ruff check .` | 通過 |
| `ruff format --check .` | 18 個 Python 檔案格式一致 |
| `uv lock --check --offline` | 鎖檔符合 pyproject |
| `uv build` | wheel 與 sdist 建置成功 |
| `scripts/check_wheel.py` | 必要 Python 模組、TOML 與模板存在；離開 checkout 後仍可載入首頁 |
| 重構前後比較 | 上漲、下跌、固定價格、斜率暖機未完成、Yahoo MultiIndex 共 5 組完整 API JSON 相等 |
| HTML 相容性 | 預設設定渲染後與使用者重構前的 HTML 相同（忽略檔尾換行） |
| 真實 Yahoo 請求 | `scripts/smoke.py --live`：NVDA 551 個指標日期，最後可用日期 2026-09-21 |
| 瀏覽器 | 暫時在 localhost:5051 啟動；NVDA KPI、價格圖、斜率圖與 Z-Score 圖皆載入成功 |

## 刻意保留與修正

- 保留使用者原有介面、API 欄位與正常行情的數值結果。
- 模板移入 Python 套件；預設畫面不變，自訂均線／band 設定會反映在標題。
- 修正一筆行情被 `squeeze()` 轉為 scalar 的問題，現在回應資料不足。
- 日期輸入錯誤會在呼叫行情服務前回傳 400。
- 上游拋出的例外回傳 502，不將內部例外內容直接放進公開回應。
- `.gitignore` 的 `/data/` 與 `/models/` 僅匹配根目錄，避免把程式模組一起排除。已透過 wheel 執行檢查驗證。

## 尚未由本次驗證涵蓋

- 本報告記錄本機驗證結果；遠端 GitHub Actions 的執行結果以儲存庫 Actions 頁面為準。
- 本機沒有 Docker，未在本機建置 Linux 容器；CI 已加入 Docker build 與 HTTP smoke check。
- 未重建既有 Windows exe。
- HF 公開 Demo 的驗證來自前一次部署；本次重構的線上部署結果不包含在此本機驗證報告中。
- 沒有併發壓力測試、策略回測或獲利／預測能力驗證。
- Yahoo 的可用性與最後資料日期可能變動；上述 live check 是當次結果，不是永久保證。

本次暫時啟動的本機驗證服務在檢查後停止。
