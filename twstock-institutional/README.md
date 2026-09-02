# 我的持股．三大法人買賣超儀表板

自動每天抓取你持股的三大法人（外資、投信、自營商）買賣超，並計算近 7 日、近 30 日的累計變化，用網頁儀表板呈現。完全免費：資料來自證交所/櫃買中心公開資訊，排程與網頁託管都用 GitHub 的免費額度。

## 建立步驟（第一次設定，大約 10 分鐘）

### 1. 建立 GitHub 儲存庫
1. 到 GitHub 建立一個新的 **Private** 或 **Public** repository，例如取名 `my-twstock-tracker`
2. 把這個資料夾裡的所有檔案上傳上去（可以直接把整個資料夾拖進 GitHub 網頁的上傳介面，或用 git 指令）

```bash
cd twstock-institutional
git init
git add .
git commit -m "初始化"
git branch -M main
git remote add origin https://github.com/你的帳號/my-twstock-tracker.git
git push -u origin main
```

### 2. 編輯你的持股清單
打開 `holdings.json`，把裡面的範例（台積電、鴻海）改成你自己的持股：

```json
{
  "holdings": [
    { "code": "2330", "name": "台積電", "market": "TWSE" },
    { "code": "6488", "name": "環球晶", "market": "TWSE" }
  ]
}
```

- `code`：股票代號
- `name`：股票名稱（隨便填，只是給自己看的顯示用文字）
- `market`：`TWSE`（上市）或 `TPEx`（上櫃）。不確定的話先填 `TWSE`，程式如果抓不到會提醒你，再改成 `TPEx` 即可

改完後 commit + push 上去即可，之後想加減持股，隨時回來編輯這個檔案。

### 3. 開啟 GitHub Pages（讓網頁能被瀏覽）
1. 到 repo 的 **Settings → Pages**
2. Source 選擇 **Deploy from a branch**
3. Branch 選擇 `main`，資料夾選擇 `/ (root)`
4. 存檔後，等 1-2 分鐘，GitHub 會給你一個網址，例如：
   `https://你的帳號.github.io/my-twstock-tracker/`
5. 打開這個網址，就是你的儀表板

### 4. 確認自動排程已啟用
- `.github/workflows/daily.yml` 已經幫你設定好，每個交易日下午 4:20（台灣時間）會自動執行一次
- 想立刻手動測試，不用等排程：到 repo 的 **Actions** 分頁 → 選擇「每日更新三大法人買賣超」→ 右上角 **Run workflow**

## 之後的日常使用
- 什麼都不用做，程式會每個交易日自動更新
- 想新增/刪除持股：編輯 `holdings.json` 後 push
- 想立即更新（不想等排程）：到 Actions 分頁手動 Run workflow

## 檔案說明
| 檔案 | 用途 |
|---|---|
| `holdings.json` | 你可以自己編輯的持股清單 |
| `fetch_institutional.py` | 每日抓資料、計算7日/30日加總的主程式 |
| `data/history.json` | 每檔股票的逐日歷史資料（程式自動維護） |
| `data/summary.json` | 給網頁看的摘要資料（程式自動維護） |
| `index.html` | 網頁儀表板 |
| `.github/workflows/daily.yml` | GitHub Actions 每日排程設定 |

## 已知限制
- 資料來源是證交所（TWSE）與櫃買中心（TPEx）的公開網頁 API，非官方正式文件化的介面，未來若對方網站改版，抓取程式可能需要跟著調整
- 如果某檔股票當天沒有交易或剛掛牌，該日會顯示抓不到資料的提醒，屬正常現象
- 免費 GitHub Actions 排程有時會延遲幾分鐘執行，屬正常現象
