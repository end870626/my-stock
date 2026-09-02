#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日抓取台股持股的三大法人買賣超資料。

資料來源（皆為免費公開資訊，不需 API key）：
- 上市（TWSE）：https://www.twse.com.tw/rwd/zh/fund/T86
- 上櫃（TPEx）：https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php

執行方式：
    python fetch_institutional.py

會自動：
1. 讀取 holdings.json 裡的持股清單
2. 抓取「最近一個有資料的交易日」的三大法人買賣超（股數，換算成「張」＝1000股）
3. 把當日資料累加進 data/history.json（每檔股票一份逐日歷史）
4. 重新計算 7 日 / 30 日 買賣超加總，寫入 data/summary.json 給網頁儀表板使用
"""
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HOLDINGS_FILE = BASE_DIR / "holdings.json"
HISTORY_FILE = BASE_DIR / "data" / "history.json"
SUMMARY_FILE = BASE_DIR / "data" / "summary.json"

TWSE_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"
TPEX_URL = "https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; personal-portfolio-tracker/1.0)"
}

TAIPEI_TZ = timezone(timedelta(hours=8))


def http_get_json(url: str, params: dict, retries: int = 3, timeout: int = 20):
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(full_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8-sig", errors="replace")
                return json.loads(raw)
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2)
    print(f"[警告] 抓取失敗：{full_url}\n原因：{last_err}")
    return None


def to_number(s):
    """把 '1,234' 或 '' 或 '--' 轉成 int，抓不到就回傳 0"""
    if s is None:
        return 0
    s = str(s).replace(",", "").strip()
    if s in ("", "--", "-"):
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def fetch_twse_day(date_str: str):
    """
    date_str: YYYYMMDD
    回傳 {股票代號: {foreign, trust, dealer, total}}（單位：股）
    """
    payload = http_get_json(TWSE_URL, {"date": date_str, "selectType": "ALL", "response": "json"})
    if not payload or payload.get("stat") != "OK":
        return None

    fields = payload.get("fields", [])
    rows = payload.get("data", [])
    result = {}
    for row in rows:
        rec = dict(zip(fields, row))
        code = str(rec.get("證券代號", "")).strip()
        if not code:
            continue
        foreign = to_number(rec.get("外資買賣超股數") or rec.get("外陸資買賣超股數(不含外資自營商)"))
        trust = to_number(rec.get("投信買賣超股數"))
        dealer = to_number(rec.get("自營商買賣超股數"))
        total = to_number(rec.get("三大法人買賣超股數"))
        result[code] = {
            "foreign": foreign,
            "trust": trust,
            "dealer": dealer,
            "total": total if total else (foreign + trust + dealer),
        }
    return result


def fetch_tpex_day(date_str: str):
    """
    date_str: YYYYMMDD（西元），TPEx 需要民國年 yyy/mm/dd
    回傳 {股票代號: {foreign, trust, dealer, total}}（單位：股）
    """
    y = int(date_str[:4]) - 1911
    m = date_str[4:6]
    d = date_str[6:8]
    roc_date = f"{y}/{m}/{d}"

    payload = http_get_json(
        TPEX_URL,
        {"l": "zh-tw", "se": "AL", "t": "D", "d": roc_date, "o": "json"},
    )
    if not payload:
        return None

    rows = payload.get("aaData") or payload.get("data") or []
    if not rows:
        return None

    result = {}
    for row in rows:
        try:
            code = str(row[0]).strip()
            # 欄位順序: 代號,名稱,外資及陸資買,賣,買賣超,外資自營商買,賣,買賣超,
            #          投信買,賣,買賣超,自營商買,賣,買賣超,自營商買賣超避險,...,三大法人買賣超
            foreign = to_number(row[4])
            trust = to_number(row[10])
            dealer = to_number(row[13])
            total = to_number(row[-1])
            result[code] = {
                "foreign": foreign,
                "trust": trust,
                "dealer": dealer,
                "total": total if total else (foreign + trust + dealer),
            }
        except (IndexError, ValueError):
            continue
    return result


def find_latest_trading_day(holdings_codes, max_back_days=10):
    """從今天往回找，直到抓到有資料的一天（跳過假日/尚未公布）"""
    now_taipei = datetime.now(TAIPEI_TZ)
    for back in range(0, max_back_days):
        d = now_taipei - timedelta(days=back)
        date_str = d.strftime("%Y%m%d")
        print(f"嘗試抓取日期：{date_str} ...")
        twse_data = fetch_twse_day(date_str)
        tpex_data = fetch_tpex_day(date_str)
        if twse_data or tpex_data:
            return date_str, (twse_data or {}), (tpex_data or {})
        time.sleep(1)
    return None, {}, {}


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    holdings_conf = load_json(HOLDINGS_FILE, {"holdings": []})
    holdings = holdings_conf.get("holdings", [])
    if not holdings:
        print("holdings.json 裡沒有任何持股，請先編輯後再執行。")
        return

    codes = [h["code"] for h in holdings]
    date_str, twse_data, tpex_data = find_latest_trading_day(codes)

    if date_str is None:
        print("找不到最近的交易日資料，可能是假日或來源網站異常，本次不更新。")
        return

    history = load_json(HISTORY_FILE, {})

    for h in holdings:
        code = h["code"]
        name = h.get("name", code)
        market = h.get("market", "TWSE").upper()

        src = twse_data if market != "TPEX" else tpex_data
        # 找不到就兩邊都試試看（避免使用者填錯市場別）
        rec = src.get(code) or twse_data.get(code) or tpex_data.get(code)

        if rec is None:
            print(f"[提醒] {code} {name}：{date_str} 抓不到三大法人資料（可能當天無交易、剛掛牌，或市場別設定錯誤）")
            continue

        stock_history = history.setdefault(code, {"name": name, "market": market, "daily": []})
        stock_history["name"] = name  # 保持名稱最新

        daily = stock_history["daily"]
        if daily and daily[-1]["date"] == date_str:
            daily[-1] = {"date": date_str, **rec}
        else:
            daily.append({"date": date_str, **rec})

        # 只保留最近 400 個交易日，避免檔案無限長大
        stock_history["daily"] = daily[-400:]

    save_json(HISTORY_FILE, history)

    # 計算 7 日 / 30 日 加總，寫成給網頁用的摘要
    summary = {"updated_at": date_str, "stocks": []}
    for code, stock_history in history.items():
        daily = stock_history["daily"]
        last_7 = daily[-7:]
        last_30 = daily[-30:]

        def agg(records):
            return {
                "foreign": sum(r["foreign"] for r in records),
                "trust": sum(r["trust"] for r in records),
                "dealer": sum(r["dealer"] for r in records),
                "total": sum(r["total"] for r in records),
            }

        latest = daily[-1] if daily else None
        summary["stocks"].append(
            {
                "code": code,
                "name": stock_history.get("name", code),
                "market": stock_history.get("market", "TWSE"),
                "latest_date": latest["date"] if latest else None,
                "latest": {
                    "foreign": latest["foreign"],
                    "trust": latest["trust"],
                    "dealer": latest["dealer"],
                    "total": latest["total"],
                }
                if latest
                else None,
                "last_7_days": agg(last_7),
                "last_30_days": agg(last_30),
                "history_days": len(daily),
            }
        )

    save_json(SUMMARY_FILE, summary)
    print(f"完成！最新資料日期：{date_str}，共更新 {len(summary['stocks'])} 檔股票。")


if __name__ == "__main__":
    main()
