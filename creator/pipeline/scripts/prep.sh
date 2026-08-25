#!/usr/bin/env bash
# prep.sh — 아이폰 원본 폴더에서 (1) 클립 목록 JSON (2) 저용량 프록시 (3) 컨택트시트를 만듭니다.
#
#   ./prep.sh <원본폴더> [출력폴더]
#
# 출력폴더 기본값: <원본폴더>/_prep
#   _prep/inventory.json     ← Claude에게 붙여넣을 클립 메타데이터
#   _prep/proxy/*.mp4        ← 480p 저용량 (업로드용 / 편집 프록시용)
#   _prep/sheets/*.jpg       ← 클립별 프레임 격자 (Claude가 화면을 보고 기획)
set -euo pipefail

SRC="${1:?사용법: ./prep.sh <원본폴더> [출력폴더]}"
OUT="${2:-$SRC/_prep}"
mkdir -p "$OUT/proxy" "$OUT/sheets"

command -v ffmpeg  >/dev/null || { echo "ffmpeg 가 필요합니다"; exit 1; }
command -v ffprobe >/dev/null || { echo "ffprobe 가 필요합니다"; exit 1; }

# 컨택트시트 타임코드용 폰트 (없으면 타임코드 없이 진행)
TCFONT=""
for c in /System/Library/Fonts/Supplemental/Arial.ttf \
         /System/Library/Fonts/Helvetica.ttc \
         /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
         /usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf \
         C:/Windows/Fonts/arial.ttf ; do
  [ -f "$c" ] && { TCFONT="$c"; break; }
done

echo "[" > "$OUT/inventory.json"
first=1

shopt -s nullglob nocaseglob
for f in "$SRC"/*.{mov,mp4,m4v,avi,hevc}; do
  base="$(basename "${f%.*}")"
  echo "▶ $base"

  meta=$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height,r_frame_rate,codec_name \
    -show_entries format=duration,size \
    -of default=noprint_wrappers=1:nokey=0 "$f")

  dur=$(sed -n 's/^duration=//p'   <<<"$meta" | head -1)
  w=$(sed -n   's/^width=//p'      <<<"$meta" | head -1)
  h=$(sed -n   's/^height=//p'     <<<"$meta" | head -1)
  fps=$(sed -n 's/^r_frame_rate=//p' <<<"$meta" | head -1)
  size=$(sed -n 's/^size=//p'      <<<"$meta" | head -1)
  ctime=$(ffprobe -v error -show_entries format_tags=creation_time \
          -of default=nw=1:nk=1 "$f" 2>/dev/null | head -1)

  [ $first -eq 0 ] && echo "," >> "$OUT/inventory.json"
  first=0
  printf '  {"file":"%s","dur":%s,"w":%s,"h":%s,"fps":"%s","bytes":%s,"created":"%s"}' \
    "$(basename "$f")" "${dur:-0}" "${w:-0}" "${h:-0}" "${fps:-0/0}" "${size:-0}" "${ctime:-}" \
    >> "$OUT/inventory.json"

  # 프록시: 480p, 무거운 원본을 업로드 가능한 크기로
  ffmpeg -y -loglevel error -i "$f" \
    -vf "scale=-2:480" -c:v libx264 -preset veryfast -crf 30 \
    -c:a aac -b:a 96k "$OUT/proxy/$base.mp4"

  # 컨택트시트: 전체 길이에 균등 배치된 12프레임을 4x3 격자로.
  # 각 프레임에 원본 기준 타임코드를 새겨 넣습니다 —
  # 이게 있어야 Claude 가 EDL 의 in/out 초를 추정이 아니라 확인해서 쓸 수 있습니다.
  rate=$(python3 -c "d=float('${dur:-1}') or 1.0; print(max(12.0/d, 0.01))")
  step=$(python3 -c "d=float('${dur:-1}') or 1.0; print(d/12.0)")
  ffmpeg -y -loglevel error -i "$f" \
    -vf "fps=${rate},scale=320:-2,\
drawtext=fontfile=${TCFONT}:text='%{eif\\:n*${step}\\:d}s':x=6:y=6:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.75:boxborderw=5,\
tile=4x3:margin=4:padding=4:color=black" \
    -frames:v 1 -q:v 3 "$OUT/sheets/$base.jpg" 2>/dev/null \
  || ffmpeg -y -loglevel error -i "$f" -vf "fps=${rate},scale=320:-2,tile=4x3" \
       -frames:v 1 -q:v 3 "$OUT/sheets/$base.jpg"
done
echo "]" >> "$OUT/inventory.json"

python3 -c "import json,sys;json.load(open('$OUT/inventory.json'))" \
  && echo "✅ inventory.json 유효"

cat <<MSG

완료: $OUT
  · inventory.json  → Claude 채팅에 그대로 붙여넣기
  · sheets/*.jpg    → Claude에 업로드 (화면을 보고 기획합니다)
  · proxy/*.mp4     → 용량 크면 이것만 업로드

다음: Claude에게  /reels  또는  /longform  실행
MSG
