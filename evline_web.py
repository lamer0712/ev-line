#!/usr/bin/env python3
import html
import json
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse


HOST = os.environ.get("EVLINE_WEB_HOST", "0.0.0.0")
PORT = int(os.environ.get("EVLINE_WEB_PORT", "8787"))
APP_DIR = os.path.dirname(os.path.abspath(__file__))
FETCH_SCRIPT = os.path.join(APP_DIR, "evline_fetch.sh")
COOKIE_FILE = os.path.join(APP_DIR, ".evline.cookies.txt")
BASE_URL = "https://www.ev-line.co.kr"
STATION_API = "/charge/new_mapdataadd_202008.asp"


PAGE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="60">
  <title>EV-Line</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #050706;
      --fg: #f7fff9;
      --muted: #a9b5ad;
      --line: #2a342e;
      --panel: #101511;
      --panel-2: #182019;
      --accent: #84f4bd;
      --ok: #87ffbd;
      --warn: #ffd86b;
      --bad: #ff7f7f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
      line-height: 1.25;
    }}
    main {{
      width: min(960px, calc(100vw - 40px));
      margin: 0 auto;
      padding: 28px 0 32px;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0;
      font-size: 40px;
      font-weight: 820;
      letter-spacing: 0;
    }}
    .title {{
      display: flex;
      align-items: baseline;
      gap: 14px;
      min-width: 0;
    }}
    .station {{
      color: var(--muted);
      font-size: 24px;
      font-weight: 720;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .meta {{
      color: var(--muted);
      font-size: 18px;
      font-weight: 650;
      text-align: right;
      white-space: nowrap;
    }}
    pre, .content {{
      margin: 0;
      padding: 18px;
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    pre {{
      font: 15px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      white-space: pre-wrap;
    }}
    .content {{
      font-size: 15px;
      color: var(--fg);
    }}
    .dashboard {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
    }}
    .status-card {{
      position: relative;
      min-height: 270px;
      display: grid;
      align-content: center;
      gap: 18px;
      padding: 30px 84px 30px 30px;
      border: 2px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .status-card.hidden {{
      display: none;
    }}
    .favorite {{
      position: absolute;
      top: 18px;
      right: 18px;
      width: 58px;
      height: 58px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.04);
      color: var(--muted);
      font-size: 40px;
      line-height: 1;
      cursor: pointer;
    }}
    .favorite.active {{
      color: #ffd86b;
      border-color: #8c6b23;
      background: rgba(255, 216, 107, 0.12);
    }}
    .status-card.ok {{
      border-color: #2d8058;
      background: #0b2318;
    }}
    .status-card.warn {{
      border-color: #8c6b23;
      background: #251d0d;
    }}
    .status-card.bad {{
      border-color: #803535;
      background: #261111;
    }}
    .group {{
      color: var(--muted);
      font-size: 38px;
      font-weight: 820;
      letter-spacing: 0;
    }}
    .state {{
      color: var(--fg);
      font-size: 50px;
      font-weight: 880;
      letter-spacing: 0;
    }}
    .status-card.ok .state {{
      color: var(--ok);
    }}
    .status-card.warn .state {{
      color: var(--warn);
    }}
    .status-card.bad .state {{
      color: var(--bad);
    }}
    .content table {{
      width: 100%;
      border-collapse: collapse;
      margin: 8px 0 12px;
      color: var(--fg) !important;
      background: var(--panel) !important;
    }}
    .content td {{
      padding: 8px 10px;
      border: 1px solid var(--line);
      color: var(--fg) !important;
      background: var(--panel) !important;
    }}
    .content td:first-child {{
      width: 88px;
      color: var(--muted) !important;
      font-weight: 650;
    }}
    .content [bgcolor="#999999"] {{
      color: white !important;
      background: var(--accent-strong) !important;
      font-weight: 760;
    }}
    .content [bgcolor="#E7E7E7"] {{
      color: var(--fg) !important;
      background: var(--panel-2) !important;
      font-weight: 760;
    }}
    .content font[color="blue"] {{
      color: var(--ok) !important;
      font-weight: 700;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    .actions {{
      display: flex;
      justify-content: flex-end;
      flex-wrap: wrap;
      gap: 18px;
      margin: 0 0 22px;
      font-size: 20px;
      font-weight: 720;
    }}
    .actions a, .actions button {{
      min-height: 56px;
      display: inline-flex;
      align-items: center;
      padding: 0 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--accent);
      font: inherit;
      cursor: pointer;
    }}
    .station-panel {{
      display: none;
      margin: 0 0 22px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .station-panel.open {{
      display: block;
    }}
    .panel-title {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
      color: var(--muted);
      font-size: 20px;
      font-weight: 760;
    }}
    .station-list {{
      display: grid;
      gap: 12px;
    }}
    .station-row {{
      display: grid;
      grid-template-columns: 58px 1fr auto;
      align-items: center;
      gap: 14px;
      min-height: 76px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-2);
    }}
    .station-favorite {{
      width: 52px;
      height: 52px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.04);
      color: var(--muted);
      font-size: 34px;
      cursor: pointer;
    }}
    .station-favorite.active {{
      color: #ffd86b;
      border-color: #8c6b23;
      background: rgba(255, 216, 107, 0.12);
    }}
    .station-name {{
      color: var(--fg);
      font-size: 22px;
      font-weight: 760;
    }}
    .station-sub {{
      margin-top: 4px;
      color: var(--muted);
      font-size: 16px;
      font-weight: 650;
    }}
    .station-select {{
      min-height: 52px;
      padding: 0 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0b2318;
      color: var(--ok);
      font-size: 18px;
      font-weight: 760;
      cursor: pointer;
    }}
    @media (max-width: 520px) {{
      header {{
        display: block;
      }}
      .meta {{
        margin-top: 8px;
        text-align: left;
      }}
      h1 {{
        font-size: 32px;
      }}
      .title {{
        display: block;
      }}
      .station {{
        margin-top: 4px;
        font-size: 18px;
      }}
      .dashboard {{
        grid-template-columns: 1fr;
      }}
      .status-card {{
        min-height: 210px;
        padding-right: 78px;
      }}
      .state {{
        font-size: 38px;
      }}
      .station-row {{
        grid-template-columns: 52px 1fr;
      }}
      .station-select {{
        grid-column: 1 / -1;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="title">
        <h1>EV-Line</h1>
        {station}
      </div>
      <div class="meta">{updated}</div>
    </header>
    <div class="actions">
      <a href="/">새로고침</a>
      <button type="button" id="choose-station" style="display: none;">충전소 선택</button>
      <button type="button" id="toggle-view">전체보기</button>
    </div>
    <section class="station-panel" id="station-panel">
      <div class="panel-title">
        <span id="station-panel-title">주변 충전소</span>
      </div>
      <div class="station-list" id="station-list"></div>
    </section>
    {body}
  </main>
  <script>
    (() => {{
      const key = "evline.favoriteGroups";
      const stationKey = "evline.favoriteStations";
      const selectedStationKey = "evline.selectedStationId";
      const cards = [...document.querySelectorAll(".status-card")];
      const toggle = document.querySelector("#toggle-view");
      const chooseStation = document.querySelector("#choose-station");
      const stationPanel = document.querySelector("#station-panel");
      const stationPanelTitle = document.querySelector("#station-panel-title");
      const stationList = document.querySelector("#station-list");
      let showAll = false;
      let stationPanelOpen = false;

      const params = new URLSearchParams(location.search);
      const selectedStation = localStorage.getItem(selectedStationKey);
      if (!params.has("id") && selectedStation) {{
        location.replace(`/?id=${{encodeURIComponent(selectedStation)}}`);
        return;
      }}

      const load = () => {{
        try {{
          return new Set(JSON.parse(localStorage.getItem(key) || "[]"));
        }} catch (_) {{
          return new Set();
        }}
      }};

      const save = (favorites) => {{
        localStorage.setItem(key, JSON.stringify([...favorites].sort()));
      }};

      const loadStations = () => {{
        try {{
          return JSON.parse(localStorage.getItem(stationKey) || "[]");
        }} catch (_) {{
          return [];
        }}
      }};

      const saveStations = (stations) => {{
        localStorage.setItem(stationKey, JSON.stringify(stations));
      }};

      const stationFavorites = () => new Map(loadStations().map((station) => [station.id, station]));

      const saveStationFavorite = (station) => {{
        const favorites = stationFavorites();
        if (favorites.has(station.id)) {{
          favorites.delete(station.id);
        }} else {{
          favorites.set(station.id, {{
            id: station.id,
            name: station.name,
            lat: station.lat,
            lng: station.lng,
            count: station.count
          }});
          localStorage.setItem(selectedStationKey, station.id);
        }}
        saveStations([...favorites.values()]);
      }};

      const render = () => {{
        const favorites = load();
        const hasFavorites = favorites.size > 0;
        cards.forEach((card) => {{
          const group = card.dataset.group;
          const starred = favorites.has(group);
          const favorite = card.querySelector(".favorite");
          favorite.classList.toggle("active", starred);
          favorite.textContent = starred ? "★" : "☆";
          card.classList.toggle("hidden", hasFavorites && !showAll && !starred);
        }});
        if (toggle) {{
          toggle.textContent = showAll ? "즐겨찾기" : "전체보기";
        }}
      }};

      cards.forEach((card) => {{
        card.querySelector(".favorite").addEventListener("click", () => {{
          const favorites = load();
          const group = card.dataset.group;
          if (favorites.has(group)) {{
            favorites.delete(group);
          }} else {{
            favorites.add(group);
          }}
          save(favorites);
          render();
        }});
      }});

      if (toggle) {{
        toggle.addEventListener("click", () => {{
          showAll = !showAll;
          render();
        }});
      }}

      const renderStationList = (stations, title) => {{
        stationPanelOpen = true;
        stationPanel.classList.add("open");
        stationPanelTitle.textContent = title;
        const favorites = stationFavorites();
        stationList.innerHTML = "";
        stations.forEach((station) => {{
          const row = document.createElement("div");
          row.className = "station-row";

          const star = document.createElement("button");
          star.type = "button";
          star.className = "station-favorite";
          star.textContent = favorites.has(station.id) ? "★" : "☆";
          star.classList.toggle("active", favorites.has(station.id));
          star.setAttribute("aria-label", `${{station.name}} 즐겨찾기`);

          const info = document.createElement("div");
          const distance = station.distance_m == null ? "" : `${{Math.round(station.distance_m)}}m`;
          info.innerHTML = `
            <div class="station-name">${{escapeHtml(station.name)}}</div>
            <div class="station-sub">${{distance}} · 충전기 ${{escapeHtml(String(station.count || "-"))}}대</div>
          `;

          const select = document.createElement("button");
          select.type = "button";
          select.className = "station-select";
          select.textContent = "선택";

          star.addEventListener("click", () => {{
            saveStationFavorite(station);
            renderStationList(stations, title);
          }});
          select.addEventListener("click", () => {{
            localStorage.setItem(selectedStationKey, station.id);
            location.href = `/?id=${{encodeURIComponent(station.id)}}`;
          }});

          row.append(star, info, select);
          stationList.append(row);
        }});
      }};

      const escapeHtml = (value) => value.replace(/[&<>"']/g, (char) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }}[char]));

      if (chooseStation) {{
        chooseStation.addEventListener("click", () => {{
          stationPanelOpen = !stationPanelOpen;
          if (stationPanelOpen && loadStations().length) {{
            renderStationList(loadStations(), "즐겨찾는 충전소");
            return;
          }}
          if (!stationPanelOpen) {{
            stationPanel.classList.remove("open");
            return;
          }}
          const saved = loadStations();
          if (saved.length) {{
            renderStationList(saved, "즐겨찾는 충전소");
          }}

          if (!navigator.geolocation) {{
            stationPanel.classList.add("open");
            stationPanelTitle.textContent = "위치 사용 불가";
            stationList.innerHTML = '<div class="station-sub">이 브라우저는 현재 위치를 지원하지 않습니다.</div>';
            return;
          }}

          stationPanel.classList.add("open");
          stationPanelTitle.textContent = "현재 위치 확인 중";
          stationList.innerHTML = '<div class="station-sub">주변 충전소를 찾고 있습니다.</div>';

          navigator.geolocation.getCurrentPosition(async (position) => {{
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            stationPanelTitle.textContent = "주변 충전소";
            try {{
              const response = await fetch(`/api/stations?lat=${{encodeURIComponent(lat)}}&lng=${{encodeURIComponent(lng)}}`);
              if (!response.ok) throw new Error("station lookup failed");
              const stations = await response.json();
              renderStationList(stations, stations.length ? "주변 충전소" : "주변 충전소 없음");
            }} catch (_) {{
              stationPanelTitle.textContent = "조회 실패";
              stationList.innerHTML = '<div class="station-sub">주변 충전소를 가져오지 못했습니다.</div>';
            }}
          }}, () => {{
            const saved = loadStations();
            if (saved.length) {{
              renderStationList(saved, "즐겨찾는 충전소");
              return;
            }}
            stationPanel.classList.add("open");
            stationPanelTitle.textContent = "위치 권한 필요";
            stationList.innerHTML = '<div class="station-sub">현재 위치 권한을 허용하면 주변 충전소를 찾을 수 있습니다.</div>';
          }}, {{
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 30000
          }});
        }});
      }}

      render();
    }})();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/stations":
            self.respond_stations(parsed)
            return

        if parsed.path not in ("/", "/raw", "/text", "/healthz"):
            self.send_error(404)
            return

        if parsed.path == "/healthz":
            self.respond_text("ok\n")
            return

        query = parse_qs(parsed.query)
        detail_id = query.get("id", [""])[0].strip()
        args = [FETCH_SCRIPT]
        if parsed.path in ("/", "/raw"):
            args.append("--raw")
        if detail_id:
            args.append(detail_id)

        try:
            result = subprocess.run(
                args,
                cwd=APP_DIR,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=25,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.respond_html("EV-Line", "요청 시간이 초과되었습니다.")
            return

        output = result.stdout.strip() or result.stderr.strip()
        if result.returncode != 0:
            output = f"오류가 발생했습니다.\\n\\n{output}"

        station = ""
        if parsed.path in ("/", "/raw"):
            station = parse_station_name(extract_raw_html(output))

        updated = subprocess.run(
            ["date", "+%Y-%m-%d %H:%M:%S"],
            text=True,
            stdout=subprocess.PIPE,
            check=False,
        ).stdout.strip()
        render_raw_html = parsed.path == "/"
        self.respond_html(updated, output, render_raw_html, station)

    def respond_text(self, body):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_json(self, body, status=200):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_stations(self, parsed):
        query = parse_qs(parsed.query)
        try:
            lat = float(query.get("lat", [""])[0])
            lng = float(query.get("lng", [""])[0])
            radius_m = float(query.get("radius_m", ["1200"])[0])
        except ValueError:
            self.respond_json({"error": "lat and lng are required"}, 400)
            return

        try:
            stations = fetch_stations(lat, lng, radius_m)
        except RuntimeError as error:
            self.respond_json({"error": str(error)}, 502)
            return

        self.respond_json(stations)

    def respond_html(self, updated, body, render_raw_html=False, station=""):
        formatted_body = f"<pre>{html.escape(body)}</pre>"
        if render_raw_html:
            formatted_body = render_dashboard(extract_raw_html(body))
        station_html = ""
        if station:
            station_html = f'<div class="station">{html.escape(station)}</div>'

        data = PAGE.format(
            updated=html.escape(updated),
            station=station_html,
            body=formatted_body,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def extract_raw_html(raw):
    marker = '[{"id":"'
    if raw.startswith(marker) and raw.endswith('"}]'):
        raw = raw[len(marker):-3]
    raw = raw.replace('\\"', '"').replace("\\/", "/")
    return raw


def parse_station_name(raw_html):
    """
    raw_html 내에서 충전소명 엘리먼트를 찾아 텍스트를 반환합니다.
    """
    # <tr> 또는 <td> 구조 내에서 '충전소명'을 키로 매칭합니다.
    match = re.search(
        r"<td[^>]*>\s*충전소명\s*</td>\s*<td[^>]*>(.*?)</td>",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        name_html = match.group(1)
        # HTML 태그 제거 및 공백 정리
        name = re.sub(r"<[^>]+>", "", name_html)
        name = re.sub(r"\s+", " ", name).strip()
        return name
    return ""


def render_dashboard(raw_html):
    rows = parse_group_states(raw_html)
    cards = []
    for group, state in sorted(rows.items()):
        cards.append(
            '<section class="status-card {kind}" data-group="{group}">'
            '<button type="button" class="favorite" aria-label="그룹 {group} 즐겨찾기">☆</button>'
            '<div class="group">그룹 {group}</div>'
            '<div class="state">{state}</div>'
            "</section>".format(
                kind=state_kind(state),
                group=html.escape(group),
                state=html.escape(state),
            )
        )
    return '<div class="dashboard">' + "".join(cards) + "</div>"


def parse_group_states(raw_html):
    rows = {}
    for group, state_html in re.findall(
        r"<tr>\s*<td[^>]*>\s*([A-Z])\s*</td>\s*<td[^>]*>(.*?)</td>\s*</tr>",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        state = re.sub(r"<[^>]+>", "", state_html)
        state = re.sub(r"\s+", " ", state).strip()
        rows[group.upper()] = state
    return rows


def state_kind(state):
    if "가능" in state:
        return "ok"
    if "확인" in state:
        return "warn"
    return "bad"


def fetch_stations(lat, lng, radius_m):
    login = subprocess.run(
        [FETCH_SCRIPT, "--login-only"],
        cwd=APP_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if login.returncode != 0:
        raise RuntimeError(login.stderr.strip() or "login failed")

    # EV-Line's API uses swapped field names: lat is longitude, lng is latitude.
    bounds = compute_bounds(lat, lng, radius_m)
    params = urlencode(
        {
            "level": "4",
            "swLat": bounds["sw_lng"],
            "neLat": bounds["ne_lng"],
            "swLng": bounds["sw_lat"],
            "neLng": bounds["ne_lat"],
        }
    )
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "-L",
            "-b",
            COOKIE_FILE,
            "-H",
            "Accept: */*",
            "-H",
            f"Referer: {BASE_URL}/charge/serch.asp",
            "-H",
            "X-Requested-With: XMLHttpRequest",
            "-A",
            "Mozilla/5.0",
            f"{BASE_URL}{STATION_API}?{params}",
        ],
        cwd=APP_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "station lookup failed")

    raw = result.stdout.strip()
    if raw.startswith("[") and raw.endswith("]"):
        stations = json.loads(raw)
    else:
        stations = json.loads(extract_raw_html(raw))

    out = []
    for station in stations:
        name = str(station.get("cont", "")).strip()
        station_id = str(station.get("id", "")).strip()
        if not name or not station_id:
            continue
        lon = safe_float(station.get("lat"))
        lat2 = safe_float(station.get("lng"))
        distance_m = haversine_m(lat, lng, lat2, lon) if lat2 is not None and lon is not None else None
        out.append(
            {
                "id": station_id,
                "name": name,
                "count": safe_int(station.get("su")),
                "lat": lat2,
                "lng": lon,
                "distance_m": distance_m,
            }
        )
    out.sort(key=lambda item: (item["distance_m"] is None, item["distance_m"] or 0.0, item["name"]))
    return out


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value):
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compute_bounds(lat, lng, radius_m):
    lat_delta = radius_m / 111_320.0
    lng_delta = radius_m / max(1.0, 111_320.0 * math.cos(math.radians(lat)))
    return {
        "sw_lat": lat - lat_delta,
        "ne_lat": lat + lat_delta,
        "sw_lng": lng - lng_delta,
        "ne_lng": lng + lng_delta,
    }


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"EV-Line web server listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
