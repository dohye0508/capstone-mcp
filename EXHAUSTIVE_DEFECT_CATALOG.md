# Capstone-MCP Exhaustive Defect Catalog & Live Runtime Stabilization Whitepaper

- **일자**: 2026-11-15
- **감사 대상**: `src/capstone_mcp/` 207개 파일 (2,145,077 바이트)
- **적용 규약**: ADR 0005 (`docs/adr/0005-exhaustive-live-stabilization.md`), GLOSSARY.md
- **감사 목적**: 단위 테스트(570개, 85% 커버리지)의 실기 사각지대(Live Runtime Blind Spot)를 돌파하고, 실제 Windows OS 및 실물 Capstone.exe 구동 시 폭발하는 잠재 뇌관 전수 규명 및 격퇴 계획 수립

---

## 1. 📊 종합 결함 매트릭스 (Executive Summary)

| 카테고리 | 검출 건수 | 위험도 | 주요 해당 파일 | 실기(Live) 폭발 조건 |
| :--- | :---: | :---: | :--- | :--- |
| **A. OS 전역 자원 침범** | **64건** | **치명적 (Critical)** | `graphs/inspection.py` | 사용자 클립보드 데이터 유실, 타 앱과 클립보드 경합 시 조회 중단 |
| **B. Silent Failure (묵살)** | **47건** | **치명적 (Critical)** | `runs/manager.py`, `displays/harness.py`, `graphs/toolbox.py` | 키입력(F2, Delete) 및 드래그 실패 시 정상 처리로 위장하거나 더블클릭 둔갑 |
| **C. 로케일 종속 하드코딩** | **18건** | **높음 (High)** | `file_workflows.py`, `calculator.py`, `graphs/inspection.py` | 한글 윈도우/한글 언어팩 Capstone 구동 시 100% `AutomationError` 폭발 |
| **D. 리버싱 미연결 매크로** | **4대 핵심 도구** | **높음 (High)** | `capfiles/archive.py`, `bridge.py`, `fake_backend.py` | QWebChannel 53개 RPC 및 .cap 파일 합성 역량 미연결로 취약한 화면 매크로에 갇힘 |

---

## 2. 🔬 서브시스템별 상세 결함 목록 (Exhaustive Defect Breakdown)

### [카테고리 A] Zero OS Pollution 위반 (외부 OS 자원 오염 및 경합)

#### 🔴 DEFECT-A01: OS 전역 클립보드 백업-복원 트릭 잔존
- **파일**: `src/capstone_mcp/graphs/inspection.py` (L322-L357)
- **코드**:
  ```python
  def _backup_clipboard() -> dict[int, Any]:
      clip.OpenClipboard()
      while fmt := clip.EnumClipboardFormats(fmt):
          backup[fmt] = clip.GetClipboardData(fmt)
  ```
- **실기 폭발 시나리오**: 클립보드에 대용량 비트맵이나 비표준 OLE 객체가 들어있을 경우 OpenClipboard 타임아웃 또는 과도한 메모리 점유 발생. 타 프로세스와 충돌 시 시스템 클립보드 데이터 유실.
- **해결책**: 백업-복원 트릭을 완전 적출하고 클립보드 API 호출 일체 금지.

#### 🔴 DEFECT-A02: `GetClipboardSequenceNumber` 기반 클립보드 강제 덮어쓰기
- **파일**: `src/capstone_mcp/graphs/inspection.py` (L359-L381, L445-L450)
- **코드**:
  ```python
  sequence = win32clipboard.GetClipboardSequenceNumber()
  app.control(copies[0].ref).invoke() # Copy Display 메뉴 호출
  state = events.changes.until(lambda: _copied_graph(sequence, pid), ...)
  ```
- **실기 폭발 시나리오**: Capstone의 "Copy Display" 메뉴를 UIA로 호출하여 OS 전역 클립보드를 오버라이트함. 이 과정에서 다른 프로세스가 클립보드를 갱신하면 `msg = "Another application changed the clipboard"` 예외를 던지며 분석이 중단됨.
- **해결책**: CDP QWebChannel WebSocket RPC 또는 임시 파일 저장 후 파싱으로 전환.

---

### [카테고리 B] Bi-furcated Exception Contract 위반 (Silent Failure & 기만적 폴백)

#### 🔴 DEFECT-B01: UIA 드래그 실패 시 더블클릭 둔갑 (기만적 폴백)
- **파일**: `src/capstone_mcp/displays/harness.py` (L99-L126)
- **코드**:
  ```python
  def drag_control(app, handle, source, target, ...):
      with contextlib.suppress(Exception): app.focus_window(handle)
      with contextlib.suppress(Exception):
          if hasattr(node, "drag_mouse"): node.drag_mouse(dst_coords); return
      # 드래그 실패 시 엉뚱하게 더블클릭 수행!
      double_click_control(app, handle, source)
  ```
- **실기 폭발 시나리오**: 팔레트 아이템을 특정 컨테이너로 드래그해야 하는데 드래그가 씹히면 조용히 더블클릭을 실행함. 실기 Capstone에서 팔레트 더블클릭은 엉뚱한 위치에 위젯을 중첩 생성하거나 무시되어 레이아웃이 파괴됨.
- **해결책**: 기만적 폴백 삭제, 드래그 액션 실패 시 즉시 `AutomationError` 페일패스트 발생.

#### 🔴 DEFECT-B02: 런 이름 변경(F2) 및 삭제(DELETE) 키스트로크 무음 묵살
- **파일**: `src/capstone_mcp/runs/manager.py` (L65-L75, L203-L220)
- **코드**:
  ```python
  # rename_run
  with contextlib.suppress(Exception): _ = node.set_focus()
  if hasattr(app, "keys"):
      _ = app.keys(handle, "{F2}", ...) # 키입력 실패 무음 은폐
      _ = app.keys(handle, request.new_name + "{ENTER}", ...)

  # delete_run
  with contextlib.suppress(Exception): node.select()
  with contextlib.suppress(Exception):
      app.keys(request.handle, "{DELETE}", ...) # 키입력 실패 무음 은폐
  ```
- **실기 폭발 시나리오**: 포커스가 어긋나거나 위젯이 바빠서 F2나 DELETE 키가 씹혔음에도 에러가 발생하지 않아, 런이 삭제되거나 이름이 바뀌지 않았는데도 호출자에게는 정상 성공으로 반환됨.
- **해결책**: 키 전송 전후의 컨트롤 상태(트리 아이템 이름, 항목 개수)를 재확인하고, 변경이 반영되지 않았을 경우 즉시 `AutomationError` 발생.

#### 🔴 DEFECT-B03: 툴박스(ZSmartToolBox) 조작 8중 `suppress`
- **파일**: `src/capstone_mcp/graphs/toolbox.py` (L85-L160)
- **코드**: 도구 버튼 클릭, 좌표 델타 측정, 통계치 토글 시 `contextlib.suppress(Exception)` 남발.
- **실기 폭발 시나리오**: 툴박스 팝업이 닫혀 있거나 비활성화된 상태에서 도구를 켰다고 거짓 보고.
- **해결책**: 툴박스 가시성 및 버튼 활성화 상태를 검증하고 실패 시 명시적 예외 처리.

---

### [카테고리 C] Locale Decoupling 위반 (로케일 종속 하드코딩)

#### 🔴 DEFECT-C01: `export_data` 내보내기 대화상자 영문 하드코딩
- **파일**: `src/capstone_mcp/file_workflows.py` (L262-L270)
- **코드**:
  ```python
  _choose_export_option(app, events, export_handle, "Export Format", "Comma separated values")
  _choose_export_option(app, events, export_handle, "Alignment Options", "Align by Index")
  select = _named_button(app, export_handle, "Select All")
  export = _named_button(app, export_handle, "Export to file...")
  ```
- **실기 폭발 시나리오**: 한글 윈도우 환경 Capstone에서는 "내보내기 형식", "쉼표로 구분된 값", "모두 선택"으로 렌더링되므로 `_named_button`에서 대화상자 요소를 찾지 못하고 100% 무조건 타임아웃 폭발.
- **해결책**: `AutomationId` 기반 선택 또는 중앙 `LocaleTable`을 통한 다국어 정규식 매칭.

#### 🔴 DEFECT-C02: 메뉴바 및 팝업 메뉴 영문 하드코딩
- **파일**: `src/capstone_mcp/graphs/inspection.py` (L417, L437)
- **코드**: `c.name == "Display"`, `c.name == "Copy Display"`
- **실기 폭발 시나리오**: 한글 환경에서 메뉴명이 달라 즉시 `Expected one enabled Display menu` 폭발.
- **해결책**: 메뉴 텍스트 매칭 제거, 네이티브 인터페이스로 전환.

#### 🔴 DEFECT-C03: 계산기 및 하드웨어 서랍 팔레트 이름 하드코딩
- **파일**: `src/capstone_mcp/calculator.py` (L57-L98), `src/capstone_mcp/instruments/models.py` (L272-L274)
- **코드**: `ctrl.name.strip() == "Calculator"`, `HARDWARE_SETUP_NAME = "Hardware Setup"`, `"formula" in name_lower`
- **실기 폭발 시나리오**: 한글 언어팩에서 "계산기", "하드웨어 설정", "수식"으로 표시되어 컨트롤 탐색 실패.
- **해결책**: AutomationId suffix (`.calc`, `.SamplingRateTargetSelector`) 우선 탐색 강제.

---

### [카테고리 D] Direct Synthesis Path 부재 (리버싱 자산 미연결)

#### 🔴 DEFECT-D01: `.cap` (ZIP+XML) 아카이브 생성/합성 엔진 부재
- **파일**: `src/capstone_mcp/capfiles/archive.py`
- **실태**: `.cap` 내부의 XML/바이너리 레코드 구조를 읽는 역공학은 100% 완료되었으나, 쓰기/패칭 기능이 없음.
- **결과**: 계산식을 넣거나 워크북 레이아웃을 생성할 때 마우스 클릭과 타이핑 매크로에 전적 의존.
- **해결책**: `.cap` 구조에 계산식 및 레이아웃을 직접 주입하는 파일 합성기(Synthesis Engine) 구축.

#### 🔴 DEFECT-D02: QWebChannel 53개 C++ RPC 실기 파이프라인 단절
- **파일**: `src/capstone_mcp/bridge.py`, `src/capstone_mcp/fake_backend.py`
- **실태**: `fake_backend.py`에는 53개 네이티브 RPC가 모의 구현되어 있으나, 실기 `bridge.py`에서는 단 2개(`RequestSensorsAndMeasurements`, `RequestReadMeasurement`)만 CDP 웹소켓으로 연결되어 있음.
- **결과**: 나머지 51개 액션이 실기에서 네이티브 슬롯을 타지 못하고 취약한 UIA로 굴러떨어짐.
- **해결책**: 실기 `bridge.py`에 QWebChannel RPC 채널을 확장 연결.

---

## 3. 🛠️ Phase 12 결함 격퇴 마스터 로드맵 (Actionable Plan)

| 순번 | 작업 명칭 | 대상 결함 | 산출물 및 검증 기준 |
| :---: | :--- | :--- | :--- |
| **Ticket 1** | **클립보드 오염 완전 적출 (Zero OS Pollution)** | DEFECT-A01, A02 | `graphs/inspection.py`에서 `win32clipboard`, 백업/복원 코드 완전 제거. OS 자원 격리 검증. |
| **Ticket 2** | **페일패스트 에러 계약 개혁 (Fail-Fast Reform)** | DEFECT-B01, B02, B03 | `displays/harness.py`, `runs/manager.py` 등 47개 suppress 전수 심문 및 기만적 폴백 박멸. |
| **Ticket 3** | **다국어 로케일 디커플링 (Locale Decoupling)** | DEFECT-C01, C02, C03 | `file_workflows.py`, `calculator.py`에서 영문 하드코딩 제거, AutomationId 및 `LocaleTable` 도입. |
| **Ticket 4** | **`.cap` 직접 합성 엔진 구축 (Direct Synthesis)** | DEFECT-D01 | 계산식 및 설정을 파일 구조에 직접 주입하여 UI 매크로 우회. |
| **Ticket 5** | **QWebChannel C++ RPC 실기 연결 확장 (Direct IPC)** | DEFECT-D02 | `bridge.py`의 CDP 평가 메서드를 50여 개 RPC로 확장하여 고속 네이티브 통신 실현. |
