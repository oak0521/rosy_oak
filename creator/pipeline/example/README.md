# 예제 산출물 — `/longform` 실행 결과가 실제로 이렇게 나옵니다

가상의 소재("25개월 아들과 첫 키즈카페, 낮잠 어긋나서 30분 울었고 그 뒤 볼풀에서 잘 놂,
수유실은 있는데 의자 2개, 2시간 34,000원")로 만든 **완성 예시**입니다.

| 파일 | 내용 |
|---|---|
| `edl.json` | 롱폼 컷 편집 설계 |
| `longform.srt` | 롱폼 자막 |
| `shorts.json` | 숏폼 4편 파생 명세 |
| `shorts/*.srt` | 숏폼별 새 훅 자막 |
| `captions.md` | 유튜브·인스타 본문 문안 전부 |
| `music-cue.md` | 구간별 음악 큐 시트 |

렌더:
```bash
cd creator/pipeline/example
python3 ../scripts/render.py longform edl.json     # 원본 클립이 있어야 실행됩니다
python3 ../scripts/render.py shorts   shorts.json
```
(원본 없이 형식만 확인하려면 `--dry-run` 을 붙이세요)
