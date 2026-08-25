---
name: longform
description: 아이폰 원본 클립(컨택트시트·inventory.json)과 상황 설명을 받아 유튜브 롱폼 브이로그 1편과 거기서 파생되는 숏폼 3~4편을 한 번에 설계합니다. 롱폼 구조·EDL·자막, 숏폼별 새 훅과 재편집 명세, 유튜브 제목/챕터/설명란과 인스타 본문까지 산출합니다. 사용자가 /longform 을 실행하거나 "브이로그 만들어줘", "롱폼이랑 숏폼 같이", "이번 나들이로 영상 만들어줘" 라고 할 때 사용하세요.
---

# 롱폼 브이로그 1편 + 숏폼 파생

## 먼저 읽을 것

작업 전에 반드시 읽으세요 (매번):

- `creator/playbooks/vlog-longform.md` — 10분 구조, 파생 규칙, 촬영 샷 리스트
- `creator/playbooks/short-reels.md` — 파생 숏폼의 포맷
- `creator/strategy/02-growth-engine.md` — 참여 장치
- `creator/playbooks/hooks.md` / `captions.md` / `subtitles-and-music.md`
- `creator/strategy/05-child-safety.md` — 노출 원칙

## 입력 확인

컨택트시트 이미지를 **실제로 보고** 작업하세요. 없으면
`creator/pipeline/scripts/prep.sh <원본폴더>` 실행을 먼저 안내하세요.

상황 설명에서 반드시 뽑아낼 것:
- **그날의 "작은 위기"** — 울음, 낮잠 어긋남, 두고 온 물건.
  이게 없으면 브이로그가 성립하지 않습니다. 없다고 하면 되물으세요.
- 검증 7항목 (수유실/기저귀대/유모차/이유식/소음/주차/비용)
- 총 비용과 체류 시간

## 산출물

`creator/pipeline/out/<날짜>_<소재>/` 에 저장.

### 1. 롱폼 구성표 (채팅에 표로)
`vlog-longform.md` 의 9구간(콜드오픈~아웃트로)에 실제 클립을 배치한 표.
각 구간의 목적·길이·쓸 클립·핵심 자막.

### 2. `edl.json` (가로 1920×1080)
- 콜드 오픈에 **그날 가장 극적인 순간**을 배치. 인사·인트로 금지
- 30초마다 시각적 변화가 생기도록 컷 배분
- 롱테이크가 필요한 구간(도착 첫 반응)은 자르지 말 것

### 3. `<이름>_longform.srt`

### 4. `shorts.json` + `shorts/*.srt`
`creator/pipeline/templates/shorts.example.json` 형식. 숏폼 3~4편.

**중요**: `source` 는 반드시 `*_master_자막없음.mp4` 를 가리켜야 합니다.
자막이 박힌 롱폼에서 뽑으면 자막이 이중으로 보입니다.

각 숏폼마다:
- **새 훅**을 붙일 것. 롱폼 구간을 그냥 자르기만 하면 안 됩니다
- 포맷(F1~F5)을 지정
- 끝에 "전체 영상은 프로필 링크" 유도
- 가로→세로 변환 방식(`blur` / `crop`)을 화면 내용에 따라 선택
  (인물이 중앙에 있으면 crop, 배경 정보가 중요하면 blur)

### 5. `captions.md`
- **유튜브**: 제목(개월수·지역·시설명 포함), 챕터 타임스탬프(0:00부터), 설명란, 고정 댓글
- **인스타**: 숏폼 3~4편 각각의 본문·해시태그
- 롱폼↔인스타 상호 유입 문구

### 6. `music-cue.md`
구간별 무드·BPM·볼륨. 위기 구간은 현장음을 살리고 BGM을 -24dB까지 낮출 것.

## 마지막에 할 것

렌더 순서를 알려주세요:
```bash
python3 creator/pipeline/scripts/render.py longform <경로>/edl.json
python3 creator/pipeline/scripts/render.py shorts   <경로>/shorts.json
```
`creator/ops/kpi-log.csv` 에 롱폼 1행 + 숏폼 행들을 추가하세요.

## 하지 말 것

- 다 좋았던 하루로 구성하기 — 위기 구간이 없으면 브이로그가 아니라 홍보영상이 됩니다
- 챕터 없이 설명란 쓰기
- 숏폼을 롱폼에서 단순 절단만 하기 (새 훅 필수)
- 노출 원칙 위반 클립 포함 (발견 시 먼저 지적)
