#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://www.ev-line.co.kr"
ENV_FILE="${ENV_FILE:-.env}"
COOKIE_FILE="${COOKIE_FILE:-.evline.cookies.txt}"
RAW=0
LOGIN_ONLY=0

if [[ "${1:-}" == "--raw" ]]; then
  RAW=1
  shift
fi

if [[ "${1:-}" == "--login-only" ]]; then
  LOGIN_ONLY=1
  shift
fi

DETAIL_ID="${1:-${EVLINE_DETAIL_ID:-001513355667}}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${EVLINE_USER_ID:-}" || -z "${EVLINE_USER_PWD:-}" ]]; then
  echo "EVLINE_USER_ID and EVLINE_USER_PWD must be set in $ENV_FILE" >&2
  echo "Copy .env.example to .env, then fill in your credentials." >&2
  exit 1
fi

decode_euckr() {
  if command -v iconv >/dev/null 2>&1; then
    iconv -f euc-kr -t utf-8 2>/dev/null || true
  else
    cat
  fi
}

login() {
  curl -sS -L \
    -c "$COOKIE_FILE" \
    -b "$COOKIE_FILE" \
    -e "$BASE_URL/login/login.asp" \
    -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari/537.36" \
    --data-urlencode "user_id=$EVLINE_USER_ID" \
    --data-urlencode "user_pwd=$EVLINE_USER_PWD" \
    --data-urlencode "url=/login/login.asp" \
    "$BASE_URL/login/login_ok.asp" >/dev/null
}

fetch_detail() {
  curl -sS -L \
    -b "$COOKIE_FILE" \
    -H "Accept: */*" \
    -H "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7" \
    -H "Referer: $BASE_URL/charge/serch.asp" \
    -H "X-Requested-With: XMLHttpRequest" \
    -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari/537.36" \
    "$BASE_URL/charge/mapdatadetail_202008.asp?id=$DETAIL_ID" | decode_euckr
}

format_detail() {
  LC_ALL=en_US.UTF-8 perl -0777 -CS -Mutf8 -pe '
    BEGIN {
      binmode STDIN, ":encoding(UTF-8)";
      binmode STDOUT, ":encoding(UTF-8)";
    }

    s/\r//g;
    if (/\[\{"id":"(.*)"\}\]\s*$/s) {
      $_ = $1;
      s/\\"/"/g;
      s/\\\//\//g;
    }

    s/&nbsp;/ /gi;
    s/&amp;/&/gi;
    s/&lt;/</gi;
    s/&gt;/>/gi;
    s/&quot;/"/gi;
    s/&#39;/'\''/gi;

    if (/alert\('\''([^'\'']+)'\''\)/) {
      $_ = "알림: $1\n";
      next;
    }

    sub clean {
      my ($text) = @_;
      $text =~ s/<[^>]+>//g;
      $text =~ s/\s+/ /g;
      $text =~ s/^\s+|\s+$//g;
      return $text;
    }

    my ($name) = /<td[^>]*>\s*충전소명\s*<\/td>\s*<td[^>]*>(.*?)<\/td>/si;
    my ($addr) = /<td[^>]*>\s*주소\s*<\/td>\s*<td[^>]*>(.*?)<\/td>/si;
    my @rows = /<tr>\s*<td[^>]*>([A-Z])<\/td>\s*<td[^>]*>(.*?)<\/td>\s*<\/tr>/gsi;

    if (defined $name || defined $addr || @rows) {
      my @out;
      push @out, "충전소 정보";
      push @out, "============";
      push @out, "ID: " . $ENV{DETAIL_ID_FOR_FORMAT};
      push @out, "충전소명: " . clean($name) if defined $name;
      push @out, "주소: " . clean($addr) if defined $addr;

      if (@rows) {
        push @out, "";
        push @out, "그룹 상태";
        push @out, "---------";
        while (@rows) {
          my $group = shift @rows;
          my $state = clean(shift @rows);
          push @out, sprintf("%-2s %s", $group, $state);
        }
      }

      $_ = join("\n", @out) . "\n";
      next;
    }

    s/<\/tr>/\n/gi;
    s/<\/td>\s*<td[^>]*>/ : /gi;
    s/<[^>]+>//g;
    s/[ \t]+/ /g;
    s/^\s+|\s+$//g;
    s/\n{3,}/\n\n/g;
    $_ .= "\n" if length $_;
  '
}

login
if [[ "$LOGIN_ONLY" == "1" ]]; then
  exit 0
fi

if [[ "$RAW" == "1" ]]; then
  fetch_detail
else
  export DETAIL_ID_FOR_FORMAT="$DETAIL_ID"
  fetch_detail | format_detail
fi
