
#!/usr/bin/env python3
import html
import json
import math
import os
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlencode, urlparse
import requests
from bs4 import BeautifulSoup

# 환경 변수 로드 (Vercel 대시보드에서 등록 가능)
EVLINE_USER_ID = os.environ.get("EVLINE_USER_ID", "")
EVLINE_USER_PWD = os.environ.get("EVLINE_USER_PWD", "")
BASE_URL = "https://www.ev-line.co.kr"
STATION_API = "/charge/new_mapdataadd_202008.asp"

# 앞서 작성하신 아름다운 다크모드 HTML UI 템플릿 (PAGE 생략 - 기존 소스 그대로 사용 가능)
PAGE = """...""" # (이전 코드의 HTML PAGE 템플릿을 그대로 복사해서 넣어주세요)

def get_authenticated_session():
    """
    Vercel은 파일 쓰기가 제한되므로, 파일(.cookies.txt) 대신 
    메모리 상에서 requests.Session 객체를 생성하여 세션을 유지합니다.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari/537.36"
    })
    
    # 로그인 요청
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
    """
    기존 쉘 스크립트와 Perl 정규식 파싱을 대체하는 순수 파이썬 로직입니다.
    EUC-KR 디코딩 후 BeautifulSoup으로 데이터를 정제합니다.
    """
    url = f"{BASE_URL}/charge/mapdatadetail_202008.asp?id={detail_id}"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": f"{BASE_URL}/charge/serch.asp",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        res = session.get(url, headers=headers, timeout=10)
        # EUC-KR 수동 지정 디코딩
        raw_html = res.content.decode('euc-kr', errors='ignore')
    except Exception as e:
        return f"데이터 패치 실패: {str(e)}"

    # JSON 래핑 언패킹 ([{"id":"..."}])
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
            # 알파벳 1글자 그룹명 필터링 (A, B, C...)
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

class handler(BaseHTTPRequestHandler):
    """
    Vercel 서버리스 환경은 이 'handler' 클래스를 인스턴스화하여 인바운드 요청을 처리합니다.
    """
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
        detail_id = query.get("id", ["001513355667"])[0].strip()

        # 매 요청마다 메모리 세션을 열어 인증을 수행
        session = get_authenticated_session()
        raw_html = fetch_and_parse_detail(session, detail_id)

        station = parse_station_name(raw_html)
        formatted_body = render_dashboard(raw_html)

        # 시간대 가져오기 (Vercel서버 시간 기준 단순 출력 대신 가독성 포맷팅)
        import datetime
        updated = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        data = PAGE.format(
            updated=html.escape(updated),
            station=f'<div class="station">{html.escape(station)}</div>' if station else "",
            body=formatted_body,
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)