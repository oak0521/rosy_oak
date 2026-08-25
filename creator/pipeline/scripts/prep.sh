#!/usr/bin/env bash
# prep.sh — 맥/리눅스용 래퍼. 실제 구현은 prep.py 에 있습니다 (윈도우와 공용).
exec python3 "$(dirname "$0")/prep.py" "$@"
