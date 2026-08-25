# 파이프라인 — 원본 올리고 완성본 받기까지

## 전체 흐름

```
[아이폰]  촬영 (주말 30분, 샷 리스트대로)
   │
   │  ① AirDrop / 사진앱 내보내기 → 컴퓨터 폴더
   ▼
[컴퓨터] creator/pipeline/inbox/2026-08-30/  에 원본 넣기
   │
   │  ② ./scripts/prep.sh inbox/2026-08-30
   │     → inventory.json (클립 목록) + sheets/*.jpg (화면) + proxy/*.mp4 (저용량)
   ▼
[Claude] 채팅에 sheets/*.jpg 업로드 + inventory.json 붙여넣기
   │      → /longform  또는  /reels  실행
   │
   │  ③ Claude 산출물
   │     · edl.json          어느 클립 몇 초를 어떤 순서로
   │     · *.srt             자막 전문 + 타이밍
   │     · shorts.json       롱폼에서 숏폼 뽑는 명세
   │     · shorts/*.srt      숏폼별 새 훅 자막
   │     · captions.md       인스타/유튜브 본문 + 해시태그 + 고정 댓글
   │     · music-cue.md      구간별 음악 무드·볼륨
   ▼
[컴퓨터] ④ 렌더 (둘 중 하나 선택)
   │
   ├─ 자동:  python3 scripts/render.py longform edl.json
   │         python3 scripts/render.py shorts   shorts.json
   │
   └─ 수동:  캡컷/VLLO 에서 edl.json 표대로 컷 배치 + srt 임포트 (25분)
   ▼
[업로드] 인스타 릴스 / 유튜브 쇼츠 + 롱폼
```

## ① 촬영본 옮기기

아이폰 → 컴퓨터로 옮길 때 **"원본 유지"**로 내보내세요.
(사진 앱 → 공유 → 옵션 → "모든 사진 데이터" 켜기, 위치정보는 **끄기**)

폴더 이름은 `YYYY-MM-DD_장소` 형식으로. 나중에 소재를 다시 찾을 때 이게 전부입니다.

```
creator/pipeline/inbox/2026-08-30_키즈카페/
   IMG_2201.MOV
   IMG_2205.MOV
   ...
```

## ② prep.sh 실행

```bash
cd creator/pipeline
./scripts/prep.sh inbox/2026-08-30_키즈카페
```

만들어지는 것:

| 파일 | 용도 |
|---|---|
| `_prep/inventory.json` | 클립별 길이·해상도·촬영시각. Claude 채팅에 **텍스트로 붙여넣기** |
| `_prep/sheets/*.jpg` | 클립당 12프레임 격자 이미지. Claude 채팅에 **이미지로 업로드** |
| `_prep/proxy/*.mp4` | 480p 저용량. 원본이 커서 못 올릴 때 이것만 올리기 |

> **컨택트시트를 꼭 올려주세요.** Claude가 실제 화면을 봐야
> "3번 클립 8초에 아이가 처음 웃는 순간" 같은 구체적인 편집 설계가 나옵니다.
> 파일명만으로는 일반론밖에 못 씁니다.

macOS에 ffmpeg가 없다면: `brew install ffmpeg`

## ③ Claude에게 요청

컨택트시트를 올린 뒤 스킬을 실행하세요.

```
/longform 2026-08-30 키즈카페 첫 방문. 25개월. 낮잠 타이밍 어긋나서 30분쯤 울었고
          그 뒤에 볼풀에서 제일 잘 놀았어요. 수유실은 있는데 의자가 2개뿐이었음.
          총 2시간, 34,000원.
```

```
/reels 위와 같은 소재로 검증 리스트형 1편만
```

**상황 설명을 같이 주세요.** 화면에 안 나오는 정보(총비용, 그날의 감정, 아이 컨디션)가
훅과 본문의 재료입니다.

산출물은 `creator/pipeline/out/<날짜>/` 아래에 저장됩니다.

## ④ 렌더

### 자동 렌더 (ffmpeg)

```bash
cd creator/pipeline/out/2026-08-30_키즈카페
python3 ../../scripts/render.py longform edl.json
python3 ../../scripts/render.py shorts   shorts.json
```

`--dry-run` 을 붙이면 실행 없이 ffmpeg 명령만 확인할 수 있습니다.

**롱폼 렌더는 파일 두 개를 만듭니다.**
- `*_longform.mp4` — 자막 번인. **업로드용**
- `*_longform_master_자막없음.mp4` — **숏폼 파생용.**
  자막이 박힌 영상에서 숏폼을 뽑으면 새 훅 자막과 겹쳐 이중으로 보입니다.
  `shorts.json` 의 `source` 는 항상 이 마스터를 가리킵니다.

**숏폼도 파일 두 개씩 나옵니다.**
- `이름.mp4` — 음악 포함. **유튜브 쇼츠용**
- `이름_무음_인스타용.mp4` — 오디오 없음. **인스타에 올려서 앱 안에서 트렌딩 오디오를 얹으세요.**
  이유는 `playbooks/subtitles-and-music.md` 의 이중 배포 규칙 참고.

### 수동 편집 (캡컷 / VLLO)

자동 렌더가 부담스러우면 `edl.json` 을 **작업 지시서로만** 쓰세요.
어느 클립 몇 초를 어떤 순서로 붙일지 다 적혀 있어서, 그대로 옮기면 25분 안에 끝납니다.
`.srt` 파일은 캡컷·프리미어·VLLO 모두 임포트를 지원하므로 자막은 타이핑할 필요가 없습니다.

**캡컷 자막 임포트**: 타임라인 → 텍스트 → 자막 가져오기 → `.srt` 선택 → 스타일 일괄 적용

## 폴더 규칙

```
creator/pipeline/
  inbox/      원본 (git 에 커밋하지 않음)
  out/        산출물 (git 에 커밋하지 않음)
  scripts/    prep.sh, render.py
  templates/  edl.example.json, shorts.example.json
  assets/     BGM, 폰트, 캐릭터 이미지 (직접 만들어 쓰세요)
```

영상 파일은 저장소에 올리지 않습니다 (`.gitignore` 처리됨).
**기획서·자막·본문 문안은 커밋하세요** — 나중에 무엇이 잘 됐는지 되짚는 자산이 됩니다.

## 자주 걸리는 문제

| 증상 | 원인 / 해결 |
|---|---|
| `ffmpeg 가 설치되어 있지 않습니다` | macOS `brew install ffmpeg` / Windows `winget install ffmpeg` |
| 자막이 화면 밖으로 밀림 | `edl.json` 에 `"subtitle_style": {"margin_v": 400}` 추가해 조정 |
| 자막 폰트가 이상함 | `"subtitle_style": {"font": "Apple SD Gothic Neo"}` — 설치된 한글 폰트 이름으로 |
| 숏폼에 자막이 두 개 | `shorts.json` 의 `source` 가 `_master_자막없음.mp4` 인지 확인 |
| 클립 해상도가 섞여 있음 | 정상입니다. `render.py` 가 자동으로 통일합니다 |
| BGM이 너무 큼 | `"music": [{"gain_db": -24}]` 로 낮추기 (기본 -20) |
| 가로 영상이 9:16에서 너무 잘림 | `"framing": "blur"` 로 (기본값). 잘라도 되면 `"crop"` |
