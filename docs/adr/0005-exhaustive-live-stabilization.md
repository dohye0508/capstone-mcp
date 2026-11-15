# ADR 0005: 실기(Live Capstone) 런타임 사각지대 전수 격퇴 및 무결성 아키텍처 확립

- **상태 (Status)**: 승인됨 (Accepted)
- **일자 (Date)**: 2026-11-15
- **결정권자 (Deciders)**: 사용자, 에이전트

## 맥락 (Context)
1. **Live Runtime Blind Spot의 착시**: Phase 11에서 570개 단위 테스트가 100% 통과하고 Seam 커버리지 85.0%를 달성했으나, 이 테스트들은 가상 백엔드(`InMemoryFakeBackend`)와 `MagicMock` 위에서 구동되어 실제 Windows OS 환경 및 실물 Capstone 런타임 뇌관들을 은폐하고 있었음.
2. **OS 전역 자원 침범 잔존**: Phase 11 Ticket 1에서 박멸되었다고 보고된 클립보드 코드가 `graphs/inspection.py`에서 `_backup_clipboard()` / `_restore_clipboard()` 트릭으로 온존하여, 실기 구동 시 사용자 OS의 클립보드를 오버라이트하고 외부 앱과의 경합 시 즉시 폭발하는 위험이 상존함.
3. **무음 실패(Silent Failure)의 만연**: 코드베이스 전역 44곳에 `contextlib.suppress`가 산재하여, 포커스 실패, F2 키입력 씹힘, Delete 키입력 무시, 마우스 드래그 실패 시 에러를 던지지 않고 엉뚱한 폴백(드래그 실패 시 더블클릭 등)을 감행하거나 성공으로 위장함.
4. **로케일 종속성으로 인한 한글 환경 폭발**: `file_workflows.py`, `calculator.py`, `instruments/` 등에서 `"File"`, `"Export to file..."`, `"Select All"`, `"Calculator"` 등 영문 UI 문자열이 하드코딩되어 한글 윈도우/한글 언어팩 Capstone에서 100% `AutomationError`가 폭발함.
5. **리버싱 자산과 런타임 구현의 단절**: `.cap` 복합 아카이브 구조(ZIP+XML)와 QWebChannel 53개 RPC를 역공학해두었음에도, 실기 도구들은 여전히 가장 취약한 UIA 화면 마우스/키보드 매크로에 전적으로 의존하고 있었음.

## 결정 (Decision)

### 1. Zero OS Pollution (외부 OS 자원 침범 원천 금지)
- MCP 서버는 실행 중인 호스트 OS의 전역 클립보드, 마우스 포커스 강탈, 시스템 단축키 전역 가로채기, 관리되지 않는 임시파일 잔류를 일체 금지함.
- `graphs/inspection.py`의 `_backup_clipboard()`, `_restore_clipboard()`, `GetClipboardSequenceNumber()`를 완전 적출하고, 데이터 수집은 QWebChannel RPC 직접 질의 또는 파일 덤프/파싱으로만 수행함.

### 2. Bi-furcated Exception Contract (이중 예외 처리 계약)
- **단순 조회형 프로빙 (Inspection Probing)**: 노드의 특정 COM 인터페이스나 속성 유무를 확인하는 검사(`hasattr(node, "iface_value")`)에 한해서만 안전한 예외 제어를 허용함.
- **상태 변경 액션 (State-Mutating Action)**: 마우스 클릭, 드래그, 키입력(F2, Delete), 값 변경, 창 닫기 등 시스템 상태를 바꾸는 모든 액션의 실패는 절대 `suppress`하지 않으며, 즉시 구체적인 도메인 예외(`AutomationError`)를 던져 페일패스트(Fail-Fast)함. 드래그 실패 시 더블클릭과 같은 기만적 폴백은 영구 추방함.

### 3. Locale Decoupling (다국어 로케일 비종속성)
- UI 컨트롤 탐색 시 텍스트 매칭(`c.name == "..."`)을 1순위로 사용하는 방식을 전면 폐기하고, 언어 중립적인 `AutomationId` 매칭을 최우선으로 일원화함.
- 부득이한 UI 문자열 탐색이 필요한 경우, 중앙 집중식 다국어 매핑 테이블(`LocaleTable`) 또는 정규식 패턴을 통해서만 매칭하여 한글/영문 환경 모두에서 동일하게 작동하도록 보장함.

### 4. Direct Synthesis Path (리버싱 자산 기반 직통로 구축)
- `.cap` 아카이브(ZIP+XML)의 쓰기/합성(Synthesis) 엔진을 구축하여, 계산식 등록, 센서 설정, 워크북 페이지 구성을 불안정한 UI 매크로 대신 파일 직접 주입 방식으로 전환함.
- QWebChannel 53개 RPC 슬롯을 실기 `bridge.py`와 `SessionCdpClient`에 순차적으로 연결하여 고속 네이티브 IPC 통신을 실현함.
