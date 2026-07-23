#!/usr/bin/env python3
import html
import json
import math
import os
import re
import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlencode, urlparse
import requests
from bs4 import BeautifulSoup

# 환경 변수 로드 (Vercel 대시보드에서 등록 필요)
EVLINE_USER_ID = os.environ.get("EVLINE_USER_ID", "")
EVLINE_USER_PWD = os.environ.get("EVLINE_USER_PWD", "")
BASE_URL = "https://www.ev-line.co.kr"
DEFAULT_DETAIL_ID = "001513355667"
STATIONS = [
    {"id": "001513355667", "name": "동탄시범계룡리슈빌아파트"},
    {"id": "001544793284", "name": "네이버주식회사"},
    {"id": "184760000001", "name": "동탄역시범호반써밋아파트"},
]
STATION_NAME_BY_ID = {station["id"]: station["name"] for station in STATIONS}
MONTHLY_USAGE_LABELS = ("경부하", "중부하", "최대부하")
SEASONAL_TOU_RATES = {
    "summer": {
        "경부하": 83.2,
        "중부하": 137.4,
        "최대부하": 205.6,
    },
    "winter": {
        "경부하": 100.2,
        "중부하": 127.7,
        "최대부하": 179.4,
    },
    "other": {
        "경부하": 85.2,
        "중부하": 96.0,
        "최대부하": 99.9,
    },
}

PAGE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="60">
  <title>EV-Line</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #050706;
      --fg: #f7fff9;
      --muted: #a9b5ad;
      --line: #2a342e;
      --panel: #101511;
      --panel-2: #182019;
      --ok: #00e676;
      --ok-bg: #002914;
      --ok-line: #00592c;
      --warn: #ffd600;
      --warn-bg: #2b2400;
      --warn-line: #594b00;
      --bad: #ff1744;
      --bad-bg: #2b030b;
      --bad-line: #590a1a;
      --fav: #ffca28;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 16px;
      line-height: 1.4;
    }
    main { max-width: 600px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 16px;
    }
    h1 { font-size: 24px; font-weight: 850; letter-spacing: -0.5px; }
    .station { font-size: 14px; color: var(--muted); margin-top: 2px; }
    .meta { font-size: 11px; color: var(--muted); text-align: right; font-variant-numeric: tabular-nums; line-height: 1.6; }
    .actions { display: flex; gap: 8px; margin-bottom: 16px; }
    .actions a, .actions button {
      background: var(--panel);
      border: 1px solid var(--line);
      color: var(--fg);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 13px;
      text-decoration: none;
      cursor: pointer;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
    }
    .actions a:hover, .actions button:hover { background: var(--panel-2); border-color: var(--muted); }
    .station-switcher {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 20px;
      align-items: center;
    }
    .station-switcher-label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.02em;
      margin-right: 2px;
    }
    .station-switcher a {
      display: inline-flex;
      align-items: center;
      padding: 7px 11px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--fg);
      text-decoration: none;
      font-size: 13px;
      line-height: 1;
      white-space: nowrap;
    }
    .station-switcher a:hover { background: var(--panel-2); border-color: var(--muted); }
    .station-switcher a.is-current {
      background: var(--ok-bg);
      border-color: var(--ok-line);
      color: #b9ffd8;
      font-weight: 700;
    }
    .monthly-summary {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: linear-gradient(180deg, rgba(16, 21, 17, 0.98), rgba(9, 12, 10, 0.98));
    }
    .monthly-summary-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: flex-start;
    }
    .monthly-summary-title {
      font-size: 15px;
      font-weight: 800;
      letter-spacing: -0.02em;
    }
    .monthly-summary-subtitle {
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
    }
    .monthly-summary-note {
      color: var(--muted);
      font-size: 11px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .monthly-summary-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }
    .monthly-usage-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 11px;
      min-width: 0;
    }
    .monthly-usage-label {
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 6px;
      letter-spacing: 0.02em;
    }
    .monthly-usage-value {
      font-size: 20px;
      font-weight: 850;
      letter-spacing: -0.02em;
      line-height: 1.1;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .monthly-usage-unit {
      margin-left: 4px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
    }
    .monthly-summary.empty {
      border-color: var(--warn-line);
      background: var(--warn-bg);
    }
    .monthly-summary.empty .monthly-summary-title,
    .monthly-summary.empty .monthly-summary-subtitle {
      color: #fff3b0;
    }
    .fee-summary {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 16px;
      padding: 14px;
      border: 1px solid var(--ok-line);
      border-radius: 12px;
      background: linear-gradient(180deg, rgba(0, 41, 20, 0.96), rgba(6, 15, 10, 0.98));
    }
    .fee-summary-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: flex-start;
    }
    .fee-summary-head-line {
      width: 100%;
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
    }
    .fee-summary-title {
      font-size: 15px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #b9ffd8;
    }
    .fee-summary-subtitle {
      color: #92c7a9;
      font-size: 12px;
      margin-top: 3px;
    }
    .fee-summary-note {
      color: #92c7a9;
      font-size: 11px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .fee-summary-total {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      padding: 10px 12px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(185, 255, 216, 0.16);
    }
    .fee-summary-total-label {
      font-size: 11px;
      color: #b9ffd8;
      font-weight: 700;
      letter-spacing: 0.02em;
    }
    .fee-summary-total-value {
      font-size: 26px;
      font-weight: 900;
      letter-spacing: -0.03em;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .fee-summary-rate {
      color: #92c7a9;
      font-size: 11px;
      margin-top: 4px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .fee-summary-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    .fee-metric-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(185, 255, 216, 0.12);
      border-radius: 10px;
      padding: 10px 11px;
      min-width: 0;
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
    }
    .fee-metric-label {
      color: #92c7a9;
      font-size: 10px;
      letter-spacing: 0.02em;
      line-height: 1.2;
      flex: 1 1 auto;
    }
    .fee-metric-value {
      font-size: 18px;
      font-weight: 850;
      letter-spacing: -0.02em;
      line-height: 1.1;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
      text-align: right;
    }
    .fee-metric-unit {
      color: #92c7a9;
      font-size: 11px;
      line-height: 1.2;
      margin-left: 4px;
      white-space: nowrap;
    }
    .fee-mission-card {
      grid-column: 1 / -1;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(185, 255, 216, 0.12);
      border-radius: 10px;
      padding: 10px 11px;
    }
    .fee-mission-title {
      color: #92c7a9;
      font-size: 10px;
      letter-spacing: 0.02em;
      margin-bottom: 8px;
    }
    .fee-mission-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .fee-mission-row {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
    }
    .fee-mission-label {
      color: #e2f8e9;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .fee-mission-value {
      color: #f7fff9;
      font-size: 18px;
      font-weight: 850;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
      text-align: right;
    }
    .fee-mission-unit {
      color: #92c7a9;
      font-size: 11px;
      margin-left: 4px;
      white-space: nowrap;
    }
    .top-divider {
      border-top: 1px solid var(--line);
      margin: 12px 0 16px;
    }
    .dashboard { display: flex; flex-direction: column; gap: 12px; }
    .status-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .status-card.ok { background: var(--ok-bg); border-color: var(--ok-line); }
    .status-card.warn { background: var(--warn-bg); border-color: var(--warn-line); }
    .status-card.bad { background: var(--bad-bg); border-color: var(--bad-line); }
    .group {
      color: var(--muted);
      font-size: 20px;
      font-weight: 820;
      letter-spacing: 0;
    }
    .status-card.ok .group { color: #81c784; }
    .status-card.warn .group { color: #fff176; }
    .status-card.bad .group { color: #e57373; }
    .state {
      color: var(--fg);
      font-size: 29px;
      font-weight: 880;
      letter-spacing: 0;
    }
    .favorite {
      position: absolute;
      top: 12px;
      right: 12px;
      background: none;
      border: none;
      color: var(--line);
      font-size: 20px;
      cursor: pointer;
      padding: 4px;
      line-height: 1;
    }
    .status-card.is-favorite .favorite { color: var(--fav); }
    @media (max-width: 520px) {
      body { padding: 12px; }
      .group { font-size: 18px; }
      .state { font-size: 24px; }
    }
  </style>
</head>
<body>
  <main>
    __STATION_SWITCHER__
    <div class="top-divider" aria-hidden="true"></div>
    <header>
      <div>
        <h1>EV-Line</h1>
        __STATION__
      </div>
      <div class="meta">
        <div>__UPDATED__</div>
      </div>
    </header>
    <div class="actions">
      <a href="#" id="refresh-link">새로고침</a>
      <button type="button" id="choose-station" style="display: none;">충전소 선택</button>
      <button type="button" id="toggle-view">전체보기</button>
    </div>
    __FEE_ESTIMATE__
    __BODY__
  </main>
  <script>
    document.addEventListener("DOMContentLoaded", () => {
      const toggleView = document.getElementById("toggle-view");
      const refreshLink = document.getElementById("refresh-link");
      const cards = document.querySelectorAll(".status-card");
      
      // 1. 현재 URL에서 id 값을 추출 (없으면 기본값 지정)
      const urlParams = new URLSearchParams(window.location.search);
      const stationId = urlParams.get("id") || "__DEFAULT_ID__";
      
      // 새로고침 링크 동적 유지
      refreshLink.href = window.location.pathname + window.location.search;

      // 2. 스토리지 키 이름을 충전소 id 단위로 격리 분리 ('evline_favs_001513355667' 형태)
      const favKey = `evline_favs_id_${stationId}`;
      const showAllKey = `evline_show_all_id_${stationId}`;

      let favorites = JSON.parse(localStorage.getItem(favKey) || '[]');
      let showAll = localStorage.getItem(showAllKey) !== "0";

      function saveFavs() { localStorage.setItem(favKey, JSON.stringify(favorites)); }
      function updateToggleText() { toggleView.textContent = showAll ? "즐겨찾기만" : "전체보기"; }

      function applyFilter() {
        cards.forEach(card => {
          const g = card.getAttribute("data-group").toUpperCase();
          const isFav = favorites.includes(g);
          
          if (isFav) card.classList.add("is-favorite");
          else card.classList.remove("is-favorite");
          
          if (showAll) {
            card.style.display = "flex";
          } else {
            // 현재 충전소 id 기반의 즐겨찾기 목록에 포함된 그룹만 표시
            if (isFav) {
              card.style.display = "flex";
            } else {
              card.style.display = "none";
            }
          }
        });
      }

      cards.forEach(card => {
        const btn = card.querySelector(".favorite");
        const g = card.getAttribute("data-group").toUpperCase();
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          if (favorites.includes(g)) favorites = favorites.filter(x => x !== g);
          else favorites.push(g);
          saveFavs();
          applyFilter();
        });
      });

      toggleView.addEventListener("click", () => {
        showAll = !showAll;
        localStorage.setItem(showAllKey, showAll ? "1" : "0");
        updateToggleText();
        applyFilter();
      });

      updateToggleText();
      applyFilter();
    });
  </script>
</body>
</html>
"""

def get_authenticated_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari/537.36"
    })
    login_url = f"{BASE_URL}/login/login_ok.asp"
    payload = {
        "user_id": EVLINE_USER_ID,
        "user_pwd": EVLINE_USER_PWD,
        "url": "/login/login.asp"
    }
    headers = {"Referer": f"{BASE_URL}/login/login.asp"}
    try:
        session.post(login_url, data=payload, headers=headers, timeout=10)
    except Exception:
        pass
    return session

def fetch_monthly_usage(session):
    url = f"{BASE_URL}/asp/view_new.asp"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": f"{BASE_URL}/login/login.asp",
    }
    try:
        res = session.get(url, headers=headers, timeout=10)
        return res.content.decode("euc-kr", errors="ignore")
    except Exception as e:
        return f"데이터 패치 실패: {str(e)}"

def get_previous_month_yyyymm():
    now_kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    year = now_kst.year
    month = now_kst.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year}-{month:02d}"

def get_current_month_yyyymm():
    now_kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    return f"{now_kst.year}-{now_kst.month:02d}"

def fetch_billing_reference(session, yyyymm):
    url = f"{BASE_URL}/eacd/bill_202010.asp?ead_date={yyyymm}"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": f"{BASE_URL}/asp/bill.asp",
    }
    try:
        res = session.get(url, headers=headers, timeout=10)
        return res.content.decode("euc-kr", errors="ignore")
    except Exception as e:
        return f"데이터 패치 실패: {str(e)}"

def fetch_and_parse_detail(session, detail_id):
    url = f"{BASE_URL}/charge/mapdatadetail_202008.asp?id={detail_id}"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": f"{BASE_URL}/charge/serch.asp",
        "X-Requested-With": "XMLHttpRequest"
    }
    try:
        res = session.get(url, headers=headers, timeout=10)
        raw_html = res.content.decode('euc-kr', errors='ignore')
    except Exception as e:
        return f"데이터 패치 실패: {str(e)}"

    marker = '[{"id":"'
    if raw_html.startswith(marker) and raw_html.endswith('"}]'):
        raw_html = raw_html[len(marker):-3]
    raw_html = raw_html.replace('\\"', '"').replace('\\/', '/')
    if "alert('" in raw_html:
        alert_msg = re.search(r"alert\('([^']+)'\)", raw_html)
        return f"알림: {alert_msg.group(1)}" if alert_msg else "알림 발생"
    return raw_html

def _format_usage_value(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")

def _extract_number_after_label(text, label):
    patterns = [
        rf"{label}\s*(?:충전량)?\s*[:：]?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:kWh|kW|kw|kwh)?",
        rf"{label}.*?([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:kWh|kW|kw|kwh)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    return None

def _extract_int_from_rows(raw_html, label):
    soup = BeautifulSoup(raw_html, 'html.parser')
    for tr in soup.find_all('tr'):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all('td')]
        if len(cells) != 3:
            continue
        first_cell = cells[0].replace(" ", "")
        if first_cell != label.replace(" ", ""):
            continue
        for candidate in cells[1:]:
            cleaned = candidate.replace("원", "").replace(",", "").strip()
            if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", cleaned):
                return int(float(cleaned))
    return None

def _current_month_season():
    now_kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    month = now_kst.month
    if month in (6, 7, 8):
        return "summer"
    if month in (11, 12, 1, 2):
        return "winter"
    return "other"

def _get_mobile_rate_table():
    season = _current_month_season()
    return SEASONAL_TOU_RATES.get(season, {})

def _estimate_total_with_extra_low(usage_by_label, rates, extra_low_usage):
    low = float(usage_by_label.get("경부하", 0) or 0) + extra_low_usage
    mid = float(usage_by_label.get("중부하", 0) or 0)
    peak = float(usage_by_label.get("최대부하", 0) or 0)
    usage_total = low + mid + peak

    energy_total = (
        math.floor(low * rates.get("경부하", 0))
        + math.floor(mid * rates.get("중부하", 0))
        + math.floor(peak * rates.get("최대부하", 0))
    )
    climate_fee = math.floor(usage_total * 9)
    fuel_fee = math.floor(usage_total * 5)
    power_fund = math.floor((7740 + energy_total + climate_fee + fuel_fee) * 0.027)
    vat = math.floor((energy_total + 17740 + climate_fee + fuel_fee) * 0.1)
    total = energy_total + 17740 + power_fund + climate_fee + fuel_fee + vat
    return total, usage_total

def _find_additional_usage_for_target_rate(usage_by_label, rates, target_rate, step=0.01, max_extra_usage=1000.0):
    extra_usage = step
    while extra_usage <= max_extra_usage:
        total, usage = _estimate_total_with_extra_low(usage_by_label, rates, extra_usage)
        if total / usage < target_rate:
            return extra_usage
        extra_usage = round(extra_usage + step, 2)
    return None

def estimate_mobile_fee(monthly_usage, billing_reference_html, reference_month):
    rates = _get_mobile_rate_table()
    if not rates:
        return {}

    usage_total = sum(float(monthly_usage.get(label, 0) or 0) for label in MONTHLY_USAGE_LABELS)
    if usage_total <= 0:
        return {}

    energy_by_label = {}
    usage_by_label = {}
    for label in MONTHLY_USAGE_LABELS:
        usage = float(monthly_usage.get(label, 0) or 0)
        rate = rates.get(label)
        if rate is None:
            continue
        usage_by_label[label] = usage
        energy_by_label[label] = math.floor(usage * rate)

    energy_total = sum(energy_by_label.values())
    mobile_basic_fee = 17740
    climate_fee = math.floor(usage_total * 9)
    fuel_fee = math.floor(usage_total * 5)
    power_base_fee = 7740
    power_fund = math.floor((power_base_fee + energy_total + climate_fee + fuel_fee) * 0.027)
    vat = math.floor((energy_total + mobile_basic_fee + climate_fee + fuel_fee) * 0.1)
    total = energy_total + mobile_basic_fee + power_fund + climate_fee + fuel_fee + vat
    target_rates = (324, 300, 250, 200, 150)
    extra_usage_by_target = {}
    for target in target_rates:
        if total / usage_total <= target:
            extra_usage_by_target[target] = None
        else:
            extra_usage_by_target[target] = _find_additional_usage_for_target_rate(usage_by_label, rates, target)

    return {
        "reference_month": reference_month,
        "season": _current_month_season(),
        "usage_total": usage_total,
        "usage_by_label": usage_by_label,
        "energy_total": energy_total,
        "energy_by_label": energy_by_label,
        "mobile_basic_fee": mobile_basic_fee,
        "power_base_fee": power_base_fee,
        "power_fund": power_fund,
        "climate_fee": climate_fee,
        "fuel_fee": fuel_fee,
        "vat": vat,
        "total": total,
        "extra_usage_by_target": extra_usage_by_target,
        "rates": rates,
    }

def parse_monthly_usage(raw_html):
    soup = BeautifulSoup(raw_html, 'html.parser')
    text = soup.get_text(" ", strip=True)

    # "이번달 충전량" 구간을 우선적으로 탐색하고, 없으면 전체 텍스트에서 찾는다.
    search_chunks = []
    for anchor in ("이번달 충전량", "이번달", "월 충전량", "충전량"):
        idx = text.find(anchor)
        if idx >= 0:
            search_chunks.append(text[max(0, idx - 250): idx + 1500])
            break
    if not search_chunks:
        search_chunks.append(text)

    results = {}
    for label in MONTHLY_USAGE_LABELS:
        value = None
        for chunk in search_chunks:
            value = _extract_number_after_label(chunk, label)
            if value is not None:
                break
        if value is None:
            for node in soup.find_all(string=re.compile(label)):
                container_text = node.parent.get_text(" ", strip=True)
                value = _extract_number_after_label(container_text, label)
                if value is not None:
                    break
        results[label] = _format_usage_value(value)

    if not any(results.values()):
        return {}
    return results

def parse_station_name(raw_html):
    soup = BeautifulSoup(raw_html, 'html.parser')
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 2 and "충전소명" in tds[0].get_text():
            return tds[1].get_text(strip=True).replace('&nbsp;', ' ')
    return ""

def parse_group_states(raw_html):
    rows = {}
    soup = BeautifulSoup(raw_html, 'html.parser')
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) == 2:
            group_text = tds[0].get_text(strip=True)
            if len(group_text) == 1 and group_text.isalpha():
                state_text = tds[1].get_text(strip=True).replace('&nbsp;', ' ')
                rows[group_text.upper()] = state_text
    return rows

def render_dashboard(raw_html):
    rows = parse_group_states(raw_html)
    cards = []
    for group, state in sorted(rows.items()):
        kind = "ok" if "가능" in state else ("warn" if "확인" in state else "bad")
        cards.append(
            f'<section class="status-card {kind}" data-group="{html.escape(group)}">'
            f'<button type="button" class="favorite" aria-label="그룹 {group} 즐겨찾기">☆</button>'
            f'<div class="group">그룹 {group}</div>'
            f'<div class="state">{html.escape(state)}</div>'
            f'</section>'
        )
    return '<div class="dashboard">' + "".join(cards) + "</div>"

def render_fee_estimate(estimate):
    if not estimate:
        return (
            '<section class="fee-summary">'
            '<div class="fee-summary-head">'
            '<div class="fee-summary-head-line">'
            '<div class="fee-summary-title">이동형 충전기 예상 요금</div>'
            '<div class="fee-summary-subtitle">이번달 사용량을 기준으로 요금을 계산하지 못했습니다.</div>'
            '</div>'
            '<div class="fee-summary-note">여름철 단가표 기준</div>'
            '</div>'
            '</section>'
        )
    usage_total = f'{estimate["usage_total"]:.2f}'
    reference_month = html.escape(estimate["reference_month"])
    effective_rate = estimate["total"] / estimate["usage_total"] if estimate.get("usage_total") else 0
    usage_display = f'{estimate["usage_total"]:.2f}'
    extra_usage_by_target = estimate.get("extra_usage_by_target", {})
    mission_rows = []
    for target in (324, 300, 250, 200, 150):
        value = extra_usage_by_target.get(target)
        value_text = f'{value:.2f}' if value is not None else ''
        mission_rows.append(
            '<div class="fee-mission-row">'
            f'<div class="fee-mission-label">{target}원</div>'
            f'<div class="fee-mission-value">{value_text}</div>'
            '<div class="fee-mission-unit">kWh</div>'
            '</div>'
        )
    parts = [
        '<section class="fee-summary">',
        '<div class="fee-summary-head">',
        '<div class="fee-summary-head-line">',
        '<div class="fee-summary-title">이동형 충전기 예상 요금</div>',
        f'<div class="fee-summary-subtitle">{reference_month}</div>',
        '</div>',
        '<div class="fee-summary-grid">',
        '<div class="fee-metric-card">',
        '<div class="fee-metric-label">예상 총액</div>',
        '<div style="display:flex; align-items:baseline; gap:4px; margin-left:auto;">',
        f'<div class="fee-metric-value">{estimate["total"]:,}</div>',
        '<div class="fee-metric-unit">원</div>',
        '</div>',
        '</div>',
        '<div class="fee-metric-card">',
        '<div class="fee-metric-label">환산단가</div>',
        '<div style="display:flex; align-items:baseline; gap:4px; margin-left:auto;">',
        f'<div class="fee-metric-value">{effective_rate:.1f}</div>',
        '<div class="fee-metric-unit">원/kWh</div>',
        '</div>',
        '</div>',
        '<div class="fee-mission-card">',
        '<div class="fee-mission-title">목표</div>',
        '<div class="fee-mission-list">',
        ''.join(mission_rows),
        '</div>',
        '</div>',
        '</div>',
        '</section>',
    ]
    return ''.join(parts)

def render_monthly_usage(monthly_usage):
    if not monthly_usage:
        return (
            '<section class="monthly-summary empty">'
            '<div class="monthly-summary-head">'
            '<div>'
            '<div class="monthly-summary-title">이번달 충전량</div>'
            '<div class="monthly-summary-subtitle">충전량 정보를 불러오지 못했습니다.</div>'
            '</div>'
            '<div class="monthly-summary-note">view_new.asp</div>'
            '</div>'
            '</section>'
        )

    cards = []
    for label in MONTHLY_USAGE_LABELS:
        value = monthly_usage.get(label)
        display_value = value if value else "-"
        cards.append(
            '<div class="monthly-usage-card">'
            f'<div class="monthly-usage-label">{html.escape(label)}</div>'
            f'<div class="monthly-usage-value">{html.escape(display_value)}'
            '<span class="monthly-usage-unit">kWh</span>'
            '</div>'
            '</div>'
        )

    return (
        '<section class="monthly-summary">'
        '<div class="monthly-summary-head">'
        '<div>'
        '<div class="monthly-summary-title">이번달 충전량</div>'
        '<div class="monthly-summary-subtitle">경부하 / 중부하 / 최대부하 기준 누적 충전량</div>'
        '</div>'
        '<div class="monthly-summary-note">view_new.asp</div>'
        '</div>'
        '<div class="monthly-summary-grid">'
        + "".join(cards)
        + '</div>'
        '</section>'
    )

def render_station_switcher(current_id):
    items = []
    for station in STATIONS:
        station_id = station["id"]
        name = html.escape(station["name"])
        is_current = station_id == current_id
        current_attr = ' aria-current="page"' if is_current else ""
        class_attr = "is-current" if is_current else ""
        items.append(
            f'<a class="{class_attr}" '
            f'href="?id={html.escape(station_id)}"{current_attr}>'
            f'{name}</a>'
        )
    return (
        '<nav class="station-switcher" aria-label="충전소 전환">'
        '<span class="station-switcher-label">충전소</span>'
        + "".join(items)
        + "</nav>"
    )

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path not in ("/", "/healthz"):
            self.send_error(404)
            return
        if parsed.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok\n")
            return

        query = parse_qs(parsed.query)
        detail_id = query.get("id", [DEFAULT_DETAIL_ID])[0].strip()

        session = get_authenticated_session()
        raw_html = fetch_and_parse_detail(session, detail_id)
        monthly_usage_html = fetch_monthly_usage(session)
        reference_month = get_current_month_yyyymm()
        billing_reference_html = fetch_billing_reference(session, reference_month)

        station = parse_station_name(raw_html)
        station_label = STATION_NAME_BY_ID.get(detail_id, station)
        formatted_body = render_dashboard(raw_html)
        monthly_usage = parse_monthly_usage(monthly_usage_html)
        fee_estimate = estimate_mobile_fee(monthly_usage, billing_reference_html, reference_month)
        formatted_fee_estimate = render_fee_estimate(fee_estimate)

        updated = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        response_html = PAGE
        response_html = response_html.replace("__UPDATED__", html.escape(updated))
        response_html = response_html.replace("__DEFAULT_ID__", DEFAULT_DETAIL_ID)
        response_html = response_html.replace("__STATION__", f'<div class="station">{html.escape(station_label)}</div>' if station_label else "")
        response_html = response_html.replace("__STATION_SWITCHER__", render_station_switcher(detail_id))
        response_html = response_html.replace("__FEE_ESTIMATE__", formatted_fee_estimate)
        response_html = response_html.replace("__BODY__", formatted_body)

        data = response_html.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
