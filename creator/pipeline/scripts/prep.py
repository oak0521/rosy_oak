#!/usr/bin/env python3
"""
prep.py — 원본 영상 폴더에서 (1) 클립 목록 JSON (2) 컨택트시트 (3) 저용량 프록시를 만듭니다.
윈도우/맥/리눅스 공통. 윈도우에서는 scripts/윈도우/1_준비하기.bat 을 더블클릭하면 이게 실행됩니다.

  python3 prep.py <원본폴더> [출력폴더]

출력폴더 기본값: <원본폴더>/_prep
  _prep/inventory.json   Claude 채팅에 붙여넣을 클립 메타데이터
  _prep/sheets/*.jpg     클립당 12프레임 격자 + 타임코드 각인 → Claude 가 화면을 보고 기획
  _prep/proxy/*.mp4      480p 저용량 (업로드용)
"""
import json, os, shutil, subprocess, sys

EXTS = {".mov", ".mp4", ".m4v", ".avi", ".hevc", ".mkv"}
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgun.ttf",                          # 윈도우 맑은 고딕
    r"C:\Windows\Fonts\arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",           # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",        # 리눅스
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]


def die(msg):
    print(f"\n오류: {msg}\n")
    sys.exit(1)


def tool(name):
    p = shutil.which(name)
    if not p:
        die(f"{name} 를 찾을 수 없습니다.\n"
            f"윈도우: scripts/윈도우/0_최초설치.bat 을 먼저 한 번 실행하세요.\n"
            f"맥:    brew install ffmpeg")
    return p


def font_arg():
    for c in FONT_CANDIDATES:
        if os.path.exists(c):
            # ffmpeg 필터 안에서 윈도우 경로의 콜론·역슬래시는 이스케이프가 필요합니다
            return c.replace("\\", "/").replace(":", r"\:")
    return None


def probe(ffprobe, path):
    out = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate",
         "-show_entries", "format=duration,size",
         "-show_entries", "format_tags=creation_time",
         "-of", "json", path],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None
    d = json.loads(out.stdout or "{}")
    st = (d.get("streams") or [{}])[0]
    fm = d.get("format") or {}
    return {
        "file": os.path.basename(path),
        "dur": round(float(fm.get("duration") or 0), 2),
        "w": st.get("width", 0),
        "h": st.get("height", 0),
        "fps": st.get("r_frame_rate", "0/0"),
        "bytes": int(fm.get("size") or 0),
        "created": (fm.get("tags") or {}).get("creation_time", ""),
    }


def contact_sheet(ffmpeg, src, dst, dur, font):
    """전체 길이에 균등 배치된 12프레임을 4x3 격자로. 각 타일에 원본 기준 초를 새깁니다 —
    이게 있어야 Claude 가 EDL 의 in/out 을 추정이 아니라 확인해서 씁니다."""
    dur = max(dur, 0.5)
    rate = max(12.0 / dur, 0.01)
    step = dur / 12.0
    parts = [f"fps={rate}", "scale=320:-2"]
    if font:
        parts.append(
            f"drawtext=fontfile='{font}':text='%{{eif\\:n*{step}\\:d}}s'"
            ":x=6:y=6:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.75:boxborderw=5")
    parts.append("tile=4x3:margin=4:padding=4:color=black")
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", src,
           "-vf", ",".join(parts), "-frames:v", "1", "-q:v", "3", dst]
    if subprocess.run(cmd, capture_output=True).returncode != 0:
        # 폰트 문제 등으로 실패하면 타임코드 없이 재시도
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", src,
                        "-vf", f"fps={rate},scale=320:-2,tile=4x3",
                        "-frames:v", "1", "-q:v", "3", dst], capture_output=True)


def main():
    if len(sys.argv) < 2:
        die("사용법: python3 prep.py <원본폴더> [출력폴더]")
    src_dir = os.path.abspath(sys.argv[1].strip().strip('"'))
    if not os.path.isdir(src_dir):
        die(f"폴더를 찾을 수 없습니다: {src_dir}")
    out_dir = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(src_dir, "_prep")

    ffmpeg, ffprobe = tool("ffmpeg"), tool("ffprobe")
    font = font_arg()
    os.makedirs(os.path.join(out_dir, "sheets"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "proxy"), exist_ok=True)

    files = sorted(f for f in os.listdir(src_dir)
                   if os.path.splitext(f)[1].lower() in EXTS)
    if not files:
        die(f"영상 파일이 없습니다: {src_dir}\n(.mov .mp4 .m4v .avi 를 찾습니다)")

    print(f"\n원본 {len(files)}개 처리 중...\n")
    inv = []
    for i, name in enumerate(files, 1):
        path = os.path.join(src_dir, name)
        base = os.path.splitext(name)[0]
        meta = probe(ffprobe, path)
        if not meta:
            print(f"  [{i}/{len(files)}] {name} — 읽을 수 없어 건너뜁니다")
            continue
        inv.append(meta)
        print(f"  [{i}/{len(files)}] {name}  {meta['w']}x{meta['h']}  {meta['dur']}초")

        contact_sheet(ffmpeg, path, os.path.join(out_dir, "sheets", base + ".jpg"),
                      meta["dur"], font)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", path,
                        "-vf", "scale=-2:480", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "30", "-c:a", "aac", "-b:a", "96k",
                        os.path.join(out_dir, "proxy", base + ".mp4")], capture_output=True)

    with open(os.path.join(out_dir, "inventory.json"), "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, indent=1)

    print(f"""
완료: {out_dir}

  sheets\\*.jpg      ← Claude 채팅에 이미지로 올리세요 (제일 중요)
  inventory.json    ← 채팅에 텍스트로 붙여넣으세요
  proxy\\*.mp4       ← 원본이 커서 못 올릴 때만

다음: Claude 에게 /longform 또는 /reels 실행 + 그날 상황 설명
""")


if __name__ == "__main__":
    main()
