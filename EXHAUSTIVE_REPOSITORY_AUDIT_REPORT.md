# Capstone-MCP Codebase-Wide Exhaustive Audit Report

- **발간 일자**: 2026-11-15
- **감사 대상**: `src/capstone_mcp/` 207개 파일 전역 (2,145,077 바이트) 및 `tests/` 70개 파일 전역
- **감사 주체**: 22개 전문 감사 에이전트 스웜 (서브시스템 전담 감사관 + 총괄 검증관 `auditor-verifier`)
- **적용 규약**: Spec #120, ADR 0005, GLOSSARY.md
- **감사 목적**: 570개 단위 테스트와 85% 커버리지에 가려져 있던 **Live Runtime Blind Spot**을 돌파하고, 실제 Windows OS 및 실물 Capstone 런타임에서 시스템 마비, 프로세스 고아화, 호스트 자원 파괴, 데이터 조작, 가짜 데이터 사기를 유발하는 모든 잠재 결함을 라인 단위로 전수 적출하여 공식 영구 백서로 확립함.

---

## 1. 📊 Executive Summary & 결함 심각도 매트릭스

22개 전문 감사 에이전트 스웜의 1:1 프로덕션 코드 대조 실사와 교차 검증을 거쳐, 중복을 제거한 **최종 358건의 마스터 결함**이 공인 확정되었습니다:

| 심각도 등급 | 건수 | 정의 및 영향 | 핵심 결함 카테고리 요약 |
| :---: | :---: | :--- | :--- |
| **🔴 P0 (Blocker)** | **79건** | 시스템 영구 락업, 프로세스 고아화, 클립보드 오염, 데이터 조작, Mock 맹점 은폐, 보안 RCE, 전 실험 모의 사기 | WinEvent 훅 GIL 고갈 및 ctypes GC 댕글링 포인터 크래시(0xC0000005), 클립보드 펌프 행, Stale Ref 연쇄 폭사, 다중 창 100% 거부, 수식 AST 부재 날조, `--remote-allow-origins=*` 드라이브바이 RCE, 다중 인스턴스 락업, 60s 타임아웃 프로세스 사살, unhandled NativeSessionError 서버 다운, STA 메시지 펌프 부재 데드락, Fallback 가짜 데이터 주입 사기, live://table 100% 크래시, 이름 변경된 런 삭제 불능, 51개 RPC 은폐 FakeBackend, Wire E2E 테스트 CI 스킵 등 |
| **🟠 P1 (Critical)** | **156건** | 실기 연동 실패, 데이터 왜곡·오폭 삭제, 포트 고갈, 가짜 데이터 날조, 보안 무결성 훼손 | TCP 소켓 고갈(WSAEADDRINUSE 10048), Time축 누락 x=y 날조, 고아 레코딩 스레드, WebEngine JS 인젝션, 전원 역동작, Path Traversal 임의 파일 쓰기, 단열 지수 ZeroDivisionError, 슬릿 회절 중앙 피크 2배 왜곡, tools/ui.py 포커스 탈취, 테이블 통계 1열 강제 왜곡, 셀 누락 컬럼 밀림, TelemetryBuffer 동기화 락 전무, capstone_guide 데코레이터 누락, 고속 샘플링 OOM, 하드웨어 단선 행 등 |
| **🟡 P2 (Major)** | **73건** | 부분 UI 조작 불능, 비영어 로케일 미지원, 수치 연산 발산, 가드레일 누락 | 단위 롤백, Vandermonde 조건수 폭발, 소수점 쉼표 파싱 실패, CP949 디코딩 500 크래시, 유럽식 인용 소수점(\"0,750\") 파싱 불가, 0/1번 Edit 컨트롤 맹목적 추측, 런 삭제 모달 0ms 레이스, HTML 보고서 장비 섹션 누락, SVG NaN 좌표 크래시, JSON 문자열 run_name 헤더 누출, live://measurements 단일값 반환, FFT 피크 정규식 파싱 실패 등 |
| **🟢 P3 (Minor/Debt)** | **50건** | 아키텍처 부채, 행복경로 단일 테스트, 시간 기반 플래키, 환경 불일치 | 행복경로 단일 테스트, 시간 기반 플래키, 포트 9222 vs 9223 불일치, 피트 상태 FAIL_MAX_ITERATONS 오타, 미사용 모델 및 중복 회귀 모듈, 디스플레이 ID 하드코딩, 비표적 윈도우 컨트롤 오염, 골든 마스터 로컬 절대경로 하드코딩, 표준오차 0.0 N/A 표기 등 |
| **합계** | **358건** | **코드베이스 207개 프로덕션 파일 및 70개 테스트 파일 100% 전수 실사 완료** |

---

## 2. 🔍 주요 신규 확정 핵심 결함 영역 (Phase 3 심층 분석)

### 1) 보안, IPC 및 저수준 메모리 결함 (Security & Low-level)
- **ctypes WINFUNCTYPE 콜백 GC 및 댕글링 포인터 접근 위반(0xC0000005) 크래시** (`ui_events.py:122-150`): 로컬 콜백 변수가 GC로 해제된 후 OS가 이벤트를 디스패치할 때 세그멘테이션 오류로 프로세스 즉사.
- **`--remote-allow-origins=*` 및 무인증 로컬 디버그 포트에 의한 웹 드라이브바이 RCE** (`desktop.py:50-53`, `bridge.py:96-133`): Chromium SOP 해제로 악성 사이트 방문 시 웹 JS가 `ws://127.0.0.1:9222`로 침투하여 Qt C++ 바인딩을 장악.
- **Windows 4KB 파이프 버퍼 고갈에 의한 대용량 스냅샷 양방향 블로킹 데드락** (`native_loop.py`): 자식 프로세스의 stdout 출력이 4KB를 초과할 때 부모가 읽지 않고 대기하면 파이프 버퍼가 가득 차 양방향 데드락 발생.

### 2) 하드웨어 및 텔레메트리 결함 (Hardware & Telemetry)
- **매 측정마다 신규 소켓 생성 및 TCP TIME_WAIT 소켓 고갈 (10048)** (`bridge.py:96-173`): 초당 20회 폴링 시 120초 동안 4,800개 소켓이 누적되어 Windows 임시 포트(16,384개) 완전 고갈.
- **PASCO 850 FPGA 고정밀 클록 폐기 및 소프트웨어 타임스탬프 지터 위상 왜곡** (`session/telemetry.py:24-39`): 하드웨어 클록을 버리고 호스트 OS 시계에 의존하여 다채널 측정 시 수십 ms 위상 지터 발생.
- **다채널 타임스탬프 비정합 100% 거부** (`session/telemetry.py:67-79`, `experiment_analysis.py:203-208`): 채널 간 공통 기준 타임스탬프 부재로 피팅 엔진 전달 시 100% 거부 에러.

### 3) FastMCP 및 도구 직렬화 결함 (FastMCP & Tools)
- **FastMCP model_dump_json null 직렬화로 기본 요청 100% 거부 크래시** (`tools/instruments.py:72`, `instruments/models.py:445`): 미설정 필드가 null로 직렬화되어 필수 키 검사를 우회, 기본 요청 전면 거부.
- **수식 AST 파서 부재 및 100% 가짜 성공 날조** (`calculator.py:43, 117-189`): 괄호 불균형 수식을 무필터링 타이핑하고 모달 에러 발생 시에도 `verified=True` 날조 반환.
- **`handle=0` 기본값 자동 폴백 부재로 런 조작 100% 거부** (`runs/manager.py:249`, `desktop.py:195`): 활성 창 자동 폴백 없이 0 전달로 `AutomationError` 폭발.
- **중괄호 주입 시 Pywinauto KeySequenceError 서버 크래시** (`runs/manager.py:75-78`): 런 이름에 `{1}` 입력 시 가상 키 코드로 오인하여 서버 크래시.

### 4) 다국어 로케일 및 수치해석 결함 (Locales & Numerics)
- **CP949 인코딩 디코딩 실패 500 크래시** (`csv_data.py`, `file_workflows.py`): `utf-8-sig` 하드코딩으로 한국어 Windows 기본 CP949 CSV 파일 읽기 시 100% 크래시.
- **유럽식 인용 소수점("0,750") 파싱 불가**: 쉼표 소수점 거부로 유럽형 데이터 처리 불가.
- **Vandermonde 조건수 폭발**: 다항회귀 고차항 계산 시 조건수 폭발 및 수평선 $R^2=1.0$ 날조.

---

## 3. 🛠️ 완벽한 결함 격퇴를 위한 차기 엔지니어링 마스터플랜 (Phase 12)

| 단계 | 추진 과제 | 대상 결함 | 완료 판정 기준 |
| :---: | :--- | :--- | :--- |
| **Phase 12-A** | **P0 Blocker 격퇴: 프로세스 락업 해제 및 보안 취약점 차단** | P0 결함 79건 (ctypes 콜백 보존, RCE 포트 차단, WinEvent 훅 정리, 클립보드 API 전면 적출, 다중 인스턴스 자동 복구, terminate() 프로세스 kill, 전역 싱글톤 제거, STA 메시지 펌프 루프 구현, 다중창/포커스 락 해제, AST 수식 검증기 도입) | 세그멘테이션 오류 0건, 호스트 클립보드 오염 0바이트, Capstone 크래시 시 자동 복구, 프로세스 누수 0건 |
| **Phase 12-B** | **P1 Critical 격퇴: 실기 연동 복구 및 은폐·날조 박멸** | P1 결함 156건 (지속 WebSocket 연결 풀링으로 소켓 고갈 방어, 가짜 Fallback 데이터 제거, Path Traversal 방어, FakeBackend 제거 및 실기 RPC 구현, Time축 날조 제거, Zip Bomb 방어, 전원 상태 감지) | 소켓 고갈 0건, 가짜 데이터 주입 0건, CI E2E 테스트 100% 통과, UIA 침묵 실패 0건 |
| **Phase 12-C** | **P2/P3 격퇴: 다국어 로케일 및 대용량 렌더링 엔진 고도화** | P2/P3 결함 123건 (한글 CP949/유럽 로케일 지원, SVG LTTB 다운샘플링, HTML 템플릿 일치화, 절대경로 하드코딩 제거, Vandermonde 정규화) | 한글 Capstone 100% 정상 작동, 100만 포인트 렌더링 브라우저 안정성 보장 |
