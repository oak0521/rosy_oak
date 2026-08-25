#!/usr/bin/env python3
"""
render.py — EDL(편집 결정 리스트) JSON 을 실제 영상으로 렌더합니다.

  python3 render.py longform edl.json          # 클립들을 이어붙여 롱폼 1편
  python3 render.py shorts   shorts.json       # 롱폼에서 9:16 숏폼 여러 편
  python3 render.py ... --dry-run              # 실행 없이 ffmpeg 명령만 출력

JSON 안의 모든 경로는 그 JSON 파일이 있는 폴더 기준 상대경로입니다.
포맷은 ../templates/edl.example.json / shorts.example.json 참고.

이 스크립트는 "렌더 버튼" 역할만 합니다. 무엇을 어디서 자를지(EDL)와
자막 .srt 는 Claude 가 만들어 줍니다. 캡컷/VLLO 로 손편집할 거면
이 스크립트 없이 EDL 표만 보고 작업해도 됩니다.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

FFMPEG = shutil.which("ffmpeg")
DRY = False

# 자막 기본 스타일 — playbooks/subtitles-and-music.md 규칙과 맞춘 값.
# spec 의 "subtitle_style" 로 항목별 덮어쓸 수 있습니다.
#   font       : libass 가 fontconfig 로 찾는 가족 이름. 없으면 자동 대체됩니다.
#                macOS "Apple SD Gothic Neo" / Windows "Malgun Gothic" / 나눔 계열 모두 가능
#   size       : 출력 높이 1920 기준 픽셀. 규칙상 58~72px
#   margin_v   : 하단에서 띄울 거리(px). 릴스/쇼츠는 하단 20%(=384px)를 UI 가 가리므로
#                두 줄 자막 높이까지 감안해 480 을 기본값으로 둡니다
DEFAULT_SUB_STYLE = {
    "font": "Apple SD Gothic Neo",
    "size": 64,
    "bold": 1,
    "primary": "&H00FFFFFF",   # 흰 글자
    "outline_colour": "&H00000000",
    "outline": 3,
    "shadow": 0,
    "alignment": 2,            # 하단 중앙 기준 + margin_v 로 올림
    "margin_v": 480,
}


def die(msg):
    sys.exit(f"오류: {msg}")


def run(cmd):
    print("  $ " + " ".join(cmd if DRY else cmd[:6] + ["..."]))
    if DRY:
        return
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        die("ffmpeg 실패\n" + p.stderr[-2000:])


def esc(path):
    """ffmpeg 필터 인자 안에 들어가는 경로 이스케이프"""
    return path.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def srt_to_ass(srt_path, ass_path, w, h, style):
    """SRT 를 ASS 로 변환하면서 PlayRes 를 출력 해상도에 맞춥니다.

    ffmpeg 의 subtitles 필터에 SRT 를 그대로 넣으면 libass 가 작은 기본
    PlayRes(보통 384x288)를 가정해서, force_style 로 준 글자 크기와 여백이
    출력 해상도 비율만큼 뻥튀기됩니다. (자막이 화면 밖으로 밀려 올라가는 원인)
    PlayResX/Y 를 직접 박아 넣으면 지정한 px 값이 그대로 적용됩니다.
    """
    st = {**DEFAULT_SUB_STYLE, **(style or {})}
    with open(srt_path, encoding="utf-8-sig") as f:
        raw = f.read()

    events = []
    for block in [b for b in raw.replace("\r\n", "\n").split("\n\n") if b.strip()]:
        lines = [l for l in block.split("\n") if l.strip()]
        tc = next((l for l in lines if "-->" in l), None)
        if not tc:
            continue
        start, end = [t.strip() for t in tc.split("-->")]
        text = "\\N".join(lines[lines.index(tc) + 1:])
        events.append((_ass_time(start), _ass_time(end), text))

    check_cues(events, os.path.basename(srt_path))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{st['font']},{st['size']},{st['primary']},{st['outline_colour']},&H00000000,{st['bold']},0,1,{st['outline']},{st['shadow']},{st['alignment']},60,60,{st['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(f"Dialogue: 0,{a},{b},Default,,0,0,0,,{t}\n" for a, b, t in events)
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + body)
    return ass_path


def check_cues(events, name):
    """자막이 서로 겹치거나 너무 오래 머무는지 확인하고 경고합니다.

    playbooks/subtitles-and-music.md 규칙: 한 자막은 1.5~2.5초, 4초를 넘기지 않습니다.
    겹치는 자막은 화면에 두 줄이 동시에 떠서 편집 사고로 이어지므로 반드시 잡아야 합니다.
    """
    warns = []
    prev_end, prev_i = None, None
    for i, (a, b, txt) in enumerate(events, 1):
        sa, sb = _secs(a), _secs(b)
        if sb <= sa:
            warns.append(f"  #{i} 끝이 시작보다 빠르거나 같음 ({a} → {b})")
        if sb - sa > 4.0:
            warns.append(f"  #{i} {sb-sa:.1f}초 표시 — 4초 초과 (이탈 지점이 됩니다)")
        if prev_end is not None and sa < prev_end - 1e-6:
            warns.append(f"  #{i} 가 #{prev_i} 와 겹침 ({a} < 앞 자막 끝)")
        if not txt.strip() or txt.strip() == ".":
            warns.append(f"  #{i} 내용이 비어 있음")
        prev_end, prev_i = sb, i
    if warns:
        print(f"⚠ 자막 확인 필요 — {name}")
        for w in warns:
            print(w)


def _secs(t):
    """0:01:23.45 → 83.45"""
    h, m, rest = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def _ass_time(t):
    """00:00:01,500 → 0:00:01.50"""
    t = t.replace(",", ".")
    hh, mm, rest = t.split(":")
    ss = f"{float(rest):05.2f}"
    return f"{int(hh)}:{mm}:{ss}"


def atempo_chain(speed):
    """atempo 는 0.5~2.0 배만 지원하므로 그 밖의 배속은 여러 단으로 나눕니다.
    (3배속 타임랩스에서 오디오만 원래 길이로 남아 영상보다 길어지는 것을 막습니다)"""
    out, s = [], float(speed)
    while s > 2.0:
        out.append(2.0)
        s /= 2.0
    while s < 0.5:
        out.append(0.5)
        s /= 0.5
    if abs(s - 1.0) > 1e-6:
        out.append(s)
    return out


def norm_segment(src, t_in, t_out, speed, w, h, fps, dst):
    """클립 한 조각을 동일한 규격(해상도/fps/오디오)으로 정규화해 중간 파일 생성.
    아이폰 원본은 클립마다 해상도·프레임레이트가 섞이므로 이 단계가 필요합니다."""
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps},setsar=1")
    af = "aformat=sample_rates=48000:channel_layouts=stereo"
    if speed and speed != 1.0:
        vf += f",setpts={1.0/speed:.6f}*PTS"
        af += "".join(f",atempo={t:.6f}" for t in atempo_chain(speed))
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-ss", str(t_in), "-to", str(t_out), "-i", src,
           "-vf", vf, "-af", af,
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-c:a", "aac", "-b:a", "192k", "-video_track_timescale", "90000", dst]
    run(cmd)


def mux_music_and_subs(video, out, music, subs, base):
    """정규화된 비디오에 BGM 믹스 + 자막 번인 + 라우드니스 정규화(-14 LUFS)"""
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", video]
    filters = []

    if music:
        mpath = os.path.join(base, music["file"])
        if not os.path.exists(mpath) and not DRY:
            die(f"음원 파일 없음: {mpath}")
        cmd += ["-stream_loop", "-1", "-i", mpath]
        gain = music.get("gain_db", -20)
        # 현장음(아이 목소리)이 주인공 — BGM 은 gain 만큼 낮춰 깔고,
        # 길이는 현장음 기준으로 자릅니다.
        filters.append(f"[1:a]volume={gain}dB[bg]")
        filters.append("[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[mix]")
        asrc = "[mix]"
    else:
        asrc = "[0:a]"
    filters.append(f"{asrc}loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

    if subs:
        filters.append(f"[0:v]subtitles='{esc(subs)}'[vout]")
    else:
        filters.append("[0:v]null[vout]")
    vmap = "[vout]"

    cmd += ["-filter_complex", ";".join(filters),
            "-map", vmap, "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", out]
    run(cmd)


def cmd_longform(spec, base):
    v = spec.get("video", {})
    w, h, fps = v.get("w", 1920), v.get("h", 1080), v.get("fps", 30)
    clips = spec.get("clips") or die("clips 가 비어 있습니다")
    src_dir = os.path.join(base, spec.get("source_dir", "."))
    out = os.path.join(base, spec.get("output", "longform.mp4"))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    tmp = tempfile.mkdtemp(prefix="edl_")
    parts = []
    print(f"■ 롱폼 {len(clips)}컷 → {out}")
    for i, c in enumerate(clips):
        src = os.path.join(src_dir, c["src"])
        if not os.path.exists(src) and not DRY:
            die(f"원본 없음: {src}")
        dst = os.path.join(tmp, f"{i:03d}.mp4")
        print(f"  [{i+1}/{len(clips)}] {c['src']} {c['in']}~{c['out']}s  {c.get('note','')}")
        norm_segment(src, c["in"], c["out"], c.get("speed", 1.0), w, h, fps, dst)
        parts.append(dst)

    lst = os.path.join(tmp, "concat.txt")
    if not DRY:
        with open(lst, "w") as f:
            for p in parts:
                f.write(f"file '{p}'\n")
    joined = os.path.join(tmp, "joined.mp4")
    run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-c", "copy", joined])

    music = (spec.get("music") or [None])[0]
    ass = None
    if spec.get("subtitles"):
        srt = os.path.join(base, spec["subtitles"])
        if not os.path.exists(srt) and not DRY:
            die(f"자막 파일 없음: {srt}")
        ass = os.path.join(tmp, "subs.ass")
        if not DRY:
            srt_to_ass(srt, ass, w, h, spec.get("subtitle_style"))

    # ① 업로드용: 자막 번인
    mux_music_and_subs(joined, out, music, ass, base)

    # ② 숏폼 파생용 마스터: 자막 없음.
    #    자막이 박힌 롱폼에서 숏폼을 뽑으면 새 자막과 겹쳐 이중으로 보입니다.
    master = out
    if ass:
        stem, ext = os.path.splitext(out)
        master = f"{stem}_master_자막없음{ext}"
        mux_music_and_subs(joined, master, music, None, base)

    if not DRY:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"✅ 업로드용   : {out}")
    if ass:
        print(f"✅ 숏폼 마스터: {master}   ← shorts.json 의 source 로 쓰세요")


def framing_filter(mode, w, h, pos=0.5):
    """가로 원본 → 9:16 변환. crop 은 화면이 잘리고, blur 는 전체를 살립니다."""
    if mode == "crop":
        return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h}:(iw-{w})*{pos}:(ih-{h})/2,setsar=1")
    # blur: 배경은 꽉 채워 흐리게, 원본은 통째로 가운데 배치
    return (f"split=2[bg][fg];"
            f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},gblur=sigma=24[bgb];"
            f"[fg]scale={w}:-2[fgs];"
            f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1")


def cmd_shorts(spec, base):
    v = spec.get("video", {})
    w, h, fps = v.get("w", 1080), v.get("h", 1920), v.get("fps", 30)
    src = os.path.join(base, spec["source"])
    out_dir = os.path.join(base, spec.get("out_dir", "shorts"))
    os.makedirs(out_dir, exist_ok=True)
    items = spec.get("shorts") or die("shorts 가 비어 있습니다")

    tmp = tempfile.mkdtemp(prefix="shorts_")
    print(f"■ 숏폼 {len(items)}편 ← {os.path.basename(src)}")
    for s in items:
        name = s["name"]
        out = os.path.join(out_dir, f"{name}.mp4")
        print(f"  · {name}  {s['in']}~{s['out']}s  ({s.get('framing','blur')})")

        chain = framing_filter(s.get("framing", "blur"), w, h, s.get("crop_pos", 0.5))
        if s.get("subtitles"):
            sp = os.path.join(base, s["subtitles"])
            if not os.path.exists(sp) and not DRY:
                die(f"자막 없음: {sp}")
            ass = os.path.join(tmp, f"{name}.ass")
            if not DRY:
                srt_to_ass(sp, ass, w, h, {**(spec.get("subtitle_style") or {}),
                                           **(s.get("subtitle_style") or {})})
            chain += f",subtitles='{esc(ass)}'"

        cmd = [FFMPEG, "-y", "-loglevel", "error",
               "-ss", str(s["in"]), "-to", str(s["out"]), "-i", src,
               "-filter_complex", f"[0:v]{chain}[vout]",
               "-map", "[vout]", "-map", "0:a?",
               "-r", str(fps),
               "-c:v", "libx264", "-preset", "medium", "-crf", "20",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
        run(cmd)

        # 인스타용: 오디오 없는 버전 (앱에서 트렌딩 오디오를 얹어야 도달이 붙습니다)
        if s.get("mute_for_instagram", True):
            mout = os.path.join(out_dir, f"{name}_무음_인스타용.mp4")
            run([FFMPEG, "-y", "-loglevel", "error", "-i", out,
                 "-c:v", "copy", "-an", mout])
    if not DRY:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"✅ {out_dir}")


def main():
    ap = argparse.ArgumentParser(description="EDL JSON → 영상 렌더")
    ap.add_argument("mode", choices=["longform", "shorts"])
    ap.add_argument("spec", help="edl.json 또는 shorts.json")
    ap.add_argument("--dry-run", action="store_true", help="ffmpeg 실행 없이 명령만 출력")
    a = ap.parse_args()

    global DRY
    DRY = a.dry_run
    if not FFMPEG and not DRY:
        die("ffmpeg 가 설치되어 있지 않습니다.  macOS: brew install ffmpeg")

    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    base = os.path.dirname(os.path.abspath(a.spec))

    (cmd_longform if a.mode == "longform" else cmd_shorts)(spec, base)


if __name__ == "__main__":
    main()
