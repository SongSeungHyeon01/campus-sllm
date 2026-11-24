# 오류 보고서 목록

개발 중 실제로 만난 오류와 해결 과정입니다. 문서(요구사항 정의서·화면설계서) 수정 내역은 `문서/보고서/수정내역/`에 따로 있습니다.

- [2026-11-25] Figma MCP 호출이 Starter 플랜 한도에 걸려 화면 수정이 멈춤 — 플랜 호출 한도 소진 (우회함: Figma에서 직접 수정) → 2026-11-25_figma-mcp-starter-call-limit.md
- [2026-11-20] 사이트 전체 수집에 학생이 쓴 복학 신청 글·학번이 든 제목이 가림 없이 들어감 — 학생 게시판을 주소 이름으로만 판단 (해결됨: 해당 게시판 수집 제외, 95건 삭제) → 2026-11-20_student-posts-crawled.md
- [2026-11-10] 다른 표현의 근거없음 답이 답변 대기에 안 올라감 + 빈 연락처 '010-'·맺음말 노출 — 판정 문구 목록·후처리 부족 (해결됨) → 2026-11-10_not-found-phrase-and-answer-cleanup.md
- [2026-11-10] Kanana-2 다운로드가 64MB에서 멈춤 — Xet 전송 문제로 추정 (우회함: HF_HUB_DISABLE_XET=1) → 2026-11-10_hf-download-stall-xet.md
- [2026-10-12] '가장 빠른 버스'에 08:00 대신 10:15 — 시간표 청크 일부만 검색 + 현재 시각 없음 + 2B 모델의 시간 비교 한계 (해결됨: 시간표 조회는 코드가 답함) → 2026-10-12_bus-next-departure-wrong.md
- [2026-10-12] Git Bash curl 한글 깨짐 — 시험 도구 인코딩 문제, 서버는 정상 (우회함) → 2026-10-12_curl-korean-encoding.md
- [2026-10-12] Android 빌드 실패 — JBR Java 25 / local.properties 경로 이스케이프 (해결됨) → 2026-10-12_android-build-jdk25-sdk-path.md
- [2026-10-12] sLLM 느림·오답 — VRAM 부족, 학사일정 월별 청크, 근거 기준값 (해결됨, 한계 일부 남음) → 2026-10-12_gpu-vram-slow-and-wrong-answers.md
- [2026-10-12] FAQ 등록 직후 500 — Chroma "Nothing found on disk" (우회함: SQLite로 이동) → 2026-10-12_chroma-hnsw-nothing-on-disk.md
- [2026-10-12] 서버 시작 실패 — transformers 5.x가 Kanana 설정 거부 (해결됨: transformers 4.x 고정) → 2026-10-12_transformers5-kanana-config.md
