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
    .top-divider {
      border-top: 1px solid var(--line);
      margin: 12px 0 16px;
    }
    .dashboard { display: flex; flex-direction: column; gap: 12px; }
    .status-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px;
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .status-card.ok { background: var(--ok-bg); border-color: var(--ok-line); }
    .status-card.warn { background: var(--warn-bg); border-color: var(--warn-line); }
    .status-card.bad { background: var(--bad-bg); border-color: var(--bad-line); }
    .group {
      color: var(--muted);
      font-size: 24px;
      font-weight: 820;
      letter-spacing: 0;
    }
    .status-card.ok .group { color: #81c784; }
    .status-card.warn .group { color: #fff176; }
    .status-card.bad .group { color: #e57373; }
    .state {
      color: var(--fg);
      font-size: 36px;
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
      .group { font-size: 20px; }
      .state { font-size: 28px; }
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

        station = parse_station_name(raw_html)
        station_label = STATION_NAME_BY_ID.get(detail_id, station)
        formatted_body = render_dashboard(raw_html)

        updated = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        response_html = PAGE
        response_html = response_html.replace("__UPDATED__", html.escape(updated))
        response_html = response_html.replace("__DEFAULT_ID__", DEFAULT_DETAIL_ID)
        response_html = response_html.replace("__STATION__", f'<div class="station">{html.escape(station_label)}</div>' if station_label else "")
        response_html = response_html.replace("__STATION_SWITCHER__", render_station_switcher(detail_id))
        response_html = response_html.replace("__BODY__", formatted_body)

        data = response_html.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
