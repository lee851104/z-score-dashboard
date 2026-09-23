# 架構與部署

## 模組邊界

`serving/app.py` 負責 HTTP 輸入、錯誤狀態與應用程式組裝；`data/market.py` 負責外部行情及資料驗證；`features/indicators.py` 是不連網、不依賴 Flask 的純計算；`serving/schemas.py` 將計算結果轉成既有前端使用的 JSON。

`create_app(settings=None, provider=None)` 接受設定與行情 provider，讓測試能替換外部服務。provider 提供 `download(ticker, start, end)` 和 `search(query)`。正式環境使用 `YahooMarketData`。

TOML 設定由 `settings.py` 載入並驗證。原始碼開發時讀取根目錄 `configs/dashboard.toml`；wheel 打包時將同一份檔案放進套件，避免工作目錄改變就找不到設定。模板隨 Python 套件一起打包。

## HTTP 契約

| 路徑 | 行為 |
| --- | --- |
| `GET /` | 載入既有 HTML／CSS／JS；設定可控制均線及 band 標題 |
| `GET /api/search?q=NVDA` | 最多回傳設定指定的候選數，預設 8；無查詢或上游失敗時回傳空陣列 |
| `GET /api/regime?ticker=NVDA&start=2023-01-01&end=2026-01-01` | 回傳 ticker、meta、price_chart、slope_chart、zscore_chart |

重構保留有效查詢的 JSON 欄位、四位小數序列化及標籤。新增日期輸入驗證、單筆行情的正常資料不足回應；上游拋出例外時回傳 502 和簡短訊息，完整診斷寫入服務日誌。yfinance 若自行吞掉上游錯誤並回傳空資料，仍沿用原版的 400「找不到資料」回應。

## 設定與入口

- 依賴唯一來源：`pyproject.toml`；精確版本：`uv.lock`。
- `requirements*.txt` 為 pip 相容入口，不再重複列出依賴。
- 本機：`uv run --frozen python server.py` 或 `uv run --frozen zscore-serve`。
- Windows 不需要安裝 Make；README 列有全部等效 uv 命令。
- 自訂設定：設定 `ZSCORE_CONFIG`；指向不存在的檔案會明確失敗，不會悄悄使用預設值。
- 開發伺服器預設只監聽 `127.0.0.1:5050`；平台提供 `PORT` 時預設監聽 `0.0.0.0`，讓外部請求能連入。`HOST` 可明確覆寫監聽位址。

## Hugging Face Docker

Docker 以 Python 3.12 和鎖定版本的 uv 執行 `uv sync --frozen --no-dev --extra serve --no-editable`，由非 root 使用者執行 Gunicorn，對外監聽 `7860`。應用程式直接從已安裝套件載入。

完整部署包含 README 的 HF metadata、Dockerfile、`.dockerignore`、`pyproject.toml`、`uv.lock`、`configs/` 與 `src/`；不能只上傳舊版的 `server.py` 與模板。

`.dockerignore` 使用允許清單，排除本機環境、Git、日誌及測試暫存。設定不含 token；未來需要秘密值時應透過 hosting secrets 提供。

## Railway 與桌面封裝

`Procfile` 明確使用 `HOST=0.0.0.0`，並由平台提供 `PORT`。既有 Railway 與 GitHub 的連線狀態需在實際發布時確認。

本機既有 `launcher.py` 和 PyInstaller spec 可繼續使用；spec 已改成納入 `src/`、套件模板與 TOML。現有 `dist/RegimeDashboard.exe` 是舊的封裝檔，本次沒有重新建置 exe。

## 品質檢查

CI 定義 Windows／Linux × Python 3.11／3.12 的 lint、離線測試與 wheel 驗證，另有 Linux Docker 建置與首頁 smoke check。工作流程檔存在不表示遠端 CI 已經跑過。

`scripts/check_wheel.py` 會檢查必要資源，並在臨時工作目錄匯入 wheel 內的套件，避免只在開發目錄成功、部署時缺少模板或 data 模組的問題。
