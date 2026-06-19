# EV-Line detail fetcher

EV-Line에 로그인한 뒤 충전소 상세 정보를 가져오는 작은 curl 래퍼입니다.

## 설정

```sh
cp .env.example .env
```

`.env`에 EV-Line 아이디와 비밀번호를 입력합니다.

```sh
EVLINE_USER_ID='your_id'
EVLINE_USER_PWD='your_password'
EVLINE_DETAIL_ID='001513355667'
```

`.env`와 로그인 쿠키 파일 `.evline.cookies.txt`는 `.gitignore`에 들어있습니다.

## 실행

기본 상세 ID는 `.env`의 `EVLINE_DETAIL_ID`를 사용합니다.

```sh
./evline_fetch.sh
```

다른 상세 ID를 가져오려면 첫 번째 인자로 넘기면 됩니다.

```sh
./evline_fetch.sh 001513355667
```

기본 출력은 사람이 읽기 좋게 정리됩니다.

```text
충전소 정보
============
ID: 001513355667
충전소명: 동탄시범계룡리슈빌아파트
주소: 경기도 화성시 동탄대로시범길 236

그룹 상태
---------
A  충전가능
B  충전가능
```

서버 원문 응답을 그대로 보고 싶으면 `--raw`를 붙입니다.

```sh
./evline_fetch.sh --raw
./evline_fetch.sh --raw 001513355667
```

스크립트는 매번 `/login/login_ok.asp`로 로그인하고, 받은 쿠키를 `.evline.cookies.txt`에 저장한 다음 `/charge/mapdatadetail_202008.asp`를 호출합니다.

## 웹서버

Mac mini의 `~/ev`에서 웹서버를 실행하면 브라우저로 볼 수 있습니다.
기본 웹 화면(`/`)은 차량에서 보기 쉽도록 각 그룹 상태를 큰 카드로 보여줍니다. 카드 우상단 별을 누르면 해당 브라우저에 즐겨찾기로 저장되고, 즐겨찾기가 있으면 기본 화면에는 즐겨찾기 카드만 표시됩니다. `전체보기` 버튼으로 모든 그룹을 볼 수 있습니다.

```sh
cd ~/ev
EVLINE_WEB_HOST=127.0.0.1 EVLINE_WEB_PORT=8787 ./evline_web.py
```

백그라운드 실행:

```sh
cd ~/ev
nohup env EVLINE_WEB_HOST=127.0.0.1 EVLINE_WEB_PORT=8787 ./evline_web.py > evline_web.log 2>&1 &
```

Mac mini 안에서 확인:

```sh
curl http://127.0.0.1:8787/healthz
curl http://127.0.0.1:8787/
```

내 컴퓨터에서 SSH 터널로 잠깐 열어보기:

```sh
ssh -L 8787:127.0.0.1:8787 home
```

그 다음 브라우저에서 `http://127.0.0.1:8787`을 엽니다.

Cloudflare Tunnel을 붙일 때는 origin을 `http://127.0.0.1:8787`로 지정하면 됩니다.
