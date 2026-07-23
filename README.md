# EV-Line

EV-Line 충전소의 그룹별 상태와 이번달 충전량(경부하/중부하/최대부하)을 보여주는 Vercel 웹 앱입니다. `api/index.py`가 Vercel Python Function으로 동작합니다.

## Vercel 배포

1. Vercel에서 이 Git 저장소를 새 프로젝트로 가져옵니다.
2. 프로젝트의 **Settings > Environment Variables**에 다음 값을 등록합니다.

   | 이름 | 설명 |
   | --- | --- |
   | `EVLINE_USER_ID` | EV-Line 로그인 아이디 |
   | `EVLINE_USER_PWD` | EV-Line 로그인 비밀번호 |

3. Production, Preview 등 필요한 배포 환경을 선택한 뒤 배포합니다. Git에 push하면 Vercel이 연결된 브랜치를 자동으로 다시 배포합니다.

`requirements.txt`의 Python 패키지는 배포 시 자동으로 설치되고, `vercel.json`이 모든 요청을 `api/index.py`로 전달합니다.

## 사용

배포된 도메인을 열면 기본 충전소 상태가 표시됩니다.

```text
https://<project>.vercel.app/
```

다른 충전소를 보려면 `id` 쿼리 파라미터를 사용합니다.

```text
https://<project>.vercel.app/?id=001513355667
```

각 그룹 카드의 별을 누르면 현재 브라우저에 즐겨찾기가 저장됩니다. `전체보기`/즐겨찾기 보기 상태도 충전소별로 유지됩니다.

상단에는 로그인 세션으로 가져온 `view_new.asp`의 이번달 충전량이 함께 표시됩니다.

배포 상태 확인용 엔드포인트:

```text
https://<project>.vercel.app/healthz
```
