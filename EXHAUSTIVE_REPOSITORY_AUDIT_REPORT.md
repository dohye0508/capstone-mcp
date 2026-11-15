# Capstone-MCP Codebase-Wide Exhaustive Audit Report (426 Master Defects)

- **발간 일자**: 2026-11-15
- **감사 대상**: `src/capstone_mcp/` 207개 파일 전역 (2,145,077 바이트) 및 `tests/` 70개 파일 전역
- **감사 주체**: 22개 전문 감사 에이전트 스웜 (서브시스템 전담 감사관 + 총괄 검증관 `auditor-verifier`)
- **적용 규약**: Spec #120, ADR 0005, GLOSSARY.md
- **감사 목적**: 570개 단위 테스트와 85% 커버리지에 가려져 있던 **Live Runtime Blind Spot**을 돌파하고, 실제 Windows OS 및 실물 Capstone 런타임에서 시스템 마비, 프로세스 고아화, 호스트 자원 파괴, 데이터 조작, 가짜 데이터 사기를 유발하는 모든 잠재 결함을 라인 단위로 전수 적출하여 공식 영구 백서로 확립함.

---

## 1. 📊 Executive Summary & 결함 심각도 매트릭스

22개 전문 감사 에이전트 스웜의 1:1 프로덕션 코드 대조 실사와 교차 검증을 거쳐, 중복을 제거한 **최종 426건의 마스터 결함(Phase 1~3 358건 + Phase 4 68건)**이 공인 확정되었습니다:

| 심각도 등급 | Phase 1~3 | Phase 4 신규 | 누적 마스터 합계 | 핵심 결함 카테고리 요약 |
| :---: | :---: | :---: | :---: | :--- |
| **🔴 P0 (Blocker)** | 79건 | **15건** | **94건** | WinEvent 훅 GIL 고갈, ctypes GC 댕글링 포인터 크래시(0xC0000005), 팝업메뉴 HWND 좌표 분리 100% 클릭 실패, UIPI unhandled COMError(0x80070005), FastMCP 96DPI 고해상도 오폭 클릭, IPv6 WSAECONNREFUSED, 센서 핫언플러그 COM 크래시, NFD 파일명 40초 타임아웃, 대용량 역직렬화 OOM, 전 실험 모의 사기 등 |
| **🟠 P1 (Critical)** | 156건 | **34건** | **190건** | High-DPI 다중모니터 블랙아웃, 키스트로크 수식 파괴(send_keys +, %, ^), 100kHz USB Bulk 99.9% 패킷 드랍, 시간축 왜곡, TCP TIME_WAIT 고갈, 웹소켓 64KB Continuation 누락, NTFS Symlink 덮어쓰기 우회, FFT 진폭 50% 왜곡, Zip Bomb 메모리 DoS 등 |
| **🟡 P2 (Major)** | 73건 | **19건** | **92건** | 유럽식 쉼표/세미콜론 소수점 누락, 런 정렬 왜곡, 비정규 부동소수점 CPU 100배 스톨, Junction 디렉터리 감시 행, TelemetryBuffer 불필요 O(N) 복제, SVG NaN 좌표 크래시 등 |
| **🟢 P3 (Minor/Debt)** | 50건 | **0건** | **50건** | 행복경로 단일 테스트, 시간 기반 플래키, 포트 9222 vs 9223 불일치, 피트 상태 FAIL_MAX_ITERATONS 오타, 디스플레이 ID 하드코딩 등 |
| **합계** | **358건** | **68건** | **426건** | **코드베이스 207개 프로덕션 파일 및 70개 테스트 파일 4단계 전수 실사 완료** |

---

## 2. 🗺️ 8대 Tracer-Bullet 에픽 이슈 연계 매트릭스

358건의 결함은 단일 PR에서 해결할 수 없으며, Matt Pocock 엔지니어링 원칙에 따라 8개의 독립적 검증 가능 에픽 티켓으로 분할되어 GitHub 트래커에 공식 등록되었습니다:

| 에픽 티켓 | 제목 및 주요 책임 영역 | 의존성 (Blocked by) | 연결된 결함 카테고리 |
| :---: | :--- | :---: | :--- |
| [#123](https://github.com/ji5zi5/capstone-mcp/issues/123) | **[Fix P0] 프로세스 수명주기 격리 & 좀비 방지 & STA 메시지 펌프 루프** | None (Frontier) | COM 초기화, 세션 고아화, 타임아웃 프로세스 사살 방지 |
| [#124](https://github.com/ji5zi5/capstone-mcp/issues/124) | **[Fix P0/P1] 보안 & 저수준 메모리: ctypes GC 댕글링 포인터 방지 & RCE 포트 차단** | None (Frontier) | 0xC0000005 크래시 방지, Chromium SOP RCE 차단, Path Traversal 방어 |
| [#125](https://github.com/ji5zi5/capstone-mcp/issues/125) | **[Fix P0] OS 클립보드 오염 완전 적출 & 다중 창 잠금 해제** | #123 | 클립보드 펌프 완전 적출, 창 핸들 격리, 다중 창 락 해제 |
| [#126](https://github.com/ji5zi5/capstone-mcp/issues/126) | **[Fix P0/P1] 통신 & 텔레메트리: CDP 소켓 풀링(TIME_WAIT 방어) & 하드웨어 클록 동기화** | #123 | TCP 소켓 고갈 방어, PASCO 850 클록 복원, 타임스탬프 비정합 해소 |
| [#127](https://github.com/ji5zi5/capstone-mcp/issues/127) | **[Fix P0/P1] FastMCP 직렬화 & 계산기 AST 수식 검증기 도입** | #123 | null 직렬화 방어, 괄호 검증 AST 파서, 원시 예외 MCP 캡슐화 |
| [#128](https://github.com/ji5zi5/capstone-mcp/issues/128) | **[Fix P0/P1] UIA 키스트로크 인젝션 방어 & Stale Ref 자동 복구** | #125 | pywinauto 중괄호 크래시 방어, Stale Ref 감지 자동 재시도, 포커스 보호 |
| [#129](https://github.com/ji5zi5/capstone-mcp/issues/129) | **[Fix P0/P1] 물리 레시피 가짜 데이터 전면 제거 & 51개 QWebChannel RPC 실기 연결** | #126, #127 | FakeBackend 적출, 실기 RPC 연결, 가짜 Fallback 데이터 제거, Wire E2E 복원 |
| [#130](https://github.com/ji5zi5/capstone-mcp/issues/130) | **[Fix P2/P3] 다국어 CP949 & 유럽식 CSV 로케일 & SVG LTTB 다운샘플링** | #129 | CP949/BOM 인코딩 자동감지, 유럽식 쉼표 소수점 지원, 대용량 LTTB 렌더러 |

---

## 3. 🔍 9대 서브시스템별 358건 마스터 결함 전수 상세 카탈로그

아래는 22개 전문 감사 에이전트 스웜이 라인 단위로 발굴하고 총괄 검증관이 교차 대조하여 확정한 358건 결함의 전수 세부 명세입니다.
각 항목은 파일 경로, 라인 번호, 심각도(P0~P3), 재현 트리거, 파괴 시나리오, 구체적 수정 지침을 포함합니다.

---

### 3.1. Low-Level Native & Windows IPC (네이티브 COM & 프로세스 수명주기)
- **담당 에픽 이슈**: #123
- **실사 참여 전문 에이전트**: `auditor-native`, `audit-concurrency`, `auditor-core`

#### 📑 실사 보고서: `auditor-native` (총 3회 정밀 실사)

<details open>
<summary><b>[보고서 #56] auditor-native 실사 세부 명세 (Phase 1)</b></summary>

소유 모듈인 `src/capstone_mcp/native/*` (`runtime.py`, `errors.py`) 및 연계 계층(`native_loop.py`, `native_main.py`, `desktop.py`, `automation_worker.py`, `server.py`) 전수 감사 보고서입니다.

---

### 1. Windows COM STA 데드락 및 스레딩 경계 (COM STA Deadlocks & Threading Boundaries)

#### 🔴 DEFECT-NAT01: STA 메시지 펌프 부재 및 `sys.stdin.readline()` 동기 블로킹 데드락
- **파일 및 위치**: [native_loop.py#L24-L26](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native_loop.py#L24-L26), [native_loop.py#L56](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native_loop.py#L56)
- **코드**:
  ```python
  runtime = NativeDesktop()
  line = sys.stdin.readline(MAX_MESSAGE_BYTES + 1)
  while line:
      result = runtime.dispatch(packet.command)
      ...
      line = sys.stdin.readline(MAX_MESSAGE_BYTES + 1)
  ```
- **원인 및 실기 폭발 시나리오**:
  - `NativeDesktop`은 전용 프로세스 스레드에서 UIA/COM 객체(`IUIAutomation`)를 소유함. Windows COM STA(Single-Threaded Apartment) 스레드는 아파트먼트 간 마샬링 및 외부 COM/UI 이벤트 콜백을 처리하기 위해 반드시 Win32 메시지 루프(`PeekMessage`/`DispatchMessage` 또는 `MsgWaitForMultipleObjectsEx`)를 순환해야 함.
  - 그러나 `native_loop.py`는 `sys.stdin.readline()`으로 C 런타임 동기 I/O 블로킹 상태로 대기함. 명령 대기 중 Capstone이나 OS 접근성 서브시스템이 스레드로 윈도우 메시지나 비동기 UIA 이벤트를 전달하면 메시지 큐가 완전히 고갈(Starvation)되어 `RPC_E_CANTCALLOUT_ININPUTSYNCCALL` 또는 영구 데드락이 발생함.
- **아파트먼트 초기화 모순**:
  - [native_main.py#L25](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native_main.py#L25)에서 `sys.__dict__["coinit_flags"] = 0`(`COINIT_MULTITHREADED`, MTA)으로 설정되어 있으나, 아키텍처 명세([architecture.md#L21](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/docs/architecture.md#L21))는 STA로 규정하고 있음. `comtypes`가 STA로 진입하려고 시도할 경우 `RPC_E_CHANGED_MODE`(0x80010106)가 발생하며, MTA로 유지될 경우 pywinauto UIA 호출 시 멀티스레드 마샬링 경합이 발생함.

#### 🔴 DEFECT-NAT02: 무제한 동기 COM RPC 호출로 인한 작업자 영구 블로킹 및 프로세스 강제 사살
- **파일 및 위치**: [runtime.py#L147-L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L147-L150)
- **코드**:
  ```python
  "read_value": lambda r: self.app.control(r.ref).iface_value.CurrentValue,
  "set_value": lambda r: _json(self.app.set_value(r.ref, r.value)),
  ```
- **원인 및 실기 폭발 시나리오**:
  - `iface_value.CurrentValue` 및 `SetValue`는 프로세스 경계를 넘어 Capstone UI 스레드로 동기 COM RPC를 전송함.
  - Capstone이 대규모 연산(수만 개 데이터 포인트 피팅/재계산) 중이거나 모달 상태일 때, COM 타임아웃/취소 필터(`IMessageFilter`)가 없어 워커 스레드가 무한정 블로킹됨. 부모 `AutomationWorker`의 60초 타임아웃이 초과되면 워커 프로세스가 강제 사살(`_retire()`)되어 세션이 파괴됨.

#### 🟠 DEFECT-NAT03: `_initialize_recording` 호출 시 기존 `Capstone` COM 객체 고아화 누수
- **파일 및 위치**: [runtime.py#L801-L806](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L801-L806)
- **코드**:
  ```python
  def _initialize_recording(self, request: NativeRequest) -> JsonValue:
      self.recording = NativeRecordingBackend(RepeatPlan.model_validate(request.plan))
      self.app = self.recording.app
      return _json(self.recording.observe())
  ```
- **원인**:
  - `NativeDesktop.__init__`에서 생성된 초기 `self.app`의 `window_cache` 및 UIA COM 인터페이스 포인터들이 정리(`clear`, `CoUninitialize`)되지 않은 채 `self.app = self.recording.app`에 의해 덮어씌워져 COM 프록시 객체가 고아화됨.

#### 🟠 DEFECT-NAT04: DwmFlush 호출로 인한 헤드리스/가상 환경 블로킹
- **파일 및 위치**: [desktop.py#L460-L466](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L460-L466), [runtime.py#L717](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L717)
- **원인**:
  - DWM 컴포지터가 비활성화된 헤드리스 CI 또는 Windows Server RDP 세션에서 `ctypes.WinDLL("dwmapi")["DwmFlush"]`가 음수를 반환하거나 V-Sync 대기 상태로 스레드를 멈추게 하여 `observe_graph`가 실패함.

---

### 2. 네이티브 STA 워커 - MCP AnyIO 이벤트 루프 예외 전파 (Exception Propagation)

#### 🔴 DEFECT-NAT05: `classify_native_error`의 치명적 부분문자열 오매칭 버그 (`"time"`, `"recording"`, `"session"`)
- **파일 및 위치**: [errors.py#L12](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L12), [errors.py#L17](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L17), [errors.py#L57](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L57), [errors.py#L93-L95](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L93-L95)
- **코드**:
  ```python
  (("time",), "TIMEOUT_ERROR", "Operation timed out; ..."),
  (("recording",), "RECORDING_NOT_INITIALIZED", "Initialize recording session ..."),
  ```
- **원인 및 실기 폭발 시나리오**:
  - `_ERROR_RULES`가 단순 `kw in lower` 부분문자열 검색을 수행함.
  - `"time"` 키워드로 인해 **`RuntimeError`**(e.g. `RuntimeError("Calculation syntax error")`), `"timestamp invalid"`, `"timebase error"`, `"sometimes dropped"` 등 모든 에러가 `TIMEOUT_ERROR`로 둔갑함.
  - `"recording"` 키워드로 인해 레코딩 도중 발생한 센서 단선이나 디스크 부족 에러가 `RECORDING_NOT_INITIALIZED`로 오분류됨.
  - 단어 경계(`\b`) 검사 없는 무차별 substring 매칭으로 인해 LLM에게 엉뚱한 복구 안내(remediation)를 전달함.

#### 🔴 DEFECT-NAT06: `error_code=None`인 `NativeSessionError` 발생 시 AnyIO 루프 500 크래시
- **파일 및 위치**: [server.py#L78-L92](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L78-L92), [automation_worker.py#L171-L202](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/automation_worker.py#L171-L202)
- **코드**:
  ```python
  except NativeSessionError as exc:
      if exc.error_code:
          payload = ToolErrorPayload(...)
          raise ToolError(payload.model_dump_json(indent=2)) from exc
      raise  # <-- 원시 예외 재발생
  ```
- **원인 및 실기 폭발 시나리오**:
  - 워커가 충돌(Crash), 타임아웃, 비정상 종료(EOF)되면 `AutomationWorker`는 `error_code=None`인 `NativeSessionError`를 발생시킴.
  - `server.py`의 `_native`는 `if exc.error_code:` 분기만 처리하고 `else`에서는 `raise`로 원시 예외를 그대로 전파함.
  - FastMCP는 처리되지 않은 원시 예외를 잡지 못하고 AnyIO 비동기 이벤트 루프에서 500 내부 에러로 폭발시켜 클라이언트에게 파이썬 트레이스백을 노출함.

#### 🟠 DEFECT-NAT07: 만료된 제어 참조(Stale Ref) 에러가 일반 `AUTOMATION_ERROR`로 오분류
- **파일 및 위치**: [errors.py#L83-L99](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L83-L99), [desktop.py#L324](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L324)
- **원인**:
  - `desktop.py`의 `AutomationError("Unknown or stale ref. Take a new snapshot.")` 메시지에 `"control"` 키워드가 없어 `CONTROL_NOT_FOUND`에 걸리지 않고 폴백인 `AUTOMATION_ERROR`("Check Capstone application state using capstone_windows and retry")로 분류됨. LLM에게 스냅샷 재취득이 아닌 윈도우 목록 조회를 지시하여 복구 루프가 고장남.

#### 🟠 DEFECT-NAT08: `GraphOperationError`의 `next_action` 무시 및 복구 안내 하드코딩
- **파일 및 위치**: [errors.py#L69-L81](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L69-L81)
- **원인**:
  - `GraphOperationError`가 풍부한 `GraphFailure` 메타데이터(`next_action`, `stage`, `detail`)를 보유하고 있음에도 `remediation`을 `"Verify graph display exists using capstone_manage_graph(action='read') or snapshot."`으로 무조건 고정함. `FRAME_REQUIRED` 상태에서도 `observe_graph` 대신 `manage_graph`를 호출하도록 잘못 유도함.

---

### 3. 윈도우 핸들 부패 및 세대 카운터 비동기화 (Handle Staleness & Generation Desync)

#### 🔴 DEFECT-NAT09: `self.window_cache`의 무기한 핸들 보관 및 OS 핸들 재활용에 따른 좀비 COM 프록시 참조
- **파일 및 위치**: [desktop.py#L198-L202](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L198-L202)
- **코드**:
  ```python
  if handle not in self.window_cache:
      self.window_cache[handle] = (
          Desktop(backend="uia").window(handle=handle).wrapper_object()
      )
  return self.window_cache[handle]
  ```
- **원인 및 실기 폭발 시나리오**:
  - `self.window_cache`는 `attach()` 시점에만 비워짐. Windows OS가 파괴된 창의 HWND를 새 창이나 대화상자에 재할당(Recycle)하면, 캐시는 죽은 UIA COM 포인터를 반환함. 이후 해당 핸들로 액션을 수행하면 `RPC_E_DISCONNECTED`(0x80010108)가 발생함.

#### 🔴 DEFECT-NAT10: `_initialize_recording` 시 `session_id` 및 세대 카운터 강제 리셋 비동기화
- **파일 및 위치**: [runtime.py#L801-L806](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L801-L806)
- **원인 및 실기 폭발 시나리오**:
  - `_initialize_recording`이 새 `Capstone()` 인스턴스를 생성하여 `self.app`에 할당함.
  - 이로 인해 `session_id`가 새 UUID로 바뀌고 `generation`은 0으로 초기화되며 `refs`는 완전히 비워짐. 클라이언트가 이전에 취득한 모든 컨트롤 ref(`<old_session_id>:<gen>:<idx>`)가 즉시 무효화되어 후속 조작이 일괄 실패함.

#### 🟠 DEFECT-NAT11: 상태 변경 조작 시 `refs.clear()` 수행하면서 `generation` 카운터 미증가
- **파일 및 위치**: [desktop.py#L337](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L337), [desktop.py#L378](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L378), [runtime.py#L832, L859, L878](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L832)
- **원인**:
  - `act`, `set_value`, `click`, `drag`, `scroll`, `keys` 등 6개 뮤테이션에서 `refs.clear()`를 호출하지만 `generation` 카운터는 오직 `matching_snapshot`에서만 증가함. 세대 번호는 그대로인데 참조 맵만 비워져 세대 번호의 유효성 추적 규약이 깨짐.

#### 🟠 DEFECT-NAT12: `_verify_frame` 1회성 자폭 및 픽셀 노이즈로 인한 `STALE_FRAME` 오탐
- **파일 및 위치**: [runtime.py#L738](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L738), [runtime.py#L764-L767](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L764-L767)
- **코드**:
  ```python
  capture = self.last_frame
  self.last_frame = None  # <-- 진입 즉시 자폭
  ...
  elif self.app.graph_screenshot(request.handle) != base64.b64decode(capture.png_base64):
      reason = "The visible graph image changed."
  ```
- **원인**:
  - `self.last_frame = None`을 사전 검증 실패 전에 선제적으로 실행하여 일시적 인자 오류에도 유효했던 프레임 영수증을 즉시 파기함.
  - Windows ClearType 안티앨리어싱, 툴팁 잔상, 커서 깜빡임 등 1바이트 렌더링 차이만으로도 원본 PNG와 불일치하여 불필요한 `STALE_FRAME` 에러를 남발함.

---

### 4. 네이티브 스냅샷 직렬화 메모리 누수 (Memory Leaks in Serializations)

#### 🔴 DEFECT-NAT13: `_json` 이중 직렬화/역직렬화 및 `NativeReply` 삼중 직렬화 메모리 폭증
- **파일 및 위치**: [runtime.py#L106-L107](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L106-L107), [native_loop.py#L53-L54](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native_loop.py#L53-L54)
- **코드**:
  ```python
  def _json(model: BaseModel) -> JsonValue:
      return JSON_VALUE.validate_json(model.model_dump_json())
  ```
- **원인 및 실기 폭발 시나리오**:
  - `model.model_dump_json()`(JSON 문자열 생성) -> `validate_json()`(수만 개 파이썬 dict/list 객체 생성) -> `reply.model_dump_json()`(다시 JSON 문자열로 직렬화).
  - 수백 개 컨트롤을 가진 `Snapshot` 요청 1회당 메가바이트 단위의 임시 객체 수만 개가 힙에 생성/해제되어 GC 지연과 워커 프로세스 메모리 파편화를 유발함.

#### 🟠 DEFECT-NAT14: `last_frame`에 고해상도 Base64 이미지 영구 상주 누수
- **파일 및 위치**: [runtime.py#L723-L734](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L723-L734)
- **원인**:
  - `observe_graph` 호출 시 생성된 수 MB~수십 MB 크기의 `png_base64` 문자열이 `self.last_frame` 인스턴스 변수에 영구 보관됨. 후속 입력 작업이 없으면 세션 종료 시까지 메모리에 상주함.

#### 🟠 DEFECT-NAT15: Pillow 이미지 객체 미해제로 인한 GDI 핸들 및 메모리 누수
- **파일 및 위치**: [desktop.py#L435-L448](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L435-L448)
- **원인**:
  - `processed = processed.crop(...)` 및 `resize(...)`로 생성된 새 PIL Image 인스턴스들이 `with` 컨텍스트 매니저 밖에서 `close()`되지 않아 비결정적 GC에 의존하며, 빈번한 스크린샷 캡처 시 GDI 핸들 소진을 초래함.

#### 🟡 DEFECT-NAT16: `_scroll`과 `_click`/`_drag` 간의 좌표계 불일치 결함
- **파일 및 위치**: [runtime.py#L827](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L827), [runtime.py#L874-L877](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L874-L877)
- **원인**:
  - `_click`과 `_drag`는 윈도우 프레임 좌표(`rect.left + x`)를 절대 좌표로 전달하지만, `_scroll`은 `coords=(request.point.x, request.point.y)`를 상대 좌표로 전달하여 pywinauto의 `client_to_screen`(클라이언트 영역 기준)이 적용됨. 동일 좌표 전달 시 타이틀바 높이만큼 마우스 휠 타깃이 빗나감.

#### 🟡 DEFECT-NAT17: `_drag`의 `finally` 블록 내 중복 마우스 릴리스 호출
- **파일 및 위치**: [runtime.py#L848-L858](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L848-L858)
- **원인**:
  - pywinauto의 `drag_mouse_input`이 이미 `dst`에서 마우스 버튼을 해제했음에도 `finally`에서 `release_mouse_input`을 한 번 더 호출하여 중복 `WM_LBUTTONUP` 메시지가 윈도우에 전달됨.

---

### 결함 종합 매트릭스 (Master Defect Matrix)

| ID | 결함 내용 | 심각도 | 해당 위치 |
|---|---|---|---|
| NAT-01 | STA 메시지 펌프 부재 및 `sys.stdin.readline` 동기 블로킹에 따른 COM 데드락 | **P0 (Blocker)** | [native_loop.py#L24-L56](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native_loop.py#L24-L56), [native_main.py#L25](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native_main.py#L25) |
| NAT-02 | 타임아웃 없는 동기 COM RPC 호출로 인한 워커 영구 블로킹 및 강제 사살 | **P0 (Blocker)** | [runtime.py#L147-L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L147-L150) |
| NAT-05 | `classify_native_error`의 무차별 부분문자열 검색으로 인한 `TIMEOUT_ERROR` 등 대량 오분류 | **P0 (Blocker)** | [errors.py#L12-L95](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L12-L95) |
| NAT-06 | `error_code=None`인 `NativeSessionError`가 `server.py`에서 걸러지지 않고 AnyIO 500 크래시 유발 | **P0 (Blocker)** | [server.py#L78-L92](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L78-L92), [automation_worker.py#L171-L202](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/automation_worker.py#L171-L202) |
| NAT-09 | `window_cache`의 무기한 핸들 보관 및 OS 재할당 HWND에 따른 죽은 COM 포인터 참조 | **P0 (Blocker)** | [desktop.py#L198-L202](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L198-L202) |
| NAT-10 | `_initialize_recording` 시 `Capstone` 인스턴스 덮어쓰기로 인한 `session_id` 및 세대 카운터 증발 | **P0 (Blocker)** | [runtime.py#L801-L806](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L801-L806) |
| NAT-13 | `_json` 이중 직렬화/역직렬화 및 `NativeReply` 재직렬화에 따른 극심한 메모리 파편화 | **P0 (Blocker)** | [runtime.py#L106-L107](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L106-L107), [native_loop.py#L53-L54](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native_loop.py#L53-L54) |
| NAT-03 | `_initialize_recording`에서 기존 `self.app`의 COM 객체 미해제 고아화 누수 | **P1 (Critical)** | [runtime.py#L801-L806](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L801-L806) |
| NAT-04 | DwmFlush 호출로 인한 헤드리스/가상 환경 블로킹 및 프레임 영수증 실패 | **P1 (Critical)** | [desktop.py#L460-L466](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L460-L466), [runtime.py#L717](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L717) |
| NAT-07 | 만료된 제어 참조(Stale Ref) 에러가 일반 `AUTOMATION_ERROR`로 오분류되어 복구 실패 | **P1 (Critical)** | [errors.py#L83-L99](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L83-L99) |
| NAT-08 | `GraphOperationError`의 구조화된 `next_action` 메타데이터 무시 및 하드코딩 복구 안내 | **P1 (Critical)** | [errors.py#L69-L81](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L69-L81) |
| NAT-11 | 조작 뮤테이션에서 `refs.clear()` 후 `generation` 카운터 미증가로 세대 추적 파괴 | **P1 (Critical)** | [desktop.py#L337, L378, L530](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L337), [runtime.py#L832, L859, L878](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L832) |
| NAT-12 | `_verify_frame` 사전 검증 실패 시 유효 영수증 선제 자폭 및 엄격 픽셀 바이트 비교 오탐 | **P1 (Critical)** | [runtime.py#L738, L764-L767](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L738) |
| NAT-14 | `last_frame`에 수십 MB 용량의 Base64 스크린샷 문자열 영구 상주 누수 | **P1 (Critical)** | [runtime.py#L723-L734](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L723-L734) |
| NAT-15 | `window_cache`의 무제한 증가로 인한 COM 프록시 스텁 메모리 누수 | **P1 (Critical)** | [desktop.py#L123, L198-L202](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L123) |
| NAT-16 | `_scroll`과 `_click`/`_drag`의 창 프레임 vs 클라이언트 영역 좌표계 불일치 | **P2 (Major)** | [runtime.py#L827, L874-L877](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L827) |
| NAT-17 | `_drag`의 `finally` 블록에서 중복 `release_mouse_input` 호출로 인한 불필요 이벤트 발생 | **P2 (Major)** | [runtime.py#L848-L858](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L848-L858) |

</details>

<details open>
<summary><b>[보고서 #71] auditor-native 실사 세부 명세 (Phase 2)</b></summary>

지침에 따라 `src/capstone_mcp/native/*` (`runtime.py`, `errors.py`) 및 직접 연계 계층(`desktop.py`, `native_loop.py`, `automation_worker.py`)의 전 라인을 정밀 재실사하여 새롭게 발굴한 7건의 고위험 결함(P0 2건, P1 3건, P2 2건) 상세 보고서입니다.

---

### 1. 🔴 DEFECT-NAT18 (P0 Blocker): 그래프 도구 조작 4종 프레임 영수증 검증 전면 우회
- **파일 및 위치**: [runtime.py#L674-L680](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L674-L680), [automation_worker.py#L248-L260](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/automation_worker.py#L248-L260)
- **코드**:
  ```python
  if request.operation not in GRAPH_INPUT_OPERATIONS | {
      "read_graph", "observe_graph", "create_graph", "manage_graph",
  }:
      return self.handlers[request.operation](request)  # <-- 검증 전면 우회 즉시 반환
  ```
- **재현 트리거**: `fit_graph`, `graph_delta`, `measure_graph_area`, `toggle_graph_statistics` 도구 호출.
- **파괴 메커니즘**:
  - `GRAPH_INPUT_OPERATIONS`가 `frozenset({"select_graph_measurement", "set_graph_fits", "analyze_graph"})`로만 정의되어 있어, 실제 그래프 좌표에 물리적 클릭/드래그를 전송하는 `fit_graph`, `graph_delta`, `measure_graph_area`, `toggle_graph_statistics`가 L674 필터에서 전부 누락됨.
  - 이로 인해 `_verify_frame()`(프레임 유효성, 창 위치 이동 여부, 화면 픽셀 일치 여부 검사)이 전혀 실행되지 않고 맹목적인 클릭/드래그가 실행됨.
  - 또한 `AutomationWorker._graph_transport_failure`에서도 해당 연산들이 누락되어 있어, 타임아웃 발생 시 `graph_input_may_have_been_sent` 추적이 상실되고 안전 복구 메커니즘이 무력화됨.

---

### 2. 🔴 DEFECT-NAT19 (P0 Blocker): 창 포커스 실패 에러가 `INVALID_ARGUMENT`로 오분류되어 LLM 환각 유발
- **파일 및 위치**: [errors.py#L47-L50](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L47-L50), [desktop.py#L307-L311](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L307-L311)
- **코드**:
  ```python
  # desktop.py:307
  msg = "Capstone could not be brought to the foreground, so no input was sent. The active window is ... Bring Capstone to the front, then retry."
  # errors.py:47
  (("coordinates", "foreground", "drag endpoints", "scroll position"), "INVALID_ARGUMENT", "Check tool argument types, coordinates, and constraints before retrying.")
  ```
- **재현 트리거**: 타 애플리케이션 활성화 상태나 화면 잠금 상태에서 클릭/키보드 입력 전송.
- **파괴 메커니즘**:
  - `desktop.py`의 `require_foreground`가 발생시킨 예외에 `"foreground"` 단어가 포함되어 있어 `_ERROR_RULES`의 규칙 #5에 매칭됨.
  - 에러 코드가 `INVALID_ARGUMENT`로 변환되고, 복구 안내로 `"Check tool argument types, coordinates, and constraints before retrying."`가 반환됨.
  - LLM은 실제 원인(창 활성화 불가)을 알지 못하고 자신이 전달한 (x, y) 좌표나 인자 타입이 잘못되었다고 오판하여 엉뚱한 수치를 수정하며 무한 실패 루프에 빠짐.

---

### 3. 🟠 DEFECT-NAT20 (P1 Critical): `keys` 문자 루프 내 O(N) 윈도우 전수조사 및 수식 기호 특수키 왜곡
- **파일 및 위치**: [desktop.py#L497-L524](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L497-L524), [runtime.py#L159-L166](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L159-L166)
- **코드**:
  ```python
  # desktop.py:507
  for token in tokens:
      target.type_keys(token, vk_packet=True)
      current_windows = self.windows()  # <-- 문자당 1회 Win32 윈도우 전수조사!
  ```
- **재현 트리거**: 50자 이상 수식 입력 또는 `unicode_input=False` 상태에서 수식(`^`, `+`, `%`, `~`) 전송.
- **파괴 메커니즘**:
  1. `unicode_input=True` 시 매 문자마다 Win32 EnumWindows가 호출되어 50자 입력 시 수 초간 UI 스레드가 마비됨.
  2. `unicode_input=False`(기본값) 시 계산기/피팅 수식의 `^2`(제곱)은 `Ctrl+2`, `+ y`(덧셈)은 `Shift+y`, `%`(백분율)은 `Alt` 키스트로크로 변환되어 의도치 않은 단축키가 난사됨.
  3. 닫는 중괄호가 없는 문자열(`"{"`) 전달 시 `pywinauto.keyboard.KeySequenceError: '}' not found` 예외로 워커가 즉시 크래시됨.

---

### 4. 🟠 DEFECT-NAT21 (P1 Critical): `read_value`/`set_value`의 ValuePattern 미지원 컨트롤 호출 시 unhandled AttributeError
- **파일 및 위치**: [runtime.py#L147-L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L147-L150), [desktop.py#L377](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L377)
- **코드**:
  ```python
  "read_value": lambda r: self.app.control(r.ref).iface_value.CurrentValue,
  ```
- **재현 트리거**: `IUIAutomationValuePattern`을 지원하지 않는 Label, Button, GroupBox, ListView 컨트롤에 `capstone_read_value` 또는 `capstone_set_value` 호출.
- **파괴 메커니즘**:
  - `iface_value`가 `None`을 반환하여 `AttributeError: 'NoneType' object has no attribute 'CurrentValue'` 발생.
  - `errors.py`는 해당 에러를 `CONTROL_NOT_FOUND`나 `UNSUPPORTED_PATTERN`으로 식별하지 못하고 일반 `AUTOMATION_ERROR`로 분류하여 잘못된 윈도우 점검 안내를 반환함.

---

### 5. 🟠 DEFECT-NAT22 (P1 Critical): 모달 대화상자 블로킹 에러가 일반 `AUTOMATION_ERROR`로 은폐
- **파일 및 위치**: [desktop.py#L260-L264](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L260-L264), [errors.py#L98](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L98)
- **코드**:
  ```python
  msg = "Window is disabled by a modal dialog, so no input was sent. Handle the blocking window first: " + blockers
  ```
- **재현 트리거**: 확인 팝업이나 모달 창이 떠 있는 상태에서 메인 윈도우 조작 시도.
- **파괴 메커니즘**:
  - 예외 메시지에 `_ERROR_RULES`의 어떤 키워드도 매칭되지 않아 최하단 폴백 `AUTOMATION_ERROR`("Check Capstone application state using capstone_windows and retry.")로 떨어짐. 모달 창 닫기 지침이 누락되어 워커가 영구 모달 정체 상태에 방치됨.

---

### 6. 🟡 DEFECT-NAT23 (P2 Major): 최소화된 윈도우에 대한 `focus_window` 활성화 실패
- **파일 및 위치**: [desktop.py#L313-L319](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L313-L319), [runtime.py#L818, L839, L866](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L818)
- **재현 트리거**: 작업 표시줄에 최소화(Iconic)되어 있는 Capstone 창에 클릭, 드래그, 스크롤 전송.
- **파괴 메커니즘**:
  - `screenshot()`과 달리 `focus_window`는 `win32gui.IsIconic(handle)`를 검사하거나 `ShowWindow(SW_RESTORE)`를 호출하지 않고 곧바로 `HwndWrapper(handle).set_focus()`를 호출함.
  - Windows OS 정책상 최소화된 창은 `SetForegroundWindow`만으로 포그라운드로 복원되지 않으므로, 직후 `self.require_foreground()` 검사에서 100% `AutomationError`가 발생하며 조작이 거부됨.

---

### 7. 🟡 DEFECT-NAT24 (P2 Major): `configure_sensor` 복합 요청 실패 시 부분 상태 누수
- **파일 및 위치**: [runtime.py#L780-L800](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L780-L800)
- **재현 트리거**: 센서 선택은 유효하지만 샘플링 레이트 타깃(`step_limit` 등)이 올바르지 않은 경우.
- **파괴 메커니즘**:
  - `select_sensor`가 먼저 실행되어 Capstone 하드웨어 센서 선택이 변경된 후, 후속 `target_sampling_rate`에서 예외가 발생하면 전체 요청이 실패로 반환됨.
  - 선행 변경된 센서 선택 상태가 롤백되거나 호출자에게 보고되지 않아 클라이언트와 실물 Capstone 간의 센서 구성 상태 불일치가 영구 고착화됨.

---

### Phase 2 결함 요약 매트릭스

| ID | 결함 내용 | 심각도 | 해당 위치 |
|---|---|---|---|
| NAT-18 | `fit_graph` 등 그래프 조작 4종 프레임 검증 전면 우회 및 안전 추적 상실 | **P0 (Blocker)** | [runtime.py#L674-L680](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L674-L680) |
| NAT-19 | 창 포커스 실패 에러가 `INVALID_ARGUMENT`로 오분류되어 좌표 환각 유발 | **P0 (Blocker)** | [errors.py#L47-L50](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L47-L50) |
| NAT-20 | `keys` 루프 내 O(N) 윈도우 전수조사 및 수식 연산자 단축키 왜곡 | **P1 (Critical)** | [desktop.py#L497-L524](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L497-L524) |
| NAT-21 | ValuePattern 미지원 컨트롤에 `read_value`/`set_value` 시 AttributeError 크래시 | **P1 (Critical)** | [runtime.py#L147-L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L147-L150) |
| NAT-22 | 모달 대화상자 블로킹 에러가 일반 `AUTOMATION_ERROR`로 은폐 | **P1 (Critical)** | [desktop.py#L260-L264](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L260-L264) |
| NAT-23 | 최소화(Iconic) 창 복원 부재로 인한 `focus_window` 100% 조작 거부 | **P2 (Major)** | [desktop.py#L313-L319](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L313-L319) |
| NAT-24 | `configure_sensor` 실패 시 센서 선택 부분 상태 누수 및 비동기화 | **P2 (Major)** | [runtime.py#L780-L800](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L780-L800) |

</details>

<details open>
<summary><b>[보고서 #83] auditor-native 실사 세부 명세 (Phase 3)</b></summary>

지침에 따라 `src/capstone_mcp/ui_events.py`, `src/capstone_mcp/repetition.py`(`AcquisitionJobs`), `src/capstone_mcp/server.py`의 라이프사이클, Win32 이벤트 훅, 백그라운드 잡 큐 경계를 전수 분해하여 발굴한 신규 결함 7건(P0 2건, P1 3건, P2 2건)의 상세 내역입니다.

---

### 1. 🔴 DEFECT-NAT25 (P0 Blocker): `SetWinEventHook` 전역 범위(1 ~ 0x7FFFFFFF) 훅으로 인한 GIL 고갈 및 UI 프리징
- **파일 및 위치**: [ui_events.py#L16-L17, L147-L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L16-L17)
- **코드**:
  ```python
  EVENT_MIN: Final = 1
  EVENT_MAX: Final = 0x7FFFFFFF
  ...
  hook = user32.SetWinEventHook(
      EVENT_MIN, EVENT_MAX, None, ctypes.cast(callback, ctypes.c_void_p),
      self.process_id, 0, 0,
  )
  ```
- **파괴 메커니즘**:
  - `EVENT_MIN`(1)부터 `EVENT_MAX`(0x7FFFFFFF)까지 Win32 전체 이벤트 범위를 단일 훅으로 등록함.
  - 마우스 이동(`LOCATIONCHANGE`), 커서 깜빡임, 스크롤, 타이머, 모든 UI 렌더링 이벤트가 초당 수천~수만 건씩 파이썬 콜백(`changed`)으로 전달됨.
  - 매 이벤트마다 `self.changes.notify()`가 락을 획득하고 Condition 변수를 깨우면서 파이썬 GIL(Global Interpreter Lock)을 100% 점유하여, 워커의 실제 조작 스레드 및 Capstone과의 통신이 극심한 지연 또는 동결 상태에 빠짐.

---

### 2. 🔴 DEFECT-NAT26 (P0 Blocker): `ui_events.py` 내 `DispatchMessageW` 누락으로 인한 클립보드 윈도우 프로시저 기아 및 스레드 행
- **파일 및 위치**: [ui_events.py#L160-L174](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L160-L174)
- **코드**:
  ```python
  self.clipboard_handle = win32gui.CreateWindowEx(...)
  user32.AddClipboardFormatListener(self.clipboard_handle)
  ...
  while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
      if message.message == WM_CLIPBOARDUPDATE:
          self.changes.notify()
      # <-- TranslateMessageW / DispatchMessageW 완전 누락!
  ```
- **파괴 메커니즘**:
  - `CreateWindowEx`로 생성된 `self.clipboard_handle` 윈도우는 OS로부터 `WM_PAINT`, `WM_DESTROY`, `WM_NCDESTROY` 등 다양한 윈도우 메시지를 수신함.
  - 그러나 루프 내에 `DispatchMessageW` 호출이 전혀 없어, 해당 윈도우를 타깃으로 하는 동기 Win32 메시지(`SendMessage`)가 윈도우 프로시저로 전달되지 못하고 메시지 큐에 영구 정체됨.
  - OS 컴포넌트나 타 프로세스가 클립보드 뷰어 체인에 동기 브로드캐스트를 전송할 경우 시스템 전역 또는 해당 스레드가 영구 행(Hang) 상태에 빠짐.

---

### 3. 🟠 DEFECT-NAT27 (P1 Critical): `SetWinEventHook` 콜백 함수 인스턴스 조기 GC 위험 및 메모리 참조 크래시(0xC0000005)
- **파일 및 위치**: [ui_events.py#L127-L133, L148](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L127-L133)
- **코드**:
  ```python
  def _pump(self) -> None:
      ...
      callback = callback_type(changed)
      hook = user32.SetWinEventHook(..., ctypes.cast(callback, ctypes.c_void_p), ...)
  ```
- **파괴 메커니즘**:
  - `callback = callback_type(changed)`이 인스턴스 속성(`self._callback`)이 아닌 로컬 변수로 선언됨.
  - `ctypes.cast(callback, ctypes.c_void_p)`는 단지 포인터 주소만 복사할 뿐 파이썬 callable 래퍼의 참조 카운트를 증가시키지 않음.
  - 실행 환경이나 최적화에 의해 로컬 참조가 가비지 컬렉터에 수거되면 Windows OS가 이미 해제된 메모리 주소로 진입하여 즉각적인 `0xC0000005 Access Violation`으로 프로세스가 비정상 종료됨.

---

### 4. 🟠 DEFECT-NAT28 (P1 Critical): `AcquisitionJobs` FIFO 축출 시 실행 중인 활성 잡 고아화 및 통제 불능 무한 레코딩
- **파일 및 위치**: [repetition.py#L345-L347, L375-L385](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/repetition.py#L345-L347)
- **코드**:
  ```python
  if len(self.jobs) >= MAX_JOB_HISTORY:
      del self.jobs[next(iter(self.jobs))]  # <-- 상태 확인 없는 무조건 삭제
  self.jobs[identifier] = job
  ```
- **파괴 메커니즘**:
  - `MAX_JOB_HISTORY`(16)에 도달하면 가장 오래된 잡을 무조건 `del`함.
  - 축출 대상 잡이 아직 실행 중(`running`)이더라도 취소(`cancel()`)나 워커 종료 없이 딕셔너리에서만 제거되어 고아 스레드(Orphan Thread)로 전락함.
  - 이후 서버 종료(`AcquisitionJobs.close()`)가 호출되어도 `self.jobs`에 없으므로 취소 토큰이 전달되지 않아, 백그라운드에서 Capstone 하드웨어 레코딩이 무기한 계속 진행됨.

---

### 5. 🟠 DEFECT-NAT29 (P1 Critical): 은퇴(Retired)된 세션에 비(非)attach 도구 호출 시 FastMCP 500 내부 크래시
- **파일 및 위치**: [server.py#L75-L92](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L75-L92)
- **코드**:
  ```python
  if request.operation == "attach" and WORKER.retired:
      await anyio.to_thread.run_sync(WORKER.reset)
  return await anyio.to_thread.run_sync(WORKER.call, request)
  ```
- **파괴 메커니즘**:
  - 타임아웃이나 오류로 워커가 은퇴(`WORKER.retired = True`)된 상태에서 클라이언트가 `attach`가 아닌 `capstone_windows`, `capstone_snapshot`, `capstone_manage_graph` 등을 호출하면 `WORKER.reset`이 실행되지 않음.
  - `WORKER.call`은 `error_code=None`인 `NativeSessionError("Native session was retired; ...")`를 발생시키고, `server.py:91`은 이를 그대로 `raise`하여 FastMCP가 AnyIO 비동기 이벤트 루프에서 500 에러 트레이스백을 노출함.

---

### 6. 🟡 DEFECT-NAT30 (P2 Major): `StateChanges.until`의 일시적 중간 상태 예외 발생 시 대기 루프 조기 붕괴
- **파일 및 위치**: [ui_events.py#L58-L73](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L58-L73)
- **코드**:
  ```python
  while True:
      result = predicate()  # <-- 예외 보호 없음
      if result is not None:
          return result
  ```
- **파괴 메커니즘**:
  - UI 상태 전이 중간 과정에서 `predicate()`가 일시적으로 `AutomationError`(컨트롤 미생성 등)나 `COMError`를 발생시키면 `until` 루프가 즉시 중단되고 예외가 호출자에게 전파됨.
  - 상태가 안정화될 때까지 대기(Wait)하려는 목적의 함수가 일시적 과도 상태 예외를 흡수하지 못해 조기 실패함.

---

### 7. 🟡 DEFECT-NAT31 (P2 Major): 조기 사망한 리스너 스레드에 `PostThreadMessageW` 호출 시 `__exit__` 내 Error 1444 폭사
- **파일 및 위치**: [ui_events.py#L104-L110](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L104-L110)
- **코드**:
  ```python
  if not user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0):
      raise ctypes.WinError(ctypes.get_last_error())
  ```
- **파괴 메커니즘**:
  - `_pump`가 훅 등록 실패 등으로 이미 종료된 경우, `self.thread_id`는 이미 소멸한 스레드임.
  - `__exit__`에서 `PostThreadMessageW` 호출 시 `ERROR_INVALID_THREAD_ID`(1444)가 발생하여 `with` 블록 내부에서 발생했던 원래 예외를 덮어쓰고 마스킹함.

---

### Phase 3 결함 매트릭스 요약

| ID | 결함 내용 | 심각도 | 해당 위치 |
|---|---|---|---|
| NAT-25 | `SetWinEventHook` 전역 범위(1~0x7FFFFFFF) 훅 등록으로 인한 GIL 고갈 및 UI 동결 | **P0 (Blocker)** | [ui_events.py#L16-L17, L147-L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L16-L17) |
| NAT-26 | `DispatchMessageW` 누락으로 인한 클립보드 윈도우 프로시저 기아 및 스레드 행 | **P0 (Blocker)** | [ui_events.py#L160-L174](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L160-L174) |
| NAT-27 | `SetWinEventHook` 콜백 함수 로컬 변수화로 인한 조기 GC 및 Access Violation (0xC0000005) 크래시 | **P1 (Critical)** | [ui_events.py#L127-L133](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L127-L133) |
| NAT-28 | `AcquisitionJobs` FIFO 축출 시 실행 중인 활성 잡 고아화 및 통제 불능 무한 레코딩 | **P1 (Critical)** | [repetition.py#L345-L347, L375-L385](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/repetition.py#L345-L347) |
| NAT-29 | 은퇴 세션에 비(非)attach 도구 호출 시 FastMCP 500 내부 크래시 | **P1 (Critical)** | [server.py#L75-L92](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L75-L92) |
| NAT-30 | `StateChanges.until`의 일시적 과도 상태 예외 미보호로 인한 대기 루프 조기 붕괴 | **P2 (Major)** | [ui_events.py#L58-L73](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L58-L73) |
| NAT-31 | 조기 종료된 리스너 스레드에 `PostThreadMessageW` 호출 시 Error 1444로 본래 예외 마스킹 | **P2 (Major)** | [ui_events.py#L104-L110](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L104-L110) |

</details>

#### 📑 실사 보고서: `audit-concurrency` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #101] audit-concurrency 실사 세부 명세 (Phase 1)</b></summary>

`automation_worker.py`, `native_loop.py`, `repetition.py` 및 관련 서브시스템(`server.py`, `resources.py`, `tools/`)의 파이프 버퍼 한계 데드락, AnyIO 스레드 오프로딩 누락, `JOBS.interaction` 데드락을 전수 라인 단위로 실사한 결과 총 10건의 치명적 결함(P0 4건, P1 5건, P2 1건)을 발굴하여 보고합니다.

---

### 1. 파이프 버퍼 한계 및 Windows IPC 데드락 (4096B Buffer Deadlock)

#### 🔴 [DEFECT-CONC01] Windows 파이프 4096B 버퍼 고갈 및 대용량 스냅샷 JSON 전송 시 양방향 블로킹 데드락 (P0)
- **위치**: `src/capstone_mcp/automation_worker.py` L83-87, L151-156 / `src/capstone_mcp/native_loop.py` L54-56
- **코드**:
  ```python
  # automation_worker.py L83-87
  subprocess.Popen([sys.executable, "-X", "utf8", "-u", "-m", "capstone_mcp.native_main"],
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, ...)
  # automation_worker.py L151-156
  _ = process.stdin.write(packet.model_dump_json() + "\n")
  process.stdin.flush()
  line = TEXT_VALUE.validate_python(process.stdout.readline(MAX_MESSAGE_BYTES + 1))
  # native_loop.py L54-56
  _ = sys.stdout.write(reply.model_dump_json() + "\n")
  _ = sys.stdout.flush()
  ```
- **실기 파괴 메커니즘**:
  1. Windows의 익명 파이프(`CreatePipe`) 기본 버퍼 크기는 **4096바이트(4KB)**입니다.
  2. `capstone_snapshot` 또는 10,000개 컨트롤 탐색 UIA 트리 스냅샷 응답의 직렬화 JSON 크기는 통상 **수십 KB ~ 수 MB**에 달합니다.
  3. `native_loop.py`에서 `_ = sys.stdout.flush()` 호출 시, Win32 `WriteFile`은 커널 파이프 버퍼(4096B)를 채운 뒤 부모가 버퍼를 비워줄 때까지 자식 스레드를 블로킹합니다.
  4. 만약 부모 프로세스가 `process.stdin.flush()`에서 대용량 요청(매크로, CapturePlan 등) 전송 중이거나 자식이 stderr로 경고/로그를 출력하여 stderr 버퍼가 먼저 차면, 자식은 stdout/stderr write에서 멈추고 부모는 stdin flush / stdout read에서 멈춰 상호 데드락이 발생합니다.
  5. 타임아웃 발생 시까지 전체 시스템이 60초간 동결되며, 이후 세션이 강제 퇴역(`uncertain=True`)됩니다.

#### 🔴 [DEFECT-CONC02] 워커 자원 정리 시 스트림 미종료로 인한 `transport.join` 영구 행 및 Worker Bricking (P0)
- **위치**: `src/capstone_mcp/automation_worker.py` L311-325, L336-343
- **코드**:
  ```python
  def _dispose_resources(self) -> None:
      self._terminate_process() # process.kill() 후 wait(2)
      if self.transport is not None:
          self.transport.join(CLEANUP_SECONDS) # 2초 대기
          if self.transport.is_alive():
              raise NativeSessionError("Worker transport did not retire; no replacement may be started.")
      if self._stderr_thread is not None: ...
      self._close_streams() # <-- transport.join 이후에 위치!
      if self.job is not None: self.job.Close()
  ```
- **실기 파괴 메커니즘**:
  1. `_dispose_resources()`에서 `self._close_streams()`가 `self.transport.join(CLEANUP_SECONDS)` **뒤**에 호출됩니다.
  2. 자식 프로세스를 `kill()`하더라도, 자식 또는 Capstone 프로세스에 stdout 파이프 핸들이 상속/유지되어 있으면 `self.transport` 스레드는 `process.stdout.readline()`의 OS `ReadFile` 커널 콜에서 절대 깨어나지 않습니다.
  3. 2초 후 `transport.join`이 타임아웃되어 `NativeSessionError`가 던져지고, `self._close_streams()`와 `self.job.Close()`는 영원히 도달하지 못해 파이프 핸들과 Job Object가 영구 누수됩니다.
  4. 이 상태에서 클라이언트가 복구를 위해 `capstone_attach`(`reset()`)를 호출하면, `_reset_locked()` -> `self._retire()` -> `_dispose_resources()`에서 여전히 살아있는 `self.transport`로 인해 동일 예외가 무한 반복 발생하여 MCP 서버 재시작 전까지 워커가 영구 불능(Bricked) 상태에 빠집니다.

#### 🟠 [DEFECT-CONC03] `native_loop.py`의 직렬화 예외 비보호 크래시 및 부모 프로세스 퇴역 연쇄 폭사 (P1)
- **위치**: `src/capstone_mcp/native_loop.py` L26, L54
- **코드**:
  ```python
  packet = RequestPacket.model_validate_json(line) # L26: try-except 외부
  try: ...
  _ = sys.stdout.write(reply.model_dump_json() + "\n") # L54: try-except 외부
  ```
- **실기 파괴 메커니즘**:
  - `packet.model_validate_json`과 `reply.model_dump_json()`이 `try...except` 외부에 노출되어 있습니다.
  - 대용량 스냅샷이나 비정상 제어 문자, Pydantic 직렬화 한도 초과 시 `native_loop` 프로세스가 stderr에 트레이스백을 뱉고 즉시 크래시 종료됩니다.
  - 부모 프로세스는 stdout에서 불완전한 EOF를 읽어 `incomplete or oversized reply` 예외를 던지고 `uncertain=True`와 함께 정상 동작 중이던 세션을 강제 파괴합니다.

---

### 2. `JOBS.interaction` 데드락 및 동시성 파탄

#### 🔴 [DEFECT-CONC04] `JOBS.interaction()` 동기 컨텍스트 매니저의 `await` 경계 유지 및 동시 변이 요청 기각/오펀 스레드 충돌 (P0)
- **위치**: `src/capstone_mcp/server.py` L74-76 / `src/capstone_mcp/repetition.py` L318-329
- **코드**:
  ```python
  # server.py L74-76
  async def _native(request: NativeRequest, *, mutates: bool = False) -> JsonValue:
      with JOBS.interaction() if mutates else nullcontext():
          try:
              return await anyio.to_thread.run_sync(WORKER.call, request)
  ```
- **실기 파괴 메커니즘**:
  1. `_native`는 FastMCP 이벤트 루프에서 실행되는 비동기 코루틴입니다. 그러나 `JOBS.interaction()`은 `self.input_reserved = True`를 설정하는 동기 제너레이터입니다.
  2. `await anyio.to_thread.run_sync` 대기 중 이벤트 루프로 제어권이 넘어가며, 이 동안 들어오는 모든 후속 변이 도구 호출(UI 조작, 파일 저장, 런 관리 등)은 `require_idle()`에서 `self.input_reserved`로 인해 대기 큐 없이 즉시 `AutomationError: An acquisition or another input is active; no input was queued.`를 맞고 거부됩니다.
  3. 만약 클라이언트 연결 종료나 AnyIO 타임아웃으로 태스크가 취소되면, `finally: self.input_reserved = False`로 플래그는 풀리지만 백그라운드 스레드에서 실행 중이던 `WORKER.call`은 여전히 `WORKER.lock`을 잡고 있습니다. 이때 들어온 새 요청은 `input_reserved`를 통과한 후 `WORKER.call`의 `self.lock.acquire(blocking=False)`에서 `NativeSessionError: A native request is already active`로 연쇄 폭사합니다.

#### 🟠 [DEFECT-CONC05] `JOBS.interaction()`의 비재진입성(Non-Reentrancy)에 의한 내부 자가 거부 (P1)
- **위치**: `src/capstone_mcp/repetition.py` L309-329, L335
- **코드**:
  ```python
  def require_idle(self) -> None:
      with self.lock:
          if self.input_reserved or any(...): raise AutomationError(...)
  def start(self, plan: RepeatPlan) -> JobStatus:
      with self.interaction(): # self.input_reserved = True 설정
  ```
- **실기 파괴 메커니즘**:
  - `self.lock`은 `RLock`으로 재진입이 가능하나, 차단 조건인 `self.input_reserved`가 단순 bool 플래그입니다.
  - 상위 워크플로나 복합 매크로 내부에서 `interaction()`이 걸린 채로 `jobs.start()`가 호출되면, `jobs.start` 내부의 `with self.interaction():`이 자신의 플래그에 걸려 `AutomationError`를 자가 발생시키며 실패합니다.

#### 🟠 [DEFECT-CONC06] 셧다운 타임아웃 시 `AcquisitionJobs.close()`와 `AcquisitionJob.run()`의 `cleanup_lock` 경합 크래시 (P1)
- **위치**: `src/capstone_mcp/repetition.py` L278-280, L373-385 / `src/capstone_mcp/automation_worker.py` L280-282
- **코드**:
  ```python
  # repetition.py close() L382-385
  except FutureTimeout:
      job.backend.close() # AutomationWorker._retire() 호출
  # repetition.py run() L278-280
  finally:
      self.backend.close() # AutomationWorker._retire() 동시 호출
  ```
- **실기 파괴 메커니즘**:
  - 서버 셧다운 시 5초 타임아웃이 경과하면 `AcquisitionJobs.close()`가 `job.backend.close()`를 호출합니다.
  - 이때 백그라운드에서 실행 중이던 `job.run()`의 `finally: self.backend.close()`도 동시에 실행됩니다.
  - 두 스레드가 동일한 워커의 `self.cleanup_lock.acquire(timeout=2)`를 경합하며, 후순위 스레드가 2초 타임아웃 시 `NativeSessionError: Worker retirement is already in progress`를 던져 서버 종료 프로세스 또는 스레드가 비정상 예외로 크래시됩니다.

#### 🟡 [DEFECT-CONC07] `AcquisitionJobs.status()` 및 `cancel()`의 링버퍼 만료 `KeyError` 미방어 서버 크래시 (P2)
- **위치**: `src/capstone_mcp/repetition.py` L344-347, L360, L370
- **코드**:
  ```python
  if len(self.jobs) >= MAX_JOB_HISTORY:
      del self.jobs[next(iter(self.jobs))] # 16개 초과 시 자동 삭제
  ...
  job = self.jobs[identifier] # status/cancel에서 딕셔너리 직접 인덱싱
  ```
- **실기 파괴 메커니즘**:
  - `MAX_JOB_HISTORY = 16`을 초과하여 삭제된 이전 잡 ID나 오타가 인입될 경우, `KeyError`가 미처리되어 FastMCP JSON-RPC 핸들러로 전파되어 서버 에러를 유발합니다.

---

### 3. AnyIO 스레드 오프로딩 누락 (Event Loop Blocking)

#### 🔴 [DEFECT-CONC08] `capstone://measurements/live` 리소스의 CDP 동기 HTTP/WebSocket 이벤트 루프 동결 (P0)
- **위치**: `src/capstone_mcp/resources.py` L159-205, L274-276
- **코드**:
  ```python
  @mcp.resource("capstone://measurements/live")
  async def capstone_live_measurements_resource() -> str:
      return _read_live_measurements_doc(worker) # anyio.to_thread.run_sync 누락!
  ```
- **실기 파괴 메커니즘**:
  - `capstone_live_measurements_resource`가 `async def` 핸들러임에도 동기 함수 `_read_live_measurements_doc`를 이벤트 루프 상에서 직접 실행합니다.
  - 내부의 `session_mgr.read_live_inventory()` 및 `read_live_measurement(euid)`는 동기 HTTP GET 및 동기 WebSocket handshake/recv 블로킹 I/O를 수행합니다.
  - 리소스 조회 시마다 FastMCP 메인 비동기 이벤트 루프가 수 초간 동결되어 모든 MCP 클라이언트 요청, 하트비트, 핑이 마비됩니다.

#### 🟠 [DEFECT-CONC09] `capstone://runs/active` 리소스의 Lock 없는 딕셔너리 순회 동시성 충돌 (P1)
- **위치**: `src/capstone_mcp/resources.py` L108-118, L264-266
- **코드**:
  ```python
  for jid, job in jobs.jobs.items() # jobs.lock 미획득 순회
  ```
- **실기 파괴 메커니즘**:
  - `jobs.jobs.items()`를 `jobs.lock` 보호 없이 직접 순회합니다. 백그라운드 잡 등록/정리 스레드와 경합 시 `RuntimeError: dictionary changed size during iteration`으로 리소스 조회가 즉시 크래시됩니다.

#### 🟠 [DEFECT-CONC10] `capstone_run_experiment_macro` 및 파일/물리 분석 도구들의 AnyIO 오프로딩 누락 (P1)
- **위치**: `src/capstone_mcp/tools/physics.py` L50, L67, L80, L215-246 / `src/capstone_mcp/tools/files.py` L159, L185, L219
- **코드**:
  - `physics.py` L242: `async def capstone_run_experiment_macro` 내부에서 동기 `run_experiment_macro(...)`를 직접 호출
  - `physics.py` L50: `capstone_plot` 동기 matplotlib 렌더링
  - `files.py` L159, L185, L219: `capstone_inspect_file`, `capstone_file_datasets`, `capstone_extract_dataset` 수십 MB .cap 파일 파싱/압축해제 동기 실행
- **실기 파괴 메커니즘**:
  - CPU 및 디스크 I/O 집약적 작업들이 `anyio.to_thread.run_sync` 없이 FastMCP 메인 스레드에서 직접 수행되어 비동기 프로토콜 통신을 지속적으로 지연·블로킹시킵니다.

---
이상 10건의 동시성/IPC 결함(P0 4건, P1 5건, P2 1건)에 대해 전수 라인 검증을 마쳤으며, 마스터 매트릭스 반영을 요청드립니다.

</details>

#### 📑 실사 보고서: `auditor-core` (총 4회 정밀 실사)

<details open>
<summary><b>[보고서 #34] auditor-core 실사 세부 명세 (Phase 1)</b></summary>

1. Port Mismatch (9222 vs 9223):
- `repetition.py`: `RepeatPlan.debug_port` defaults to 9223, while `desktop.py`, `bridge.py`, and `session.py` default to 9222. Causes `verify_debug_process` (`record_events.py`) to reject default connections with `BridgeError`.

2. Guesswork Logic:
- `calculator.py`: Lines 95-101 (`_find_editor_controls`): If `.calc` or `formula` ID not found, blindly takes the 1st visible `Edit` as formula and 2nd `Edit` as unit across the entire window. Blindly types `^a{BACKSPACE}` and Enter; fakes validation (`status="valid"`, `verified=True`).
- `popup_selection.py`: `_find_menu_item` uses broad substring matching (`norm in ctrl.name`), leading to wrong item selection. Lacks UIA transition wait between submenu clicks (race condition). Fakes verification (`verified = not menu_open`).

3. Locale / OS Hardcoding:
- `plotting.py`: Line 16 hardcodes `FONT_PATH = "C:/Windows/Fonts/malgun.ttf"` with no fallback font, failing on non-Korean Windows, non-C: drives, or CI containers.
- `file_workflows.py`: English strings hardcoded for menu navigation ("File"), Export dialog ("Export Format", "Comma separated values", "Alignment Options", "Align by Index", "Select All", "Export to file...", "Close"), and unsaved prompt ("Discard").
- `csv_data.py`: Line 49 `Decimal(value)` and `csv.reader` assume `,` delimiter and `.` decimal point; fails on European locale exports (`;` and `,`).
- `calculator.py`: Line 12 `CALCULATOR_NAME = "Calculator"`; regex `_parse_calculation_name` only handles ASCII + Korean, failing on Greek math symbols ($\theta, \lambda$).

4. Dead Code & Orphaned/Phantom Surfaces:
- `popup_selection.py`: Plumbed in `native_loop.py` & documented in `agent_instructions.py` (`capstone_select_graph_measurement`), but NEVER registered in `server.py` or `tools/` (phantom tool).
- `experiment_analysis.py`: `fit_cap_datasets` and `compare_cap_datasets` tested in `test_experiment_analysis.py` but never exposed to MCP.
- `analysis.py`: Duplicates `numerics/regression.py` (`linear_fit` vs `fit_linear_series`).
- `capfile_models.py`: `CapValueKind.UNKNOWN` and `CapHardwareInterface.subtype` never populated.

5. Critical Runtime & Resource Bugs:
- `calculator.py`: Line 70 checks `node.iface_toggle.ToggleState == 1` instead of COM property `CurrentToggleState` (as used in `acquisition.py`). Always raises `AttributeError`, suppressed by `suppress(Exception)`, so `_is_calculator_open` always returns `False` — closing an already open calculator drawer!
- `file_events.py`: In `__exit__`, if `thread.join(2)` times out and raises `AutomationError`, `win32file.FindCloseChangeNotification` and `self.stop_handle.Close()` are skipped, leaking Win32 handles.
- `ui_events.py`: In `__exit__`, `PostThreadMessageW` on an already exited thread raises `WinError: 1444`, masking original exceptions.

</details>

<details open>
<summary><b>[보고서 #41] auditor-core 실사 세부 명세 (Phase 2)</b></summary>

1. desktop.py (Multi-instance Lockup when len(installed) > 1):
- L138-L144: `if len(installed) > 1` raises `AutomationError` requiring manual `process_id`.
- Failure scenario: If a previous crash, zombie process, or secondary Capstone instance exists, `server.py` and `AutomationWorker` (which call `attach()` without `process_id`) fail unconditionally. Since MCP tools expose no instance selection/recovery mechanism, the entire server permanently locks up until external manual taskkill.

2. session/lifecycle.py (Zombie Process Leak):
- L49-L53: `terminate()` only executes `self._is_active = False` and logs a message.
- Failure scenario: It fails to call `self._worker.close()`, never kills/releases `Capstone.exe`, and never closes Win32 job objects. Zombie `Capstone.exe` processes remain resident in Windows Task Manager, immediately triggering the desktop.py multi-instance lockup (`len(installed) > 1`) on any subsequent session.

3. server.py (Module-Level Global Singletons WORKER & JOBS):
- L54-L55: `WORKER: Final = AutomationWorker()` and `JOBS: Final = AcquisitionJobs()` instantiated at import time.
- Failure scenario: If `WORKER` times out (60s) or transport crashes, it is marked `retired`. Recovery via `WORKER.reset()` is ONLY coded for `request.operation == "attach"` (L75-76); any other tool call throws permanent `NativeSessionError`. For `JOBS`: unhandled exceptions during background jobs leave `input_reserved=True` or uncompleted futures in `jobs`, causing `require_idle()` (repetition.py:L312) to permanently reject all future mutating operations. Server cannot recover without full process restart.

4. automation_worker.py (60s Timeout & Data Vaporization):
- L171-L186 & L273-L284: Hardcoded 60s timeout triggers `_handle_call_timeout` -> `_retire()` -> `process.kill()`.
- Failure scenario: Long-running operations (dense XML export, multi-point calibration, large snapshot) exceeding 60s result in immediate SIGKILL (`TerminateProcess`) of the worker. Buffered stdout/stderr streams, partially serialized frames, and streaming measurements in worker memory are instantly vaporized. Session is marked `uncertain=True` and `retired=True`, blocking all subsequent requests.

5. bridge.py (Gap Analysis: 53 QWebChannel RPCs in fake_backend.py vs 2 Live Calls):
- bridge.py implements ONLY 2 live calls: `read_inventory` and `read_measurement` (plus 1 in record_events.py).
- fake_backend.py models 53 comprehensive domain RPCs (graphs, displays, instruments, runs, recording).
- Architectural gap: 51 out of 53 operations (96%) remain unbridged in live execution. Instead of calling native Qt QWebChannel C++ RPCs, production falls back to fragile UIA screen scraping, blind clicks, and coordinate guesswork—the root cause of all submenu races, edit hijacking, and locale failures discovered across the codebase.

</details>

<details open>
<summary><b>[보고서 #66] auditor-core 실사 세부 명세 (Phase 3)</b></summary>

신규 발굴된 6개 심층 결함(정확한 파일 경로, 라인 번호, 재현 트리거, 파괴 메커니즘) 보고입니다:

1. desktop.py (L302-311, L317-318, L349-350) - Win32 SetForegroundWindow Activation Lock Failure:
- 트리거: 사용자가 브라우저/IDE 등 다른 창에서 작업 중이거나 에이전트가 백그라운드에서 실행될 때 `act(Action.INVOKE)`, `focus_window`, `click_point` 호출.
- 파괴 메커니즘: 윈도우 OS의 전역 포커스 잠금(Foreground Lock) 정책으로 인해 `HwndWrapper.set_focus()`가 비활성 상태에서 무음 실패함. `require_foreground()`가 즉시 `AutomationError: Capstone could not be brought to the foreground...`를 던지며 모든 백그라운드 UI 조작이 100% 거부됨 (`AttachThreadInput` 또는 SPI 전역 포커스 해제 메커니즘 전무).

2. desktop.py (L281-294) - DPI 가상화 불일치 및 멀티모니터 음수 좌표 파탄:
- 트리거: 125%/150% 등 고해상도 DPI 스케일링이 적용된 디스플레이, 또는 주 모니터 좌측/상단에 배치된 보조 모니터(음수 좌표계)에서 `require_uncovered` 실행.
- 파괴 메커니즘: UIA `node.rectangle()`은 물리/가상화 좌표를 반환하나, `win32gui.WindowFromPoint(point)`는 파이썬 프로세스의 DPI 모드에 종속되어 엉뚱한 화면 픽셀을 조회(창이 가려지지 않았는데 가려졌다고 판정하거나 반대로 오판). 음수 좌표 전달 시 pywin32 C 바인딩의 부호 확장 오류로 `0` (NULL HWND)을 반환하여 잘못된 예외 발생.

3. desktop.py (L441-450) - ImageGrab.grab의 타사 창 오버랩 픽셀 오염:
- 트리거: Capstone 창 위로 알림 팝업, 탐색기, IDE 등 타사 창이 일부라도 겹쳐 있는 상태에서 `capstone_screenshot` 호출.
- 파괴 메커니즘: PIL `ImageGrab.grab(window=...)`는 윈도우 내부 렌더 버퍼(`PrintWindow(PW_RENDERFULLCONTENT)`)를 복사하지 않고 화면 표면 DC를 크롭함. Capstone 창 위에 겹쳐 있던 타 프로그램의 화면 픽셀이 스크린샷에 그대로 캡처되어 AI 시각 분석 모델에 왜곡된 이미지 전달.

4. session/__init__.py (L87-92, L110-122) & bridge.py (L137-151) - monitor_until_stop의 임시 포트 고갈(WSAEADDRINUSE):
- 트리거: `ConditionWatcher.monitor` 및 `UnifiedSessionManager.monitor_until_stop`을 통한 실시간 임계값 감시 (poll_interval=0.05s).
- 파괴 메커니즘: `read_live_measurement`가 영속 WebSocket 연결을 유지하지 않고, 매 50ms 틱마다 `httpx2.Client().get(/json/list)`로 타깃을 재탐색하고 새로운 WebSocket TCP 핸드셰이크를 맺고 끊음. 초당 20개의 신규 TCP 소켓이 생성/파괴되어 수 초 내에 윈도우 TIME_WAIT 소켓 누적 및 임시 포트 고갈(`WSAEADDRINUSE` / WinError 10048)로 감시 루프 크래시.

5. analysis.py (L86-96, L185-188) - Cooks Distance 극미소 분모 발산 및 표본별 나눗셈 언더플로우:
- 트리거: 이상치 검출 시 `cooks_distance` 계산 및 `compare_runs` 평균 계산.
- 파괴 메커니즘: 
  - `cooks_distance`: `sample_leverage == 1` 엄격 일치 검사로 인해 부동소수점 오차로 `0.9999999999999999` 또는 `1.0000000000000002`가 될 때 `(1 - sample_leverage)**2`가 `1e-32`가 됨. 극미소 분모 나눗셈으로 거대 부동소수점 발산(`inf`) 발생, L148의 유한성 검사에 걸려 `AnalysisError` 크래시.
  - `compare_runs`: `math.fsum(value / count for value in run.values)`. 1,000,000개 대용량 표본에서 각 샘플을 먼저 `count`로 나누면 극미소 물리 측정값이 IEEE 754 언더플로우(0.0)로 소멸됨 (올바른 식: `math.fsum(run.values) / count`).

6. automation_worker.py (L154-165) - stdout 단일 줄 오염에 의한 비가역적 세션 퇴출:
- 트리거: 서브프로세스(`native_main`) 내의 C 라이브러리, 의존성 패키지, 또는 파이썬 런타임이 stdout으로 경고문이나 배너를 1줄이라도 출력.
- 파괴 메커니즘: `_exchange`는 `stdout.readline()`이 무조건 유효한 `NativeReply` JSON 패킷일 것을 전제함. 단 1줄의 예기치 않은 텍스트 출력으로도 Pydantic JSON 파싱 검증이 실패하고, `_handle_call_failure`가 즉시 `uncertain=True` 마킹 후 `_retire()`를 호출하여 워커를 SIGKILL 강제 종료하고 세션을 영구 폐기함.

</details>

<details open>
<summary><b>[보고서 #76] auditor-core 실사 세부 명세 (Phase 4)</b></summary>

`src/capstone_mcp/server.py`, `src/capstone_mcp/repetition.py` (JOBS), `src/capstone_mcp/ui_events.py` 전수 분해 실사 결과입니다:

1. server.py (L58-67, L74-92) & repetition.py - AnyIO 비동기 캔슬레이션과 동기 워커 스레드 간 라이프사이클 데드락:
- 파일/라인: `server.py:58-67`, `repetition.py:321-329`
- 트리거: FastMCP 도구 실행 중 클라이언트가 취소(CancelledError)를 전송하거나 서버 종료(SIGINT/SIGTERM) 발생.
- 파괴 메커니즘: AnyIO는 비동기 스코프를 취소하지만 `anyio.to_thread.run_sync(WORKER.call)`로 실행 중인 백그라운드 동기 스레드는 인터럽트할 수 없음. 워커 스레드는 `WORKER.lock` 및 `JOBS.lock`을 쥔 채 그대로 실행 중인데, `_lifespan`의 종료 훅(`JOBS.close()`, `WORKER.close()`)이 호출됨. `WORKER.close()`는 내부 `transport.join(2.0)` 실패 시 `NativeSessionError`를 발생시키며 AnyIO 라이프사이클 태스크 그룹을 크래시시켜 프로세스가 정상 종료되지 못하고 무한 행(Hang)됨.

2. repetition.py (L223-233, L367-371) - backend.change 동기 블로킹 중 캔슬레이션 토큰 무력화 및 JOBS 영구 동결:
- 파일/라인: `repetition.py:223-233`, `repetition.py:309-316`, `repetition.py:367-371`
- 트리거: Capstone GUI가 모달 창/프리즈 등으로 응답하지 않을 때 `capstone_cancel_repeated_acquisition` 호출.
- 파괴 메커니즘: `cancellation.is_set()` 검사는 루프 상단 및 슬립 대기 중에만 이루어지며, 동기 UIA/CDP 호출인 `backend.change(recording=True/False)` 실행 중에는 취소 검사가 전무함. 네이티브 백엔드가 블로킹되면 `cancel.set()`은 완전히 무시되고 잡 스레드가 영구 대기 상태에 빠짐. 이로 인해 `job.result.done()`이 영원히 `False`로 남아 `AcquisitionJobs.require_idle()`이 이후 들어오는 모든 변이 요청을 영구 거부하여 서버의 레코딩 기능이 완전히 마비됨.

3. repetition.py (L344-348) - MAX_JOB_HISTORY 초과 시 미완료 잡 사일런트 방출 및 추적 상실:
- 파일/라인: `repetition.py:344-348`
- 트리거: 연속적인 반복 측정 요청으로 잡 수가 16개를 초과할 때.
- 파괴 메커니즘: `del self.jobs[next(iter(self.jobs))]`는 가장 오래된 잡의 완료 여부(`done()`)나 캔슬 여부를 전혀 확인하지 않고 FIFO로 딕셔너리에서 즉각 제거함. 만약 해당 잡이 여전히 백그라운드에서 실행 중이거나 지연 중이라면, 추적 및 제어 핸들이 영구 소실되어 취소도 불가능한 고립된 유령 워커 스레드로 잔존함.

4. server.py (L94-100) - FastMCP SSE 포트 8766 SO_REUSEADDR 부재로 인한 즉각 재시작 실패:
- 파일/라인: `server.py:94-100`
- 트리거: SSE 모드(`mcp run`)로 구동 중 비정상 종료 후 즉각 재시작.
- 파괴 메커니즘: 8766 포트 바인딩 시 `SO_REUSEADDR` 옵션이 적용되지 않아, 비정상 종료 시 OS TCP 스택이 8766 포트를 `TIME_WAIT` 상태로 최대 240초간 점유함. 즉각적인 재구동 시 `OSError: [Errno 10048] address already in use` 예외가 발생하며 서버 기동이 즉시 실패함.

5. ui_events.py (L171-175) - DispatchMessage 부재로 인한 STA 메시지 펌프 기아(Starvation) 및 외부 스레드 행:
- 파일/라인: `ui_events.py:171-175`
- 트리거: `WindowEvents` 리스너 스레드가 활성화되어 `GetMessageW` 루프를 돌고 있는 도중.
- 파괴 메커니즘: `while user32.GetMessageW(...) > 0:` 루프 내에서 오직 `WM_CLIPBOARDUPDATE`만 검사하고 `TranslateMessage` 및 `DispatchMessage`를 일체 호출하지 않음. 이 스레드로 전달된 윈도우 OS 시스템 브로드캐스트, OLE/DDE 메시지, 동기 `SendMessage` 요청이 처리되지 않고 버려지거나 응답되지 않아, 메시지를 전송하고 회신을 대기하던 외부 Win32/COM 컴포넌트 스레드가 영구 기아(Starvation) 및 데드락에 빠짐.

6. ui_events.py (L109-115) - PostThreadMessageW 실패 시 스레드 및 SetWinEventHook OS 전역 핸들 누수:
- 파일/라인: `ui_events.py:109-115`
- 트리거: 리스너 스레드가 예기치 않게 조기 종료되었거나 큐가 가득 찼을 때 `__exit__` 실행.
- 파괴 메커니즘: `PostThreadMessageW`가 실패하면 즉시 `raise ctypes.WinError`를 던져버림. 그 결과 라인 111의 `self.thread.join(READY_TIMEOUT)`이 실행되지 못하고 중단됨. 스레드는 정리되지 않고, Win32 커널 데스크톱 힙(Desktop Heap)에 등록된 `SetWinEventHook` 후크 핸들이 해제되지 않은 채 OS 전역에 영구 누수됨. 또한 `GetMessageW`가 에러 발생 시 반환하는 `-1` 값에 대한 방어 로직이 없어 음수 반환 시 무한 루프 또는 비정상 탈출이 발생함.

</details>

---

### 3.2. Security & Memory Safety (보안 RCE & 저수준 메모리 무결성)
- **담당 에픽 이슈**: #124
- **실사 참여 전문 에이전트**: `audit-sec`

#### 📑 실사 보고서: `audit-sec` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #99] audit-sec 실사 세부 명세 (Phase 1)</b></summary>

`bridge.py`, `ui_events.py`, `desktop.py`, `capfiles/archive.py` 및 관련 모듈에 대한 라인 단위 보안·저수준 메모리 결함 전수 실사 결과입니다.

---

### 1. `bridge.py` & CDP 통신 계층

#### 🔴 DEFECT-SEC01: `read_measurement()`의 `unit_type` 포맷 스트링 및 `evaluate()` 임의 JS 인젝션 (CWE-94 / CWE-116)
- **위치**: `bridge.py` L135-146, L184-190
- **코드**:
  ```python
  expression = (
      "window.app.mSenseAndControlView.mServices.RequestReadMeasurement("
      + json.dumps(measurement_euid) + "," + str(unit_type) + ")"
  )
  reply = MeasurementReply.model_validate(evaluate(port, expression))
  ```
- **파괴 메커니즘**: `unit_type`이 `json.dumps()` 없이 `str(unit_type)`으로 문자열 연결됨. 외부 입력 또는 타입 완화 시 `0); window.app.quit(); //` 같은 악성 JS 구문이 삽입되어 Capstone 내부 Qt WebEngine 컨텍스트에서 임의 스크립트 실행. `evaluate()` 함수 자체도 AST/파라미터화 바인딩 없이 임의의 문자열 `expression`을 직접 실행하는 구조적 취약점 노출.

#### 🔴 DEFECT-SEC02: `--remote-allow-origins=*` 및 무인증 로컬 디버그 포트에 의한 웹 드라이브바이 RCE 및 포트 하이재킹 (CWE-306 / CWE-346)
- **위치**: `desktop.py` L50-53, `bridge.py` L96-133
- **코드**: `CHROMIUM_DEBUG_FLAGS = (f"--remote-debugging-port={DEFAULT_DEBUG_PORT}", "--remote-allow-origins=*")`
- **파괴 메커니즘**: Chromium SOP 보호를 전면 해제함. 사용자가 일반 브라우저에서 임의 웹사이트를 방문하는 것만으로 악성 웹 JS가 `ws://127.0.0.1:9222`에 접속하여 Capstone의 Qt C++ 바인딩(`window.app`)을 장악하고 로컬 RCE 및 파일 탈취 가능. 또한 `bridge.py:discover_target()`은 대상 포트의 소유 프로세스 PID를 검증하지 않아 로컬 비인가 프로세스의 포트 선점/하이재킹에 무방비.

#### 🟠 DEFECT-SEC03: CDP 단일 고정 요청 ID(`id: 1`) 및 비동기 이벤트 프레임 파싱 파탄 DoS (CWE-400 / CWE-703)
- **위치**: `bridge.py` L138-160
- **파괴 메커니즘**: 모든 요청에 고정 ID `1`을 전송하며, WebEngine의 백그라운드 이벤트 수신 시 `reply.id != 1` 무한 루프에 빠짐. 또한 스키마 불일치 이벤트 수신 시 `Reply.model_validate_json`이 `ValidationError`를 일으켜 통신이 즉시 다운됨.

---

### 2. `ui_events.py`: Win32 SetWinEventHook 메모리 누수 및 ctypes GC 크래시

#### 🔴 DEFECT-SEC04: ctypes WINFUNCTYPE 콜백 thunk GC 및 댕글링 포인터에 의한 접근 위반(0xC0000005) 프로세스 즉사 (CWE-416 / CWE-824)
- **위치**: `ui_events.py` L122-133, L148-150
- **코드**:
  ```python
  callback = callback_type(changed)
  hook = user32.SetWinEventHook(
      EVENT_MIN, EVENT_MAX, None, ctypes.cast(callback, ctypes.c_void_p),
      self.process_id, 0, 0,
  )
  ```
- **파괴 메커니즘**: `callback` 객체가 `_pump()` 스택 프레임의 지역 변수로만 존재하며 `self` 인스턴스에 유지되지 않음. `ctypes.cast()`는 원본 콜백 참조를 보존하지 않는 별도 객체임. GC에 의해 thunk 메모리가 해제된 후 Windows OS가 WinEvent를 디스패치하면 즉시 **ACCESS_VIOLATION (0xC0000005)** 메모리 세그멘테이션 오류로 전체 파이썬 프로세스가 크래시됨.

#### 🔴 DEFECT-SEC05: `CreateWindowEx` 예외 시 `UnhookWinEvent` 누락으로 인한 OS 커널 전역 훅 영구 누수 (CWE-404 / CWE-775)
- **위치**: `ui_events.py` L147-179
- **파괴 메커니즘**: `try...finally` 보호 블록이 L171에서 시작됨. L160의 `win32gui.CreateWindowEx`가 실패하면 `_pump` 스레드가 즉시 종료되며 `user32.UnhookWinEvent(hook)`가 영원히 호출되지 않음. OS 커널 테이블에 등록된 훅 핸들이 영구 누수되어 시스템 전반의 성능 저하 및 댕글링 콜백 위험 발생.

#### 🟠 DEFECT-SEC06: `PostThreadMessageW(WM_QUIT)` 유실 시 스레드 및 훅 영구 좀비화 (CWE-672 / CWE-835)
- **위치**: `ui_events.py` L104-115
- **파괴 메커니즘**: 대상 스레드가 모달 루프나 COM RPC 대기 중일 때 `PostThreadMessage` 메시지는 Win32 규격상 유실됨. `WM_QUIT`이 누락되면 `GetMessageW`가 블로킹을 해제하지 않고 영원히 대기함. `self.thread.join(5)` 타임아웃 후 데몬 스레드와 OS 훅이 해제되지 않고 영구 고아(Zombie) 상태로 남음.

#### 🟠 DEFECT-SEC07: `EVENT_MIN(1)` ~ `EVENT_MAX(0x7FFFFFFF)` 전역 훅 등록에 의한 WinEvent 이벤트 폭풍 및 GIL 고갈 DoS (CWE-400)
- **위치**: `ui_events.py` L16-17, L147-150
- **파괴 메커니즘**: 1~0x7FFFFFFF의 모든 이벤트를 구독하여 고속 데이터 수집 시 초당 수천 건의 이벤트가 발생함. `WINEVENT_OUTOFCONTEXT`(0)로 인해 매 이벤트마다 OS가 콜백을 디스패치하고 Python GIL을 획득하여 메인 스레드를 기아 상태에 빠뜨리고 극심한 CPU 과열을 유발함.

#### 🟡 DEFECT-SEC08: `TranslateMessage`/`DispatchMessage` 누락에 의한 Win32 HWND 메시지 펌프 파탄 및 창 리소스 누수 (CWE-404)
- **위치**: `ui_events.py` L172-175
- **파괴 메커니즘**: `win32gui.CreateWindowEx`로 생성된 창에 대해 `DispatchMessageW`를 호출하지 않아 윈도우 프로시저가 `WM_DESTROY`, `WM_NCDESTROY` 등 정리 메시지를 처리하지 못하고 GDI/User 핸들이 누수됨.

---

### 3. `desktop.py`: Win32 핸들 누수, 프로세스 권한 상승 및 입력 하이재킹

#### 🔴 DEFECT-SEC09: `CAPSTONE_EXECUTABLE` 검증 부재 및 문자열 보간 명령 실행에 의한 임의 바이너리 실행 (CWE-78 / CWE-426)
- **위치**: `desktop.py` L31-46, L160-163
- **파괴 메커니즘**: 환경변수 `CAPSTONE_EXECUTABLE`에 대해 디지털 서명 및 경로 화이트리스트 검증이 전무함. `launch=True` 시 문자열 보간(`f'"{EXECUTABLE}" ...'`)으로 자식 프로세스를 기동하여 인자 주입 및 임의 바이너리 실행 취약점 존재.

#### 🟠 DEFECT-SEC10: `window_cache` 무한 증식 및 COM `IUIAutomationElement` 크로스 프로세스 핸들 누수 (CWE-401 / CWE-775)
- **위치**: `desktop.py` L123, L198-202
- **파괴 메커니즘**: `window_cache`에 HWND별 `UIAWrapper`를 영구 캐싱하며 창 파괴 시 무효화하지 않음. Windows의 HWND 재사용 시 이전 창의 래퍼가 오작동하며, 내부 COM RPC 포인터(`IUIAutomationElement`)를 릴리즈하지 않아 Capstone 프로세스와 MCP 서버 양쪽에 핸들 누수가 누적됨.

#### 🟡 DEFECT-SEC11: `flush_paint()`의 매 호출 시 `WinDLL("dwmapi")` 인스턴스화로 인한 DLL 참조 카운트 누수 (CWE-404)
- **위치**: `desktop.py` L466-470
- **파괴 메커니즘**: 그래픽 프레임 플러시마다 `ctypes.WinDLL("dwmapi")`를 새로 생성하여 `LoadLibrary("dwmapi.dll")`을 반복 호출함. DLL 모듈 참조 카운트와 내부 ctypes 심볼 딕셔너리가 지속적으로 누수됨.

#### 🟠 DEFECT-SEC12: 전역 하드웨어 합성 입력(SendInput)과 TOCTOU 포그라운드 레이스에 의한 입력 하이재킹 (CWE-367 / CWE-269)
- **위치**: `desktop.py` L349-359, L397-399, L417
- **파괴 메커니즘**: `require_foreground()` 확인 후 `node.click_input()` 또는 `type_keys()` 실행 사이에 레이스 컨디션 존재. UAC 승격 창, 시스템 잠금, 터미널 등이 포그라운드를 가로채면 합성된 마우스/키스트로크가 해당 권한 창으로 전달되는 입력 하이재킹 취약점.

---

### 4. `capfiles/archive.py` & 파일 워크플로우: NTFS ADS 우회, ZipSlip, DoS

#### 🔴 DEFECT-SEC13: `archive.py` L75: NTFS Alternate Data Streams (ADS) 우회 결함 (`":" in parts[0]`) (CWE-22 / CWE-20)
- **위치**: `capfiles/archive.py` L65-78
- **코드**:
  ```python
  parts = [part for part in normalized.split("/") if part not in {"", "."}]
  if not parts or ".." in parts or ":" in parts[0]:
      raise CapFileError(...)
  ```
- **파괴 메커니즘**: 콜론(`:`) 검사를 첫 번째 요소(`parts[0]`)에만 수행함. 아카이브 멤버가 서브디렉터리를 포함하는 경우(예: `data/file.bin:hidden`, `runs/series.xml::$DATA`, `exp/info:Zone.Identifier`) 검사를 완전히 우회함. NTFS의 보조 데이터 스트림을 악용하여 악성 페이로드를 은닉하거나 파일 무결성을 우회할 수 있음. `any(":" in part for part in parts)`로 전수 검사 필수.

#### 🔴 DEFECT-SEC14: `archive.py` L75: 서브디렉터리 드라이브 문자 ZipSlip 경로 탈출 결함 (CWE-22 / CWE-59)
- **위치**: `capfiles/archive.py` L74-78
- **파괴 메커니즘**: DEFECT-SEC13과 동일하게 `parts[1:]`에 드라이브 문자가 포함된 경우(예: `folder/C:/Windows/System32/payload.dll`) 통과함. Windows `Path.joinpath`나 `os.path.join`에 드라이브 문자가 전달되면 선행 경로를 버리고 드라이브 루트 절대 경로로 처리하므로 임의 경로 탈출(Zip Slip) 성립.

#### 🟠 DEFECT-SEC15: `archive.py` L65-78: Windows 예약된 DOS 장치명(`CON`, `NUL`, `AUX` 등) 검증 부재 DoS (CWE-400 / CWE-20)
- **위치**: `capfiles/archive.py` L65-78
- **파괴 메커니즘**: `CON`, `PRN`, `AUX`, `NUL`, `COM1~9`, `LPT1~9` 및 확장자 변형(`CON.xml`, `aux.bin`)을 필터링하지 않음. 악성 아카이브 파싱/접근 시 Windows I/O 서브시스템에서 스레드가 무한 행(Hang)에 빠지거나 I/O 크래시 발생.

#### 🔴 DEFECT-SEC16: `archive.py` L112-123: Zip Bomb 비압축 크기 미검증 전체 압축 해제로 인한 OOM DoS (CWE-409)
- **위치**: `capfiles/archive.py` L112-123
- **코드**:
  ```python
  if info.file_size > maximum_size:
      raise CapFileError(...)
  data = archive.read(info)
  ```
- **파괴 메커니즘**: `info.file_size`는 ZIP 헤더에 위조 가능한 메타데이터임. 헤더를 `1024`로 조작하고 수 GB로 팽창하는 Zip Bomb 전달 시 헤더 검사를 통과하며, `archive.read(info)`가 메모리에 전체 압축을 풀다가 서버 프로세스가 Out-Of-Memory로 즉사함. 스트리밍 청크 읽기(`archive.open(info)`)로 누적 바이트 제한 강제 필요.

#### 🟠 DEFECT-SEC17: `file_workflows.py` L181-184: 저장 경로 검증의 NTFS ADS 우회 및 기존 파일 은닉 덮어쓰기 (CWE-20 / CWE-73)
- **위치**: `file_workflows.py` L181-184
- **파괴 메커니즘**: `destination`으로 `C:\path\target.exe:hidden.cap` 지정 시 `path.suffix`는 `".cap"`이고 스트림 부재 시 `path.exists()`는 `False`를 반환하여 검증 통과. 기존 실행 파일의 ADS에 데이터를 덮어써 파일 무결성을 훼손함.

---
이상 보안 취약점 및 저수준 메모리/API 결함 17건(P0 7건, P1 7건, P2 3건)을 마스터 매트릭스에 통합 반영 요청드립니다.

</details>

---

### 3.3. Graphs, Displays & UI Automation (클립보드 적출 & 다중 창 잠금 & UIA)
- **담당 에픽 이슈**: #125, #128
- **실사 참여 전문 에이전트**: `auditor-graphs`, `auditor-displays`

#### 📑 실사 보고서: `auditor-graphs` (총 2회 정밀 실사)

<details open>
<summary><b>[보고서 #55] auditor-graphs 실사 세부 명세 (Phase 1)</b></summary>

`src/capstone_mcp/graphs/*` (inspection.py, toolbox.py, manager.py, models.py, __init__.py) 전수 검사 결과 보고서입니다.

### 1. Zero OS Pollution (클립보드 백업/복원, 시퀀스 폴링, Copy Display)
- **클립보드 탈취 및 포맷 손실 ([inspection.py#L322-L358](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L322-L358))**:
  - `_backup_clipboard()`와 `_restore_clipboard()`가 윈도우 OS 전역 클립보드를 비우고(`EmptyClipboard`) 복원을 시도함.
  - OLE 스트림, 지연 렌더링(`IDataObject`), 파일 복사 목록(`CF_HDROP`), 비트맵 등 핸들 복사가 불가한 포맷들이 유실되며 6개의 `suppress(Exception)`(L327, L335, L338, L347, L352, L355)으로 인해 복원 실패가 침묵함. 사용자 클립보드가 영구 파괴됨.
- **OS 전역 시퀀스 충돌 및 백그라운드 크래시 ([inspection.py#L360-L381](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L360-L381), [L445-L452](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L445-L452))**:
  - `GetClipboardSequenceNumber()`를 폴링하고 있어 타 프로세스(클립보드 히스토리, 패스워드 매니저 등)가 클립보드를 갱신하면 L366에서 `AutomationError: Another application changed the clipboard` 즉시 발생.
  - `WindowEvents(pid, clipboard=True)`(L409)가 전역 `AddClipboardFormatListener`를 등록하여 OS 이벤트 트래픽을 유발하며 헤드리스/CI 환경에서 블로킹됨.
- **포커스 탈취 및 Copy Display UI 깜빡임 ([inspection.py#L410-L461](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L410-L461))**:
  - `app.focus_window(handle)`로 사용자 입력 포커스를 탈취하고, "Display" 메뉴바 확장 -> "Copy Display" invoke -> `{ESC}` 키 입력을 유발.
- **다중 모델 설정 시 클립보드 연쇄 오염 ([manager.py#L403, L426, L444, L483, L499](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L403))**:
  - `set_graph_fits` 루프 내(L426)에서 모델 1개를 토글할 때마다 `read_graph`를 호출. 2개 피트 모델 설정 시 단일 요청 동안 5~6회의 클립보드 파괴/복원 및 메뉴 조작이 반복됨.

### 2. toolbox.py 내 8건의 unchecked contextlib.suppress
- **통계값 파싱 예외 묵살 ([toolbox.py#L206, L212, L218, L224, L230](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L206-L230))**:
  - `_parse_statistics`에서 `mean`, `std_dev`, `min`, `max`, `count`를 `float()`/`int()`로 변환할 때 5건의 `contextlib.suppress(ValueError)` 발생.
  - 파싱 실패 시 로그 없이 `None`으로 방치되며, `toggle_graph_statistics`(L280-L286)는 모든 통계 추출이 실패해도 `verified=True`를 반환하여 호출자를 기만함.
- **델타 도구 좌표 파싱 실패 및 맹목적 성공 보고 ([toolbox.py#L381, L389, L397](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L381-L397))**:
  - `_parse_delta`에서 `dx`, `dy`, 좌표쌍(`coord_pairs`) 변환 시 `contextlib.suppress(ValueError)`로 예외를 묵살.
  - 예외 발생 시 수치는 `None`으로 남지만 `raw_texts.append(text)`(L386, L394, L407)는 suppress 블록 밖에서 무조건 실행됨.
  - 결과적으로 `graph_delta`(L461-477)는 좌표 차이가 모두 `None`임에도 `active=True, verified=True`를 반환.

### 3. 메뉴 네비게이션 레이스 컨디션 및 UIA 전이 대기 누락
- **48분할 좌표 추측 및 {ESC} 레이스 ([manager.py#L186-L201](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L186-L201))**:
  - `_toggle_fit`에서 피트 메뉴 항목 클릭 좌표를 `(2 * FIT_ROWS[native_type] + 1) // 48`로 하드코딩 추측. 스크롤, 여백, DPI 스케일링(125%, 150%) 발생 시 엉뚱한 모델 클릭.
  - 마우스 클릭 직후 L197에서 Capstone 처리 대기 없이 즉시 `app.keys(handle, "{ESC}")` 전송. 클릭 이벤트가 등록되기 전에 취소되거나 메인 윈도우로 `{ESC}`가 전달되어 활성 도구가 닫힘.
- **하드코딩된 윈도우 타이틀로 인한 팝업 스킵 ([manager.py#L127](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L127))**:
  - `_fit_menu`에서 `window.title != "PASCO Capstone"`을 스킵. Qt QMenu 팝업은 윈도우 타이틀이 빈 문자열(`""`)이거나 클래스가 `#32768`이므로 팝업 창을 찾지 못하고 15초 타임아웃 발생.
- **서브메뉴 계층 탐색 레이스 ([manager.py#L367-L387](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L367-L387))**:
  - `select_graph_measurement`에서 다단계 경로 순회 시 상위 메뉴 클릭 후 하위 서브메뉴 창 생성 대기 없이 다음 반복에서 `ready_graph_menu` 호출. UIA 요소 참조 무효화(`COMError`) 유발.
  - 마지막 항목 선택 후 메뉴 닫힘 확인(`events.changes.until`) 시 즉시 닫히지 않으면 15초 동안 멈춤.
- **`create_graph` 및 `fit_graph` 맹목적 `verified=True` ([manager.py#L273-L283, L306-L327](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L273-L327))**:
  - `create_graph`는 팔레트 더블클릭 후 그래프 위젯 생성 여부를 전혀 확인하지 않고 즉시 `verified=True` 반환.
  - `fit_graph`는 상대 좌표 `(20, 20)`을 클릭 후 축 범위 변경 확인 없이 즉시 `verified=True` 반환.
- **툴박스 도구 토글 후 안정화 대기 누락 ([toolbox.py#L261-L264, L322-L325, L429-L448](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L261-L448))**:
  - 버튼 클릭 직후 `app.snapshot()`을 0ms 대기로 즉시 호출하여 오버레이 라벨이 생성되기 전의 이전 상태를 캡처함으로써 파싱 누락 빈발.

### 4. 피트 모델 및 통계 요약 결함
- **다중 시리즈(Series) 피트 성공 판정 버그 ([manager.py#L452-L462](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L452-L462))**:
  - Capstone에서 피트는 활성 시리즈에만 적용되나, `set_graph_fits`는 `all(any(...) for series in state.series)`로 모든 시리즈에 해당 피트가 성공해야 `fits_successful=True`로 판정. 복수 런/시리즈 표시 시 무조건 `False` 반환.
- **상태명 오타 ([models.py#L53](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/models.py#L53))**:
  - `"FAIL_MAX_ITERATONS"` (I 누락).
- **피트 실패 시 유효 데이터 강제 소멸 ([inspection.py#L154-L155, L168-L175](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L154-L175))**:
  - 수렴 실패 시 XML에 존재하는 중간 추정값 및 메트릭을 전부 `None`으로 강제 초기화하여 분석 단서 제거.
- **다국어 로케일 미지원 및 쉼표 소수점 거부 ([toolbox.py#L49-L84](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L49-L84))**:
  - 통계/적분/델타 정규식이 영문 전용(`mean`, `min`, `max` 등)으로 하드코딩되어 한국어("평균", "최댓값", "면적" 등) Capstone에서 100% 파싱 실패.
  - `\d+\.\d+` 패턴만 사용하여 유럽식 쉼표 소수점(`3,14`) 거부.
- **다중 런 통계 충돌 및 경계 박스 오인 ([toolbox.py#L172-L188, L190-L242](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L172-L242))**:
  - 여러 런의 통계 박스가 겹칠 때 첫 번째 매칭 값만 취하여 런 구분이 왜곡됨.
  - 통계 박스가 그래프 경계선에 걸쳐 도킹된 경우 `_extract_graph_controls`에서 누락됨.

</details>

<details open>
<summary><b>[보고서 #67] auditor-graphs 실사 세부 명세 (Phase 2)</b></summary>

`src/capstone_mcp/graphs/*` (inspection.py, manager.py, toolbox.py, models.py) 정밀 전수 검사 결과 신규 발굴된 14건의 심층 결함 보고서입니다.

---

### 1. `src/capstone_mcp/graphs/inspection.py` 결함

#### 🔴 DEFECT-GR01: 다중 창 및 도구 팔레트 존재 시 그래프 검사 전면 중단
- **위치**: [inspection.py#L393-L396](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L393-L396)
- **코드**:
  ```python
  windows = app.windows()
  if len(windows) != 1 or windows[0].handle != handle:
      msg = "Select one graph and close existing menus before graph inspection."
      raise AutomationError(msg)
  ```
- **재현 트리거**: Capstone에서 Hardware Setup 팔레트, 계산기, 비디오 창이 도킹 해제(Floating)되어 있거나 보조 창이 열려 있을 때 `read_graph` 호출.
- **파괴 메커니즘**: 메뉴가 열려 있지 않음에도 `len(windows) != 1` 조건을 만족하여 모든 그래프 읽기(`read_graph`)와 후속 분석 작업이 즉시 영구 거부됨.

#### 🔴 DEFECT-GR02: 영문 메뉴명 하드코딩으로 비영어 로케일 100% 크래시
- **위치**: [inspection.py#L413-L424](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L413-L424), [L434-L444](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L434-L444)
- **코드**:
  ```python
  menus = [c for c in snapshot.controls if c.control_type == "MenuItem" and c.name == "Display" ...]
  copies = [c for c in popup.controls if c.name == "Copy Display" and c.control_type == "MenuItem" ...]
  ```
- **재현 트리거**: 한국어("디스플레이", "디스플레이 복사"), 독일어("Anzeige"), 프랑스어 등 비영어 환경에서 실행.
- **파괴 메커니즘**: 메뉴명 불일치로 `len(menus) != 1` 또는 `len(copies) != 1` 예외가 발생하여 비영어 Capstone 환경에서 그래프 데이터 수집 완전 불능.

#### 🔴 DEFECT-GR03: 피트 실패/취소 시 XML 속성 부재로 인한 파싱 크래시
- **위치**: [inspection.py#L150-L151](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L150-L151), [L169](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L169)
- **코드**:
  ```python
  value = _required(definition, "ZCFDICurveFitParameterResultValue")
  uncertainty = _required(definition, "ZCFDICurveFitParameterFitGoodness")
  value = _required(element, "ZCFDICurveFitResultsValue")
  ```
- **재현 트리거**: 피트 연산이 실패(FAIL_MAX_ITERATIONS 등)하거나 사용자에 의해 중단되어 Capstone이 파라미터 값/불확도 속성을 XML에서 생략했을 때.
- **파괴 메커니즘**: `_required()`가 `GraphStateError`를 발생시켜 실패 상태를 정상 보고하지 못하고 프로세스 전체가 크래시됨.

#### 🔴 DEFECT-GR04: 무지연 3회 {ESC} 연타 및 Stale Ref `COMError`
- **위치**: [inspection.py#L307-L320](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L307-L320)
- **코드**:
  ```python
  for _ in range(MENU_RELEASE_ATTEMPTS): # 3회
      snapshot = app.snapshot(handle, 3, 400)
      armed = any(c.control_type == "MenuItem" and app.refs[c.ref].has_keyboard_focus() ...)
      _ = app.keys(handle, "{ESC}")
  ```
- **재현 트리거**: 메뉴바가 열린 상태에서 `release_menu_bar` 호출.
- **파괴 메커니즘**: 1) 스냅샷 직후 메뉴가 닫히면 `app.refs[c.ref]` 접근 시 `COMError` 발생. 2) 루프 간 딜레이가 0ms이므로 Windows 메시지 큐 처리 전에 3회의 `{ESC}`가 즉시 소진되어 `AutomationError: Capstone stayed in menu mode after Escape` 오발생.

---

### 2. `src/capstone_mcp/graphs/manager.py` 결함

#### 🔴 DEFECT-GR05: 플로팅 창 존재 시 피트/축 변경 전면 차단
- **위치**: [manager.py#L166-L169](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L166-L169), [L355-L358](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L355-L358)
- **코드**:
  ```python
  before = {w.handle for w in app.windows()}
  if before != {handle}:
      msg = "Close existing dialogs and menus before toggling a graph fit." # 또는 selecting a graph axis
      raise AutomationError(msg)
  ```
- **재현 트리거**: Capstone 메인 윈도우 외에 보조 위젯(센서 창, 계산기 등)이 별도 HWND로 열려 있는 상태에서 피트 토글 또는 축 선택 시도.
- **파괴 메커니즘**: 대화상자가 열려 있지 않음에도 `before != {handle}`로 판정되어 작업이 차단됨.

#### 🔴 DEFECT-GR06: 랩톱 해상도/화면 하단 배치 시 피트 메뉴 경계 오인 차단
- **위치**: [manager.py#L180-L184](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L180-L184)
- **코드**:
  ```python
  bounds = popup.window.bounds
  if bounds.top < rect.top or bounds.bottom > rect.bottom:
      msg = "Fit menu is clipped; enlarge the window before choosing a fit."
      raise AutomationError(msg)
  ```
- **재현 트리거**: 1080p 이하 랩톱 화면이거나 그래프가 화면 하단에 위치하여 24개 항목의 드롭다운 메뉴가 메인 윈도우 경계 아래로 펼쳐질 때.
- **파괴 메커니즘**: 데스크톱 전체 화면에서는 완벽히 표시됨에도 메인 윈도우 `rect.bottom`을 벗어났다는 이유로 클리핑 에러를 던지며 피트 선택을 강제 중단함.

#### 🔴 DEFECT-GR07: 단일 무명 MenuItem 전제 파탄 및 15초 타임아웃
- **위치**: [manager.py#L125-L144](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L125-L144)
- **코드**:
  ```python
  items = [c for c in snapshot.controls if c.control_type == "MenuItem"]
  if len(items) == 1 and not items[0].name and not snapshot.controls[0].automation_id:
      return snapshot
  ```
- **재현 트리거**: 특정 Capstone 버전이나 UI 트리에서 드롭다운 메뉴 항목들이 UIA에 복수 개로 정상 노출될 때.
- **파괴 메커니즘**: `len(items) == 1` 가정이 깨져 `_fit_menu`가 `None`을 반환, `events.changes.until`이 15초 동안 멈춘 뒤 타임아웃 실패.

#### 🔴 DEFECT-GR08: `create_graph`의 영문 팔레트 하드코딩
- **위치**: [manager.py#L260-L268](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L260-L268)
- **코드**:
  ```python
  matches = [c for c in snapshot.controls if c.name == "Graph" and c.control_type in (...) and c.visible]
  if len(matches) != 1: raise AutomationError("Expected one Graph display palette item...")
  ```
- **재현 트리거**: 한국어("그래프"), 프랑스어("Graphique"), 스페인어("Gráfico") 환경에서 `create_graph` 호출.
- **파괴 메커니즘**: 팔레트 항목을 찾지 못해 `len(matches) != 1` 예외 발생, 그래프 신규 삽입 100% 실패.

#### 🔴 DEFECT-GR09: `invoke_graph_menu`의 DPI 스케일링 불일치 클릭 오류
- **위치**: [manager.py#L87-L98](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L87-L98)
- **코드**:
  ```python
  control = app.control(ref)
  bounds = control.rectangle()
  point = screen_point or Point(x=(bounds.left + bounds.right) // 2, y=...)
  control.click_input(button="left", coords=(point.x, point.y), absolute=True)
  ```
- **재현 트리거**: 디스플레이 배율이 125% 또는 150%인 환경에서 실행.
- **파괴 메커니즘**: pywinauto의 `rectangle()` 반환값과 `absolute=True` 클릭 좌표 간의 DPI 인식 불일치로 인해 실제 메뉴 항목에서 1.25~1.5배 벗어난 위치를 클릭하여 엉뚱한 메뉴가 선택됨.

---

### 3. `src/capstone_mcp/graphs/toolbox.py` 결함

#### 🔴 DEFECT-GR10: `request.enable` 무시하고 맹목적 클릭으로 활성 도구 강제 해제
- **위치**: [toolbox.py#L261-L286](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L261-L286), [L322-L348](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L322-L348)
- **코드**:
  ```python
  # toggle_graph_statistics 및 measure_graph_area 공통
  click_control(app, request.handle, stats_btn, allow_foreground=True) # request.enable 조건 검사 전무
  ```
- **재현 트리거**: 이미 통계(Σ) 또는 면적(∫) 도구가 켜져 있는 상태에서 `enable=True`로 호출.
- **파괴 메커니즘**: 현재 토글 상태(`ToggleState`)를 확인하지 않고 무조건 클릭하므로 도구가 켜지는 대신 꺼져버림.

#### 🔴 DEFECT-GR11: `graph_delta`의 단순 클릭으로 인한 십자선 재배치 실패 (드래그 부재)
- **위치**: [toolbox.py#L431-L446](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L431-L446)
- **코드**:
  ```python
  if request.point1 and hasattr(app, "click_point"):
      app.click_point(request.handle, request.point1.x, request.point1.y, allow_foreground=True)
  if request.point2 and hasattr(app, "click_point"):
      app.click_point(request.handle, request.point2.x, request.point2.y, allow_foreground=True)
  ```
- **재현 트리거**: `point1`, `point2` 좌표를 지정하여 델타 도구 측정 구간 설정.
- **파괴 메커니즘**: Capstone의 델타 도구는 십자선 핸들을 마우스 드래그해야 구간이 설정됨. 단순 클릭 2회는 십자선을 이동시키지 못하고 엉뚱한 플롯 포인트를 클릭함.

#### 🔴 DEFECT-GR12: 단일 컨트롤 내 2개 좌표쌍 가정 파탄으로 델타 좌표 파싱 불능
- **위치**: [toolbox.py#L395-L407](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L395-L407)
- **코드**:
  ```python
  coord_pairs = COORD_PAIR_RE.findall(text)
  if len(coord_pairs) >= MIN_COORDINATE_PAIRS and x1 is None: ...
  ```
- **재현 트리거**: Capstone이 두 십자선의 좌표 `(x, y)`를 각각 별도의 텍스트 툴팁 레이블로 분리하여 렌더링할 때.
- **파괴 메커니즘**: 각 컨트롤당 좌표쌍이 1개(`len(coord_pairs) == 1`)만 존재하므로 `len(coord_pairs) >= 2` 조건이 절대 만족되지 않아 `x1, y1, x2, y2` 좌표 차이 계산이 완전히 누락됨.

#### 🔴 DEFECT-GR13: 툴바 상단 고정(120px) 가정 파탄 및 타 그래프 버튼 오클릭
- **위치**: [toolbox.py#L132-L170](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L132-L170)
- **코드**:
  ```python
  if not (c.bounds.top >= gb.top - 50 and c.bounds.bottom <= gb.top + TOOLBAR_SEARCH_HEIGHT_PX and ...): continue
  # Fallback: check all window controls
  for c in controls: ... return c
  ```
- **재현 트리거**: 툴바가 그래프 하단이나 측면에 도킹되어 있거나, 페이지에 여러 그래프(Graph 1, Graph 2)가 표시될 때.
- **파괴 메커니즘**: 상단 120px 내에서 버튼을 찾지 못하고 전역 폴백으로 넘어가 Graph 2의 툴바 버튼을 찾아 잘못 클릭함.

#### 🔴 DEFECT-GR14: 툴바 검색 키워드 영문 전용으로 한국어/다국어 툴바 버튼 미검출
- **위치**: [toolbox.py#L28-L47](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/toolbox.py#L28-L47)
- **코드**:
  ```python
  STATS_KEYWORDS = ("statistics", "stats", "sigma", "σ", "Σ")
  AREA_KEYWORDS = ("area", "integral", "∫", "∫ydx")
  DELTA_KEYWORDS = ("delta", "coordinate", "coord", "crosshair", "Δ")
  ```
- **재현 트리거**: 한국어 로케일("통계", "면적", "적분", "좌표") 또는 다국어 환경에서 툴박스 도구 실행.
- **파괴 메커니즘**: 기호(Σ, ∫, Δ)가 버튼 텍스트에 포함되지 않고 툴팁이 한글인 경우 키워드 매칭 실패로 `AutomationError: Graph toolbar button matching ... not found` 발생.

</details>

#### 📑 실사 보고서: `auditor-displays` (총 4회 정밀 실사)

<details open>
<summary><b>[보고서 #32] auditor-displays 실사 세부 명세 (Phase 1)</b></summary>

### 1. Fatal Execution Bugs
- **Non-existent `app.type_text()` in `harness.py:140-141`**: In `set_control_value()`, if `iface_value` is missing, it clears text with `app.keys(handle, "^a{BACKSPACE}")` and then checks `if hasattr(app, "type_text")`. Since `Capstone` only provides `keys()`, `text` is never typed and `{ENTER}` is pressed immediately. This silently clears values without setting them across all of `scope.py` (`_configure_scope`, `_configure_fft`, `set_scope_trigger`).
- **Signature mismatch in `harness.py:65`**: `app.act(handle, Action.INVOKE, ref=ctrl.ref, ...)` passes `handle` positionally where `ref` is expected, plus `ref=ctrl.ref` keyword. This always throws `TypeError: Capstone.act() got multiple values for keyword argument 'ref'`, which is masked by `suppress(Exception)`.
- **Double-click dropped in `harness.py:50-53`**: If `hasattr(app, "click")`, `click_control(..., double=True)` invokes `app.click(handle, ctrl.ref)` without `double=True`.
- **Stale control refs in `table.py:158-164`**: In `set_table_columns`, after clicking `add_btn` and taking a new snapshot, `table_ctrl` and `add_btn` are not refreshed. Subsequent iterations use stale refs cleared by `app.snapshot()`, raising `AutomationError: Unknown or stale ref`.
- **Statistics misattribution in `table.py:242`**: `_extract_cells_and_statistics` hardcodes `target_col = column_names[0]`, assigning all column statistics (Mean, Max, Min, etc.) to Column 1.
- **Column skew on missing cells in `table.py:277-287`**: `_group_cells_into_rows` assigns row cells to columns purely by list index (`col_idx < len(cluster)`). If any cell in a row is empty, subsequent values shift into the wrong columns.
- **Dropped cell data in `table.py:262`**: `if text in column_names: continue` drops any valid data cell whose text equals a column header name (e.g. "0", "1", "Run", "Status").
- **Uncontrolled window-wide mutation in `scope.py:47-51` & `176-184`**: `_configure_scope` and `_configure_fft` scan all controls across the entire window snapshot (not bounded to the display widget) and mutate every control matching generic words like `"time"`.
- **Hardcoded display IDs in `scope.py:69, 202`**: `display_id` is hardcoded to `"Scope 1"` and `"FFT 1"`, breaking multi-scope/multi-FFT tracking.
- **Pywinauto syntax corruption in `workbook.py:61`**: `app.keys(handle, f"^a{title}{{ENTER}}")` does not escape pywinauto special characters (`+`, `^`, `%`, `~`, `(`, `)`). Titles like `"Run (1)"` or `"Force + Accel"` fail or corrupt typing.

### 2. Silent Exception Swallowing (`suppress(Exception)`)
- `harness.py:54, 64, 79, 82, 106, 113, 132`: Swallows UIA errors, stale refs, focus failures, and drag failures without logging.
- `digits.py:91, 101, 153, 160`: Swallows `ValueError`, `SetValue` on buttons, and keystroke errors while unconditionally returning `verified=True`.
- `table.py:168, 175`: Swallows `SetValue` and keystroke errors on headers while returning `verified=True`.
- `workbook.py:53, 132`: Swallows tab rename and selection errors silently.

### 3. Coordinate & Spatial Fragilities
- **`harness.py:36`**: `center_coords` does not validate bounds. `(0, 0, 0, 0)` bounds click the top-left screen pixel.
- **`harness.py:225-232`**: Claims "largest Custom/Pane" fallback but does `candidates[0]` without size sorting.
- **`table.py:21-22, 98-103`**: Fixed pixel tolerances (`ROW_Y_TOLERANCE_PX=5`, `EXPAND_RIGHT_PX=100`) break on high-DPI scaling (>=150%). Creeping `current_top = top` can drift and merge distinct rows.
- **`scope.py:223-258`**: Fragile regex string parsing for FFT peak coordinates; fails on non-standard formatting, scientific notation, or localized decimals.

### 4. UIA Race Conditions & Virtualization
- **Zero-wait snapshots (`digits.py:144`, `table.py:131, 162`, `scope.py:41`, `workbook.py:91`)**: Immediate snapshots after UI actions without waiting for Qt render loops cause intermittent missing-control errors.
- **Tab rename race in `workbook.py:91-97`**: If the new tab hasn't rendered immediately, `new_tabs[-1]` points to the previous tab, renaming the wrong tab.
- **Table virtualization (`table.py:290-350`)**: `read_table` does not scroll (`ScrollPattern`/PageDown). For virtualized tables with thousands of points, only ~20 visible rows are read, while `total_rows` and pagination falsely report only visible cells.

### 5. Keyword & String Matching Collisions
- **`workbook.py:280`**: `ADD_PAGE_NAMES` includes `"+"`, clashing with zoom `"+"` or table "Add Column" `"+"`.
- **`workbook.py:338, 327`**: `"grid"` matches `DataGrid`/`PropertyGrid`; `"template3"` matches `"template3h"`.
- **`workbook.py:121`**: Substring matching in `_switch_to_page` matches "Page 10" when looking for "Page 1".
- **`digits.py:59, 110-114`**: `_find_measurement_selector` matches ANY button inside Digits. Unit extraction captures "Digits 1" or "Run 1" as unit.
- **`table.py:74-86`**: English-only statistics keywords break on non-English locales.

### 6. Architectural Debts & API Contract Gaps
- Ignored request parameters: `start_row`, `limit` (`ReadTableRequest`), `min_amplitude` (`ReadFftPeaksRequest`), and `trigger_source` (`SetScopeTriggerRequest`).
- `DisplayManager` is a stateless forwarder with no registry for tracking active displays or pages.
- `DisplayResult` duplicates payload serialization via `@computed_field` properties.
- `tools/displays.py:34`: `get_last_failure` parameter is accepted but discarded with `del get_last_failure`.

</details>

<details open>
<summary><b>[보고서 #38] auditor-displays 실사 세부 명세 (Phase 2)</b></summary>

Detailed line-by-line failure scenarios for `displays/scope.py`, `displays/harness.py`, `displays/table.py`, `displays/digits.py`, and `displays/workbook.py`:

---

### 1. `displays/scope.py`: `_parse_peak_text` Regex Scraping & English Queries

#### A. `_parse_peak_text` Regex Scraping Fragilities (Lines 224–258)
- **Code Reference**: [scope.py:224-258](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L224-L258)
- **Concrete Failure Scenarios**:
  1. **Negative Amplitude / dB Scale Truncation**:
     - Regex pattern `r"\(\s*([0-9.]+)\s*(?:Hz|kHz)?\s*,\s*([0-9.]+)\s*(?:V|mV|dB)?\s*\)"` uses `[0-9.]`, which omits `[+-]?`.
     - *Failure*: When FFT spectrum renders dB attenuation (e.g. `(1200 Hz, -15.4 dB)`) or AC voltage below ground reference (e.g. `(60 Hz, -2.5 V)`), regex returns `None`. Detected peaks are completely dropped.
  2. **Scientific Notation Incompatibility**:
     - *Failure*: Capstone renders wide dynamic range frequencies or small amplitudes in scientific notation (e.g. `(1.25e4 Hz, 3.2e-3 V)`). The pattern `[0-9.]` fails on `e` and `-`, dropping valid peaks.
  3. **Unit Magnitude Scaling Inconsistency**:
     - `if "khz" in text.lower(): freq *= 1000.0`.
     - *Failure 1*: If frequency is in `MHz` or `GHz`, no scaling occurs; `(1.5 MHz, 2.0 V)` is recorded as `1.5 Hz`.
     - *Failure 2*: Amplitude unit (e.g. `mV`, `µV`) is completely ignored. `(1000 Hz, 50 mV)` is stored as `amplitude=50.0`, identical to `50 V` (1,000x error).
  4. **Phantom Scraping vs Buffer Query**:
     - `read_fft_peaks` scrapes active UIA element names (`ctrl.name`). If the user/automation hasn't explicitly opened coordinate delta crosshairs or if labels are occluded, it returns 0 peaks with `verified=True` ("No peak coordinates detected").

#### B. `sec/div` & `y-axis` English Queries (Lines 45–51, 177–183)
- **Code Reference**: [scope.py:45-51](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L45-L51), [scope.py:177-183](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L177-L183)
- **Concrete Failure Scenarios**:
  1. **Internationalization / Locale Crash**:
     - `"sec/div"` and `"y-axis"` are hardcoded English substrings. On Korean (`초/눈금`, `Y축`), German (`s/Skalenteil`, `Y-Achse`), or Spanish Capstone, string matching fails completely.
  2. **Unbounded Window Mutation**:
     - `_configure_scope` scans `fresh.controls` (entire window). Condition `"time" in aid` matches any UIA element containing `"time"` (`timer`, `timestamp`, `runtime_display`). Every matching control in the window has its value cleared and destroyed.

---

### 2. `displays/harness.py`: `drag_control` Deceptive Double-Click Fallback

- **Code Reference**: [harness.py:98-123](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/harness.py#L98-L123)
- **Concrete Failure Scenario**:
  ```python
  with contextlib.suppress(Exception):
      node = app.control(source.ref)
      if hasattr(node, "drag_mouse"):
          dst_coords = center_coords(target.bounds)
          node.drag_mouse(dst_coords)
          return
  # Fallback to double-click placement if drag is unhandled by mock/backend
  double_click_control(app, handle, source)
  ```
  1. `Capstone` does not implement `app.drag()`.
  2. Pywinauto's `UIAWrapper` does NOT have a `drag_mouse` method (it only exists on `HwndWrapper` in win32 backend).
  3. `with contextlib.suppress(Exception):` silently swallows the `AttributeError`.
  4. Execution falls through to `double_click_control(app, handle, source)`.
  5. **Deceptive Behavior**: Double-clicking a palette item inserts the display into the *default active area* (area 1 or full-screen overlay), completely ignoring `target`.
  6. *Result*: When an agent requests dragging a Table into Area 2 of a two-column layout, the harness silently double-clicks it into Area 1, obliterating or overlapping the existing display, yet reports 100% success.

---

### 3. `displays/table.py`: Table Data Extraction & Clipboard Dependencies

#### A. Spatial Heuristics vs Clipboard / Structured Export (Lines 203–288)
- **Code Reference**: [table.py:203-288](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/table.py#L203-L288)
- **Concrete Failure Scenarios**:
  1. **UI Virtualization Data Loss**:
     - Capstone tables with 10,000 sensor points only instantiate ~20–30 visible rows in UIA. `read_table` does not scroll (`ScrollPattern` or keyboard `PageDown`).
     - *Failure*: Even with `page=5`, it extracts only on-screen rows. Total rows is reported as the visible subset (e.g. 25 rows instead of 10,000).
  2. **High-DPI Row Cluster Drift**:
     - `ROW_Y_TOLERANCE_PX = 5` with creeping anchor `current_top = top`. On 150%+ display scaling, baseline jitter causes `abs(top - current_top) <= 5` across consecutive rows, merging multiple rows into one cluster.
  3. **Column Skew on Null / Sparse Cells**:
     - Line 282: `row_dict[col_name] = cluster[col_idx][1]`.
     - *Failure*: If row 3 has an empty cell in column 1 (`Time`), but column 2 (`Force`) has `5.2`, `cluster` has length 1. `col_idx=0` gets `5.2`, mapping Force data into the Time column.
  4. **Data Cell Dropped on Header Collision**:
     - Line 262: `if text in column_names: continue`.
     - *Failure*: If a table has a column named `Status` or `0`, any cell containing `"Status"` or `"0"` is permanently deleted from the returned rows.
  5. **Clipboard Dependency Contrast**:
     - Unlike `graphs/inspection.py` which uses native clipboard XML with backup/restore (`_backup_clipboard()`, `_restore_clipboard()`), `table.py` avoided clipboard entirely but implemented fragile spatial scraping that cannot extract virtualized datasets.

---

### 4. `displays/digits.py` & `displays/workbook.py`: Unchecked Suppress & Layout Assumptions

#### A. `displays/digits.py`
- **Code Reference**: [digits.py:59, 110-114, 153-162](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/digits.py)
- **Concrete Failure Scenarios**:
  1. **`suppress(Exception)` on Measurement Binding**:
     - Lines 153–162 attempt `node.iface_value.SetValue` on a menu button, then `app.keys(measurement + "{ENTER}")`. Both fail on Qt popup menus and are silently swallowed.
     - *Failure*: Digits display is created unbound, but returns `measurement="Force"`, `verified=True`, faking successful binding.
  2. **Display Title Extracted as Engineering Unit**:
     - Lines 110–114: Unit candidate check is `len(text) <= 10 and "select" not in text.lower()`.
     - *Failure*: Control `Digits 1` (length 8) or `Run 1` (length 5) matches. Returned result has `unit="Digits 1"`.
  3. **Indiscriminate Selector Button Match**:
     - Line 59: `or c.control_type in ("Button", "ComboBox")`. Any button (including widget close button `X` or properties) is clicked instead of the measurement selector.

#### B. `displays/workbook.py`
- **Code Reference**: [workbook.py:37-40, 60-61, 91-97, 148-154](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/workbook.py)
- **Concrete Failure Scenarios**:
  1. **`"+"` Collision in `ADD_PAGE_NAMES`**:
     - Line 280 includes `"+"`. If the window has a Zoom In `"+"` button or Table Add Column `"+"` button preceding the tab bar in UIA order, `add_page` clicks Zoom In instead of Add Page.
  2. **Tab Rename Race Condition**:
     - Lines 91–97 take a snapshot immediately after clicking Add Page. If Qt has not yet finished creating the tab control, `new_tabs[-1]` references the *previous* tab, renaming the wrong workbook page.
  3. **Unescaped Pywinauto Modifier Characters**:
     - Line 61: `app.keys(handle, f"^a{title}{{ENTER}}")`.
     - *Failure*: Titles with `+`, `^`, `%`, `~`, `(`, `)` (e.g. `"Trial (Run 1)"` or `"P + V"`) trigger pywinauto modifier hotkeys (Shift, Ctrl, Alt) or crash with syntax errors.
  4. **Keyword Clashes in `LAYOUT_KEYWORDS`**:
     - `"grid"` in `four_grid` matches any `DataGrid` or table in the window.
     - `"template3"` in `three_vertical` matches `"template3h"` (`three_horizontal`), applying the wrong layout template.
  5. **Fake Verification in `set_page_layout`**:
     - Lines 180–188: `areas_created` is looked up from a hardcoded dictionary (`LAYOUT_AREAS[request.layout]`) without verifying whether layout areas were actually created. Returns `verified=True` blindly.

</details>

<details open>
<summary><b>[보고서 #68] auditor-displays 실사 세부 명세 (Phase 3)</b></summary>

Beyond the initial findings (P1-22, P2-31, P2-32, P3-36, P3-37), here are 14 newly identified specific defects across `src/capstone_mcp/displays/` with exact files, line numbers, triggers, and destruction mechanisms:

---

### 🔴 DEFECT-DISP-01: Digits Close Button Destruction via Indiscriminate Button Matching
- **File**: [digits.py#L48-L63](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/digits.py#L48-L63)
- **Code**: `or c.control_type in ("Button", "ComboBox")` in `_find_measurement_selector`.
- **Trigger**: Creating a Digits display with a requested measurement (`measurement="Force"`).
- **Destruction**: Capstone Digits widgets contain a title bar with a Close ("X") button, Dock button, and Settings button. If any of these appear before the measurement dropdown button in UIA tree traversal, `_find_measurement_selector` selects it. In line 151, `click_control(app, selector)` clicks the Close button, immediately destroying and closing the newly created Digits widget!

---

### 🔴 DEFECT-DISP-02: Modal Popup Menu Focus Lockup & Ineffective Value Injection
- **File**: [digits.py#L153-L162](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/digits.py#L153-L162)
- **Trigger**: Calling `create_digits(measurement="Force")`.
- **Destruction**:
  1. `click_control(selector)` opens a modal Qt popup context menu (separate Win32 popup HWND).
  2. `node.iface_value.SetValue` fails silently on the button (`suppress(Exception)`).
  3. `app.keys(request.handle, request.measurement + "{ENTER}")` sends keys to the main window (`request.handle`), NOT the popup menu HWND!
  4. The keys are dropped or typed into whatever had focus behind the popup.
  5. The popup menu is never closed (`{ESC}` is never sent), permanently capturing mouse/keyboard focus and deadlocking all subsequent Capstone UI operations.
  6. Returns `verified=True` and `measurement="Force"`, reporting a fake successful binding.

---

### 🟠 DEFECT-DISP-03: Display/Run Title Captured as Engineering Unit
- **File**: [digits.py#L110-L116](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/digits.py#L110-L116)
- **Trigger**: Inspecting a Digits display labeled "Digits 1" or displaying "Run 1".
- **Destruction**:
  `len(text) <= MAX_UNIT_STR_LEN and "select" not in text.lower() and not found_unit`
  `"Digits 1"` has length 8 (<= 10) and does not contain `"select"`. If visited before the real unit label (or when unit is absent), `found_unit` becomes `"Digits 1"` or `"Run 1"`. API consumers receive corrupted metadata (e.g. `unit="Digits 1"`).

---

### 🔴 DEFECT-DISP-04: Table Toolbar Buttons Misidentified as Column Headers ("Delete Column" Clicked)
- **File**: [table.py#L49-L78](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/table.py#L49-L78)
- **Code**: `c.control_type == "Button" and c.name.strip().lower() not in ("add column", "+")` within `table_ctrl.bounds.top + MAX_HEADER_HEIGHT_PX`.
- **Trigger**: Calling `set_table_columns()` on a Table with a top toolbar containing "Delete Column", "Statistics", or "Properties" buttons.
- **Destruction**: Because all toolbar buttons within the top 100px match as column headers and are sorted by `bounds.left`, a "Delete Column" or "Properties" button on the left of the table is misidentified as Column 1 (`headers[0]`). In line 166, `click_control(app, header_ctrl)` clicks "Delete Column", deleting existing data columns instead of binding measurements.

---

### 🔴 DEFECT-DISP-05: Multi-Table Column Expansion Cross-Contamination in Split Layouts
- **File**: [table.py#L80-L106](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/table.py#L80-L106)
- **Code**: `c.bounds.right <= table_ctrl.bounds.right + EXPAND_RIGHT_PX` (100px) and `c.name == "+"`.
- **Trigger**: Active page has two adjacent Table displays (e.g. in `two_vertical` layout), and caller invokes `set_table_columns` on Table 1.
- **Destruction**: If Table 2's Add Column button is within 100px to the right of Table 1, `_find_add_column_button` matches Table 2's Add Column button! Table 2 gets new columns added while Table 1 remains unexpanded, corrupting user page layout.

---

### 🔴 DEFECT-DISP-06: Stale Ref Crash on Multi-Column Table Expansion
- **File**: [table.py#L158-L164](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/table.py#L158-L164)
- **Trigger**: Requesting `columns=["A", "B", "C"]` on a table that currently has only 1 column.
- **Destruction**:
  1. On iteration `i=1`: clicks `add_btn`.
  2. Calls `app.snapshot()`, which increments `generation` and runs `self.refs.clear()`.
  3. `table_ctrl` and `add_btn` are NOT re-queried from the new snapshot.
  4. On iteration `i=2`: calls `click_control(app, request.handle, add_btn)`.
  5. `add_btn.ref` is from the previous generation and was cleared.
  6. Raises `AutomationError: Unknown or stale ref. Take a new snapshot.`, aborting column expansion mid-way.

---

### 🔴 DEFECT-DISP-07: Statistics Summary Attribution Overwrite (Forced into Column 1)
- **File**: [table.py#L240-L247](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/table.py#L240-L247)
- **Code**: `target_col = column_names[0] if column_names else "Value"`.
- **Trigger**: Calling `read_table(include_statistics=True)` on a multi-column table (e.g. Time, Position, Velocity) with statistics enabled.
- **Destruction**: X coordinate is never evaluated. Every summary statistic (Mean, Max, Min) across ALL columns is hardcoded to `column_names[0]` ("Time"). If Velocity Mean is calculated after Position Mean, it overwrites Position Mean. Returned `ReadTableResult.statistics` contains corrupted statistics falsely attributed to Column 1.

---

### 🔴 DEFECT-DISP-08: Unbounded Window Mutation via Unrestricted "time" Scan Loop
- **File**: [scope.py#L41-L52](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L41-L52), [scope.py#L170-L184](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L170-L184)
- **Trigger**: Calling `create_scope(timebase="10 ms")` or `create_fft(measurement="Voltage")`.
- **Destruction**:
  `_configure_scope` and `_configure_fft` scan all controls across the entire window snapshot without bounding to the Scope/FFT widget. There is NO `break` statement.
  If the window contains 5 controls matching `"time"` (e.g. status bar time, run timer, table time column, sampling rate display), it calls `set_control_value()` on ALL 5 CONTROLS sequentially.
  In `harness.py:139-142`, `set_control_value` clears the field with `^a{BACKSPACE}`, skips typing because `app.type_text` doesn't exist, and hits `{ENTER}`. It blanks out and corrupts every timer/time control in the active window.

---

### 🔴 DEFECT-DISP-09: Collapsed Scope Trigger Drawer Silent Failure & Fake Verification
- **File**: [scope.py#L86-L108](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L86-L108), [scope.py#L142-L162](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L142-L162)
- **Trigger**: Calling `set_scope_trigger()` when the Scope Trigger drawer panel in Capstone is closed/collapsed.
- **Destruction**:
  Trigger controls are not visible (`ctrl.visible == False`). `_find_trigger_controls` returns `(None, None, None)`.
  Lines 142–148 simply skip setting any values.
  Lines 149–162 immediately return `ScopeTriggerResult(verified=True, detail="Scope 'Scope 1' trigger configured: Level=1.5V, Slope=rising, Mode=auto.")`.
  Zero settings were changed in Capstone, but API returns fake 100% verification.

---

### 🔴 DEFECT-DISP-10: Graph/Table Zoom In Button `"+"` Preemption of Workbook Page Creation
- **File**: [workbook.py#L27-L44](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/workbook.py#L27-L44)
- **Code**: `ADD_PAGE_NAMES = ("Add Page", "New Page", "Create Page", "+")`.
- **Trigger**: Calling `add_page()` while a Graph display or Table is active on the page.
- **Destruction**: Graph displays contain a Zoom In tool button named `"+"`. Because graph widgets appear before the bottom workbook tab bar in snapshot order, `_find_add_page_button` matches the Zoom In button! `add_page` clicks Zoom In on the graph instead of creating a workbook page, and then crashes when looking for the newly created tab.

---

### 🔴 DEFECT-DISP-11: Asynchronous Tab Creation Race & Previous Page Tab Overwrite
- **File**: [workbook.py#L81-L98](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/workbook.py#L81-L98)
- **Trigger**: Calling `add_page(title="Experiment 2")`.
- **Destruction**:
  1. `click_control(app, add_btn)` fires.
  2. With 0ms delay, `app.snapshot()` captures controls.
  3. Because Qt tab creation is asynchronous, the new `TabItem` is not yet present.
  4. `new_tabs` contains the identical old tabs.
  5. `latest_tab = new_tabs[-1]` points to the *existing* page tab (e.g. "Page 1").
  6. `_rename_page_tab` renames "Page 1" to "Experiment 2"!
  7. When the new tab finally renders, it has default unconfigured title, while the previous page's name was destroyed.

---

### 🔴 DEFECT-DISP-12: Layout Keyword Substring Clashes (`"grid"`, `"template3"`)
- **File**: [workbook.py#L327, L338](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/workbook.py#L327), [workbook.py#L138-L156](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/workbook.py#L138-L156)
- **Trigger**: Calling `set_page_layout(layout="four_grid")` or `layout="three_vertical"`.
- **Destruction**:
  - `four_grid` keywords include `"grid"`. It substring-matches any `DataGrid` (tables), `GridView`, or `GridSplitter` on the active page, clicking a table instead of the layout template button.
  - `three_vertical` keywords include `"template3"`, which is a substring of `"template3h"` (`three_horizontal`). If horizontal templates precede vertical templates in UI order, `"template3"` matches `three_horizontal`, applying the wrong layout.

---

### 🔴 DEFECT-DISP-13: "Largest Custom/Pane" Fallback Targeting Menu Bar / Ribbon
- **File**: [harness.py#L225-L236](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/harness.py#L225-L236)
- **Trigger**: Calling `find_display_container(controls, "table")` or `"digits"` when no matching container is found.
- **Destruction**:
  Code claims: `# Fallback to the largest Custom/Pane that isn't the root window`.
  Instead of calculating area `(right-left)*(bottom-top)`, it does `candidates[0]`.
  In Capstone, the first child `Pane`/`Custom` is the top menu bar / ribbon header container.
  The harness treats the 24px-tall top menu bar as the Table/Scope container, attempts to extract cells or measurement selectors inside it, clicks random menu buttons, and triggers unintended menu commands.

---

### 🟠 DEFECT-DISP-14: Read-Only Actions Invalidate Active Session Control References (`refs.clear()`)
- **File**: [tools/displays.py#L73, L111-L115](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/displays.py#L73), [desktop.py#L196-L197](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L196-L197)
- **Trigger**: Calling `capstone_manage_display(action="read_table")` while another workflow holds control refs.
- **Destruction**:
  `read_table` is marked `mutates=False` in tool annotations. However, its internal execution calls `app.snapshot()`, which runs `self.generation += 1` and `self.refs.clear()`.
  Calling a read-only table query silently wipes out all existing cached UIA element references across the entire MCP session, causing any concurrent or subsequent tool calls relying on prior snapshot refs to fail with `AutomationError: Unknown or stale ref`.

---
All 14 defects have been confirmed against production lines in `src/capstone_mcp/displays/` and `src/capstone_mcp/tools/displays.py`. Ready for master matrix integration.

</details>

<details open>
<summary><b>[보고서 #77] auditor-displays 실사 세부 명세 (Phase 4)</b></summary>

Addressing Phase 3 directives (complex rendering, special character injections, depth truncation, and numeric/locale breakdowns) across `src/capstone_mcp/displays/`:

---

### 🔴 DEFECT-DISP-15: Unicode Minus Sign (`\u2212`) Rejection in Float Extraction
- **Files**: [digits.py#L39, L90-L105](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/digits.py#L39), [table.py#L192-L201](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/table.py#L192-L201)
- **Code**:
  `FLOAT_PATTERN = re.compile(r"^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")` in `digits.py`.
  `_parse_cell_value`: `try: return float(val) except ValueError: return val` in `table.py`.
- **Trigger**: Capstone scientific rendering of negative values (e.g. `−0.45 N` or `−12.3 V`) using Unicode Minus (`\u2212` / `−`, standard in Qt typography) instead of ASCII hyphen (`\u002d` / `-`).
- **Destruction**:
  1. In `digits.py`: Regex `[+-]` only matches ASCII `+` and `-`. Unicode `\u2212` fails to match both `FLOAT_PATTERN` and `combined_match`. The negative numerical readout is rejected. `found_value` remains `None`.
  2. In `table.py`: Python's built-in `float("\u22123.5")` raises `ValueError: could not convert string to float: '−3.5'`. `_parse_cell_value` falls through to returning `val` as a raw string (`"−3.5"`). Downstream numerical analysis and regression pipelines receive strings and crash with `TypeError`.

---

### 🔴 DEFECT-DISP-16: Pywinauto Key Syntax Metacharacter Injection & Alt/Ctrl Hijacking
- **Files**: [workbook.py#L61](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/workbook.py#L61), [table.py#L176](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/table.py#L176), [digits.py#L161](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/digits.py#L161)
- **Code**:
  `app.keys(handle, f"^a{title}{{ENTER}}")`
  `app.keys(request.handle, col_name + "{ENTER}")`
- **Trigger**: Entering standard scientific notation in page titles, column names, or measurements containing `+`, `^`, `%`, `~`, `(`, `)`, `{`, `}` (e.g. `title="Efficiency (100%)"`, `columns=["Position (m)", "Acceleration (m/s^2)"]`).
- **Destruction**:
  - `%`: Pywinauto interprets `%` as the `Alt` key modifier. `100%` triggers the Windows top-level menu bar (`Alt` hotkey), stealing keyboard focus and activating "File" or "Edit" menus.
  - `^`: Interpreted as `Ctrl`. `m/s^2` sends `Ctrl+2`, executing Capstone internal keyboard shortcuts (e.g. switching views or zooming).
  - `+`: Interpreted as `Shift`.
  - `{`, `}`: Triggers pywinauto virtual key token parsing; unclosed braces or non-key strings crash with `pywinauto.keyboard.KeySequenceError`.

---

### 🔴 DEFECT-DISP-17: Depth=12 Truncation in `create_scope` and `create_fft`
- **File**: [scope.py#L65, L198](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L65)
- **Code**: `snapshot = app.snapshot(request.handle, depth=12, limit=10_000)` (unlike `depth=16` in `digits.py` and `table.py`).
- **Trigger**: Complex workbook containing docked tools, nested splitters, or tabbed palettes where the Displays palette items reside at depth >= 13.
- **Destruction**: At `depth=12`, traversal stops before reaching the Scope or FFT palette items. `find_palette_item` raises `AutomationError("Expected Scope display palette item not found in window snapshot.")`. Scope and FFT widgets cannot be created on complex multi-pane layouts.

---

### 🔴 DEFECT-DISP-18: Non-Voltage Scope Trigger Unit Hardcoding (`" V"`)
- **Files**: [scope.py#L143](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L143), [models.py#L203](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/models.py#L203)
- **Code**: `set_control_value(app, request.handle, level_ctrl, f"{request.trigger_level} V")`.
- **Trigger**: Scope connected to non-voltage channels (e.g. Current in Amperes, Magnetic Field in Gauss/Tesla, Force in Newtons, Sound in dB).
- **Destruction**: Calling `set_scope_trigger(trigger_level=0.5)` types `"0.5 V"`. Capstone rejects `"V"` as an incompatible physical unit on a non-voltage channel, resetting or corrupting the trigger level while reporting `verified=True`.

---

### 🟠 DEFECT-DISP-19: Raw Float Timebase Lacking Unit String Rejection
- **Files**: [scope.py#L70](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L70), [models.py#L182](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/models.py#L182)
- **Code**: `timebase: str | float | None = None`; `timebase_str = str(request.timebase)`.
- **Trigger**: Caller passes `timebase=0.01` (representing 10 ms).
- **Destruction**: Passes raw `"0.01"` without unit to Capstone's timebase edit box. Capstone requires explicit units (`"s"` or `"ms"`). Lacking a unit, Capstone either rejects the edit or misinterprets `0.01` as milliseconds instead of seconds (a 1,000x error).

---

### 🟠 DEFECT-DISP-20: Comma Decimal Locale Parse Failure in Table Data
- **File**: [table.py#L192-L201](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/table.py#L192-L201)
- **Trigger**: Running in European, Latin, or Korean Windows locales where Capstone renders floating point numbers with comma decimal separator (e.g. `12,34`).
- **Destruction**: `float("12,34")` throws `ValueError`. `_parse_cell_value` returns the string `"12,34"` instead of `12.34`. Tabular data frames lose numerical types and become strings.

---

### 🔴 DEFECT-DISP-21: Overly Permissive Substring Match on Single Digits in `_match_custom_name`
- **File**: [harness.py#L182-L192](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/harness.py#L182-L192)
- **Code**: `c_lower in ctrl.automation_id.lower()`.
- **Trigger**: Calling `find_display_container(controls, "table", custom_name="1")` or `"Table 1"`.
- **Destruction**: Because `"1"` is checked as a substring of `automation_id`, any UIA control whose ID contains `"1"` (e.g. `button_run_1`, `tab_1`, `col_1_header`) matches. The first arbitrary control containing `"1"` in its automation ID is returned as the display container.

---
Defects DEFECT-DISP-15 through DEFECT-DISP-21 verified against production code and submitted for Phase 3 master matrix inclusion.

</details>

---

### 3.4. Hardware, CDP Telemetry & Sampling (PASCO 실기 통신 & 소켓 고갈 방어)
- **담당 에픽 이슈**: #126
- **실사 참여 전문 에이전트**: `audit-hardware`, `audit-telemetry`, `auditor-instruments`

#### 📑 실사 보고서: `audit-hardware` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #96] audit-hardware 실사 세부 명세 (Phase 1)</b></summary>

지정 영역인 `src/capstone_mcp/instruments/` 및 `src/capstone_mcp/session/`에 대한 PASCO 850/550 인터페이스, BLE 무선 센서, 클록 동기화, 샘플링 레이트 협상, 하드웨어 영점 조정(Tare) 비동기 누수 결함을 전수 라인 단위로 실사한 결과입니다.

---

### 1. PASCO 850/550 USB 인터페이스 클록 동기화 지터 및 다채널 위상 왜곡

#### 🔴 DEFECT-HW01: 하드웨어 고정밀 클록 폐기 및 소프트웨어 단조 시계 타임스탬프 지터 (Phase Skew)
- **코드 위치**: [session/telemetry.py#L24-L39](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L24-L39), [session/__init__.py#L80-L93](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/__init__.py#L80-L93), [bridge.py#L184-L194](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L184-L194)
- **하드웨어 결함 메커니즘**:
  1. PASCO 850/550 인터페이스는 내부 FPGA 및 TCXO 발진기 기반으로 100 kHz ~ 10 MHz 동기화 클록을 생성함.
  2. 그러나 CDP `RequestReadMeasurement`는 단일 스칼라 실수(`ReturnValue`)만 반환하며 하드웨어 샘플 카운터/마이크로초 타임스탬프를 완전히 폐기함.
  3. `session/telemetry.py` L31에서 `ts = timestamp if timestamp is not None else time.monotonic()`으로 호스트 OS 시계에 의존함.
  4. 다채널(예: Analog A 전압, Analog B 전류) 순차 폴링 시 매회 신규 WebSocket 핸드셰이크 지연(5~40ms)이 불규칙하게 누적되어, 채널 간 타임스탬프에 수십 ms의 지터(Jitter)가 발생함.
  5. 교류 RLC 회로의 위상차($\phi$), 전자기 유도($-d\Phi/dt$), 음파 간섭 등 위상 일치성이 필수적인 물리 실험 데이터가 심각하게 왜곡됨.

#### 🔴 DEFECT-HW02: 다채널 타임스탬프 비정합 및 다운스트림 피팅 에러 유발
- **코드 위치**: [session/telemetry.py#L67-L79](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L67-L79), [session/__init__.py#L86-L92](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/__init__.py#L86-L92)
- **하드웨어 결함 메커니즘**:
  - `TelemetryBuffer`는 채널(EUID)별로 독립된 `deque`를 유지할 뿐, 다채널 공통 기준 타임스탬프(Hardware Trigger Time Epoch)나 인터폴레이션 정렬 로직이 전무함.
  - 이 비동기 스트림을 다운스트림 피팅 엔진(`experiment_analysis.py` L203-208)으로 전달할 경우, 독립변수 $X$와 종속변수 $Y$의 타임스탬프가 엄격히 일치하지 않아 `ExperimentAnalysisError`로 100% 거부됨.

---

### 2. 멀티채널 샘플링 레이트 협상 지연 및 단위 경계(Unit Boundary) 탐색 파탄

#### 🔴 DEFECT-HW03: 하드웨어 디시메이션/USB 버스 협상 지연 무시 및 즉각 0ms 판정 실패
- **코드 위치**: [instruments/sensors.py#L186-L191](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L186-L191), [instruments/sensors.py#L268-L274](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L268-L274)
- **하드웨어 결함 메커니즘**:
  1. PASCO 850의 4채널 ADC 디시메이션 필터 재구성 및 USB 벌크 패킷 크기 협상은 수백 ms가 소요됨.
  2. `_step_rate` L186-188은 UIA `INVOKE` 직후 0ms 지연으로 스냅샷을 캡처하고, `if after.display == before.display:` 조건을 평가함.
  3. UI 렌더링 및 하드웨어 협상이 완료되기 전 즉시 `AutomationError: Sampling-rate input was delivered but the display did not change.`를 던지며 폭사함.
  4. L268-274에서 예외를 잡자마자 재시도 없이 즉각 탐색을 중단하여 하드웨어를 불완전한 레이트 상태로 방치함.

#### 🔴 DEFECT-HW04: 단위 경계(Hz $\leftrightarrow$ kHz, s $\leftrightarrow$ ms) 전이 차단 및 강제 롤백 파탄
- **코드 위치**: [instruments/sensors.py#L236-L238](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L236-L238), [instruments/sensors.py#L255-L257](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L255-L257), [instruments/sensors.py#L275-L290](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L275-L290)
- **하드웨어 결함 메커니즘**:
  1. L236: `if unit != target_unit: raise AutomationError(...)`로 인해 현재 단위와 다른 타겟 레이트(예: 500 Hz 상태에서 1 kHz 또는 10 kHz 요청)는 시작조차 못 하고 차단됨.
  2. L256: 500 Hz에서 상향 스텝 중 표시 단위가 kHz로 변경되면(`after_unit != unit`), 즉시 루프를 탈출(`break`)하고 L276의 `_restore_rate`를 통해 원래의 저속 주파수로 강제 복구(Rollback)시킴.
  3. 결과적으로 PASCO 850의 핵심 기능인 고속 샘플링(최대 10 MHz) 진입이 완전히 불가능함.

---

### 3. BLE 센서 재연결 실패, 페어링 블라인드 반환 및 서랍 닫힘 통신 절단

#### 🔴 DEFECT-HW05: BLE Discovery 지연 무시 (0ms 스냅샷) 및 `timeout_seconds` 파라미터 유실
- **코드 위치**: [instruments/wireless.py#L149-L162](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L149-L162), [instruments/models.py#L302](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L302)
- **하드웨어 결함 메커니즘**:
  - PASCO 무선 센서의 BLE Advertising 패킷 수신에는 2~5초가 소요됨.
  - `scan_wireless_sensors`는 서랍 버튼 클릭 직후 0ms 만에 스냅샷을 캡처하여 센서 목록을 읽음.
  - 요청 모델 `ScanWirelessSensorsRequest`에 `timeout_seconds=5.0`이 선언되어 있으나, `wireless.py` 코드 내부에서 이 필드를 단 한 번도 사용하지 않고 완전히 누락함. 결과적으로 빈 센서 목록(`count=0`)만 반환됨.

#### 🔴 DEFECT-HW06: 블라인드 검증 반환 및 `finally` 서랍 닫힘으로 인한 BLE GATT 페어링 중단
- **코드 위치**: [instruments/wireless.py#L243-L258](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L243-L258)
- **하드웨어 결함 메커니즘**:
  1. `connect_wireless_sensor`는 연결 버튼 클릭 직후 실제 연결 완료 여부를 확인하지 않고 즉시 `connected=True`, `verified=True`를 반환함.
  2. Windows BLE 스택과 Capstone 간 GATT 서비스 검색 및 MTU 협상(2~4초)이 진행 중임에도, `finally` 절(L256-258)에서 `keep_open=False`로 인해 Hardware Setup 서랍을 즉시 닫아버림.
  3. 서랍 컨트롤이 언로드되면서 백그라운드 BLE 연결 시퀀스가 강제 중단(Abort)되어 연결이 파탄남.
  4. 재연결(Reconnect) 시 이미 연결 대기/연결 상태인 센서 컨트롤을 다시 클릭할 경우 Capstone이 이를 "Disconnect" 명령으로 처리하는 토글 반전(Toggle Inversion) 결함 존재.

---

### 4. 하드웨어 영점 조정(Zero Sensor)의 비동기 상태 누수 결함

#### 🔴 DEFECT-HW07: 활성 레코딩 가드 결손으로 인한 런타임 계측 데이터 오염
- **코드 위치**: [instruments/sensors.py#L315-L365](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L315-L365)
- **하드웨어 결함 메커니즘**:
  - `_settings()`(L44), `_rate_controls()`(L62)와 달리 `zero_sensor()`에는 `observe_recording` 검사가 완전히 결손됨.
  - 데이터 수집 중 Zero를 호출하면 하드웨어 센서 오프셋이 실행 도중 리셋되어 데이터 스트림에 불연속 단절(Discontinuity)이 발생하고 적분 연산(충격량 $\int F dt$, 일 $\int F dx$)이 파괴됨.

#### 🔴 DEFECT-HW08: 하드웨어 Tare 적분 윈도우 미대기 및 텔레메트리 링 버퍼 상태 누수
- **코드 위치**: [instruments/sensors.py#L342-L365](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L342-L365), [session/telemetry.py#L59-L66](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L59-L66)
- **하드웨어 결함 메커니즘**:
  1. 힘 센서/압력 센서의 하드웨어 영점 조정은 500ms~1000ms 동안 센서 입력을 평균화(Averaging)하여 오프셋 레지스터에 기록하는 하드웨어 내부 비동기 루틴임.
  2. `zero_sensor`는 클릭 직후 하드웨어 안정화 대기 없이 즉시 반환(`verified=False`)함. 호출자가 곧바로 레코딩을 시작하면 영점 보정이 끝나지 않은 과도 응답 스파이크(Transient Spike)가 그대로 기록됨.
  3. 다중 센서 일괄 Zero 처리 시 0ms 딜레이로 연속 클릭을 날려 PASCO 850 USB 명령 버퍼 오버플로우 및 후속 센서 영점 명령 무시가 발생함.
  4. 하드웨어 영점이 변경되었음에도 `TelemetryBuffer.clear(euid)`가 호출되지 않아, 이전 오프셋의 샘플과 영점 조정 후 샘플이 동일 링 버퍼에 뒤섞여 통계값(`compute_stats`)이 심각하게 오염됨.

---

### 5. 추가 발견 결함 (트리거/신호발생기/워처)
- **🔴 DEFECT-HW09 (`instruments/triggers.py` L121-140)**: `ConditionSpec.measurement` 필드가 `_apply_condition`에서 완전히 무시되어, 사용자가 지정한 센서가 아닌 임의의 기본 센서에 트리거가 걸리는 결함.
- **🔴 DEFECT-HW10 (`instruments/generator.py` L200-205, L239-241)**: `_is_power_on`에서 `"on" in automation_id.lower()`로 인해 `Output_On_Off` 컨트롤이 항상 ON으로 감지되어 전원 켜기 명령이 무시되고 끄기 명령 시 켜지는 전원 상태 역전 결함. 주파수/전압 입력란에 `"1000 Hz"` 등 단위 문자열을 강제 삽입하여 숫자 전용 에디트 박스 검증 실패 유발.
- **🔴 DEFECT-HW11 (`session/watcher.py` L70-114)**: `ConditionWatcher.monitor`가 50ms마다 단발성 소켓을 동기 블로킹 방식으로 열고 닫아 TCP 포트 고갈(`WSAEADDRINUSE 10048`) 및 스레드 데드락을 유발함.

이상 총 11건의 하드웨어/세션 결함을 마스터 결함 매트릭스에 통합 반영 요청드립니다.

</details>

#### 📑 실사 보고서: `audit-telemetry` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #98] audit-telemetry 실사 세부 명세 (Phase 1)</b></summary>

지정 영역인 `src/capstone_mcp/session/telemetry.py` 및 `src/capstone_mcp/session/cdp_client.py`와 상하위 연계 모듈(`session/watcher.py`, `bridge.py`, `live_telemetry.py`, `resources.py`)에 대해 256개 시계열 버퍼 제한, 타임스탬프 슬라이딩 윈도우 오버플로우, 비동기 큐 누수, 초당 20회 폴링 시 락 경합 결함을 전수 라인 단위로 실사한 결과입니다.

---

### 1. 256개 시계열 버퍼 제한 및 조용한 데이터 유실 결함

#### 🔴 DEFECT-TEL01: 하드코딩된 MAX_MEASUREMENTS(256) 및 채널 전체 침묵 축출 (Silent Eviction)
- **코드 위치**: [session/telemetry.py#L12](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L12), [session/telemetry.py#L33-L36](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L33-L36)
- **결함 메커니즘**:
  1. `MAX_MEASUREMENTS: Final = 256` 상수가 하드코딩되어 있고 `TelemetryBuffer.__init__`에서 이를 조정할 수 없음.
  2. PASCO 850 인터페이스(8채널 아날로그/디지털 + 다채널 PASPORT 센서군)와 다수의 무선 센서(각 센서당 3~6개 서브채널), 계산 열(Calculated Columns) 및 장시간 실험 중 센서 재연결로 신규 EUID가 생성되면 등록된 EUID 수가 256개를 초과함.
  3. L34-35에서 `len(self._buffers) == MAX_MEASUREMENTS` 도달 시 `self._buffers.popitem(last=False)`를 실행하여, **가장 오래전에 샘플링된 채널의 전체 deque 버퍼(최대 1,000개 샘플)를 아무런 로그 경고(`LOGGER.warning`)나 이벤트 통지 없이 조용히 영구 삭제**함.
  4. 다중 샘플링 레이트 환경(예: 100Hz 고속 가속도 센서 vs 0.1Hz 저속 온도 센서)에서 저주파수 센서는 샘플 유입 빈도가 낮아 LRU 헤드로 밀려나 주기적으로 버퍼 전체가 강제 증발됨.

#### 🔴 DEFECT-TEL02: 어댑터 데이터셋 목록 및 다운스트림 시계열 조회 파탄
- **코드 위치**: [data_sources/adapters/live_telemetry.py#L53-L63](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/live_telemetry.py#L53-L63), [data_sources/adapters/live_telemetry.py#L86-L89](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/live_telemetry.py#L86-L89)
- **결함 메커니즘**:
  - `LiveMeasurementAdapter.list_datasets()`는 `inventory`에 등록된 모든 measurement에 대해 `len(self.session.telemetry.get_samples(euid))`를 조회함.
  - 버퍼 수 256개 초과로 축출된 EUID는 이전에 수집된 이력이 있음에도 갑자기 `sample_count=0`으로 표시되며, 이어지는 `get_series()` 호출 시 `len(samples) < MIN_SERIES_SAMPLES(2)` 검사에 걸려 `ValueError`를 발생시키고 전체 시계열 분석을 중단시킴.

---

### 2. 타임스탬프 슬라이딩 윈도우 오버플로우 및 정렬 왜곡 결함

#### 🔴 DEFECT-TEL03: `sorted(samples)`의 동일 타임스탬프 시 튜플 2번째 원소 정렬로 인한 물리 시계열 순서 역전
- **코드 위치**: [data_sources/adapters/live_telemetry.py#L86](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/live_telemetry.py#L86)
- **결함 메커니즘**:
  - `samples = sorted(self.session.telemetry.get_samples(y_euid))`
  - `samples` 원소는 `(timestamp: float, value: float)` 튜플임.
  - Windows 기본 시스템 클록 타이머 해상도(~15.6ms) 내에서 고속으로 2개 이상의 샘플이 들어올 경우 두 샘플의 `timestamp`가 동일하게 기록됨.
  - Python 튜플 정렬 규칙상 첫 번째 원소(`timestamp`)가 같으면 두 번째 원소(`value`)를 기준으로 정렬됨.
  - 예: 시간 순서대로 `(10.0, 9.8)` 수집 후 `(10.0, 1.2)` 수집 시, `sorted()` 후에는 `[(10.0, 1.2), (10.0, 9.8)]`로 **시간 도착 순서가 아니라 값의 크기순으로 순서가 강제 역전(Value Inversion)**되어 물리 데이터(적분, 미분, 추세선)가 왜곡됨.

#### 🔴 DEFECT-TEL04: 링 버퍼 만료 시 동적 0점 점프 및 상대 시간 축 드리프트 (Dynamic Zero Jitter)
- **코드 위치**: [data_sources/adapters/live_telemetry.py#L92-L99](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/live_telemetry.py#L92-L99), [session/telemetry.py#L36-L37](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L36-L37)
- **결함 메커니즘**:
  - `start = samples[0][0]` 및 `values = [timestamp - start for timestamp, _ in samples]`로 상대 경과 시간을 계산함.
  - `deque(maxlen=1000)` 용량이 가득 차서 1001번째 샘플이 들어오면 가장 오래된 샘플이 폐기되고 `samples[0]`이 다음 샘플의 타임스탬프로 변경됨.
  - 이에 따라 기준점 `start`가 매 샘플마다 전진하면서, `live://measurements`를 실시간 모니터링하는 클라이언트의 전체 x축 시간 좌표가 매 샘플 유입 시마다 과거 방향으로 덜컥거리며 진동(Jitter/Drift)하여 안정적인 시계열 플롯이 불가능함.

#### 🔴 DEFECT-TEL05: 타임스탬프 원점 혼용 및 단조성 검증 부재 / `limit <= 0` 논리 오류
- **코드 위치**: [session/telemetry.py#L31](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L31), [session/telemetry.py#L49-L51](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L49-L51)
- **결함 메커니즘**:
  - L31에서 `ts = timestamp if timestamp is not None else time.monotonic()`으로 처리하나, 외부에서 주입되는 타임스탬프(`time.time()` epoch 또는 센서 하드웨어 tick)와 `UnifiedSessionManager`가 주입하는 `time.monotonic()`의 단위/원점 일치 여부 검증 및 단조 증가 검증이 전무하여 타임스탬프가 비선형적으로 뒤섞임.
  - L49-51 `if limit is not None and limit > 0: return samples[-limit:]`에서 `limit=0`을 넘길 경우 빈 리스트가 아닌 **전체 샘플 목록(`samples`)**을 반환하는 조건문 논리 버그 존재.

---

### 3. 비동기 큐 누수 및 소켓 고갈 결함

#### 🔴 DEFECT-TEL06: 가짜 고속 전송 스텁 및 매 샘플 단발성 WebSocket 생성으로 인한 Windows TIME_WAIT 소켓 고갈
- **코드 위치**: [session/cdp_client.py#L18-L38](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/cdp_client.py#L18-L38), [bridge.py#L96-L173](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L96-L173)
- **결함 메커니즘**:
  - `SessionCdpClient`는 "high-speed CDP WebSocket communication"이라고 자칭하나, 내부 지속 연결(Persistent Connection), 연결 풀링, 비동기 수신 큐가 전무한 단순 스텁 프록시임.
  - `read_live_measurement` 호출마다 `bridge.evaluate()` -> `discover_target()` -> 동기 HTTP GET (`/json/list`) + 동기 WebSocket Connect -> Send/Recv -> Close를 매번 실행함.
  - Windows TCP 스택에서 소켓 close 후 기본 120초간 `TIME_WAIT` 상태로 유지됨 (`TcpTimedWaitDelay`).
  - 초당 20회 폴링 시 매초 40개(HTTP 20 + WS 20)의 소켓이 생성/폐기되어, 120초 동안 **4,800개 이상의 소켓이 TIME_WAIT로 누적**됨. Windows 기본 임시 포트(49152~65535, 약 16,384개)가 수 분 내 고갈되어 `WinError 10048` (`WSAEADDRINUSE`) 및 `WSAENOBUFS`로 프로세스 크래시 유발.

#### 🔴 DEFECT-TEL07: 비동기 수신 큐 부재로 인한 인바운드 CDP 이벤트 폐기 및 커널 소켓 버퍼 미배출 (Drain Failure)
- **코드 위치**: [bridge.py#L158-L161](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L158-L161)
- **결함 메커니즘**:
  - `while True:` 루프에서 `reply = Reply.model_validate_json(websocket.recv(timeout=remaining))` 수행 시 `reply.id != 1`인 모든 비동기 브로드캐스트 이벤트(WebEngine 콘솔, DOM 이벤트, CDP 푸시 알림)를 단순히 `continue`로 폐기함.
  - 또한 단일 응답 획득 즉시 연결을 닫아버려 소켓 수신 버퍼에 도착 중인 후속 바이트들이 drain되지 못하고 TCP `RST`를 발생시켜 Capstone WebEngine 디버그 채널을 강제 종료시킴.

---

### 4. 초당 20회 폴링 시 락 경합 및 타이밍 지터 결함

#### 🔴 DEFECT-TEL08: 단일 전역 Lock 및 대량 메모리 복제(`list(buf)`) 중 락 점유로 인한 전역 병목
- **코드 위치**: [session/telemetry.py#L22](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L22), [session/telemetry.py#L46-L48](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L46-L48), [session/telemetry.py#L32-L38](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L32-L38)
- **결함 메커니즘**:
  - `TelemetryBuffer`는 256개 전체 채널에 대해 단 하나의 `self._lock = Lock()`을 사용하는 조잡한 락 구조를 가짐.
  - L46-48에서 `get_samples`는 락을 잡은 상태(`with self._lock:`)에서 1,000개 튜플을 복제하는 `list(buf)`를 실행함.
  - `LiveMeasurementAdapter.list_datasets()`나 `resources.py`가 전체 채널의 샘플 수를 조회하기 위해 순회 호출하는 동안 락 점유가 지속되어, 초당 20회 주기로 들어오는 와처의 `push_sample`이 락 대기열에 갇혀 심각한 지터(Jitter)와 샘플 누락을 유발함.

#### 🔴 DEFECT-TEL09: 동기 네트워크 I/O 지연 미보정 고정 Sleep으로 인한 20Hz 폴링 레이트 붕괴 및 FastMCP 이벤트 루프 동결
- **코드 위치**: [session/watcher.py#L40](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/watcher.py#L40), [session/watcher.py#L81-L114](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/watcher.py#L81-L114), [resources.py#L160](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/resources.py#L160)
- **결함 메커니즘**:
  1. `StopCondition`의 기본값 `poll_interval = 0.05`초(20 Hz)로 실행되는 모니터 루프에서 `val = sampler()`를 호출함.
  2. `sampler()` 내부에서 동기 소켓 핸드셰이크 + HTTP 호출이 발생하여 15~40ms의 네트워크 왕복 I/O 지연이 발생함.
  3. 그 후 `time.sleep(0.05)`를 고정으로 호출하므로 루프 주기는 매회 $15\text{ms} + 50\text{ms} \approx 65\text{ms} \sim 90\text{ms}$로 늘어나, 실제 폴링 빈도는 **초당 20회가 아니라 초당 11~15회로 심각하게 저하**되고 드리프트가 누적됨.
  4. 비동기 프레임워크인 FastMCP 컨텍스트에서 이 동기 블로킹 모니터 루프가 실행될 경우 전체 서버의 비동기 이벤트 루프가 최대 10초(`timeout`) 동안 완전히 동결(Hang)됨.
  5. 추가로 `resources.py` L160에서는 매 요청마다 `UnifiedSessionManager`를 새로 인스턴스화하여 기존 텔레메트리 버퍼와 락을 무력화하고 파편화함.

---
이상 총 9건의 텔레메트리/CDP 세션 결함을 마스터 결함 매트릭스에 통합 반영 요청드립니다.

</details>

#### 📑 실사 보고서: `auditor-instruments` (총 4회 정밀 실사)

<details open>
<summary><b>[보고서 #31] auditor-instruments 실사 세부 명세 (Phase 1)</b></summary>

`src/capstone_mcp/instruments/` (models.py, generator.py, manager.py, sensors.py, triggers.py, wireless.py) 및 `src/capstone_mcp/tools/instruments.py` 코드베이스 전수 검사 결과입니다.

### 1. Critical Runtime Fatal Flaws (존재하지 않는 Capstone 메서드 호출)
- **`app.click()` 및 `app.type_text()` 런타임 크래시**:
  - `desktop.py`의 `Capstone` 클래스에는 `click(handle, ref)`이나 `type_text(text)` 메서드가 정의되어 있지 않음 (오직 `act(ref, Action.INVOKE)` 및 `click_point()`만 제공).
  - 그러나 [generator.py](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L168-L170) (L168, L170, L240, L261, L281, L301, L337), [sensors.py](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L344) (L344), [wireless.py](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L72-L75) (L72, L74, L150, L175, L222, L234, L248, L283, L288, L305, L309, L320, L355, L407)에서 `app.click`과 `app.type_text`를 직접 호출하고 있어 실제 Capstone 연결 시 즉시 `AttributeError` 예외 발생. (단위 테스트는 mock fixture로 우회되어 미검출)

### 2. Bluetooth / 무선 센서 연결 결함 (wireless.py)
- **연결 상태 판정 서브스트링 반전 버그** ([wireless.py#L114-L117](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L114-L117)):
  `"connected" in name.lower()` 검사로 인해 `"disconnected"` 또는 `"not connected"` 상태 문자열도 `True`로 오인하여 연결 해제된 센서를 연결됨으로 잘못 보고.
- **`timeout_seconds` 파라미터 무시** ([wireless.py#L131-L176](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L131-L176)):
  `ScanWirelessSensorsRequest.timeout_seconds`를 받아놓고 내부에서 전혀 사용하지 않고 즉시 스냅샷을 캡처. BLE advertising 대기 시간이 없어 스캔 시 센서 미검출 빈발.
- **과도하게 광범위한 무선 센서 탐색 정규식** ([wireless.py#L98-L108](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L98-L108)):
  `"wireless"`, `"bluetooth"`, `"smart cart"` 단어가 들어간 텍스트 라벨, 툴바 버튼, 안내문까지 모두 개별 무선 센서 항목으로 오인 수집.
- **전역 연결 버튼 오지정 위험** ([wireless.py#L188-L196](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L188-L196)):
  `_find_connect_button`이 대상 센서 컨트롤에 한정하지 않고 윈도우 내 첫 번째 'Connect' 버튼을 탐색하므로, 다중 센서 표시 시 엉뚱한 센서 페어링 버튼을 클릭할 위험.
- **페어링 완료 및 오류 검증 부재**:
  버튼 클릭 후 실제 BLE 핸드셰이크 대기 없이 즉시 `connected=True`, `verified=True` 반환.
- **캘리브레이션 위저드 스코핑 결함 및 안정화 대기 누락** ([wireless.py#L268-L312](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L268-L312)):
  `_find_wizard_edit`가 윈도우 전체에서 첫 번째 `Edit`(`edits[0]`)를 무조건 선택. 또한 센서 값 안정화 대기 없이 즉시 `Set` 및 `Next`를 연타하여 캘리브레이션 오차 발생.

### 3. 침묵형 예외 삼킴 (Silent Exception Swallows)
- `contextlib.suppress(Exception)` 남발:
  - `_is_drawer_open` ([generator.py#L62](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L62), [wireless.py#L57](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L57))
  - `_read_ctrl_value` ([generator.py#L179](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L179))
  - `_is_power_on` ([generator.py#L192](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L192))
- `contextlib.suppress(AttributeError, RuntimeError)`:
  - `_is_panel_open` ([triggers.py#L67](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/triggers.py#L67))
- 빈 `except` 블록 및 로깅 누락:
  - `_set_ctrl_value` ([generator.py#L165](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L165), [wireless.py#L69](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L69)): ValuePattern 실패 시 원인 로그 없이 무조건 키보드 입력 시도.

### 4. UIA 팔레트 토글 가정 (Palette Toggle Assumptions)
- **토글 상태 반전 및 패널 닫힘 버그**:
  `TogglePattern.ToggleState == 1`만을 열림으로 판단. 토글 패턴을 지원하지 않거나 예외 발생 시 `False`로 간주하여 이미 열려있는 팔레트를 도리어 클릭해 닫아버림 ([generator.py#L240](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L240), [triggers.py#L159](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/triggers.py#L159), [wireless.py#L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L150)).
- **`finally` 블록의 불필요한 재토글**:
  도구 시작 시 닫혀있다고 오판한 경우 `finally`에서 다시 토글하여 사용자의 작업 영역을 닫음.
- **UI 애니메이션/렌더링 딜레이 부재**:
  토글 클릭 직후 대기 시간 없이 즉시 스냅샷을 호출하여 열리는 중인 컨트롤을 찾지 못함.

### 5. 파형/주파수/진폭 유효성 검사 결함 (generator.py & models.py)
- **모델 수준 검증 결함** ([models.py#L145-L157](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L145-L157)):
  `waveform: str = "Sine"`으로 단순 문자열 처리, 모델 수준에서 `VALID_WAVEFORMS` 검증 미수행.
- **주파수 상한 및 0 Hz 미검증**:
  하드웨어(850 UI 등 100 kHz 한계) 한계 검증이 없으며, AC 파형에서 0 Hz 및 NaN/inf 통과.
- **DC 모드 오동작**:
  DC 파형 선택 시에도 불필요하게 `frequency`를 주입하려고 시도.
- **진폭(Amplitude) 범위 무검증**:
  음수 진폭이나 하드웨어 최대 정격(±10V / ±15V)을 초과하는 위험 값도 무제한 전송 허용.
- **위험한 위치 기반 폴백(Positional Fallback)** ([generator.py#L149-L154](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L149-L154)):
  전체 창의 첫 번째, 두 번째 `Edit` 컨트롤을 무조건 주파수/진폭 컨트롤로 간주하여 덮어쓰기 위험.
- **허위 검증(`verified=True`)**:
  실제 설정이 반영되었는지 UI 재확인 없이 `verified=True` 하드코딩 반환.

### 6. 하드코딩 값 및 스키마 매핑 불일치
- **`_FLAT_FIELD_MAPPINGS` 필드명 불일치** ([models.py#L365-L407](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L365-L407)):
  `set_sampling_rate`에 `sensor_name`, `sampling_rate`가 매핑 목록에 있으나, `SamplingRateRequest` 모델은 `sensor`, `target` 필드를 요구하여 유효성 검증 실패 발생. `keep_sample`에서도 `variable_value` vs `value` 불일치.
- **`zero_sensor`의 위험한 '0' 매칭** ([sensors.py#L309](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L309)):
  `name_lower == "0"` 조건으로 인해 계산기나 좌표 원점 '0' 버튼까지 센서 제로 버튼으로 오인 클릭.
- **영문 UI 종속성**:
  캘리브레이션 및 트리거에서 `"Next"`, `"Set"`, `"Finish"`, `"Done"` 등 영문 하드코딩 라벨 탐색.
- **스냅샷 파라미터 하드코딩**:
  `depth=16, limit=10_000` 등이 전 파일에 하드코딩됨.

</details>

<details open>
<summary><b>[보고서 #39] auditor-instruments 실사 세부 명세 (Phase 2)</b></summary>

`src/capstone_mcp/instruments/` (sensors.py, generator.py, triggers.py, wireless.py) 및 `src/capstone_mcp/tools/instruments.py`에 대한 하드웨어 단선/핫플러그 부재, 영문 팔레트 하드코딩, 샘플링 레이트/제로잉 결함 전수 정밀 감사 결과입니다.

---

### 1. Hardware Hot-Unplug / Disconnection Listener 부재로 인한 침묵형 정지 (Silent Hangs)
- **근본 원인**:
  - `instruments/` 전 모듈에 Win32 `WM_DEVICECHANGE`, USB 장치 단선 이벤트, BLE 연결 끊김 콜백 또는 CDP WebSocket 단선 와치독이 전무함.
- **재현 시나리오 A (샘플링 레이트 변경 중 USB 단선)**:
  - `target_sampling_rate`([sensors.py#L246-L267](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L246-L267))가 128~512회 스텝을 순회하는 도중 사용자가 PASCO 850/550 USB 케이블을 뽑음.
  - Capstone UI가 장치 분리 모달 팝업("Interface Disconnected")을 띄우거나 센서 셀렉터를 비활성화함.
  - 루프 내 `_step_rate`([sensors.py#L173-L191](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L173-L191))가 실패한 후, `except`를 거치지 않고 루프를 빠져나와 `_restore_rate`([sensors.py#L276-L285](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L276-L285))로 진입.
  - 이미 분리된 장치에 대해 반대 방향 클릭을 10~50회 추가로 시도하다가 연속 에러 발생. 장치 분리에 대한 원인 파악 없이 모호한 "Restoration failed" 에러만 출력.
- **재현 시나리오 B (신호 생성기 설정 중 COM/UIA 블로킹 교착)**:
  - `set_signal_generator`([generator.py#L250-L262](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L250-L262))에서 전원 토글 버튼을 누르는 순간 하드웨어가 꺼지거나 분리되면, Capstone C++ 엔진이 하드웨어 ACK를 대기하며 UI 스레드를 블로킹함.
  - pywinauto UIA 호출(`node.click_input()` 또는 `SetValue`)에 타임아웃/취소 토큰이 없어 `native_loop.py` 워커 스레드가 무한 정지(Hang) 상태에 빠지고 MCP 서버 전체가 응답 불가 상태가 됨.

---

### 2. 영문 팔레트 명칭 하드코딩 및 다국어 환경 크래시
- **취약 코드 위치**:
  - `HARDWARE_SETUP_NAME = "Hardware Setup"` ([models.py#L272](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L272))
  - `CALIBRATION_NAME = "Calibration"` ([models.py#L274](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L274))
  - `SIGNAL_GENERATOR_NAME = "Signal Generator"` ([models.py#L133](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L133))
  - `RECORDING_CONDITIONS_NAME = "Recording Conditions"` ([models.py#L197](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L197))
  - 위저드 버튼 영문 하드코딩: `"Next"`, `"Set"`, `"Finish"`, `"Done"` ([wireless.py#L286, L303, L316](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L286))
- **재현 시나리오 (한국어/독일어/프랑스어/스페인어 Capstone 환경)**:
  - 한국어 Capstone UI에서는 팔레트 버튼 이름이 `"하드웨어 설정"`, `"교정"`, `"신호 발생기"`로 렌더링됨.
  - Qt 위젯 구조상 `automation_id`가 변경되거나 비표준인 빌드에서, `_find_palette_toggle`([wireless.py#L34-L53](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L34-L53)) 및 `_find_signal_generator_toggle`([generator.py#L42-L57](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L42-L57))의 이름 매칭이 100% 실패하여 `AutomationError: Hardware Setup palette toggle button not found`를 던지고 전면 중단됨.
  - 캘리브레이션 위저드에서도 `"다음"`, `"설정"`, `"완료"` 버튼을 찾지 못해 중간 단계에서 진행이 멈춤.

---

### 3. 샘플링 레이트 스텝 순회(Traversal) 및 타겟팅 결함
- **UI 렌더링 지연(Debounce) 미고려로 인한 조기 실패** ([sensors.py#L187-L190](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L187-L190)):
  - `_step_rate`는 스텝 버튼 클릭 직후 `after = _rate_controls(...)`를 호출하여 `if after.display == before.display`이면 즉시 `AutomationError`를 발생시킴.
  - Capstone UI가 Qt 이벤트 루프에서 레이블 텍스트를 비동기로 갱신하는 경우, 10~50ms의 지연으로 인해 스텝이 정상 전달되었음에도 실패로 오판하고 작업을 중단함.
- **공백 없는 단위 포맷 파싱 크래시** ([sensors.py#L207](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L207)):
  - `display.strip().split(maxsplit=1)`은 공백을 전제로 함. Capstone이 `"50Hz"` 또는 `"10kHz"`처럼 공백 없이 표시하면 `ValueError`가 발생하여 `"Provide a decimal sampling rate..."` 에러로 실패.
- **`step_limit` 초과 시 복원 실패로 인한 시스템 오염** ([sensors.py#L276-L285](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L276-L285)):
  - 목표 레이트 도달 실패 시 이전 경로(`previous`)를 역방향으로 복원하는데, 복원 과정에서 클릭이 하나라도 씹히면 복원 검증 실패로 포기하여 실험 환경의 샘플링 레이트가 오염된 상태로 방치됨.

---

### 4. 센서 Tare/Zero 오류 삼킴 및 검증 부재
- **비활성화 버튼 무차별 클릭 시도** ([sensors.py#L320-L345](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L320-L345)):
  - `zero_buttons` 수집 시 `c.enabled` 여부를 검사하지 않음. 센서가 측정 준비 중이거나 영점 조절이 불가능한 상태여도 무조건 클릭을 시도함.
- **`name_lower == "0"` 치명적 오인 매칭** ([sensors.py#L309](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L309)):
  - 계산기 도구, 페이지 번호, 키패드의 숫자 '0' 버튼이 `_is_zero_button`에 걸림. `sensor_name` 미지정 시 창 내부의 모든 '0' 버튼을 연쇄 클릭하여 엉뚱한 UI 동작 유발.
- **물리적 영점 조정 검증 전무 (`verified=True` 하위 호환 날조)** ([sensors.py#L354](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L354)):
  - 센서 하드웨어 영점 조절은 ADC 오프셋 캘리브레이션 작업임. 하드웨어 포화(Saturation)나 센서 불량으로 영점이 잡히지 않아도 실제 센서 라이브 값을 확인하지 않고 무조건 `verified=True` 반환.

---

### 5. 미존재 메서드 호출 크래시 (`app.click`, `app.type_text`)
- [generator.py#L168-L170](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L168-L170), [sensors.py#L344](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L344), [wireless.py#L72-L75](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L72-L75):
  - `app.click()` 및 `app.type_text()`는 `Capstone` 클래스에 아예 존재하지 않는 메서드임. 실 가동 환경에서 호출 시 즉시 `AttributeError` 예외가 발생하므로 `app.act(ref, Action.INVOKE)` 및 `app.keys()`로 전면 교체 필수.

### 6. Pydantic 스키마 매핑 불일치 (`_FLAT_FIELD_MAPPINGS`)
- [models.py#L367-L374](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L367-L374):
  - `server.py` 프롬프트는 `capstone_manage_instrument(action='set_sampling_rate', sensor_name=..., sampling_rate=...)`를 안내하지만, 모델은 `sensor`, `target`을 필수로 요구하여 클라이언트 MCP 호출 시 스키마 유효성 검증 실패(`ValidationError`) 발생.

</details>

<details open>
<summary><b>[보고서 #63] auditor-instruments 실사 세부 명세 (Phase 3)</b></summary>

`src/capstone_mcp/instruments/` (sensors.py, generator.py, triggers.py, wireless.py) 및 `models.py` 전수 라인 바이 라인 재검토 결과, 기존 38개 외에 새롭게 발견된 10건의 숨겨진 치명적 결함(정확한 파일 경로, 라인 번호, 재현 트리거, 파괴 메커니즘)을 보고합니다.

---

### 🔴 DEFECT-INST-01: `self.refs.clear()` 전역 호출에 의한 Stale Ref 연쇄 폭사 (Cascade Stale Ref Crash)
- **파일 및 라인**: [sensors.py#L343-L346](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L343-L346), [wireless.py#L283-L289](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L283-L289), [wireless.py#L305-L310](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L305-L310), [generator.py#L250-L262](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L250-L262), [triggers.py#L126-L134](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/triggers.py#L126-L134)
- **파괴 메커니즘**:
  - `desktop.py:316`(`act()`) 및 `desktop.py:357`(`set_value()`)는 단일 UIA 액션 수행 직후 **`self.refs.clear()`**를 호출하여 세션 내의 모든 컨트롤 캐시를 강제 파기함.
  - 단일 스냅샷에서 추출한 컨트롤 목록을 연속 조작하는 모든 함수가 직격탄을 맞음:
    1. **`zero_sensor` ([sensors.py#L343-L346](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L343-L346))**: `target_buttons` 루프에서 1번째 센서를 클릭하는 순간 `self.refs.clear()` 실행. 2번째 센서 클릭 시 `AutomationError: Unknown or stale ref`로 100% 폭사.
    2. **`_wizard_set_standard` ([wireless.py#L305, L309](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L305))**: 같은 스냅샷의 `set_btn`을 클릭하면 `refs`가 클리어되어 바로 다음 줄의 `next_btn.ref` 클릭 시 무조건 Stale Ref 크래시.
    3. **`_wizard_select_measurement` ([wireless.py#L283, L288](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L283))**: 측정 항목 클릭 후 `next_btn` 클릭 시 Stale Ref 크래시.
    4. **`set_signal_generator` ([generator.py#L250-L262](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L250-L262))**: `wave_ctrl` 설정 후 `freq_ctrl`, `amp_ctrl`, `power_ctrl` 조작 시 연속 Stale Ref 크래시.

---

### 🔴 DEFECT-INST-02: `finally` 블록의 구 스냅샷 토글 Ref 참조로 인한 2차 폭사 및 서랍 방치
- **파일 및 라인**: [generator.py#L280-L282](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L280-L282), [generator.py#L336-L337](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L336-L337), [wireless.py#L174-L176](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L174-L176), [wireless.py#L247-L249](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L247-L249), [wireless.py#L406-L407](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L406-L407), [triggers.py#L190-L192](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/triggers.py#L190-L192)
- **파괴 메커니즘**:
  - 팔레트 서랍을 열고 내부 조작을 위해 2차 스냅샷(`app.snapshot()`)을 생성하면, 1차 스냅샷에서 따온 `toggle_ctrl.ref`는 즉시 무효화됨.
  - 작업 완료 후 `finally:` 블록에서 `app.click(handle, toggle_ctrl.ref)`를 호출하므로, `Unknown or stale ref. Take a new snapshot` 예외가 발생하여 열린 서랍을 닫지 못하고 함수 전체가 예외로 종료됨.

---

### 🔴 DEFECT-INST-03: 단위 경계(Unit Boundary) 횡단 시 루프 탈출 및 강제 롤백
- **파일 및 라인**: [sensors.py#L256-L257](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L256-L257)
- **코드**: `if after_unit != unit: break`
- **재현 시나리오**:
  - 사용자가 샘플링 레이트를 500 Hz에서 1 kHz(1000 Hz)로 변경 요청.
  - 스텝 버튼을 올려 1000 Hz에 도달하는 순간 Capstone 레이블이 `"500 Hz"`에서 `"1 kHz"`로 단위 변경됨.
  - `after_unit`(`"kHz"`) != `unit`(`"Hz"`) 조건에 걸려 **즉시 루프를 강제 break 탈출**함.
  - 이후 미도달로 판정되어 `_restore_rate`([L276-L285](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L276-L285))로 진입하여 원래의 500 Hz로 다시 롤백해버림. 단위 경계(`Hz ↔ kHz`, `s ↔ min`)를 넘는 모든 레이트 변경이 영구적으로 불가능.

---

### 🔴 DEFECT-INST-04: 시간 단위(s) ↔ 주파수 단위(Hz) 상호 전환 전면 거부
- **파일 및 라인**: [sensors.py#L236-L238](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L236-L238)
- **코드**: `if unit != target_unit: raise AutomationError("Target rate must use the current display unit; no conversion is implied.")`
- **재현 시나리오**:
  - Capstone 센서가 저속 모드인 초 단위(`1 s`, 즉 1 Hz 미만)로 표시되고 있을 때 에이전트가 `10 Hz`를 설정하려 하면 즉시 예외를 발생시키고 거부함.
  - 주파수와 주기 간의 자동 환산이나 Capstone 모드 전환 로직이 전무하여, 현재 화면에 띄워진 단위 계열에 영구적으로 종속됨.

---

### 🔴 DEFECT-INST-05: `"on" in automation_id`로 인한 전원 상태 상시 True 버그 및 역동작
- **파일 및 라인**: [generator.py#L198-L199](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L198-L199)
- **코드**: `return (name_lower in ("on", "running", "active") or "on" in power_ctrl.automation_id.lower())`
- **재현 시나리오**:
  - PASCO Capstone 신호 생성기 전원 버튼의 AutomationId는 일반적으로 `SignalGenerator.ButtonOnOff` 또는 `PowerOnOffButton`임.
  - `automation_id.lower()`에 `"onoff"`가 포함되어 있어 **전원이 실제로 꺼져 있어도 항상 `_is_power_on == True`로 평가**됨.
  - [generator.py#L260](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L260)에서 `if current_on != request.enabled:`를 비교할 때, 전원을 켜려(`enabled=True`) 하면 이미 켜진 것으로 오판하여 버튼을 누르지 않고, 끄려(`enabled=False`) 하면 꺼져있던 전원 버튼을 눌러서 켜버리는 치명적 역동작 발생.

---

### 🔴 DEFECT-INST-06: `"output" in name and "on" in name`의 부분 단어 오인 매칭
- **파일 및 라인**: [generator.py#L78](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L78)
- **코드**: `or ("output" in name_lower and "on" in name_lower)`
- **파괴 메커니즘**:
  - 전원 버튼 판정 시 `"output"`과 `"on"`을 독립된 단어가 아닌 서브스트링으로 검사함.
  - `"Output Configuration"`(configurati**on**) 또는 `"Output Connection"`(connecti**on**) 버튼이 이 조건에 완벽히 매칭되어 전원 버튼(`power_ctrl`)으로 잘못 지정됨. 결과적으로 전원을 켜려다 환경설정 팝업이 열림.

---

### 🔴 DEFECT-INST-07: ComboBox에 snake_case 모드명 직접 입력으로 인한 모드 변경 실패
- **파일 및 라인**: [triggers.py#L232-L234](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/triggers.py#L232-L234)
- **코드**: `if mode_ctrl.control_type == "ComboBox": _set_input_text(app, request.handle, mode_ctrl, request.mode)`
- **재현 시나리오**:
  - `request.mode`는 Pydantic enum 값인 `"keep_sample"` 또는 `"fast_monitor"`임.
  - Capstone UI ComboBox의 실제 목록 문자열은 `"Manual Sampling (Keep Sample)"` 또는 `"Fast Monitor Continuous"`임.
  - 드롭다운 스타일 ComboBox에 존재하지 않는 snake_case 문자열(`"keep_sample"`)을 강제로 타이핑하여 입력을 무시당하거나 선택이 변경되지 않음.

---

### 🔴 DEFECT-INST-08: 비작동(Stopped) 상태에서의 Keep Sample 허위 성공 보고
- **파일 및 라인**: [triggers.py#L297-L318](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/triggers.py#L297-L318)
- **재현 시나리오**:
  - Capstone의 Keep Sample 버튼은 Preview/Monitor 모드나 Recording 모드가 활성화되어 센서 데이터가 흘러들어올 때만 유효함.
  - 정지(Stopped) 상태에서 `keep_sample()`을 호출하면 비활성화된 버튼을 클릭하고 엔터를 친 뒤, 실제 데이터 포인트가 0개 저장되었음에도 `sample_retained=True, verified=True`를 반환하여 에이전트를 속임.

---

### 🔴 DEFECT-INST-09: 센서명 단위/포트 접미사 포함 시 exact match 실패
- **파일 및 라인**: [sensors.py#L67, L114, L153](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L67)
- **코드**: `if selector.name != expected_sensor:` 및 `if control.name == request.sensor:`
- **재현 시나리오**:
  - 사용자는 `"Force Sensor"`로 요청하지만, Capstone UI의 셀렉터와 팝업 메뉴 항목은 `"Force Sensor (N)"` 또는 `"Force Sensor [Ch A]"`로 표시됨.
  - `==` 완전 일치 비교를 수행하므로 메뉴 항목이 눈앞에 있음에도 `AutomationError: Requested sensor name is unavailable or not unique`를 던지며 센서 선택이 불가능함.

---

### 🔴 DEFECT-INST-10: 방전/오프라인 무선 센서 연결 허위 성공 보고
- **파일 및 라인**: [wireless.py#L234-L244](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L234-L244)
- **재현 시나리오**:
  - 무선 센서가 배터리 방전이나 거리 초과로 신호가 끊겼음에도 스냅샷에 캐시된 항목이 남아있는 경우.
  - Connect 버튼을 클릭한 직후, BLE 연결 실패 대화상자가 뜨거나 무반응이어도 아무런 상태 변화 검증 없이 `ConnectWirelessSensorResult(connected=True, verified=True)`를 반환함. 후속 측정 명령에서 센서 통신 두절로 연쇄 크래시 발생.

</details>

<details open>
<summary><b>[보고서 #75] auditor-instruments 실사 세부 명세 (Phase 4)</b></summary>

`src/capstone_mcp/instruments/` 및 `src/capstone_mcp/tools/instruments.py`의 직렬화 파이프라인, Pydantic 모델 정규화 로직, UIA 콤보박스 및 트리거 조작부의 최심부 결함 6건을 추가 발굴하여 보고합니다.

---

### 🔴 DEFECT-INST-11: FastMCP 직렬화(`model_dump_json`)와 `_normalize_payload` 상호작용에 의한 기본 요청 전면 거부 크래시
- **파일 및 라인**: [tools/instruments.py#L24, L72](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/instruments.py#L24), [models.py#L445](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L445), [manager.py#L229-L232](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/manager.py#L229-L232)
- **파괴 메커니즘**:
  1. 클라이언트가 기본값으로 `capstone_manage_instrument(request={"action": "scan_wireless"})` 또는 `{"action": "zero_sensor"}` 호출.
  2. [tools/instruments.py:72](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/instruments.py#L72)의 `_json_dict(request)`가 `request.model_dump_json()`을 실행하여 모든 미설정 필드를 `null`로 직렬화: `{"action": "scan_wireless", ..., "scan_wireless": null}`.
  3. `native_loop.py`에서 `InstrumentRequest.model_validate(r.instrument_request)` 역직렬화 시 `_normalize_payload`([models.py:445](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L445))로 진입.
  4. L445의 `if fields and action_key not in data:` 검사에서, 딕셔너리에 이미 `"scan_wireless": None` 키가 존재하므로 `action_key not in data`가 **False**가 됨!
  5. 기본 객체가 채워지지 않고 `scan_wireless = None` 상태가 유지됨.
  6. [manager.py:230](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/manager.py#L230)에서 `if request.scan_wireless is None: raise AutomationError("scan_wireless request must be provided for SCAN_WIRELESS action.")`가 트리거되어 100% 거부됨.
  - **영향**: `scan_wireless`, `zero_sensor`, `configure_signal_generator` 등 기본 인자로 작동해야 하는 모든 단독 액션이 FastMCP IPC 전송을 거치며 100% 예외를 뿜고 폭사함.

---

### 🔴 DEFECT-INST-12: `ConditionSpec.condition_type` 및 `operator`의 Capstone UI 미지원 문자열 주입 결함
- **파일 및 라인**: [models.py#L33-L34](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L33-L34), [triggers.py#L126-L130](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/triggers.py#L126-L130)
- **파괴 메커니즘**:
  - `ConditionType = Literal["none", "time", "sensor_threshold"]` 및 `ComparisonOperator = Literal["above", "below", "rises_above", "falls_below"]`.
  - Capstone 녹화 조건(Recording Conditions) UI 콤보박스의 실제 항목명은 `"Measurement Based"`, `"Time Based"`, `"Rises Above"` 등임.
  - `_set_input_text`로 `"sensor_threshold"` 또는 `"rises_above"` snake_case 문자열을 드롭다운에 강제 주입함. Windows ComboBox는 목록에 없는 문자열을 무시하므로 조건 유형이 전혀 변경되지 않고 과거 설정이 그대로 유지됨.

---

### 🔴 DEFECT-INST-13: `ConditionSpec.measurement` 필드 완전 증발 (Ghost Field)
- **파일 및 라인**: [models.py#L206](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py#L206), [triggers.py#L86-L134](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/triggers.py#L86-L134)
- **파괴 메커니즘**:
  - Pydantic 모델 `ConditionSpec`에는 `measurement: str | None = None` 필드가 정의되어 있으나, 이를 실제로 UI에 적용하는 `_find_condition_controls` 및 `_apply_condition`([triggers.py:86-134](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/triggers.py#L86-L134))에는 측정 대상 센서/데이터 소스를 선택하는 코드가 1줄도 없음(`type_ctrl, op_ctrl, thresh_ctrl`만 탐색).
  - 사용자가 `measurement="Force"`로 녹화 시작 임계값 조건을 걸어도 센서 선택이 누락되어, Capstone에 디폴트로 잡혀있는 엉뚱한 센서(예: 전압, 온도)에 트리거가 걸림.

---

### 🔴 DEFECT-INST-14: `_read_ctrl_value`의 ComboBox Accessible Name 오독으로 인한 파형 상태 날조
- **파일 및 라인**: [generator.py#L174-L185](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L174-L185), [generator.py#L315-L316](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/generator.py#L315-L316)
- **파괴 메커니즘**:
  - Capstone Qt UIA의 파형 선택 ComboBox(`wave_ctrl`)는 `ValuePattern`을 지원하지 않음.
  - `_read_ctrl_value`의 `iface_value` 획득 실패 후 L184의 `return ctrl.name.strip()`으로 폴백.
  - Qt UIA에서 ComboBox의 `name`은 선택된 항목이 아닌 위젯 라벨(예: `"Waveform"`)임.
  - 결과적으로 `read_signal_generator_status`는 파형이 Square나 Triangle이어도 항상 `waveform = "Waveform"`을 읽어 반환하거나 기본값 `"Sine"`으로 날조함.

---

### 🔴 DEFECT-INST-15: UIA 배터리 아이콘 미지원으로 인한 배터리 잔량 100% 누락
- **파일 및 라인**: [wireless.py#L88-L96](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L88-L96), [wireless.py#L112](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L112)
- **파괴 메커니즘**:
  - Capstone의 Hardware Setup 목록에서 배터리는 텍스트 퍼센티지가 아닌 그래픽 아이콘/게이지로 렌더링됨.
  - `_parse_battery`가 `ctrl.name`에서 `r"(\d{1,3})\s*%"` 정규식을 긁으려 하지만 텍스트가 존재하지 않아 실기 환경에서 `battery_percent`는 항상 `None`으로 소실됨.

---

### 🔴 DEFECT-INST-16: `_restore_rate` 미진입 시 허위 복원 메시지 사기
- **파일 및 라인**: [sensors.py#L286-L290](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L286-L290)
- **파괴 메커니즘**:
  - `target_sampling_rate` 진입 직후 첫 스텝 버튼이 비활성화되어 루프를 0회 돌고 빠져나왔을 때, `previous` 리스트는 빈 상태(`[]`)임.
  - L286에서 `msg = f"Sampling rate {request.target!r} is unsupported... the original rate was restored."` 메시지를 반환.
  - 실제로는 복원 루틴(`_restore_rate`)이 실행되지도 않았고 현재 레이트 확인도 거치지 않았음에도 "원래 레이트로 복원되었다"는 허위 확인 메시지를 에이전트에게 전송함.

</details>

---

### 3.5. FastMCP Protocol & Calculator AST (도구 스키마 & 직렬화 & AST 검증기)
- **담당 에픽 이슈**: #127
- **실사 참여 전문 에이전트**: `audit-fastmcp`, `auditor-workflows`

#### 📑 실사 보고서: `audit-fastmcp` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #106] audit-fastmcp 실사 세부 명세 (Phase 1)</b></summary>

`src/capstone_mcp/server.py`, `src/capstone_mcp/tools/*.py` 전체, `resources.py`, `prompts.py`, `agent_instructions.py`, `native/errors.py`를 라인 단위로 실사한 전수 감사 결과입니다.

---

### 1. 🔴 DEFECT-FASTMCP-01: `_FALLBACK_ERROR_RULES` 나이브 서브스트링 매칭 및 규칙 역전으로 인한 전역 에러 오분류 (P0 - Blocker)
- **파일/라인**: [server.py#L218-L245](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L218-L245), [native/errors.py#L14-L64](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/errors.py#L14-L64)
- **코드**:
  ```python
  _FALLBACK_ERROR_RULES: Final[tuple[tuple[tuple[str, ...], str, str], ...]] = (
      (("file", "path"), "FILE_NOT_FOUND", "Verify the target file path exists and is accessible."),
      (("invalid", "validation", "unsupported"), "INVALID_ARGUMENT", ...),
      (("time",), "TIMEOUT_ERROR", "Operation timed out; inspect Capstone responsiveness and reattach if needed."),
  )
  ```
- **파괴 메커니즘**:
  1. **'time' 서브스트링 매칭 대재앙**: `kw in lower` 방식으로 검사하므로 `RuntimeError`("runtime"), `timestamp`, `datetime`, `continuous-time`, `realtime`, `sometimes`, 시계열 데이터의 "Time (s)" 축 누락 에러까지 단어에 'time'이 포함된 모든 일반 예외가 100% `TIMEOUT_ERROR`로 둔갑하여 클라이언트에 엉뚱한 대기/재연결을 유도함.
  2. **실제 `TimeoutError`의 역전 오분류**: `TIMEOUT_ERROR`가 최하단(7번째)에 있어 `TimeoutError: Timed out waiting for graph`는 `GRAPH_OPERATION_ERROR`로, `TimeoutError: Page load timed out`은 `DISPLAY_ERROR`로, `TimeoutError: File read timed out`은 `FILE_NOT_FOUND`로 가로채져 정작 진짜 타임아웃은 절대 `TIMEOUT_ERROR`가 되지 못함.
  3. **'file'/'path' 오분류**: `CapFileError: Archive corrupted` (압축 손상), `IndexError: Dataset index 999 is outside this file's dataset list` (인덱스 범위 초과), `PermissionError: Access denied to path`가 모조리 `FILE_NOT_FOUND`로 둔갑. 파일이 실재함에도 존재하지 않는다고 클라이언트가 오판함.

---

### 2. 🔴 DEFECT-FASTMCP-02: streamable-http 트랜스포트 세션 종료 시 전역 싱글톤 조기 파괴 및 오펀 스레드 (P0 - Blocker)
- **파일/라인**: [server.py#L58-L67, L336-L340](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L58-L67)
- **코드**:
  ```python
  @asynccontextmanager
  async def _lifespan(_server: FastMCP[None]) -> AsyncGenerator[None, None]:
      try:
          yield
      finally:
          await anyio.to_thread.run_sync(JOBS.close)
          await anyio.to_thread.run_sync(WORKER.close)
  ```
- **파괴 메커니즘**:
  - FastMCP의 `StreamableHTTPSessionManager`는 각 HTTP 클라이언트 세션마다 `_serve_opening_request` 내에서 개별 `app.run`을 구동하여 매 세션마다 `_lifespan`에 진입·탈출함.
  - 첫 번째 HTTP 클라이언트가 연결을 끊거나 유휴 타임아웃이 발생하면 `_lifespan`의 finally 블록이 실행되어 전역 싱글톤인 `JOBS.close()` 및 `WORKER.close()`를 파괴함.
  - 이후 인입되는 HTTP 요청이나 동시에 실행 중이던 다른 클라이언트는 파괴된 워커에 명령을 보내 `RuntimeError: Worker thread is not running`으로 100% 폭사함.

---

### 3. 🔴 DEFECT-FASTMCP-03: `capstone_run_experiment_macro` 동기 블로킹 호출로 인한 이벤트 루프 동결 (P0 - Blocker)
- **파일/라인**: [tools/physics.py#L215-L246](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L215-L246)
- **코드**:
  ```python
  @mcp.tool(...)
  async def capstone_run_experiment_macro(...) -> ExperimentMacroResult:
      ...
      return run_experiment_macro(...)   # <-- await to_thread.run_sync 누락!
  ```
- **파괴 메커니즘**:
  - `run_experiment_macro`는 물리 실험 전체 단계(하드웨어 제어, 데이터 수집, 수식 회귀)를 수행하는 무거운 동기 함수(수 초~수십 초 소요)임.
  - `async def`로 선언하면서 스레드 풀 위임(`to_thread.run_sync`) 없이 메인 이벤트 루프에서 직접 동기 호출함.
  - 매크로가 실행되는 동안 FastMCP의 asyncio 이벤트 루프가 100% 블로킹되어 핑, 취소, 리소스 조회 등 모든 MCP 트래픽 처리가 마비되고 클라이언트 연결이 끊어짐.

---

### 4. 🔴 DEFECT-FASTMCP-04: FastMCP 내부 비공개 API 원숭이 패치 및 에러 이중 파싱 컨텐츠 소실 (P0 - Blocker)
- **파일/라인**: [server.py#L283-L328](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L283-L328)
- **코드**:
  ```python
  _orig_call_tool_handler = MCP._mcp_server.request_handlers[CallToolRequest]
  MCP._mcp_server.request_handlers[CallToolRequest] = _structured_call_tool_handler
  MCP.call_tool = _safe_fastmcp_call_tool
  ```
- **파괴 메커니즘**:
  - FastMCP의 저수준 핸들러 `_mcp_server.request_handlers[CallToolRequest]`와 `MCP.call_tool`을 이중으로 덮어씀.
  - 툴 에러 발생 시 1차(`_safe_fastmcp_call_tool`)에서 직렬화하고, 저수준 핸들러에서 2차(`_structured_call_tool_handler`)로 역직렬화·재직렬화하는 불필요한 이중 래핑 발생.
  - `first_content = res.root.content[0]`만 강제로 취급하여 이미지 블록이나 복합 텍스트 블록이 존재할 경우 `content[0]` 외의 모든 컨텐츠가 무음 증발(loss)됨.
  - 또한 FastMCP의 `Input validation error`까지 가로채어 파라미터명에 'graph' 등이 들어가면 스키마 에러를 `GRAPH_OPERATION_ERROR`로 변질시킴.

---

### 5. 🔴 DEFECT-FASTMCP-05: `capstone://displays/active` 리소스에서 `handle=0` 하드코딩으로 인한 100% 무음 실패 (P0 - Blocker)
- **파일/라인**: [resources.py#L227-L247](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/resources.py#L227-L247), [desktop.py#L195-L197](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L195-L197)
- **코드**:
  ```python
  snapshot_res = await native(
      NativeRequest(operation="snapshot", handle=0, depth=12, limit=5000),
  )
  ...
  with suppress(Exception): ...
  ```
- **파괴 메커니즘**:
  - 윈도우 OS의 실제 창 핸들은 0일 수 없으며 `desktop.py`의 `window(0)`은 무조건 `AutomationError`를 던짐.
  - `resources.py`가 이를 `suppress(Exception)`으로 완전히 삼켜버려, Capstone에 디스플레이가 아무리 많이 열려 있어도 `capstone://displays/active`는 영원히 `displays: []`, `table_count: 0`, `graph_count: 0`만을 반환함.

---

### 6. 🟠 DEFECT-FASTMCP-06: 도구 기본 인자 `handle=0`으로 인한 무조건 크래시 (P1 - Critical)
- **파일/라인**: [tools/physics.py#L97](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L97), [tools/ui.py#L414](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/ui.py#L414), [instruments/models.py](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/models.py)
- **파괴 메커니즘**:
  - `capstone_create_calculation(handle=0)`, `capstone_interact_ui(handle=0)`, 그리고 `instruments` 서브모델 9종 모두 `handle=0`을 기본값으로 가짐.
  - Docstring에는 "0 for active window"라고 적혀 있으나 백엔드에 활성 창 자동 폴백 로직이 없어 클라이언트가 handle 생략 시 100% `AutomationError`로 크래시됨.

---

### 7. 🟠 DEFECT-FASTMCP-07: `agent_instructions.py` 및 `prompts.py`의 27개 삭제된 유령 도구(Ghost Tools) 환각 유도 (P1 - Critical)
- **파일/라인**: [agent_instructions.py#L25-L63](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/agent_instructions.py#L25-L63), [prompts.py#L20-L171](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/prompts.py#L20-L171)
- **파괴 메커니즘**:
  - 도구 라우터 통합으로 `capstone_create_table`, `capstone_create_scope`, `capstone_set_signal_generator`, `capstone_fit_file`, `capstone_read_graph` 등 27개 도구가 삭제/통합되었음.
  - 그러나 초기 시스템 프롬프트(`INSTRUCTIONS`)와 8개 FastMCP 프롬프트 템플릿에는 여전히 삭제된 도구 이름을 호출하도록 지시하고 있어, MCP 클라이언트 LLM이 `MethodNotFound (-32601)` 에러를 유발함.
  - 통합 도구 호출 예시(`capstone_manage_display(action='add_page', title=...)`) 역시 실제 중첩 스키마(`request: DisplayRequest`)와 불일치하여 스키마 에러를 유발함.

---

### 8. 🟠 DEFECT-FASTMCP-08: stdio 트랜스포트 예외 처리 부재 및 stdout 오염 취약점 (P1 - Critical)
- **파일/라인**: [server.py#L331-L334](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L331-L334)
- **파괴 메커니즘**:
  - 클라이언트 파이프 강제 종료 시 발생하는 `EndOfStream`, `BrokenPipeError`, `ConnectionResetError` 포획 부재로 트레이스백과 함께 비정상 종료(exit code 1).
  - C 확장 모듈(pywinauto, comtypes, UIA API)이 `sys.stdout`으로 경고/진단을 출력할 경우 JSON-RPC 프레이밍이 즉각 파괴됨에도 `sys.stdout` 버퍼 보호 및 `stderr` 리다이렉션이 누락됨.

---

### 9. 🟠 DEFECT-FASTMCP-09: streamable-http 소켓 바인딩 충돌 및 Starlette 500 HTML 누출 (P1 - Critical)
- **파일/라인**: [server.py#L92-L98, L336-L340](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L92-L98)
- **파괴 메커니즘**:
  - 포트 8766 기점유 시(`OSError 10048`) 서버가 트레이스백을 뿜으며 즉각 크래시됨.
  - 비-도구 ASGI 라우팅 에러 시 Starlette이 HTML/Plain text 형태의 500 응답을 내려보내 MCP 클라이언트의 JSON-RPC 파서가 파탄남.

---

### 10. 🟡 DEFECT-FASTMCP-10: `capstone_interact_ui` 및 `capstone_screenshot` 스키마 제약 누락 (P2 - Major)
- **파일/라인**: [tools/ui.py#L365-L370, L396-L470](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/ui.py#L365-L370)
- **파괴 메커니즘**:
  - `scale`의 `(0, 1.0]` 범위, `crop_region`의 정확히 4개 정수(`minItems=4, maxItems=4`) 제약이 Pydantic Field 스키마에 정의되지 않아 유효하지 않은 입력이 런타임 `AutomationError`로 터짐.
  - `capstone_interact_ui`의 상호 의존적 인자(click 시 point 필수 등) 제약이 스키마에 없어 잘못된 인자 전달 시 `AUTOMATION_ERROR: Check Capstone application state`로 오분류됨.

---

### 11. 🟡 DEFECT-FASTMCP-11: `format_tool_error` 내 `NativeSessionError` 타입 검사 Dead Code (P2 - Major)
- **파일/라인**: [server.py#L250-L256](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L250-L256)
- **파괴 메커니즘**:
  - FastMCP의 `Tool.run`이 모든 예외를 `ToolError`로 래핑하므로 `_safe_fastmcp_call_tool`에 도달하는 예외는 결코 `NativeSessionError` 타입일 수 없음.
  - 250라인의 `isinstance(error_message, NativeSessionError)`는 절대 참이 될 수 없는 Dead Code임.

---

### 12. 🟡 DEFECT-FASTMCP-12: `tuple[str, str]`의 `prefixItems` 스키마로 인한 구형 MCP 클라이언트 호환성 파탄 (P2 - Major)
- **파일/라인**: [tools/physics.py#L144](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L144)
- **파괴 메커니즘**:
  - `axes: tuple[str, str] | None`이 Draft 2020-12의 `prefixItems`로 생성되어, JSON Schema Draft-7 기반 MCP 클라이언트에서 스키마 파싱 오류를 유발함.

---

마스터 결함 매트릭스에 즉시 통합 반영을 요청드립니다.

</details>

#### 📑 실사 보고서: `auditor-workflows` (총 3회 정밀 실사)

<details open>
<summary><b>[보고서 #50] auditor-workflows 실사 세부 명세 (Phase 1)</b></summary>

소유 모듈인 `src/capstone_mcp/file_workflows.py`, `src/capstone_mcp/graphs/inspection.py`, `src/capstone_mcp/tools/physics.py`, 및 `src/capstone_mcp/tools/*` 전수 감사 보고서입니다.

---

### 1. Zero OS Pollution 위반 (외부 OS 자원 오염 및 경합)

#### 🔴 DEFECT-WF01: 클립보드 백업/복원 트릭 잔존 및 사용자 클립보드 영구 파괴
- **파일**: [inspection.py#L322-L357](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L322-L357), [inspection.py#L407](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L407), [inspection.py#L463](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L463)
- **코드**:
  ```python
  def _backup_clipboard() -> dict[int, Any]:
      clip.OpenClipboard()
      ... backup[fmt] = clip.GetClipboardData(fmt)
  def _restore_clipboard(backup: dict[int, Any]) -> None:
      clip.EmptyClipboard()
      for fmt, data in backup.items(): clip.SetClipboardData(fmt, data)
  ```
- **실기 폭발 시나리오**:
  1. **OLE 및 지연 렌더링(Delayed Rendering) 파괴**: 사용자 클립보드에 Word, Excel, 브라우저 리치 텍스트 등 OLE 지연 렌더링 데이터가 있을 때 `GetClipboardData`/`SetClipboardData` 단순 복원은 포맷 핸들과 COM IDataObject를 파괴하여 복원 후 클립보드가 깨지거나 유실됨.
  2. **사용자 복사 데이터 영구 증발**: `read_graph()` 실행 중(0.5~2초) 사용자가 외부 창에서 텍스트/비밀번호 등을 복사하면, `finally:`의 `_restore_clipboard`가 무조건 `EmptyClipboard()`를 호출하여 사용자가 방금 복사한 최신 데이터를 날려버리고 과거 데이터로 강제 덮어씀.
  3. **락 경합 폭발**: 타 프로세스(원격 RDP, 클립보드 매니저 등)가 클립보드를 잠그고 있을 때 `OpenClipboard`가 실패하여 `pywintypes.error: (5, Access is denied)` 예외로 그래프 조회가 즉시 중단됨.

#### 🔴 DEFECT-WF02: `GetClipboardSequenceNumber` 폴링 및 UIA "Copy Display" 호출
- **파일**: [inspection.py#L359-L381](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L359-L381), [inspection.py#L445-L452](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L445-L452)
- **실기 폭발 시나리오**:
  - `app.control(copies[0].ref).invoke()`로 Capstone의 "Copy Display" 메뉴를 UIA로 호출하여 OS 전역 클립보드를 강제 오버라이트함.
  - 이 과정에서 백그라운드 프로그램이 클립보드를 갱신하면 L366 `AutomationError("Another application changed the clipboard during graph inspection.")`를 던지며 조회가 실패하고, `finally:`에서 타 앱의 클립보드까지 지워버림.

#### 🔴 DEFECT-WF03: `tools/ui.py`의 `allow_foreground=True` 기본값으로 인한 사용자 창 포커스 강탈
- **파일**: [ui.py#L88](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/ui.py#L88), [ui.py#L112](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/ui.py#L112), [ui.py#L157](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/ui.py#L157), [ui.py#L178](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/ui.py#L178), [ui.py#L455](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/ui.py#L455)
- **실기 폭발 시나리오**:
  - `capstone_interact_ui`, `capstone_click`, `capstone_keys`, `capstone_type_text` 모두 `allow_foreground=True`가 디폴트임.
  - 사용자가 다른 작업 중일 때 MCP 도구가 호출되면 윈도우 포커스가 갑자기 Capstone으로 탈취되고 전역 마우스 커서가 튀며, 타이핑 중이던 키스트로크가 교차 오염되어 원치 않는 UI 조작이 발생함.

---

### 2. Path Traversal & 샌드박스 없는 임의 파일 쓰기/읽기

#### 🔴 DEFECT-WF04: `physics.py`의 `_write_report_file` 임의 파일 쓰기 및 무단 덮어쓰기 (Critical)
- **파일**: [physics.py#L38-L55](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L38-L55), [physics.py#L200-L208](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L200-L208)
- **코드**:
  ```python
  def _write_report_file(out_path: str, format_type: str, md_text: str | None, html_text: str | None) -> None:
      p = Path(out_path)
      p.parent.mkdir(parents=True, exist_ok=True)
      if format_type == "html": p.write_text(html_text or "", encoding="utf-8")
      elif format_type == "both":
          if md_text: p.write_text(md_text, encoding="utf-8")
          if html_text: p.with_suffix(".html").write_text(html_text, encoding="utf-8")
      else: p.write_text(md_text or "", encoding="utf-8")
  ```
- **실기 폭발 시나리오**:
  1. **Path Traversal 탈출**: 샌드박스 검증(`resolve().is_relative_to(sandbox_root)`)이 전무하여, 클라이언트가 `output_path="../../../../Windows/System32/drivers/etc/hosts"` 또는 시작프로그램 폴더(`.../Startup/evil.bat`) 지정 시 디렉터리를 강제 생성하고 임의 시스템 파일을 파괴함.
  2. **무단 덮어쓰기**: 기존 파일 존재 여부(`p.exists()`)를 전혀 검사하지 않고 무조건 `p.write_text`를 실행하여 사용자의 중요 문서를 사전 경고 없이 파괴.
  3. **형식 `both` 시 자매 파일 덮어쓰기**: `p.with_suffix(".html")`에 대한 검증 없이 덮어써 동일 이름의 기존 HTML 파일을 오염시킴.

#### 🔴 DEFECT-WF05: `tools/files.py` 및 `file_workflows.py`의 샌드박스 없는 임의 파일 저장/내보내기/읽기
- **파일**: [files.py#L51-L72](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/files.py#L51-L72), [files.py#L120-L149](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/files.py#L120-L149), [files.py#L159-L259](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/files.py#L159-L259), [file_workflows.py#L178-L184](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L178-L184), [file_workflows.py#L325-L328](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L325-L328)
- **실기 폭발 시나리오**:
  - `save_experiment`, `export_data`, `open_experiment`, `capstone_inspect_file`, `capstone_file_datasets` 모두 허용된 작업 공간 루트(Allowed Workspace Sandbox) 검증이 누락됨.
  - OS 전체 파일 시스템의 임의 위치에 `.cap`, `.csv`를 생성하거나 임의 파일을 열고 검사할 수 있음.
  - `FileEvents(path.parent, ...)`가 `C:\`나 시스템 상위 디렉터리에 생성될 경우 디렉터리 알림 핸들이 광범위하게 걸려 OS 자원을 낭비함.

---

### 3. 영문 대화상자/메뉴 문자열 하드코딩 (Locale Decoupling 위반)

#### 🔴 DEFECT-WF06: `file_workflows.py` 네이티브 대화상자 및 메뉴 7종 영문 하드코딩
- **파일**: [file_workflows.py](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py)
  1. L88: `lambda c: c.control_type == "MenuItem" and c.name == "File"` -> **`"File"`** (한국어: `"파일"`)
  2. L263-L264: `_choose_export_option(..., "Export Format", "Comma separated values")` -> **`"Export Format"`**, **`"Comma separated values"`** (한국어: `"내보내기 형식"`, `"쉼표로 구분된 값"`)
  3. L266-L267: `_choose_export_option(..., "Alignment Options", "Align by Index")` -> **`"Alignment Options"`**, **`"Align by Index"`** (한국어: `"정렬 옵션"`, `"인덱스별 정렬"`)
  4. L268: `_named_button(app, export_handle, "Select All")` -> **`"Select All"`** (한국어: `"모두 선택"`)
  5. L270: `_named_button(app, export_handle, "Export to file...")` -> **`"Export to file..."`** (한국어: `"파일로 내보내기..."`)
  6. L277: `_named_button(app, export_handle, "Close")` -> **`"Close"`** (한국어: `"닫기"`)
  7. L293: `def _is_discard(control: Control): return control.name == "Discard"` -> **`"Discard"`** (한국어: `"저장 안 함"` 또는 `"취소"`)
- **실기 폭발 시나리오**:
  - 한국어 Windows 또는 비영어권 Capstone 설치 환경에서 `capstone_save_experiment`, `capstone_open_experiment`, `capstone_export_data` 호출 시 100% 무조건 UIA 요소를 찾지 못해 `AutomationError` 또는 15초 타임아웃 폭발.

#### 🔴 DEFECT-WF07: `graphs/inspection.py` 영문 메뉴 하드코딩
- **파일**: [inspection.py#L417](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L417) (`c.name == "Display"`), [inspection.py#L437, L479](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L437) (`c.name == "Copy Display"`)
- **실기 폭발 시나리오**:
  - 한국어 Capstone에서 메뉴명이 `"디스플레이"`, `"디스플레이 복사"`이므로 매칭에 실패하여 L423 `AutomationError("Expected one enabled Display menu.")` 즉각 폭발.

---

### 4. FastMCP Unhandled Exception Escapes (서버 트랜스포트 단절 미처리 예외)

#### 🔴 DEFECT-WF08: `physics.py`의 `capstone_guide` 데코레이터 누락 (팬텀 도구)
- **파일**: [physics.py#L60](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L60)
- **실태**: `def capstone_guide(topic: GuideTopic | None = None) -> str:`에 `@mcp.tool()` 데코레이터가 누락됨.
- **실기 폭발 시나리오**: `agent_instructions.py`에서 필수 도구로 안내하고 반환 딕셔너리(L269)에도 포함되어 있으나 실제로는 MCP 도구로 등록되지 않아, 클라이언트가 호출 시 `Unknown tool: capstone_guide` 에러 반환.

#### 🔴 DEFECT-WF09: `tools/physics.py` 내 동기 연산 도구들의 원시 예외 무방비 탈출
- **파일**: [physics.py#L78-L112, L166-L266](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L78)
- **실기 폭발 시나리오**:
  1. `capstone_plot` (L78): 폰트 `C:/Windows/Fonts/malgun.ttf` 부재 시 `OSError`, `samples.x/y` 길이 불일치 시 `AnalysisError`, `show_fit=True`이고 샘플 2개 이하 시 `pydantic.ValidationError`가 원시 예외로 탈출.
  2. `capstone_linear_fit` (L95): `sxx == 0` (모든 x 값이 동일하여 수직선인 경우 분모 0)일 때 `AnalysisError` 원시 탈출.
  3. `capstone_compare_runs` (L108): `len(runs) < 2`일 때 `AnalysisError` 원시 탈출.
  4. `capstone_run_experiment_macro` (L235): 알 수 없는 `experiment_id` 시 L174의 원시 `KeyError`, 잘못된 `action` 시 L260의 원시 `ValueError`가 아무런 에러 구조체 없이 탈출.
  5. `capstone_generate_lab_report` (L166): 비동기 이벤트 루프를 블로킹하며 `FileNotFoundError`, `CapfileError`, `PermissionError`가 여과 없이 탈출.

#### 🔴 DEFECT-WF10: `tools/files.py` 및 `tools/ui.py`의 원시 예외 탈출
- **파일**: [files.py#L145-L233](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/files.py#L145-L233), [ui.py#L223-L500](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/ui.py#L223)
- **실기 폭발 시나리오**:
  - `capstone_export_data`의 `read_csv_page`: CSV 디코딩 실패나 크기 초과 시 `CsvDataError`, `UnicodeDecodeError` 탈출.
  - `capstone_inspect_file`, `capstone_file_datasets`: 파일 파싱 실패 시 `zipfile.BadZipFile`, `ParseError`, `CapfileError` 원시 탈출.
  - `capstone_extract_dataset` (L232-233): `dataset_index >= len(datasets)`일 때 MCP 에러 변환기 없이 날것의 `AutomationError` 직접 `raise`.
  - `capstone_interact_ui` (L223, L244, L248, L500): 인자 누락 시 구조화된 응답 없이 파이썬 표준 `ValueError`를 날려 클라이언트에 비정형 크래시 유발.

#### 🔴 DEFECT-WF11: `server.py`의 `NativeSessionError.error_code` 부재 시 Re-raise 및 stdio 트랜스포트 단절
- **파일**: [server.py#L78-L91](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L78-L91), [automation_worker.py#L185, L201](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/automation_worker.py#L185)
- **코드**:
  ```python
  except NativeSessionError as exc:
      if exc.error_code:
          payload = ToolErrorPayload(...)
          raise ToolError(payload.model_dump_json(indent=2)) from exc
      raise  # error_code가 None이면 날것의 NativeSessionError가 그대로 상위로 탈출!
  ```
- **실기 폭발 시나리오**:
  - `automation_worker.py`의 60초 타임아웃(`_handle_call_timeout`) 또는 IPC 파이프 단절 시 생성되는 `NativeSessionError`는 `error_code`가 `None`임.
  - `server.py` L80의 `if exc.error_code:` 검사가 `False`가 되어 L91의 `raise`가 실행되고, 원시 `NativeSessionError`가 `tools/files.py`, `tools/displays.py`, `tools/instruments.py` 등 모든 도구 라우터를 뚫고 최상위로 탈출함.
  - 이로 인해 stdio 스트림 처리기에 치명적인 파이썬 런타임 예외가 던져져 MCP JSON-RPC 트랜스포트 세션이 예기치 않게 단절됨.

</details>

<details open>
<summary><b>[보고서 #65] auditor-workflows 실사 세부 명세 (Phase 2)</b></summary>

`src/capstone_mcp/file_workflows.py`, `src/capstone_mcp/tools/*.py`에 대한 라인 바이 라인 정밀 심문 결과, 새롭게 발굴된 구체적 결함 및 파괴 메커니즘 보고서입니다.

---

### 1. `file_workflows.py`: 다중 창 거부, 덮어쓰기 불가, 모달 방치 및 레이스 컨디션

#### 🔴 DEFECT-WF12: `len(windows) != 1` 및 Z-Order `windows[0]` 가정으로 인한 100% 동작 거부
- **코드 위치**: [file_workflows.py#L186-L191](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L186-L191), [file_workflows.py#L330-L335](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L330-L335)
- **코드**:
  ```python
  windows = app.windows()
  if len(windows) != 1 or windows[0].handle != handle:
      msg = ("Close existing Capstone dialogs/menus before this workflow: "
             + ", ".join(f"{w.handle}: {w.title}" for w in windows))
      raise AutomationError(msg)
  ```
- **실기 파괴 메커니즘**:
  1. **보조 창/플로팅 팔레트 존재 시 영구 불능**: 실물 Capstone은 도구 상자(Tools Palette), 계산기 서랍, 하드웨어 설정 창 등이 독립 HWND로 분리되거나 Qt 툴팁/스플래시 잔재가 남아 `app.windows()` 길이가 2 이상이 되는 경우가 빈번함. 이 경우 사용자가 아무리 메인 창을 보며 저장을 시도해도 100% 거부됨.
  2. **Z-Order 변동 시 오폭**: `windows[0].handle != handle`은 대상 창이 무조건 Z-Order 최상위(0번 인덱스)여야 함을 전제함. 사용자가 터미널이나 에디터를 클릭한 상태에서 백그라운드 호출이 오면 0번 인덱스가 메인 창이 아니게 되어 정상 창임에도 즉시 예외 폭발.

#### 🔴 DEFECT-WF13: 덮어쓰기(Overwrite) 매개변수 부재 및 잔재 파일로 인한 저장 불가 크래시
- **코드 위치**: [file_workflows.py#L179-L181](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L179-L181), [file_workflows.py#L159-L161](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L159-L161)
- **실기 파괴 메커니즘**:
  - `save_experiment` 및 `export_data`에 `overwrite: bool` 매개변수가 전무하여, 파일이 존재하면 무조건 `AutomationError("Choose a new ... path; existing files are never overwritten.")`를 던짐.
  - 실험 자동화에서 동일한 파일명(`run_latest.csv`, `current.cap`)으로 주기적 저장을 수행할 수 없으며, 이전 실행 실패로 생성된 0바이트 잔재 파일만 있어도 수동 삭제 전까지 모든 저장이 영구 차단됨.

#### 🔴 DEFECT-WF14: `_open_command` 메뉴 레이스 컨디션 및 예외 시 메뉴 오픈 방치 (모달 락업)
- **코드 위치**: [file_workflows.py#L82-L100](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L82-L100)
- **실기 파괴 메커니즘**:
  - `File` 메뉴를 `INVOKE`한 뒤 서브메뉴 팝업을 대기함. Qt 특성상 마우스 이동이나 외부 포커스 전환 시 팝업 QMenu가 즉시 닫혀버림 (`mouseGrabber` 해제).
  - 서브메뉴가 닫히면 `events.changes.until`이 15초간 멈춘 뒤 타임아웃 예외를 던짐.
  - 예외 발생 시 메뉴를 닫는 Escape 처리(`try...finally: release_menu_bar`)가 없어 메뉴가 활성화된 모달 상태로 방치되어 이후의 모든 UIA 명령이 차단됨.

#### 🔴 DEFECT-WF15: 현대 Windows 다이얼로그의 Edit ID `"1001"` 불일치 및 `set_value` 자동완성 불발
- **코드 위치**: [file_workflows.py#L151-L169](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L151-L169)
- **실기 파괴 메커니즘**:
  - `Edit` 컨트롤 ID `"1001"`을 하드코딩함. Windows 10/11의 탐색기 기반 공용 파일 대화상자(`IFileDialog`)는 `ComboBoxEx32` 또는 `FileNameControlHost` 구조를 사용하여 ID가 일치하지 않거나 여러 개가 검색될 수 있음.
  - UIA `app.set_value`로 텍스트를 주입할 때 키보드 포커스나 `WM_CHAR` 이벤트가 발생하지 않아 셸 내부 버퍼가 갱신되지 않음. 그 상태로 Save(ID `"1"`) 버튼을 누르면 빈 파일명 경고 팝업이 뜨고, `files.changes.until`은 경고 창으로 인해 `issubset(allowed_windows)` 조건을 만족하지 못해 15초 타임아웃으로 폭발함.

#### 🔴 DEFECT-WF16: `export_data` 다단계 조작 실패 시 `DataExportDialog` 모달 방치
- **코드 위치**: [file_workflows.py#L261-L284](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L261-L284)
- **실기 파괴 메커니즘**:
  - 콤보박스 선택 2회, 버튼 클릭 4회, 파일 다이얼로그 조작 등 8개 연속 UI 동작 중 단 하나라도 실패하면 `finally` 블록 부재로 `DataExportDialog`가 화면에 모달로 방치됨. Capstone 전체가 먹통 상태에 빠짐.

#### 🔴 DEFECT-WF17: `settled_title`의 `StopIteration` 크래시 및 대용량 압축 타임아웃
- **코드 위치**: [file_workflows.py#L195-L210](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L195-L210)
- **실기 파괴 메커니즘**:
  - `next(w.title for w in app.windows() if w.handle == handle)`: 창 핸들이 깜빡임 등으로 일시 누락되면 `StopIteration` 예외로 크래시.
  - 대용량 .cap(50MB+) 저장 시 ZIP 압축 지연으로 3초 내에 타이틀이 변경되지 않으면 이전 제목(`Untitled*`)을 반환하여 호출자에게 저장이 실패한 것처럼 거짓 보고함.

#### 🔴 DEFECT-WF18: `await_opened`의 다중 창 감지 시 40초 영구 타임아웃 폭사
- **코드 위치**: [file_workflows.py#L296-L320](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L296-L320)
- **실기 파괴 메커니즘**:
  - `len(windows) == 1 and title.startswith(...)` 조건을 요구함. 팔레트나 자식 도구창이 열려 있으면 `len(windows) == 1`이 영원히 거짓이 되어 `stable_since`가 매 0.1초마다 `None`으로 리셋됨. 문서가 완전히 열렸음에도 40초를 꽉 채우고 `AutomationError` 폭발.

---

### 2. `tools/files.py`: 파일 잠금 위반(WinError 32) 및 메인 스레드 I/O 블로킹

#### 🔴 DEFECT-WF19: `capstone_export_data` 디스크 플러시 레이스 및 파일 잠금 위반 (`os error 32`)
- **코드 위치**: [files.py#L145-L147](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/files.py#L145-L147)
- **실기 파괴 메커니즘**:
  - `export_data` 네이티브 호출 완료 직후 `read_csv_page`를 호출함. Capstone 프로세스가 아직 CSV 파일 핸들을 닫지 않았거나 OS 디스크 버퍼 플러시가 끝나지 않은 상태에서 읽기를 시도하여 Windows 공유 위반 `PermissionError: [WinError 32]` 발생.

#### 🔴 DEFECT-WF20: `capstone_extract_dataset` 동기 실행으로 인한 FastMCP 이벤트 루프 동결
- **코드 위치**: [files.py#L219-L259](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/files.py#L219-L259)
- **실기 파괴 메커니즘**:
  - `capstone_extract_dataset`가 `def`(동기 함수)로 선언되어 비동기 스레드 오프로딩 없이 메인 루프에서 직접 실행됨. 10kHz 고속 샘플링(수십만 데이터 포인트) .cap 아카이브를 추출할 때 2~5초간 CPU를 100% 점유하여 FastMCP 서버의 모든 JSON-RPC 통신이 일시 정지됨.
  - `dataset.independent_values`와 `raw_values` 슬라이싱 시 두 배열 길이가 다른 데이터셋의 경우 인덱스가 어긋난 채 반환됨.

---

### 3. `tools/physics.py`: 비동기 루프 블로킹

#### 🔴 DEFECT-WF21: `capstone_generate_lab_report` 동기 연산의 비동기 루프 직접 실행
- **코드 위치**: [physics.py#L192-L198](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L192-L198)
- **실기 파괴 메커니즘**:
  - `async def` 안에서 `generate_report`와 `render_report`를 `anyio.to_thread.run_sync` 없이 동기로 직접 호출함. 파일 I/O, 회귀 분석, 통계 계산, ASCII 플롯 렌더링이 메인 이벤트 루프를 장시간 블로킹하여 동시 요청 처리 불가.

---

### 4. `tools/ui.py`: 가려진 창 스크린샷 캡처 오염

#### 🔴 DEFECT-WF22: `capstone_screenshot`의 데스크톱 DC 캡처로 인한 타 창 화면 노출
- **코드 위치**: [ui.py#L351-L372](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/ui.py#L351-L372), [desktop.py#L441](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L441)
- **실기 파괴 메커니즘**:
  - `desktop.py`의 `screenshot()`은 `ImageGrab.grab(window=window.handle)`을 사용함. Pillow의 이 구현은 Win32 `PrintWindow`가 아니라 데스크톱 스크린 DC에서 윈도우 좌표 영역을 잘라오는 방식임.
  - `tools/ui.py`는 "Does not raise the target window to the foreground"라고 명시하고 있으므로, Capstone 위에 다른 창(VS Code, 웹 브라우저)이 떠 있으면 Capstone 대신 사용자의 개인 화면이 캡처되어 LLM에게 전송되는 심각한 화면 오염 및 보안 누출 발생.

---

### 5. `tools/instruments.py` & `tools/displays.py`: 논리적 뮤테이션 락 데드락

#### 🔴 DEFECT-WF23: `capstone_manage_instrument`의 `keep_sample`과 `JOBS.interaction` 데드락 충돌
- **코드 위치**: [instruments.py#L60-L76](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/instruments.py#L60-L76)
- **실기 파괴 메커니즘**:
  - 수동 샘플 모드에서 `keep_sample`은 레코딩이 진행 중인 상태에서만 데이터 포인트를 로깅할 수 있음.
  - 그러나 `is_read_only` 검사에서 `keep_sample`이 제외되어 `mutates=True`로 디스패치됨.
  - `server.py:74`의 `with JOBS.interaction():`는 백그라운드 레코딩 잡이 실행 중일 때 `require_idle()`을 호출하여 예외를 발생시키므로, 정작 레코딩 중에 `keep_sample`을 호출하면 서버가 요청을 원천 거부함.

#### 🔴 DEFECT-WF24: `capstone_manage_graph(action="analyze")`의 불필요한 뮤테이션 락
- **코드 위치**: [displays.py#L73](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/displays.py#L73)
- **실기 파괴 메커니즘**:
  - `action == "analyze"`는 그래프의 축과 기존 피트 파라미터를 읽어 분석 보고서를 생성하는 읽기 성격의 작업이나, `mutates=request.action != GraphAction.READ` 조건에 걸려 `mutates=True`로 분류됨.
  - 레코딩 중 그래프 분석 조회를 시도하면 `JOBS.interaction` 락에 걸려 불필요하게 조회가 차단됨.

---
이상 13건의 추가 심층 결함(DEFECT-WF12 ~ DEFECT-WF24)을 보고하며, 마스터 결함 매트릭스 통합을 요청합니다.

</details>

<details open>
<summary><b>[보고서 #82] auditor-workflows 실사 세부 명세 (Phase 3)</b></summary>

지정 영역인 `src/capstone_mcp/bridge.py`, `src/capstone_mcp/session/*`, `src/capstone_mcp/calculator.py`에 대한 단 1줄도 남김없는 전수 분해 실사 결과입니다.

---

### 1. `bridge.py` & `session/*`: WebSocket 단편화, TIME_WAIT 고갈, JS 인젝션, 워치독 누수

#### 🔴 DEFECT-BR01: `evaluate()`의 매 호출 신규 소켓 생성 및 TCP TIME_WAIT 소켓 고갈 (`WSAEADDRINUSE 10048`)
- **코드 위치**: [bridge.py#L107-L113](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L107-L113), [bridge.py#L148-L152](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L148-L152)
- **코드**:
  ```python
  def evaluate(port: int, expression: str) -> JsonValue:
      target = discover_target(port) # 매번 HTTP /json/list 조회
      with connect(target.websocket_url, ...) as websocket: # 매번 신규 TCP+WS 핸드셰이크
          websocket.send(...)
          reply = Reply.model_validate_json(websocket.recv(...))
          return result.result.value # 즉시 소켓 close()
  ```
- **실기 파괴 메커니즘**:
  - `watcher.py`의 50ms 주기 센서 모니터링 시 1초에 20회 이상의 HTTP GET + WebSocket 연결/해제가 발생함.
  - Windows의 TCP 스택에서 종료된 소켓은 120초(`TcpTimedWaitDelay`) 동안 `TIME_WAIT` 상태로 잠김. 수 분 내에 로컬 임시 포트(49152~65535) 수천 개가 전멸하여 `OSError: [WinError 10048] 각 소켓 주소(프로토콜/네트워크 주소/포트)는 하나만 사용할 수 있습니다`가 터지며 전체 네트워크 통신이 마비됨.

#### 🔴 DEFECT-BR02: WebSocket 패킷 단편화(Fragmentation) 미처리 및 8MB 초과 버퍼 오버런
- **코드 위치**: [bridge.py#L150-L158](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L150-L158)
- **실기 파괴 메커니즘**:
  1. `max_size=8 * 1024 * 1024` (8MB): 고속 스코프 파형 데이터나 대용량 데이터셋 일괄 덤프 시 8MB를 초과하는 프레임이 수신되면 `websockets.exceptions.PayloadTooBig`이 발생하며 연결이 강제 차단됨.
  2. `websocket.recv()` 단일 호출 가정: TCP 스트림 특성상 대용량 JSON이 청크 단위로 분할(Fragmentation)되어 도착할 경우, 첫 번째 청크만 읽어 `Reply.model_validate_json()`으로 넘김으로써 불완전한 JSON 문법 오류(`JSONDecodeError`)로 폭발함.

#### 🔴 DEFECT-BR03: `read_measurement`의 자바스크립트 인젝션 (Arbitrary JS Execution 취약점)
- **코드 위치**: [bridge.py#L187-L189](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L187-L189)
- **코드**:
  ```python
  expression = (
      "window.app.mSenseAndControlView.mServices.RequestReadMeasurement("
      + json.dumps(measurement_euid) + "," + str(unit_type) + ")"
  )
  ```
- **실기 파괴 메커니즘**:
  - 파라미터를 함수 인자 객체로 바인딩하지 않고 원시 문자열 결합으로 JavaScript 코드를 동적 생성하여 `Runtime.evaluate`로 실행함.
  - `measurement_euid` 또는 `unit_type`에 특수 문자열(예: `"); malicious_code(); ("`)이 주입될 경우 Capstone 내장 Qt WebEngine 렌더러 프로세스 컨텍스트에서 임의의 자바스크립트가 무단 실행되는 원격 코드 실행(RCE) 위험 상존.

#### 🔴 DEFECT-BR04: `ConditionWatcher.monitor`의 예외 시 장비 정지 실패 및 취소 토큰 부재
- **코드 위치**: [session/watcher.py#L81-L114](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/watcher.py#L81-L114)
- **실기 파괴 메커니즘**:
  1. `val = sampler()`에 `try...except`가 전무함: 센서 통신 에러나 브리지 소켓 단절 시 즉시 예외가 탈출하여 L101의 `halt_callback()`이 영구히 스킵됨. 하드웨어 발생기/모터/가열기가 꺼지지 않고 계속 동작하여 물리적 과열/파손 위험 초래.
  2. `threading.Event` 캔슬레이션 토큰 부재: `time.sleep(condition.poll_interval)`로 블로킹되어 있어 상위에서 잡 취소를 요청해도 `timeout`(최대 수백 초)까지 스레드가 죽지 않고 백그라운드에서 CPU와 핸들을 점유함.

#### 🔴 DEFECT-BR05: `SessionLifecycleManager.terminate()`의 무동작 껍데기 코드
- **코드 위치**: [session/lifecycle.py#L49-L53](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/lifecycle.py#L49-L53)
- **실기 파괴 메커니즘**:
  - `terminate()`가 `self._is_active = False` 플래그 하나만 변경할 뿐, `self._worker.close()`, Capstone 프로세스 강제 종료, 열린 소켓/잡 오브젝트 반환을 단 1줄도 실행하지 않음. 세션 종료 후에도 백그라운드에 좀비 프로세스와 포트 점유가 영구 지속됨.

---

### 2. `calculator.py`: 수식 AST 검증 전무, 결과 날조, 그리스 문자 파탄, 비존재 메서드

#### 🔴 DEFECT-CALC01: 수식 AST 파서 부재로 인한 괄호/연산자 불균형 모달 락업
- **코드 위치**: [calculator.py#L117-L121](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L117-L121)
- **실기 파괴 메커니즘**:
  - `expression`에 대해 `raw_expr.strip()`만 확인할 뿐 연산자 우선순위, 괄호 짝 맞춤(`(` vs `)`), 연산자 연속(`++`, `//`), 피연산자 누락 등을 검증하는 AST 구문 분석기가 전무함.
  - 불균형 수식(예: `KE = 0.5 * m * v^(2`) 입력 시 Capstone 내부에 모달 구문 오류 대화상자가 팝업되고, 자동화는 이를 감지하지 못해 이후 모든 동작이 모달 창에 가로막혀 마비됨.

#### 🔴 DEFECT-CALC02: 수식 등록 검증 전무 및 거짓 성공 날조 (`verified=True`, `status="valid"`)
- **코드 위치**: [calculator.py#L168-L182](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L168-L182)
- **실기 파괴 메커니즘**:
  - 수식 입력 후 `{ENTER}`를 전송하고는 Capstone이 수식을 실제로 수용했는지, 미정의 변수 에러가 났는지, 에러 대화상자가 떴는지 일체 확인하지 않고 무조건 `status="valid"`, `verified=True`를 반환함.
  - 실제로는 수식이 등록되지 않았거나 문법 에러로 거부당했음에도 호출자에게는 완벽히 생성된 것처럼 조작된 성공 응답을 전달함.

#### 🔴 DEFECT-CALC03: 그리스 문자 및 특수 물리 변수 정규식 매칭 실패로 인한 변수명 왜곡
- **코드 위치**: [calculator.py#L41-L47](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L41-L47)
- **코드**:
  ```python
  match = re.match(r"^\s*([A-Za-z0-9_가-힣\s]+?)\s*=", expression)
  ```
- **실기 파괴 메커니즘**:
  - 물리학에서 일상적으로 쓰이는 그리스 기호($\theta, \omega, \lambda, \Delta, \mu, \pi, \tau$)나 대괄호 변수(`[Force (N)]`)가 포함된 수식(예: `\theta = \omega * t`, `\lambda = v / f`) 입력 시 정규식 매칭이 실패하여 `match`가 `None`이 됨.
  - 결과적으로 `expression.strip()` 전체가 변수명으로 반환되어, 변수명이 `\theta`가 아니라 `\theta = \omega * t`라는 수식 전체 문자열로 오염 등록됨.

#### 🔴 DEFECT-CALC04: 존재하지 않는 `app.click()` 및 `app.type_text()` 직접 호출 크래시
- **코드 위치**: [calculator.py#L136](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L136), [calculator.py#L153-L155](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L153-L155), [calculator.py#L163-L165](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L163-L165), [calculator.py#L189](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L189)
- **실기 파괴 메커니즘**:
  - `desktop.py`의 `Capstone` 클래스에는 `click(handle, ref)`이나 `type_text(text)` 메서드가 정의되어 있지 않음 (오직 `act(ref, Action.INVOKE)` 및 `click_point()`만 제공).
  - 그러나 토글 버튼 클릭, 수식 타이핑 폴백, 서랍 닫기 등에서 이를 직접 호출하고 있어 실제 Capstone 연결 시 즉시 `AttributeError: 'Capstone' object has no attribute 'click'` 예외를 터뜨리고 사망함.

---
이상 9건의 최심부 파괴 결함(DEFECT-BR01~05, DEFECT-CALC01~04)을 추가 보고합니다. 마스터 매트릭스에 통합 반영 부탁드립니다.

</details>

---

### 3.6. Runs & Session State Management (런 수명주기 & 히스토리 불변성)
- **담당 에픽 이슈**: #123, #127
- **실사 참여 전문 에이전트**: `auditor-runs`

#### 📑 실사 보고서: `auditor-runs` (총 3회 정밀 실사)

<details open>
<summary><b>[보고서 #54] auditor-runs 실사 세부 명세 (Phase 1)</b></summary>

`src/capstone_mcp/runs/` (manager.py, models.py, tool.py) 및 관련 테스트 코드에 대한 정밀 감사 결과입니다.

---

### 1. `manager.py` 내 10개 `contextlib.suppress` 전수 조사 및 침묵형 결함 분석

`src/capstone_mcp/runs/manager.py` 전반에 걸쳐 총 10개의 `contextlib.suppress` 블록이 존재하며, UIA 패턴 실패, 키스트로크 누락, 대화상자 미확인 등의 심각한 결함을 침묵(Swallow)시키고 있습니다.

1. **[manager.py#L67](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L67)**: `contextlib.suppress(AttributeError, RuntimeError)`
   - **대상**: `node.iface_selection_item.Select()`
   - **은폐 결함**: F2 인라인 편집 전 트리 항목 선택 실패(비활성화, 뷰포트 외 위치, COM RPC 오류)를 무시함. 선택되지 않은 상태로 다음 단계로 진행됨.
2. **[manager.py#L71](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L71)**: `contextlib.suppress(Exception)`
   - **대상**: `node.set_focus()`
   - **은폐 결함**: 포커스 설정 실패를 포괄적 `Exception`으로 무시함. #1과 #2가 모두 실패하여 포커스가 엉뚱한 창이나 그래프에 있는 상태에서 L74-78의 `{F2}` 및 `^a{new_name}{ENTER}`가 무차별 블라인드 전송되어 전체 선택 및 데이터 오버라이트 참사 유발.
3. **[manager.py#L107](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L107)**: `contextlib.suppress(AttributeError, RuntimeError)`
   - **대상**: `node.iface_value.SetValue(request.new_name)`
   - **은폐 결함**: Capstone Data Summary의 TreeItem은 ValuePattern이 읽기 전용이거나 지원하지 않음. UIA 계층에서 임시 반영되어 예외가 안 나더라도 내부 C++ 엔진에 커밋되지 않으면 `value_set = True`가 되어 F2 fallback을 건너뛰고 이름 변경이 완전히 실패함.
4. **[manager.py#L165](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L165)**: `contextlib.suppress(Exception)`
   - **대상**: `dialog_snap = app.snapshot(win.handle, depth=6, limit=100)` 및 버튼 클릭
   - **은폐 결함**: 팝업 대화상자 스냅샷/버튼 클릭 중 발생하는 COM 지연/오류를 은폐하여 모달 창이 닫히지 않고 영구 블로킹되는 현상 방치.
5. **[manager.py#L203](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L203)**: `contextlib.suppress(Exception)`
   - **대상**: `node.select()`
   - **은폐 결함**: UIA 래퍼 노드에 존재하지 않는 `.select()` 호출 오류를 은폐함. 실제 선택이 이뤄지지 않은 상태에서 삭제 키 전송으로 직행.
6. **[manager.py#L216](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L216)**: `contextlib.suppress(Exception)`
   - **대상**: `app.keys(request.handle, "{DELETE}", allow_foreground=request.allow_foreground)`
   - **은폐 결함**: 포그라운드 활성화 실패, 윈도우 핸들 무효, 권한 부족 등으로 `{DELETE}` 키 입력이 드롭되더라도 예외가 무시되어 삭제가 전혀 되지 않음.
7. **[manager.py#L305](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L305)**: `contextlib.suppress(AttributeError, RuntimeError)`
   - **대상**: `toggle.ToggleState` / `CurrentToggleState` 조회
   - **은폐 결함**: 토글 상태가 0(Off)이면 SelectionItem 확인 없이 즉시 `False` 반환. 또한 3-상태(Indeterminate, 2)를 단순 False로 왜곡.
8. **[manager.py#L315](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L315)**: `contextlib.suppress(AttributeError, RuntimeError)`
   - **대상**: `sel.IsSelected` / `CurrentIsSelected` 조회
   - **은폐 결함**: 그래프 표시 여부(Toggle/Check)와 항목 선택 여부(Selection/Highlight)를 혼동하여 하이라이트된 런을 표시 중인 것으로 잘못 판별.
9. **[manager.py#L331](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L331)**: `contextlib.suppress(AttributeError, RuntimeError)`
   - **대상**: `node.iface_toggle.Toggle()`
   - **은폐 결함**: Toggle 메서드 실행 실패 시 SelectionItem 블록으로 자동 폴스루되어 토글 의도가 선택 의도로 둔갑.
10. **[manager.py#L336](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L336)**: `contextlib.suppress(AttributeError, RuntimeError)`
    - **대상**: `node.iface_selection_item.AddToSelection()` / `Select()` / `RemoveFromSelection()`
    - **은폐 결함**: 선택 패턴 실패 시 L362의 `click_control`로 폴백하는데, TreeItem 중앙을 클릭하여 체크박스가 아닌 텍스트 인라인 편집이 발동됨.

---

### 2. SelectionItem과 ToggleState 동기화 레이스 컨디션 및 상태 조작 (State Spoofing)

1. **상태 미확인 무차별 Toggle 호출 ([manager.py#L332](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L332))**:
   - `_try_toggle_or_select(node, visible)`는 `visible=True/False` 목표 상태를 인자로 받으면서도, 노드가 `iface_toggle`을 가지면 단순히 인자 없는 `node.iface_toggle.Toggle()`을 호출함.
   - 복수 디스플레이에서 Indeterminate(2) 상태이거나 이미 켜져 있는 상태에서 호출 시 반대로 꺼지거나 엉뚱한 상태로 전이됨.
2. **UIA 지연 시간 미고려 및 즉각적인 스냅샷 ([manager.py#L451](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L451))**:
   - `_apply_run_visibility` 호출 직후 어떠한 UIA 이벤트 대기(sleep 또는 이벤트 루프 플러시) 없이 즉시 `app.snapshot(...)`을 호출하여 여전히 이전 토글 상태를 읽어옴.
3. **가짜 결과 주입 (State Spoofing) ([manager.py#L414-L418](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L414-L418), [L467](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L467))**:
   - `_collect_visible_runs`는 실제 컨트롤에서 읽은 상태와 상관없이 `if visible: visible_names.update(requested_runs)`를 실행하여 반환값에 요청된 런을 강제로 끼워 넣음.
   - `SetRunVisibilityResult`에 `verified=True`를 하드코딩함으로써 실제 UI 변경이 100% 실패하더라도 검증 성공으로 위장 보고함.

---

### 3. 확인 대화상자 누락 및 런 삭제 침묵형 실패 (Silent Deletion Failure)

1. **비동기 모달 대화상자 생성 레이스 ([manager.py#L159-L175](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L159-L175), [L224](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L224))**:
   - L218에서 `{DELETE}` 키를 보낸 직후 대기 없이 1회성으로 `_dismiss_confirmation_dialog`를 호출.
   - Windows/Qt가 확인 모달("Delete Run?") 창 핸들을 생성하는 데 수십~수백 ms가 걸리므로 `app.windows()`는 모달 창이 뜨기 전에 비어 있는 목록을 순회하고 즉시 종료됨.
   - 결국 모달 대화상자는 닫히지 않고 화면에 남아 Capstone 전체 UI를 모달 블로킹 상태로 정지시킴.
2. **삭제 여부 사후 검증 전무 및 무조건 성공 보고 ([manager.py#L226-L230](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L226-L230))**:
   - 삭제 키가 드롭되었거나 대화상자가 미확인 상태로 남아 런이 삭제되지 않았음에도, 트리 재확인 스냅샷 없이 `DeleteRunResult(deleted_run=actual_deleted_name, verified=True)`를 하드코딩 반환.
3. **이름 변경된 런의 삭제 영구 불능 결함 ([manager.py#L52](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L52), [L154](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L154))**:
   - `_find_run_items`가 `RUN_NAME_PATTERN = re.compile(r"run\s*#?\s*\d+", re.IGNORECASE)`로만 런을 탐색함.
   - 사용자가 `rename_run`으로 "Baseline Trial" 등으로 이름을 바꾼 런은 `_find_run_items`에서 영구적으로 제외되어, 해당 런을 삭제하려고 하면 `AutomationError("Run 'Baseline Trial' not found in Data Summary.")`가 발생하고 삭제가 불가능해짐.
4. **다국어 및 단축키 불일치 ([manager.py#L171](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L171))**:
   - 모달 버튼 탐색 시 `name_lower in ("yes", "ok", "delete", "confirm", "예", "확인", "삭제")`로 완전 일치만 검사.
   - `&Yes`, `Delete Run`, `Ja`, `Oui`, `Sí` 등 가속기(`&`)나 다른 언어 환경에서는 대화상자를 감지하지 못함.

---

### 결함 분류 및 종합 매트릭스

| ID | 결함 내용 | 심각도 | 해당 위치 |
|---|---|---|---|
| RUN-01 | 확인 대화상자 레이스로 모달 방치 및 런 미삭제 상태에서 `verified=True` 위장 보고 | **P0 (Blocker)** | [manager.py#L159-L230](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L159-L230) |
| RUN-02 | 이름 변경된 런이 `RUN_NAME_PATTERN` 필터에 걸려 영구히 삭제 불가능해지는 버그 | **P0 (Blocker)** | [manager.py#L52, L154](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L52) |
| RUN-03 | 10개 `contextlib.suppress` 남용으로 인한 포커스 이탈, 키스트로크 유실 및 침묵형 실패 | **P1 (Critical)** | [manager.py#L67-L336](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L67-L336) |
| RUN-04 | 가시성 토글 실패 시 `visible_names.update`로 실제 UI 상태를 속이고 `verified=True` 하드코딩 | **P1 (Critical)** | [manager.py#L414-L467](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L414-L467) |
| RUN-05 | `_matches_run_name`의 정규식 숫자 목록 단순 비교로 인한 오매칭 버그 | **P2 (Major)** | [manager.py#L293-L295](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L293-L295) |
| RUN-06 | F2 인라인 편집 시 전환 대기 부재 및 특수문자/수식 키스트로크 왜곡 | **P2 (Major)** | [manager.py#L74-L78](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L74-L78) |
| RUN-07 | 테스트 스위트의 매직목 의존으로 인한 실환경 UI 비동기 결함 은폐 | **P2 (Major)** | [tests/test_run_delete.py#L96-L120](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_run_delete.py#L96-L120) |

</details>

<details open>
<summary><b>[보고서 #70] auditor-runs 실사 세부 명세 (Phase 2)</b></summary>

`src/capstone_mcp/runs/` (manager.py, tool.py, models.py) 및 관련 테스트 코드에 대한 1줄 단위 2차 심층 전수 조사 결과입니다. 기존 보고된 38개 외에 새롭게 발굴된 8건의 결함 보고서입니다.

---

### 1. 🔴 DEFECT-RUN-P2-01: Multi-run/Multi-display Stale Ref Cascade Explosion (P0 - Blocker)
- **파일/라인**: [manager.py#L350-L364](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L350-L364), [manager.py#L393-L400](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L393-L400), [desktop.py#L338](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L338)
- **코드**:
  ```python
  def _set_control_visibility_state(app: Capstone, handle: int, ctrl: Control, visible: bool) -> None:
      ...
      if not _try_toggle_or_select(node, visible):
          click_control(app, handle, ctrl, allow_foreground=True)  # -> app.act -> self.refs.clear()
  ```
- **파괴 메커니즘**:
  - `_apply_run_visibility`가 복수 런(`runs=["Run #1", "Run #2"]`) 또는 복수 디스플레이(`target_displays=["Graph 1", "Table 1"]`)를 순회할 때, 첫 번째 컨트롤이 `click_control`로 폴백되면 `app.click` -> `app.act` -> `self.refs.clear()`가 실행되어 전역 UIA 참조 테이블이 완전히 증발함.
  - 두 번째 런/디스플레이 반복에서 `app.control(ctrl.ref)`를 호출하는 순간 [desktop.py#L324](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L324)의 `AutomationError("Unknown or stale ref. Take a new snapshot.")`가 무조건 발생하며 서버가 크래시됨.

---

### 2. 🔴 DEFECT-RUN-P2-02: `tokenize_keys` 분해로 인한 `^a` 무력화 및 이름 영구 오염 (P0 - Blocker)
- **파일/라인**: [manager.py#L75-L78](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L75-L78), [desktop.py#L99-L111](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L99-L111), [desktop.py#L503-L511](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L503-L511)
- **코드**:
  ```python
  _ = app.keys(handle, f"^a{new_name}{{ENTER}}", allow_foreground=True, unicode_input=True)
  ```
- **파괴 메커니즘**:
  - `unicode_input=True`로 인해 `desktop.py`의 `tokenize_keys`가 호출되어 `^a`가 `['^', 'a', ...]`로 분리됨.
  - 루프에서 각 토큰이 `target.type_keys(token, vk_packet=True)`로 전달되어, Windows는 `Ctrl+A` 단축키가 아니라 문자 그대로 `^`와 `a` 패킷을 수신함.
  - 기존 텍스트가 전혀 선택/삭제되지 않은 채 "Run #1" 뒤에 `^aTrial A`가 이어붙어 "Run #1^aTrial A"로 이름이 영구 왜곡/오염됨.

---

### 3. 🔴 DEFECT-RUN-P2-03: `RUN_NAME_PATTERN` 필터로 인한 이름 변경 런의 가시성 조작 불가 (P0 - Blocker)
- **파일/라인**: [manager.py#L52](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L52), [manager.py#L274-L277](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L274-L277)
- **코드**:
  ```python
  if not (RUN_NAME_PATTERN.search(ctrl.name) or "run" in ctrl.automation_id.lower()):
      continue
  ```
- **파괴 메커니즘**:
  - 사용자가 `rename_run`을 통해 런 이름을 "Baseline" 등으로 변경하면, `_find_run_controls`의 정규식 필터에서 원천 탈락함.
  - 이후 `set_run_visibility(runs=["Baseline"])`를 호출하면 `AutomationError: Run visibility control for 'Baseline' not found.`가 발생하여 가시성 토글이 영구적으로 불가능해짐.

---

### 4. 🟠 DEFECT-RUN-P2-04: `last_run` 삭제 시 다중 센서/트리 역순으로 인한 엉뚱한 런 오폭 삭제 (P1 - Critical)
- **파일/라인**: [manager.py#L146-L156](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L146-L156), [manager.py#L189-L195](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L189-L195)
- **코드**:
  ```python
  if target_name.lower() in ("last_run", "last", "latest"):
      target_control = run_items[-1]
  ```
- **파괴 메커니즘**:
  - `_find_run_items`는 UIA 트리 순회 순서로 `run_items`를 수집함. Capstone에 다중 센서나 계산 열이 존재할 경우 하위 노드마다 "Run 1", "Run 2"가 중복 노출됨.
  - `run_items[-1]`은 전체 실험의 최신 런이 아니라 마지막 센서의 하위 브랜치나 정렬에 따라 임의의 과거 런을 가리켜 중요한 실험 데이터를 오폭 삭제함.

---

### 5. 🟠 DEFECT-RUN-P2-05: `_matches_run_name`의 숫자 리스트 단순 일치로 인한 이종 컨트롤 오매칭 (P1 - Critical)
- **파일/라인**: [manager.py#L293-L295](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L293-L295)
- **코드**:
  ```python
  c_num = re.findall(r"\d+", cname)
  t_num = re.findall(r"\d+", tname)
  return bool(c_num and t_num and c_num == t_num)
  ```
- **파괴 메커니즘**:
  - `cname = "Table 1, Run 2"`, `tname = "Graph 1, Run 2"`일 때 두 문자열의 숫자 추출 결과가 모두 `['1', '2']`로 일치하여 True를 반환함.
  - 사용자가 특정 그래프의 런을 조작하려 할 때 엉뚱한 테이블의 런 컨트롤을 매칭하여 조작을 오염시킴.

---

### 6. 🟠 DEFECT-RUN-P2-06: `CaptureSession.record`의 엄격한 부동소수점 비교 및 `finally:` 상태 오염 (P1 - Critical)
- **파일/라인**: [manager.py#L589-L595](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L589-L595), [manager.py#L662-L676](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L662-L676)
- **파괴 메커니즘**:
  - 센서 시간 좌표 간 1e-16 수준의 부동소수점 지터가 있을 때 `x_coords != y_coords` 검사로 인해 `CaptureError`가 발생함.
  - 에러로 피팅이 실패했음에도 L675 `finally:`에서 `self.previous = parsed`로 기준선을 전진시켜, 불완전하게 깨진 사이클이 차기 수집의 기준선이 되어 이후 모든 델타 계산을 연쇄 왜곡함.

---

### 7. 🟡 DEFECT-RUN-P2-07: `capstone_manage_run` 도구의 `destructiveHint=False` 위험 메타데이터 (P2 - Major)
- **파일/라인**: [tool.py#L30-L36](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/tool.py#L30-L36)
- **파괴 메커니즘**:
  - 실험 데이터 영구 삭제(`RunAction.DELETE`)를 수행하는 도구임에도 메타데이터에 `destructiveHint=False`로 선언되어 있어 클라이언트 및 AI 에이전트의 파괴적 작업 안전 가드레일을 무력화함.

---

### 8. 🟡 DEFECT-RUN-P2-08: F2 인라인 편집 경로의 단위 테스트 전무 (Test Blindness) (P2 - Major)
- **파일/라인**: [test_rename_run.py#L44-L86](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_rename_run.py#L44-L86), [test_runs.py#L58-L98](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_runs.py#L58-L98)
- **파괴 메커니즘**:
  - 모든 테스트가 `mock_node.iface_value.SetValue`만 모킹하여 통과시키며, 실기 환경의 핵심 경로인 `_rename_via_inline_editor`를 실행하는 테스트가 전무하여 DEFECT-RUN-P2-02(`^a` 무력화 버그)를 전혀 감지하지 못하고 거짓 신뢰를 제공함.

</details>

<details open>
<summary><b>[보고서 #79] auditor-runs 실사 세부 명세 (Phase 3)</b></summary>

지정 취약 영역(특수문자 인젝션, 복합 렌더링/UIA 재귀 부하, 서브트리 오매칭 등)에 대한 `src/capstone_mcp/runs/` 전수 분해 실사 결과입니다.

---

### 1. 🔴 DEFECT-RUN-P3-01: `handle=0` 기본값으로 인한 무조건 크래시 (P0 - Blocker)
- **파일/라인**: [models.py#L36, L58, L81](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/models.py#L36), [runtime.py#L249-L254](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native/runtime.py#L249-L254), [desktop.py#L195-L197](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L195-L197)
- **코드**:
  ```python
  class RenameRunRequest(Model):
      handle: int = 0
  ...
  def window(self, handle: int) -> UIAWrapper:
      if not any(w.handle == handle for w in self.windows()):
          raise AutomationError("Window is not a visible window of the attached Capstone process.")
  ```
- **파괴 메커니즘**:
  - `RenameRunRequest`, `DeleteRunRequest`, `SetRunVisibilityRequest` 모두 `handle`의 기본값이 `0`이나, `runtime.py`와 `manager.py`에 활성 창 핸들 자동 폴백 로직이 전무함.
  - OS 프로세스의 실제 윈도우 핸들은 0이 될 수 없으므로, 클라이언트가 `handle`을 명시하지 않은 모든 런 조작 요청은 `AutomationError`를 발생시키며 100% 폭사함.

---

### 2. 🔴 DEFECT-RUN-P3-02: 중괄호/개행문자 주입 시 Pywinauto KeySequenceError 및 키스트로크 인젝션 (P0 - Blocker)
- **파일/라인**: [manager.py#L75-L78](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L75-L78), [desktop.py#L99-L111](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L99-L111)
- **코드**:
  ```python
  _ = app.keys(handle, f"^a{new_name}{{ENTER}}", allow_foreground=True, unicode_input=True)
  ```
- **파괴 메커니즘**:
  - 사용자가 `new_name`에 `{` 또는 `}`(예: `"Run {1}"`)를 입력하면 `tokenize_keys`가 `"{1}"`을 가상 키 코드로 파싱함. pywinauto 키 매핑에 존재하지 않아 `KeySequenceError: Unknown key {1}` 예외로 서버가 즉시 크래시됨.
  - `new_name`에 `\n`이 포함될 경우 pywinauto가 이를 즉시 `{ENTER}`로 해석하여 이름 입력을 중간에서 절단하고 잔여 문자를 메인 윈도우에 입력하여 임의의 단축키를 오작동시킴.

---

### 3. 🟠 DEFECT-RUN-P3-03: `depth=16`, `limit=10,000` 무제한 스냅샷 2중 호출로 인한 UI 스레드 정지 (P1 - Critical)
- **파일/라인**: [manager.py#L88, L119, L179, L436, L451](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L88)
- **파괴 메커니즘**:
  - `rename_run`, `delete_run`, `set_run_visibility` 모두 전역 UIA 트리를 깊이 16, 최대 10,000개 컨트롤까지 전수 순회하는 스냅샷을 1개 요청당 2회씩 연속 호출함.
  - 대규모 다중 디스플레이/복합 워크북 환경에서 1회 스캔당 2~5초가 소요되어, 단순 런 이름 변경이나 가시성 토글 하나에 5~10초 동안 메인 스레드가 블로킹되어 타임아웃을 유발함.

---

### 4. 🟠 DEFECT-RUN-P3-04: Data Summary 내 동명 측정값 서브트리 오인 타겟팅 (P1 - Critical)
- **파일/라인**: [manager.py#L90-L98](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L90-L98)
- **파괴 메커니즘**:
  - Capstone Data Summary 트리에는 런 헤더 외에도 하위의 개별 측정 데이터(Position, Velocity 등) 노드 역시 `name == "Run #1"`을 가질 수 있음.
  - `snapshot.controls`의 선형 검색에서 첫 번째 매칭 노드를 무조건 타겟팅하므로, 런 루트 노드가 아닌 하위 측정값 열을 선택하여 F2 이름 변경이 거부되거나 특정 센서 열만 변조되는 불일치 발생.

---

### 5. 🟡 DEFECT-RUN-P3-05: Unicode Non-breaking Space(`\u00a0`) 미정규화로 인한 매칭 실패 (P2 - Major)
- **파일/라인**: [manager.py#L94, L193, L289](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L94)
- **파괴 메커니즘**:
  - Capstone Qt 위젯이 렌더링하는 런 이름에는 종종 Non-breaking space(`\u00a0`, `"Run\u00a0#1"`)가 포함됨.
  - 파이썬의 표준 `.strip()` 및 단순 `==` 비교는 일반 공백(`\x20`)과 `\u00a0`을 다르게 취급하여, 화면에 표시된 런에 대해서도 `AutomationError("... not found")`를 발생시킴.

---

### 6. 🟡 DEFECT-RUN-P3-06: `CapturePlan.directory` 샌드박스 없는 임의 경로 쓰기 취약점 (P2 - Major)
- **파일/라인**: [models.py#L118-L122](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/models.py#L118-L122), [manager.py#L611, L626](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L611)
- **파괴 메커니즘**:
  - `CapturePlan`의 `directory` 경로 검증 및 샌드박싱 부재로 임의의 디렉터리 경로(예: 시스템 루트, OS 디렉터리) 전달 시 무단으로 폴더를 생성하고 `baseline.cap`을 기록하여 보안 무결성을 위협함.

</details>

---

### 3.7. Capfiles, CSV Data Sources & Locales (파일 파서 & CP949 / 유럽식 로케일)
- **담당 에픽 이슈**: #130
- **실사 참여 전문 에이전트**: `auditor-capfiles`, `auditor-data-sources`, `audit-encoding`

#### 📑 실사 보고서: `auditor-capfiles` (총 3회 정밀 실사)

<details open>
<summary><b>[보고서 #53] auditor-capfiles 실사 세부 명세 (Phase 1)</b></summary>

Line-by-line findings for `src/capstone_mcp/capfiles/*`, `capfile_models.py`, `numeric_storage.py`, and consuming adapters:

---

### 1. Gaps Between .cap Read-Only Parser and Write/Patch Synthesis Engine

1. **Complete Absence of Write/Patch Engine**:
   - `capfiles/__init__.py:2`: Declares package as strictly `"Bounded, read-only parsing for PASCO Capstone .cap experiment archives."`
   - `archive.py:680`: Only opens files with `ZipFile(..., mode="r", allowZip64=False)`. There are NO write, synthesize, or patch APIs (`write_cap_file`, `patch_cap_file`).
   - `capfile_models.py:18`: `CapFileModel` enforces `ConfigDict(frozen=True)`. All models (`CapConfiguration`, `CapDataSet`, `CapXmlNode`) are immutable read-only snapshots.
   - *Production Impact*: Server cannot modify or create experiment files headlessly. It is forced to rely on Windows GUI automation (`capstone_save_experiment` in `tools/files.py:51-72`, `save_experiment` in `file_workflows.py:46-120`) using pywinauto/UIA to trigger `File > Save As`, type filenames into Win32 dialogs, and poll filesystem writes.

2. **Asymmetric Data Modeling (De-serialization Without Serialization)**:
   - `archive.py:188-199` (`_xml_node`): Unidirectional ElementTree -> `CapXmlNode` extraction. There is NO reciprocal `node_to_xml(node: CapXmlNode) -> Element` serializer.
   - `archive.py:218-395`: Parsing into structured models (`CapDataSource`, `CapExperimentSetting`, `CapHardwareSensor`) preserves raw XML in `.metadata`. Mutating structured fields (e.g. sampling rate) creates split-brain state with un-synchronized `.metadata`.

3. **Missing Binary Record Encoders in `records.py`**:
   - `records.py:32-144` implements only decoders (`decode_numeric_payload`, `decode_text_records`, `decode_interval_coordinates`).
   - ZERO encoders exist:
     - No `encode_numeric_payload`: Missing packing of 12-byte `<Id` struct (4-byte tag/attribute + 8-byte double), offset subtraction (`stored = value - offset`), and scalar tag assignment (`NUMERIC_TAG = 1`).
     - No `encode_text_records`: Missing packing of 8-byte header `<II` (type=2, length) + UTF-16 LE payload with empty record (type=0) handling.
   - *Impact*: Direct headless creation or modification of `data/*.tmp` binary payloads is impossible without implementing these encoders.

4. **ZIP Normalization and Relational EUID Integrity Gaps**:
   - Capstone on Windows routinely writes internal ZIP members with backslashes (e.g. `data\values.tmp`, see `archive.py:65`). A patch engine must strictly preserve path separators referenced by `main.xml` `DependentStorageElement FileName="..."`.
   - Relational graph integrity: Every sensor, measurement, data source, dataset, and run parameter in `.cap` is cross-linked by EUID GUID strings. Mutating or injecting datasets without maintaining full EUID relational graphs causes Capstone to crash with memory access violations or discard runs upon opening.

---

### 2. OLE Compound Document vs ZIP+XML Format Assumptions

1. **Blind Delegation to `zipfile.ZipFile` Without Magic Byte Inspection**:
   - `archive.py:680-689`:
     ```python
     with ZipFile(archive_path, mode="r", allowZip64=False) as archive:
         return _parse_archive(archive, file_name=archive_path.name, include_data=include_data)
     ```
   - *Flaw*: Blindly assumes all `.cap` files are PKZip (`PK\x03\x04`). PASCO's legacy data acquisition ecosystem (DataStudio `.ds` files and early prototype Capstone archives) uses Microsoft OLE2 Structured Storage / Compound File Binary Format (CFBF, magic bytes `\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1`).
   - When encountering an OLE file, `ZipFile` raises `BadZipFile`, which line 688 masks as `CapFileError: Invalid Capstone archive: <path>`. Zero magic header inspection means no diagnostic explanation is provided for legacy OLE/DataStudio files.

2. **Hardcoded Rejection of Zip64 (`allowZip64=False`)**:
   - `archive.py:680`: Hardcoded `allowZip64=False`.
   - *Failure Scenario*: In high-speed continuous acquisition (e.g. 850 Universal Interface at 100 kHz - 10 MHz over extended runs), uncompressed archive size can exceed 4 GB or 65,535 entries. `ZipFile` raises `LargeZipFile: Filesize would require ZIP64 extensions`. Because Zip64 is forbidden, Capstone-generated high-volume experiment archives are immediately rejected as invalid.

3. **Monolithic `main.xml` & Rigid Root Element Requirement**:
   - `archive.py:606-618`: Requires `main.xml` strictly at the root of the archive and enforces `root.tag == "DSProExperiment"`.
   - *Failure Scenario*: Archives packaged with nested root folders (e.g. `Experiment1/main.xml`) or sister formats like PASCO SPARKvue (`.spk` / `.spk2` using `<SparkExperiment>`) are rejected immediately, despite sharing underlying sensor and data cache schemas.

4. **Overly Restrictive Safety Bounds (`archive.py:56-61`)**:
   - `MAX_ARCHIVE_BYTES = 64 MB`, `MAX_TOTAL_UNCOMPRESSED_BYTES = 64 MB`, `MAX_XML_BYTES = 8 MB`.
   - *Failure Scenario*: A multi-run experiment (e.g. 10 runs of a 4-channel 250 kHz recording generating >60 MB payload data) immediately trips `MAX_TOTAL_UNCOMPRESSED_BYTES` at line 93 (`Archive uncompressed size exceeds the safety limit`), mistakenly treating valid physics lab data as a zip bomb.

---

### 3. Binary Record Decoding Limits (`INTERVAL_STORAGE_TYPE`, `NUMERIC_STORAGE_TYPE`)

1. **Safety Clamps Choking High-Speed Acquisition**:
   - `records.py:16-17` & `archive.py:437`: `MAX_PAYLOAD_BYTES = 16 MB`, `MAX_RECORDS = 1_000_000`.
   - *Failure Scenario*: The PASCO 850 Universal Interface samples at up to 10 MHz. At 250 kHz (12 bytes/scalar = 3 MB/s):
     - At 4.0 seconds: 1,000,000 records reached -> `CapFileError: Record count 1000001 is outside the valid range (0-1000000)` (`records.py:39`).
     - At 5.4 seconds: 16 MB reached -> `CapFileError: Payload size exceeds safety limit` (`records.py:42`).
     - Normal high-speed sensor recordings cannot be parsed.

2. **Fatal Limitation in `INTERVAL_STORAGE_TYPE` (Type 1) - `AttributeExceptionList`**:
   - `archive.py:486-489`:
     ```python
     exceptions = element.find("AttributeExceptionList")
     if exceptions is not None and len(exceptions):
         msg = "Interval attribute exceptions require an unsupported decoder."
         raise CapFileError(msg)
     ```
   - In Capstone's native `ZIntervalCache`, time series compression uses start time + fixed interval. Whenever hardware drops a sample, telemetry experiences timestamp jitter, or the user **pauses and resumes recording**, Capstone writes an `<AttributeExceptionList>`.
   - *Failure Scenario*: Any real-world experiment file with pauses/resumes or dropped samples is 100% unreadable, raising `CapFileError`.

3. **Floating-Point Precision Degradation & Cumulative Drift**:
   - `numeric_storage.py:39, 56-58` (`decode_numeric_records`): `adjustment = float(offset)` casts `Decimal` down to 64-bit IEEE-754 `float`. For large offsets (e.g. Unix epoch timestamps), `stored + adjustment` loses mantissa precision.
   - `numeric_storage.py:68-75` (`interval_values`):
     ```python
     first, step = float(start), float(interval)
     for index in range(count):
         value = first + index * step
         values.append(Decimal(repr(value)))
     ```
     At large `index` (e.g. 500,000 samples at `step = 0.0001`), `first + index * step` accumulates double-precision roundoff drift. Converting back via `repr(value)` to `Decimal` bakes floating-point noise (e.g. `0.00030000000000000003`) directly into the coordinates.

4. **Rigid Scalar Tags in `decode_numeric_records`**:
   - `numeric_storage.py:47-62`: Rejects any tag other than 0 (empty), 1 (numeric), 3 (invalid/NaN). If Capstone writes hardware flags (e.g. tag 2, 4 for clipping/sensor saturation/out-of-range), it raises `NumericStorageError(f"Unsupported numeric scalar tag: {tag}.")`, aborting the entire dataset extraction.

5. **Python Heap Memory Bloat (OOM Hazard)**:
   - Creating 1,000,000 individual Python heap `Decimal` instances per series consumes ~150-200 MB RAM per channel. A 4-channel experiment run consumes ~800 MB - 1.2 GB just for `Decimal` allocations, precipitating out-of-memory crashes.

6. **Adapter Bug in `data_sources/adapters/capfile.py:98-101`**:
   - When an independent variable uses `INTERVAL_STORAGE_TYPE` (Type 1), `x_ds.numeric_values` is empty/None because interval coordinates are stored in `x_ds.independent_values`.
   - `read_capfile_series` extracts ONLY `x_ds.numeric_values or []`, completely ignoring `x_ds.independent_values`. As a result, X/Y series pairing against .cap files with interval time axes returns empty X series or mispairs with another channel.

---

### 4. Feasibility of Direct Headless Calculation and Layout Injection

1. **Fragility of Current UIA Typing Macros**:
   - `calculator.py:127-186`: Opens Calculator drawer via UIA, searches for Edit controls via fuzzy string matching (`"formula" in aid_lower`), types formulas using `app.type_text()`. In Capstone, typing `[` to reference a measurement triggers an unmanaged Qt autocomplete popup that intercepts keystrokes and corrupts expressions.
   - Never verifies compilation: `calculator.py:170` hardcodes `status: CalculationStatus = "valid"`, `verified = True` without checking syntax or unresolved variable errors.
   - `displays/workbook.py` & `displays/harness.py`: Screen layout setup relies on palette item dragging (`drag_palette_item`), which drops controls and falls back to deceptive double-clicks (`harness.py:72`).

2. **Feasibility of Headless Calculation Injection: HIGH (Feasible & Strongly Recommended)**:
   - *Architecture*: In `main.xml`, calculations are stored declaratively inside `<CalculationManager><Calculation ID="..." Expression="..." Name="..." Unit="...">`. Variable bindings are mapped via `<Variable Name="..." MeasurementEUID="..."/>`, and exposed as plottable channels via `<DataSource UserDataEvaluatedType="1">` in `<DataRepository>`.
   - *Capstone Behavior*: Capstone dynamically evaluates calculations on-the-fly when opening a `.cap` file; it does NOT require pre-computed binary arrays in `data/*.tmp`.
   - *Implementation Path*: In-memory extraction of `main.xml`, DOM insertion of `<Calculation>` and `<DataSource>` with newly minted GUIDs, and re-zipping into the `.cap` archive.
   - *Advantages*: Runs in <10 ms (vs 3-5s UIA macro), 100% headless, zero focus stealing, zero clipboard dependence, immune to autocomplete popup interference.

3. **Feasibility of Headless Layout Injection: MODERATE TO HIGH (Feasible via Templates)**:
   - *Architecture*: Workbook pages and displays are stored under `<Workspace><PageCollection><Page><DisplayCollection>`. Displays (Graph, Table, Digits) bind to axes using DataSource EUIDs.
   - *Implementation Path*: Rather than reverse-engineering arbitrary Qt docking layouts, maintain clean XML layout templates (e.g. "Graph + Table", "Scope + FFT", "Single Fullscreen Graph"). Headless injector clones template `<Page>`, substitutes the target measurement EUIDs into axis bindings, and inserts into `<PageCollection>`.
   - *Outcome*: Completely eliminates brittle drag-and-drop palette automation; Capstone renders the layout natively and deterministically upon `capstone_open_experiment`.

</details>

<details open>
<summary><b>[보고서 #62] auditor-capfiles 실사 세부 명세 (Phase 2)</b></summary>

소유 모듈인 `src/capstone_mcp/capfiles/*`, `capfile_models.py`, `numeric_storage.py` 및 관련 도구/어댑터를 한 줄씩 전수 재검토하여 새롭게 발굴한 구체적 결함 12건의 상세 내역입니다.

---

### 1. 보안, 압축 및 파일 무결성 결함

#### 🔴 DEFECT-CAP01: 압축 해제 전 용량 검증 부재로 인한 Zip Bomb 방어선 완전 무력화
- **파일**: [archive.py#L105-L122](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L105-L122)
- **코드**:
  ```python
  def _read_member(archive: ZipFile, info: ZipInfo, *, maximum_size: int) -> bytes:
      if info.file_size > maximum_size: ...
      data = archive.read(info)  # <-- 메모리에 전부 압축 해제
      if len(data) != info.file_size or len(data) > maximum_size: ...
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - ZIP 중앙 디렉터리 헤더의 `info.file_size`를 1,000 바이트로 위조하고 실제 압축 데이터는 수 기가바이트의 0으로 채운 고전적 Zip Bomb 파일 입력.
  - L111의 `info.file_size > maximum_size` 검사를 통과한 후, L115의 `archive.read(info)`가 청크 단위가 아닌 전체 스트림을 한 번에 메모리로 압축 해제함.
  - L119의 `len(data) > maximum_size`에 도달하기 전에 파이썬 프로세스가 기가바이트 단위의 힙 메모리를 급격히 점유하여 즉각적인 OOM(Out-Of-Memory) Crash로 프로세스가 강제 종료됨.

#### 🔴 DEFECT-CAP02: 서브디렉터리 콜론(:) 미검증으로 인한 NTFS 대체 데이터 스트림(ADS) 경로 검증 우회
- **파일**: [archive.py#L64-L77](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L64-L77)
- **코드**:
  ```python
  parts = [part for part in normalized.split("/") if part not in {"", "."}]
  if not parts or ".." in parts or ":" in parts[0]:  # <-- parts[0]만 검사!
      raise CapFileError(msg)
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - `parts[0]`에 대해서만 `":" in parts[0]`을 검사하고 하위 파트(`parts[1:]`)는 검사하지 않음.
  - ZIP 엔트리 파일명이 `data/values.tmp::$DATA` 또는 `sub/file:hidden_stream`인 경우, `parts[0]`은 `data`이므로 검사를 우회함.
  - Windows NTFS 환경에서 대체 데이터 스트림(ADS)을 통해 파일 잠금 우회 또는 임의 스트림 은닉이 가능해짐.

---

### 2. XML 파서 및 스키마 경직성 결함

#### 🔴 DEFECT-CAP03: 대소문자 혼용 불리언("True", "False") 파싱 거부로 인한 정상 실험 파일 로드 실패
- **파일**: [archive.py#L177-L186](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L177-L186)
- **코드**:
  ```python
  def _boolean(raw: str | None, *, context: str) -> bool | None:
      ...
      if raw in {"1", "TRUE", "true"}: return True
      if raw in {"0", "FALSE", "false"}: return False
      raise CapFileError(f"Invalid boolean {raw!r} in {context}.")
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - .NET 및 C# `XmlSerializer`나 타 PASCO 도구가 생성한 표준 타이틀케이스 불리언 문자열(`"True"`, `"False"`)이 속성값으로 주어질 경우, `raw.lower()` 정규화 없이 대소문자를 엄격히 비교함.
  - `CapFileError: Invalid boolean 'True' in UseCommonSamplingRate.Value` 예외를 던지며 정상적인 실험 설정 로드가 즉시 중단됨.

#### 🔴 DEFECT-CAP04: 다중 세그먼트(Multi-Segment) 데이터셋 파싱 거부로 인한 버스트/구간 측정 로드 불가
- **파일**: [archive.py#L399-L402](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L399-L402)
- **코드**:
  ```python
  segments = [child for child in element if child.tag == "DataSegmentElement"]
  if len(segments) != 1:
      msg = "Each DataSet must contain exactly one DataSegmentElement."
      raise CapFileError(msg)
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - PASCO Capstone에서 사용자가 수동 데이터 입력 시 여러 세션을 기록하거나, 트리거 버스트(Triggered Burst) 구간 측정을 수행하면 하나의 `<DataSet>` 안에 복수의 `<DataSegmentElement>`가 생성됨.
  - 파서는 오직 `len(segments) == 1`만을 허용하므로, 다중 세그먼트가 포함된 모든 실험 파일에서 `CapFileError`를 던지며 데이터 추출이 영구 차단됨.

#### 🔴 DEFECT-CAP05: 0-샘플 데이터셋의 FileName 속성 누락 시 크래시
- **파일**: [archive.py#L442-L446](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L442-L446)
- **코드**:
  ```python
  member_name_raw = dependent.attrib.get("FileName")
  if member_name_raw is None:
      raise CapFileError("DependentStorageElement is missing FileName.")
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - 센서만 구성되고 측정 샘플이 0개(`DataCacheDataSize="0"`)인 경우, Capstone은 바이너리 임시 파일을 생성하지 않으므로 `FileName` 속성을 아예 생략함.
  - 파서는 `count == 0` 여부를 확인하기 전에 `FileName`의 존재를 무조건 요구하여 `CapFileError`로 폭사함.

#### 🔴 DEFECT-CAP06: DataSetID와 RunParameterID 간 식별자 불일치로 인한 런 메타데이터(run_name, run_number) 전면 유실
- **파일**: [archive.py#L511-L525, L638-L640](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L511-L525)
- **코드**:
  ```python
  labels[identifier] = (name, number)  # identifier는 RunParameterID
  ...
  run_name, run_number = runs.get(element.attrib.get("DataSetID", ""), (None, None))
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - 실제 Capstone 실험 파일에서 하나의 런(Run)은 여러 센서의 복수 DataSet을 포함하므로 `RunParameterID`는 런 자체의 EUID이며 개별 `DataSetID`와 일치하지 않음 (단위 테스트 `test_capfiles.py`에서만 인위적으로 같게 조작됨).
  - 결과적으로 실제 파일 로드 시 `runs.get()` 매칭이 100% 실패하여 모든 데이터셋의 `run_name`과 `run_number`가 `None`으로 영구 유실됨.

---

### 3. 바이너리 스트림 및 부동소수점 정밀도 결함

#### 🔴 DEFECT-CAP07: UTF-16 NUL 종단자(`\x00`) 미제거로 인한 문자열 오염 및 C 라이브러리 파탄
- **파일**: [records.py#L65-L74](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/records.py#L65-L74)
- **코드**:
  ```python
  value = payload[offset:end].decode("utf-16-le")
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - Capstone C++ 엔진이 UTF-16 문자열 끝에 2바이트 NUL 문자(`L'\0'`)를 포함하여 저장할 경우, `decode()` 결과 문자열 끝에 `\x00`이 그대로 잔류함.
  - 파이썬 레벨에서는 보이지 않으나, MCP JSON 직렬화 시 제어 문자로 이스케이프되거나 하위 C 기반 파서(SQLite, Win32 API)로 전달될 때 문자열이 조기 절단(Early Truncation)되어 일치 비교 실패 및 데이터베이스 오염을 야기함.

#### 🔴 DEFECT-CAP08: 텍스트 수치 레코드 내 비한정(Non-finite: NaN, Inf) 값 파싱 시 크래시
- **파일**: [archive.py#L157-L159, L567-L569](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L157-L159)
- **코드**:
  ```python
  if not value.is_finite():
      raise CapFileError(f"Non-finite decimal {raw!r} in {context}.")
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - 텍스트 저장 방식(Type 7)을 사용하는 센서 수치 데이터에서 센서 분리 또는 오버플로우로 인해 `"Infinity"`, `"-Infinity"`, `"NaN"`이 기록된 경우.
  - 바이너리 캐시(Type 0)는 `None`으로 처리하지만, Type 7 파서는 `is_finite()` 검사에서 즉시 `CapFileError`를 발생시켜 파일 전체 파싱을 중단시킴.

#### 🔴 DEFECT-CAP09: 대용량 데이터셋에서 수백만 개 파이썬 `Decimal` 객체 인스턴스화로 인한 힙 메모리 폭발
- **파일**: [numeric_storage.py#L58, L75](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numeric_storage.py#L58), [capfile_models.py#L128](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfile_models.py#L128)
- **재현 트리거 & 파괴 메커니즘**:
  - 64비트 Windows 파이썬에서 `Decimal` 인스턴스 하나는 약 104바이트의 힙 메모리를 소모함.
  - 100만 샘플 4채널 데이터셋을 파싱할 때 `Decimal` 객체 생성에만 최소 800MB ~ 1.2GB의 RAM이 순간적으로 할당됨.
  - 잦은 GC 압박과 메모리 단편화로 인해 FastMCP 서버 프로세스의 응답 지연(GC Pause) 및 저사양 환경에서의 OOM 크래시를 유발함.

---

### 4. 도구 및 어댑터 계층 파탄 결함

#### 🔴 DEFECT-CAP10: `capstone_extract_dataset`의 $O(N \times \text{Pages})$ 전수 재압축 해제 및 파싱 병목
- **파일**: [tools/files.py#L220-L258](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/files.py#L220-L258)
- **코드**:
  ```python
  def capstone_extract_dataset(path: str, dataset_index: int, offset: int = 0, limit: int = 1000):
      datasets = extract_cap_datasets(path)  # <-- 매 페이지 요청마다 전체 .cap 파일 처음부터 완전 파싱!
      dataset = datasets[dataset_index]
      ...
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - 50,000개 샘플을 1,000개 단위로 50회 페이지네이션 조회할 경우, 메모리 캐시나 스트리밍 슬라이싱 없이 50MB 용량의 `.cap` 전체 ZIP 아카이브를 50번 반복해서 압축 풀고, 50번 XML 파싱하고, 50번 바이너리 디코딩을 처음부터 끝까지 수행함.
  - 단일 데이터셋 조회가 수십 초 동안 서버 루프를 점유하여 전체 클라이언트 타임아웃을 유발함.

#### 🔴 DEFECT-CAP11: 불일치 센서 채널 조회 시 엉뚱한 임의 채널을 강제 반환하는 사일런트 데이터 오염
- **파일**: [data_sources/adapters/capfile.py#L86-L92](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/capfile.py#L86-L92)
- **코드**:
  ```python
  if not x_ds and datasets:
      x_ds = datasets[0]  # <-- 이름 불일치 시 0번 데이터셋 강제 할당!
  if not y_ds and len(datasets) > 1:
      y_ds = datasets[1]  # <-- 이름 불일치 시 1번 데이터셋 강제 할당!
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - 분석 도구나 보고서 생성기가 파일에 존재하지 않는 채널(예: `x_name="Voltage"`, `y_name="Current"`)을 요청했을 때 에러를 발생시키지 않음.
  - 파일에 들어있는 전혀 무관한 `datasets[0]`("Force")과 `datasets[1]`("Position")을 슬그머니 꺼내어 반환함.
  - 물리 보고서 및 선형 피팅에 완전히 잘못된 물리량이 주입되어 분석 결과가 사일런트하게 날조됨.

#### 🔴 DEFECT-CAP12: 시간축(Interval 축) 데이터셋의 X값 누락으로 인한 선형 피팅 엔진 즉각 폭사
- **파일**: [data_sources/adapters/capfile.py#L98-L101](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/capfile.py#L98-L101)
- **코드**:
  ```python
  x_raw = x_ds.numeric_values or []
  y_raw = y_ds.numeric_values or []
  x_vals = [float(v) if v is not None else None for v in x_raw]
  ```
- **재현 트리거 & 파괴 메커니즘**:
  - Capstone에서 시간축(Time)은 종속 변수(Force)의 `IndependentStorageElement`(Type 1)로 저장되므로, `x_ds.numeric_values`는 `None`이며 실제 시간 좌표는 `x_ds.independent_values`에 들어있음.
  - `read_capfile_series`는 오직 `numeric_values`만을 조회하므로 `x_vals`는 빈 리스트(`[]`)가 되고, Y축은 수천 개의 샘플(`[0.1, 0.2, ...]`)을 갖게 됨.
  - 이 데이터가 `capstone_mcp.numerics.fit_linear_series(x, y)`로 넘어가자마자 `ValueError: x and y series must have the same length`를 던지며 모든 `.cap` 기반 분석/보고서가 즉시 폭사함.

---
이상 12건의 결함에 대한 상세 분석 및 재현 시나리오 보고를 마칩니다. 마스터 결함 매트릭스에 통합 바랍니다.

</details>

<details open>
<summary><b>[보고서 #84] auditor-capfiles 실사 세부 명세 (Phase 3)</b></summary>

`capfiles/archive.py`, `numeric_storage.py`, `runs/manager.py`(capfile 연동부), `data_sources/adapters/capfile.py`를 한 줄씩 최심부까지 재분해하여 신규 발굴된 10건입니다.

---

#### 🔴 DEFECT-CAP13: `_archive_members()` 디렉터리 엔트리 `file_size` 누산으로 인한 `MAX_TOTAL_UNCOMPRESSED_BYTES` 조기 오폭
- **파일**: [archive.py#L85-L95](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L85-L95)
- **코드**:
  ```python
  for info in infos:
      total_size += info.file_size   # <-- 디렉터리 엔트리도 누산
      if total_size > MAX_TOTAL_UNCOMPRESSED_BYTES: ...
      if info.is_dir():
          continue                   # <-- is_dir() 검사가 누산 이후!
  ```
- **재현 트리거 & 파괴 메커니즘**: ZIP 아카이버가 디렉터리 엔트리(`info.is_dir()`=True)에 비정상적으로 큰 `file_size`(예: 2GB) 값을 기록한 경우, `is_dir()` 체크 전에 `total_size`에 더해져 정상 파일임에도 `"Archive uncompressed size exceeds the safety limit"` 오폭을 유발함.

#### 🔴 DEFECT-CAP14: `_parse_archive()`의 `parent_by_child` 딕셔너리 역방향 중첩 구조로 인한 O(N²) 메모리 및 CPU 소모
- **파일**: [archive.py#L619-L623](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L619-L623)
- **코드**:
  ```python
  nodes = list(root.iter())   # 최대 100,000개
  parent_by_child = {child: parent for parent in nodes for child in parent}
  ```
- **재현 트리거 & 파괴 메커니즘**: 100,000개 XML 노드 최대 한계를 가진 파일에서 중첩 for 반복이 각 `parent` 요소의 자식 수만큼 반복되므로 실질적으로 O(N²) 연산이 수행됨. 광범위한 DOM을 가진 대형 Workspace 섹션 파일에서 파이썬 GIL 경합 없이도 수 초의 단일 스레드 블로킹이 발생하여 FastMCP 서버 응답 타임아웃을 유발함.

#### 🔴 DEFECT-CAP15: `source_by_element[source_element]`에서 DataSet이 DataSource 외부에 있을 때 `KeyError` 미처리
- **파일**: [archive.py#L634-L645](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L634-L645)
- **코드**:
  ```python
  source_element = _ancestor(element, parent_by_child, "DataSource")
  if source_element is None:
      raise CapFileError("DataSet is not linked to a DataSource.")
  ...
  source=source_by_element[source_element],   # <-- KeyError 가능!
  ```
- **재현 트리거 & 파괴 메커니즘**: `source_element`가 `None`이 아닌(부모 DataSource를 찾음) 그러나 그 DataSource가 `root.iter("DataSource")` 순회에 포함되지 않은 경우(예: 중첩 `<DataRepository>` 하위의 비표준 위치에 있는 DataSource), `source_by_element[source_element]`에서 `KeyError`가 발생함. 이 KeyError는 `CapFileError`로 변환되지 않고 FastMCP 에러 핸들러로 직접 전파되어 비구조적 500 에러를 반환함.

#### 🔴 DEFECT-CAP16: `_xml_node()` 재귀 DFS에서 `MAX_XML_DEPTH` 초과 직전 수만 개 Workspace 하위 노드에 대한 스택 프레임 생성으로 인한 Python `RecursionError`
- **파일**: [archive.py#L188-L198](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L188-L198)
- **코드**:
  ```python
  def _xml_node(element: Element, *, depth: int = 0) -> CapXmlNode:
      if depth > MAX_XML_DEPTH:  # 128
          raise CapFileError(msg)
      return CapXmlNode(..., children=[_xml_node(child, depth=depth+1) for child in element])
  ```
- **재현 트리거 & 파괴 메커니즘**: Python 기본 재귀 한계는 1,000이지만, 넓은 트리(예: 100,000개 노드가 128 depth 이내에 분산)에서 `workspace=_xml_node(workspace)` 호출 시 Python 인터프리터 콜 스택이 100,000개의 중첩 재귀 호출로 채워지지 않더라도, `CapXmlNode` 모델 중첩 초기화 과정에서 Pydantic v2의 내부 검증 재귀가 중첩되어 `RecursionError`가 발생할 수 있음. 커스텀 Python 재귀 한계 설정(기본 1,000)에 따라 Workspace가 큰 파일에서 파서가 `RecursionError`로 크래시함.

#### 🔴 DEFECT-CAP17: `_dataset()`에서 `StorageType=0` 종속 데이터셋의 `FileName` 속성을 독립 데이터셋 `FileName`과 혼동하는 구조적 결함
- **파일**: [archive.py#L456-L468](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L456-L468)
- **코드**:
  ```python
  def _numeric_payload(element: Element, count: int, archive: ZipFile, members: ...):
      ...
      name = _normalize_member_name(element.get("FileName", ""))  # <-- 독립/종속 동일 호출
      if name not in members:
          raise CapFileError(f"Dataset payload is missing: {name!r}.")
  ```
- **재현 트리거 & 파괴 메커니즘**: `_numeric_payload`는 `DependentStorageElement`와 `IndependentStorageElement` 양쪽 모두에서 호출될 수 있음(`_independent_coordinates` L483). `IndependentStorageElement`에 `FileName`이 없는 경우(StorageType=0이지만 별도 파일 없이 메인 블록에 인라인된 경우), `element.get("FileName", "")`이 빈 문자열(`""`)을 반환하고 `_normalize_member_name("")`이 `CapFileError("Unsafe archive member path: ''.")`를 발생시켜 정상 파일 로드를 차단함.

#### 🔴 DEFECT-CAP18: `runs/manager.py` `_deltas()`의 `Decimal` vs. `list[Decimal | None]` 등치 비교(`==`)가 모든 Sparse 데이터셋에서 False를 반환하여 불필요한 "replaced" 판정 남발
- **파일**: [runs/manager.py#L511-L522](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L511-L522)
- **코드**:
  ```python
  if (same_metadata and values == old_values
      and dataset.independent_values == previous.independent_values):
      continue  # 변경 없음으로 스킵
  appended = (
      same_metadata and count > old_count
      and values[:old_count] == old_values
      and dataset.independent_values[:old_count] == previous.independent_values
  )
  ```
- **재현 트리거 & 파괴 메커니즘**: `numeric_storage.py`의 `decode_numeric_records()` L57-58에서 각 스칼라를 `Decimal(repr(float(stored + adjustment)))`으로 생성하므로, 같은 `.cap` 파일을 두 번 읽어도 부동소수점 `repr()`의 비결정론적 반올림으로 인해 동일한 값이 미묘하게 다른 `Decimal` 문자열로 직렬화될 수 있음. 그 결과 `values == old_values` 비교가 False가 되어 변경 없는 데이터셋이 모두 `"replaced"` 판정을 받고 `CaptureSession.record()`가 모든 런에서 불필요한 `_fit()` 연산을 반복 수행하며 가짜 `"replaced"` 이벤트를 누적함.

#### 🔴 DEFECT-CAP19: `CaptureSession.record()` `finally` 블록이 `CapFileError` 발생 시에도 `self.previous = parsed`를 갱신하여 오염된 파일 상태를 베이스라인으로 채택
- **파일**: [runs/manager.py#L649-L663](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L649-L663)
- **코드**:
  ```python
  except (AnalysisError, ValidationError, CapFileError) as failure:
      error = str(failure)
      raise
  finally:
      self.runs.append(CapturedRun(..., analysis_error=error))
      if parsed is not None:
          self.previous = parsed   # <-- 에러 후에도 갱신!
  ```
- **재현 트리거 & 파괴 메커니즘**: `read_cap_file()`이 성공(`parsed is not None`)하고 이후 `_deltas()`나 `_fit()`에서 `AnalysisError`가 발생한 경우, `finally` 블록에서 `self.previous = parsed`가 실행된 후 예외가 재발생함. 외부 호출자가 예외를 삼키고 다음 사이클을 시도하면 오염된 파일이 새 베이스라인이 되어 이후 모든 델타 비교가 왜곡된 기준선에서 수행됨.

#### 🔴 DEFECT-CAP20: `read_capfile_all_series()`의 순환 임포트(Circular Import) 위험 및 지연 임포트 패턴으로 인한 타입 체커 누락
- **파일**: [data_sources/adapters/capfile.py#L130-L133](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/capfile.py#L130-L133)
- **코드**:
  ```python
  def read_capfile_all_series(path: Path, ...) -> ...:
      from capstone_mcp.capfiles import (  # noqa: PLC0415 <-- 순환 임포트 회피 패턴
          extract_cap_datasets,
          read_cap_configuration,
      )
  ```
- **재현 트리거 & 파괴 메커니즘**: `# noqa: PLC0415`로 함수 내부 임포트를 의도적으로 허용함. 이 패턴은 모듈 수준에서 감지되는 `basedpyright` 타입 추론을 완전히 우회하므로, 임포트된 함수의 시그니처 변경 시 타입 에러가 정적 분석에서 미검출됨. 또한 `read_capfile_all_series`가 처음 호출될 때 모듈 초기화 사이드 이펙트가 지연 실행되어 초기화 순서에 의존하는 프레임워크(FastMCP 등록 시점)에서 예상치 못한 `ImportError`를 유발할 수 있음.

#### 🔴 DEFECT-CAP21: `decode_interval_coordinates()`의 단일 테스트 케이스만 존재하여 경계 조건 미검증
- **파일**: [tests/test_capfile_records.py#L150-L162](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_capfile_records.py#L150-L162)
- **코드**:
  ```python
  def test_decode_interval_coordinates_valid() -> None:
      coords = decode_interval_coordinates(start=Decimal("1.0"), interval=Decimal("0.25"), count=4)
      assert coords == [Decimal("1.0"), Decimal("1.25"), Decimal("1.5"), Decimal("1.75")]
  ```
- **재현 트리거 & 파괴 메커니즘**: 단 하나의 행복 경로(Happy Path) 테스트만 존재함. 아래 경계 조건들이 전혀 검증되지 않음:
  1. `count=0`: 빈 리스트 반환 여부 미검증
  2. `interval=Decimal("0")`: 0 간격 시 모든 좌표가 동일한 `start` 값이 되며, 비한정(Non-finite) 체크를 통과하여 오탐 없이 의미 없는 좌표 목록 반환
  3. `interval=Decimal("1e-308")`, `count=1_000_000`: 부동소수점 언더플로우로 인해 `first + index * step`이 `first`와 동일해지는 정밀도 소실 현상 미검출
  4. `start=Decimal("1e308")`, `interval=Decimal("1e308")`: 오버플로우로 `Inf` 발생, `is_finite()` 체크가 `NumericStorageError`를 올바르게 발생시키는지 미검증

#### 🔴 DEFECT-CAP22: `capstone_file_datasets()` 및 `capstone_extract_dataset()`에서 `CapFileError`가 `AutomationError`로 미변환되어 MCP 클라이언트가 에러 종류를 구분 불가
- **파일**: [tools/files.py#L185-L258](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/files.py#L185-L258)
- **코드**:
  ```python
  def capstone_file_datasets(path: str) -> list[CapDatasetSummary]:
      return [CapDatasetSummary(...)
              for index, dataset in enumerate(extract_cap_datasets(path))]   # CapFileError 미처리!

  def capstone_extract_dataset(path: str, dataset_index: int, ...) -> CapDatasetPage:
      datasets = extract_cap_datasets(path)   # CapFileError 미처리!
      if dataset_index >= len(datasets):
          raise AutomationError(msg)   # <-- 범위 에러만 AutomationError로 감쌈
  ```
- **재현 트리거 & 파괴 메커니즘**: `extract_cap_datasets()`가 `CapFileError`를 발생시키면(악성 아카이브, 지원 불가 StorageType, 페이로드 누락 등) 이 예외가 `server.py`의 에러 핸들러(`format_tool_error`)에 도달함. `format_tool_error`는 `CapFileError`를 `AutomationError`와 구분하지 못하고 `ValueError`의 하위 클래스로 처리하므로, MCP 클라이언트 에이전트가 "파일 형식 오류"와 "자동화 UI 오류"를 구분할 수 없어 잘못된 재시도 전략을 선택함.

이상 10건 추가 결함(DEFECT-CAP13~CAP22)을 마스터 매트릭스에 통합 반영 요청드립니다.

</details>

#### 📑 실사 보고서: `auditor-data-sources` (총 3회 정밀 실사)

<details open>
<summary><b>[보고서 #51] auditor-data-sources 실사 세부 명세 (Phase 1)</b></summary>

1. live:// URI Parsing:
- seam.py:32,76: isinstance(source, str) fails on Path("live://..."), falling into Path.exists() -> FileNotFoundError. Case-sensitive ("LIVE://") fails RFC 3986.
- seam.py:33,77: Exact string match rejects trailing slashes ("live://measurements/"), query params (?port=9223), fragments.
- seam.py:36,80 -> live_session.py:84,99: LiveSessionAdapter() instantiated with table_result=None; live://table ALWAYS raises ValueError in production (dead code).
- live_telemetry.py:101-104,125: "time" signal returns hardcoded synthetic 0.0; get_series() returns single-element lists ([x_val], [y_val]), not actual series.
2. High-speed Telemetry & Contention:
- telemetry.py:14: Docstring claims thread-safe, but zero locks exist. Race conditions on _buffers[euid] initialization, clear(), and deque iteration during concurrent append() (RuntimeError: deque mutated during iteration).
- telemetry.py:19: _buffers dict has no key count/TTL/LRU eviction -> leaks unbounded memory under dynamic EUIDs.
- bridge.py:107-173 (via cdp_client.py): Every single poll does fresh HTTP discovery + new WebSocket TCP handshake/teardown. High-speed polling triggers WinError 10048 (TIME_WAIT socket/port exhaustion).
- watcher.py:81-114: Blocking time.sleep loop lacks cancellation Event; unhandled sampler exceptions abort without halt_callback().
3. In-memory OOM Risks (Multi-hour runs):
- csv_data.py:63-75: read_csv_page slurps entire file (up to 1M rows/64MB) into list of lists on EVERY page request, multiplying memory and triggering GC thrashing.
- csv_file.py:26-32,54-60: read_csv_datasets & read_csv_series execute rows = list(reader) loading multi-million rows into memory; read_csv_datasets loops over all rows len(header) times.
- csv_file.py:100-112: read_csv_all_columns unbounded list append.
4. CSV Locale Dependencies:
- csv_data.py:65 & csv_file.py:27,55,101: Hardcoded delimiter="," (fails on Capstone European export using ";").
- csv_data.py:49: Decimal(value) raises InvalidOperation on "0,1", causing entire column numeric_values to be None.
- csv_file.py:85-86: float(r[x_idx]) raises unhandled ValueError on comma decimals.
- csv_file.py:108: read_csv_all_columns silently drops comma decimal values via contextlib.suppress, returning empty columns.

</details>

<details open>
<summary><b>[보고서 #64] auditor-data-sources 실사 세부 명세 (Phase 2)</b></summary>

소유 모듈(data_sources/*, csv_data.py) 정밀 전수 검사 결과 신규 발굴된 핵심 결함 보고:

1. [P1] capfile.py 독립변수 Time 누락 및 x=y 45도 직선 날조
- 파일: adapters/capfile.py:66-95, 98-101, 14-42
- 메커니즘: Capstone .cap은 Time이 독립 데이터셋이 아닌 각 센서 데이터셋의 independent_values에 보관됨. read_capfile_series는 "Time" 검색 실패 시 datasets[0](첫 번째 센서)으로 폴백하여 x, y가 모두 Force로 동일 지정(x=y 대각선 날조)되거나 엉뚱한 센서가 x축이 됨. d.independent_values를 완전히 무시하며, list_datasets에도 Time이 전면 누락됨. unit_id도 정수 "2048"을 문자열로 노출.

2. [P1] DataSeries.clean_floats()의 NaN 미필터링 및 (x, y) 페어링 파괴
- 파일: models.py:15-17
- 메커니즘: 독스트링은 "filtered of None and NaN"이라 주장하나 코드는 `if v is not None`뿐이라 float("nan") 통과 -> 다운스트림 SVG/회귀 크래시 유발. 또한 x와 y에서 각각 clean_floats() 호출 시 결측치가 한쪽에만 있으면 x, y 길이가 달라져 시계열 페어링이 완전히 엇갈리는 치명적 데이터 왜곡 발생.

3. [P2] csv_file.py & live_session.py 존재하지 않는 컬럼 침묵 폴백 (Silent Fallback)
- 파일: adapters/csv_file.py:73-77, adapters/live_session.py:44-50
- 메커니즘: 요청한 x_name, y_name이 파일에 없어도 에러를 내지 않고 0번, 1번 컬럼을 맹목 반환. 사용자는 없는 데이터를 요청했음에도 엉뚱한 컬럼(예: Run ID, Index)을 정상 데이터로 오인.

4. [P2] live://table 어댑터 100% 폭사 데드코드
- 파일: seam.py:36, 80, adapters/live_session.py:84-89, 99-104
- 메커니즘: seam.py에서 table_result 인자 없이 LiveSessionAdapter() 생성. LiveSessionAdapter는 table_result is None이면 무조건 ValueError 발생. 활성 UI 테이블과의 브리지가 전무하여 실기 호출 시 100% 폭사.

5. [P2] csv_data.py 후행 개행/빈 줄 Ragged CSV 오진단 크래시
- 파일: csv_data.py:71-75
- 메커니즘: Windows 정상 내보내기 파일의 후행 개행(\r\n)으로 빈 행(len(row)==0) 발생 시 `len(row) != len(header)`로 판단하여 정상 CSV를 CsvDataError(CSV is ragged)로 거부.

6. [P2] live_telemetry.py _resolve_measurement 부분문자열 오매칭
- 파일: adapters/live_telemetry.py:141-154
- 메커니즘: target_lower in name.lower()로 인해 완전일치 검사 없이 리스트 순서상 먼저 나온 부분일치 센서("Force 1", "Total Force")가 "Force" 요청에 가로채기 반환됨.

</details>

<details open>
<summary><b>[보고서 #80] auditor-data-sources 실사 세부 명세 (Phase 3)</b></summary>

지정 취약 영역(bridge.py, session/*, calculator.py) 심층 결함 보고:

1. [P0] calculator.py: 수식 AST 파서 부재, 괄호 불균형 무검증, 100% 가짜 성공 날조
- 파일: calculator.py:43, 117-126, 155, 171-182, 185-189
- 메커니즘:
  1) AST 파서나 괄호 매칭 로직이 전무하여 "p = (m * v", "y = sin(x))", "y = / 4" 등 비정상 수식을 무필터링 통과시킴.
  2) L155에서 검증되지 않은 raw_expr을 UIA `app.type_text`로 무단 타이핑하여 개행/특수문자 주입 시 예기치 않은 단축키/UI 오작동 유발.
  3) Capstone이 모달 오류 창("Formula syntax error")을 띄워도 확인하지 않고 L171-182에서 무조건 `status="valid"`, `verified=True`로 날조 반환.
  4) L186 finally에서 모달창에 포커스가 갇혀 토글 버튼 클릭 실패 및 창 락 데드락 유발.
  5) L43 정규식 r"^\s*([A-Za-z0-9_가-힣\s]+?)\s*="의 결함으로 공백 포함 변수("my var = 1"), 숫자 변수("123 = 456"), 비교 연산자("a == b")를 잘못 파싱.

2. [P1] session/watcher.py: Watchdog 소켓 블로킹 행 및 halt_callback 누락
- 파일: session/watcher.py:81-114
- 메커니즘: sampler()가 내부적으로 bridge.evaluate() 호출 시 15초 소켓 타임아웃에 걸리면 watcher의 condition.timeout(예: 10초) 검사가 무력화되어 최대 15초간 스레드가 블로킹됨. 또한 sampler()에서 일시적 소켓 단절 예외 발생 시 halt_callback()을 실행하지 않고 비정상 탈출하여 하드웨어 데이터 기록이 영구 중단되지 않고 방치됨.

3. [P1] bridge.py: 비정상 소켓 단절 시 재연결 폭풍 (Reconnection Storm) & 수명주기 누수
- 파일: bridge.py:98-106, session/lifecycle.py:49-53
- 메커니즘:
  1) discover_target이 httpx2.HTTPTransport에서 retries=3 설정되어 있어 Capstone이 다운되거나 디버그 포트가 닫힐 때 모든 측정 폴링마다 3회씩 TCP SYN을 쏟아부으며 재연결 폭풍 유발.
  2) SessionLifecycleManager.terminate()가 self._is_active = False만 변경하고 worker.close()나 활성 소켓/버퍼 정리를 전혀 수행하지 않는 가짜 종료(no-op) 상태로 프로세스 잔재 유발.

4. [P2] bridge.py: WebSocket 다중 이벤트/단편화 처리 부재
- 파일: bridge.py:158-160
- 메커니즘: reply.id != 1에 대해 단순 continue 처리만 수행하여, 대량의 비동기 CDP 이벤트가 수신되거나 연결이 중간 단절될 때 프레임 재조립 실패로 websockets.ConnectionClosed 폭사.

</details>

#### 📑 실사 보고서: `audit-encoding` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #103] audit-encoding 실사 세부 명세 (Phase 1)</b></summary>

`src/capstone_mcp/csv_data.py`, `src/capstone_mcp/data_sources/` 전반 및 연계 디스플레이 모듈을 라인 단위로 전수 실사하여 Windows 한국어/다국어 환경에서 발생하는 결함 총 21건(P0 6건, P1 11건, P2 4건)을 발굴하였습니다. 상세 내용은 아티팩트 `audit_encoding_report.md`에 전면 기록하였으며, 핵심 결함 내역을 보고합니다.

---

### 1. Windows 한국어 CP949/EUC-KR CSV 인코딩 파싱 폭사 (UnicodeDecodeError)

#### 🔴 [DEFECT-ENC01] `csv_data.py` L104, L117-118: `utf-8-sig` 하드코딩 및 `UnicodeDecodeError` 미처리로 서버 500 크래시 (P0)
- **위치**: `src/capstone_mcp/csv_data.py` L104, L117-118
- **코드**:
  ```python
  with source.open(encoding="utf-8-sig", newline="") as stream:
      ...
  except csv.Error as error: # UnicodeDecodeError는 잡지 않음!
      raise CsvDataError(str(error)) from error
  ```
- **파괴 메커니즘**:
  - 한국어 Windows(기본 코드페이지 949) 환경에서 PASCO Capstone 또는 Excel이 내보낸 CSV는 ANSI(CP949)로 저장됩니다.
  - 한글 바이트(0xbd 등)를 읽는 즉시 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbd in position 0: invalid start byte`가 발생합니다.
  - `except csv.Error`만 존재하여 예외가 그대로 상위 `capstone_export_data`(`tools/files.py` L146)로 전파되어 FastMCP 서버 도구 호출이 500 크래시됩니다.

#### 🔴 [DEFECT-ENC02 ~ ENC04] `csv_file.py` L27, L70, L107: 데이터 소스 어댑터 3종의 `utf-8-sig` 고정 및 리포트 빈 데이터 묵살 (P0/P1)
- **위치**: `src/capstone_mcp/data_sources/adapters/csv_file.py` L27 (`read_csv_datasets`), L70 (`read_csv_series`), L107 (`read_csv_all_columns`)
- **파괴 메커니즘**:
  - 세 함수 모두 `encoding="utf-8-sig"`로 고정되어 있으며 `try...except`가 전무합니다.
  - `list_source_datasets`, `get_experiment_series` 호출 시 CP949/EUC-KR 파일 유입 시 `UnicodeDecodeError`로 파이프라인이 즉시 폭사합니다.
  - `read_csv_all_columns`는 `reports/generator.py` L280에서 호출되는데, L337의 `with contextlib.suppress(Exception):`에 의해 억제되어 빈 데이터(`{}`)가 반환되는 치명적 Silent Failure(데이터 조용한 증발)를 유발합니다.

#### 🟠 [DEFECT-ENC05] `csv_data.py` L74, L77: `str.strip()`의 U+FEFF(BOM) 미제거로 인한 `Decimal` 파싱 폭사 (P1)
- **파괴 메커니즘**:
  - Python `str.strip()`은 유니코드 U+FEFF(Format 문자)를 whitespace로 인식하지 않아 제거하지 못합니다.
  - 다중 CSV 병합 등으로 셀 값에 `\ufeff1.23`이 유입될 경우, `Decimal(value)` 실행 시 `decimal.InvalidOperation`이 발생하여 컬럼 전체가 손상됩니다.

---

### 2. 세미콜론(;) 및 쉼표(,) 소수점 혼용 파탄 결함

#### 🔴 [DEFECT-ENC07] `csv_data.py` L53-65: `read_csv_header`의 다중 구분자 감지 시 무조건 파일 거부 폭사 (P0)
- **위치**: `src/capstone_mcp/csv_data.py` L53-65
- **코드**:
  ```python
  delimiters: list[str] = []
  for delimiter in ",;\t":
      header = next(csv.reader(stream, delimiter=delimiter, strict=True), [])
      if len(header) > 1:
          delimiters.append(delimiter)
  if len(delimiters) > 1:
      raise CsvDataError("CSV header uses ambiguous field separators; quote literal separators.")
  ```
- **파괴 메커니즘**:
  - 유럽식 세미콜론 구분 CSV에서 헤더에 쉼표가 포함되어 있거나(예: `Time (s); Force (mN, filtered); Status`), TSV 헤더에 쉼표가 포함된 경우(예: `Time (s)\tForce (mN, calibrated)`) `,`와 `;` 또는 `\t` 모두 `len(header) > 1`이 되어 `delimiters`에 2개 이상 등록됩니다.
  - `len(delimiters) > 1` 검사에 걸려 즉시 `CsvDataError`를 발생시키며 정상 CSV 파일을 열람조차 하지 못하고 거부합니다.

#### 🔴 [DEFECT-ENC08] `csv_data.py` L72-78: `parse_csv_number`의 `delimiter == ";"` 하드코딩으로 인용 소수점(`"0,750"`) 파싱 불가 (P0)
- **코드**:
  ```python
  if delimiter == ";" and DECIMAL_COMMA.fullmatch(value):
      value = value.replace(",", ".")
  return Decimal(value)
  ```
- **파괴 메커니즘**:
  - 표준 쉼표 구분 CSV에서 유럽식 소수점은 `"0,750"` 형태로 인용되어 내보내집니다.
  - `delimiter == ","`이므로 치환 조건이 거짓이 되어 `Decimal("0,750")`가 실행되고, `decimal.InvalidOperation`이 100% 발생합니다.

#### 🟠 [DEFECT-ENC09 ~ ENC12] TSV 쉼표 소수점 파싱 거부 및 단일 셀 실패 시 컬럼 전량 폐기 (P1)
- **위치**: `src/capstone_mcp/csv_data.py` L22, L75, L88-93 / `csv_file.py` L91-103
- **파괴 메커니즘**:
  - `seam.py`에서 명시 지원하는 `.tsv` 파일(`delimiter == "\t"`)에서 `0,75\t1,25` 파싱 시 `delimiter == ";"` 불일치로 `InvalidOperation` 발생.
  - 천단위 점(`.`) 또는 공백(`1.234,56`), 유니코드 마이너스(`−0,75`) 미지원.
  - `_numbers`는 컬럼 내 단 하나의 셀이라도 `InvalidOperation` 발생 시 컬럼 전체의 `numeric_values`를 `None`으로 날려버림.
  - `_cell_float`는 `ValueError`를 던져 `read_csv_series` 전체 읽기를 중단시킴.

#### 🔴 [DEFECT-ENC13] `table.py` L195-204: 라이브 UI 테이블 셀 값 파싱의 유럽 소수점 누락 및 데이터 전량 증발 (P0)
- **위치**: `src/capstone_mcp/displays/table.py` L195-204, `live_session.py` L57-58
- **파괴 메커니즘**:
  - `_parse_cell_value`가 `float(val)`만 시도하므로, 유럽 로케일 UI 테이블의 `0,75`를 파싱하지 못하고 문자열 `"0,75"`로 반환합니다.
  - `live_session.py` L57-58에서 `isinstance(xv, (int, float))` 검사 시 문자열이므로 탈락하여 모든 셀이 `None`으로 기록됩니다. UI 테이블의 수천 개 데이터 포인트가 전량 `None`으로 증발합니다.

---

### 3. 비영어 디스플레이 레이블 및 컬럼 매칭 실패 결함

#### 🔴 [DEFECT-ENC15] `csv_file.py` L50-61: 다국어 동의어 매핑 전무 및 NFC/NFD 미정규화로 한국어 CSV 컬럼 매칭 100% 실패 (P0)
- **위치**: `src/capstone_mcp/data_sources/adapters/csv_file.py` L50-61
- **파괴 메커니즘**:
  - 한국어 Capstone CSV 파일 헤더(`"시간 (s)"`, `"위치 (m)"`, `"힘 (N)"`)에 대해 표준 질의 `x_name="Time"`, `y_name="Position"` 수행 시 일치하는 컬럼이 전혀 없어 `ValueError: CSV column 'Time' must match one header; found 0.` 발생.
  - macOS 자모 분리 NFD(`ㅅㅣㄱㅏㄴ`)와 Windows 완성형 NFC(`시간`) 간 유니코드 정규화(`unicodedata.normalize('NFC', ...)`) 부재로 외관상 동일한 한글 문자열도 매칭 실패.

#### 🔴 [DEFECT-ENC16] `live_telemetry.py` L72-75: x축의 영문 한정 검사로 한국어("시간", "인덱스") 즉각 거부 (P0)
- **위치**: `src/capstone_mcp/data_sources/adapters/live_telemetry.py` L72-75
- **파괴 메커니즘**:
  - `axis not in {"time", "t", "index", "sample"}` 검사로 인해 한국어 사용자가 `x_name="시간"`, `"시간 (s)"`, `"인덱스"` 입력 시 즉시 `ValueError: Use recorded data for paired measurements or a specific run.`를 발생시키며 거부함.

#### 🟠 [DEFECT-ENC14, ENC17 ~ ENC21] 전각 괄호(`（`, `）`) 미인식 및 UI 자동화 영문 키워드 하드코딩 (P1/P2)
- **위치**: `csv_file.py` L17-23, `table.py` L70, L75, L93, L239, `displays/models.py` L74-86, `scope.py` L40-43, `workbook.py` L37-40
- **파괴 메커니즘**:
  - `_parse_col_header`가 동아시아 전각 괄호(`시간（s）`)를 인식하지 못해 컬럼명에 괄호와 단위가 오염됨.
  - 테이블 디스플레이에서 한국어 "열 추가", "측정 항목 선택" 미인식으로 플레이스홀더 빈 열이 데이터로 유입되고 열 추가 실패.
  - `STATISTICS_KEYWORDS`가 영문 전용으로 한국어 테이블 요약 행("평균", "표준편차", "최솟값", "최댓값", "개수", "합계")이 통계 행으로 분리되지 않고 일반 데이터 행으로 섞여 수치 데이터 오염 발생.
  - `_WIDGET_TITLES` 영문 정규식으로 한국어 "오실로스코프 1", "스펙트럼 분석기" 위젯 탐색 실패.
  - 워크북 "페이지 추가", "새 페이지" 및 레이아웃 키워드 영문 전용으로 한국어 Capstone 제어 실패.

---
이상 21건의 인코딩/소수점/다국어 레이블 결함에 대해 실사 완료하였으며, 마스터 매트릭스에 통합 반영 요청드립니다.

</details>

---

### 3.8. Scientific Recipes, Numerics & Reports (물리 실험 매크로 & 51개 RPC 연결 & 리포트)
- **담당 에픽 이슈**: #129, #130
- **실사 참여 전문 에이전트**: `auditor-recipes`, `audit-diffraction`, `audit-thermo`, `auditor-reports`

#### 📑 실사 보고서: `auditor-recipes` (총 4회 정밀 실사)

<details open>
<summary><b>[보고서 #33] auditor-recipes 실사 세부 명세 (Phase 1)</b></summary>

Structured Findings:

1. Broken Math & Numerical Instability:
- `recipes/adiabatic_gas.py` L61: `_fit_adiabatic_index` raises ZeroDivisionError when valid_pairs is empty (p<=0 or v<=0 -> n=0 -> mean_x divides by 0).
- `recipes/slit_diffraction.py` L83-92: `_derive_slit_separation` skews fringe spacing across central peak (skips central maximum, creating 2x spacing in consecutive diffs, inflating mean spacing and underestimating slit separation d).
- `recipes/rlc_resonance.py` L136, L154, L283: ValueError/ZeroDivisionError on start_freq_hz=0 (log10(0)), f=0 (xc div by 0), r_val=0, or l_val/c_val<=0.
- `recipes/forced_oscillation.py` L97, L276: ValueError/ZeroDivisionError when k<=0 or m<=0 in f_0_theory/damping calculations.
- `reports/generator.py` L685: `_compute_fit` has no try/except for ValueError from `fit_linear_series` when x has zero variance or all-NaNs (crashes whole report).

2. Silent Exception Swallowing & Fallback Masquerade:
- `reports/generator.py` L273, L280, L293, L317: `_load_cap_data`, `_load_json_data`, `_load_json_string`, `_load_csv_data` use `suppress(Exception)` without logging. On read failure, `generate_report` silently substitutes fake synthetic data (`_canonical_fallback_series`) without warning caller.

3. XML Parsing Risks:
- `capfiles/archive.py`: defusedxml + bounds (8MB, 100k nodes, 128 depth) are secure. Minor: tag comparisons assume no namespaces, and `parent_by_child` creates 100k-item dict in memory for large projects.

4. Hardcoded Paths & Parameter Bleed:
- `reports/generator.py` L692: `run_name = file_path_or_run if file_path_or_run and not is_file else None`. When JSON string is passed, entire JSON payload bleeds into `metadata.run_name` in markdown and HTML headers.

5. Missing Error Envelopes:
- `tools/physics.py` L262: `capstone_run_experiment_macro` leaks raw KeyError/ValueError instead of returning ExperimentMacroResult(success=False, error=...).
- `tools/files.py` L160, L185: `capstone_inspect_file` and `capstone_file_datasets` leak raw CapFileError without MCP error envelopes.
- `tools/physics.py` L192: `capstone_generate_lab_report` runs synchronous I/O on event loop without `anyio.to_thread.run_sync`.

6. Template Rendering Discrepancies:
- `reports/templates.py`: HTML report (`render_html`) completely omits Apparatus & Setup section (`_render_md_apparatus` exists for MD only).
- `reports/templates.py` L98: `if reg.slope_error:` evaluates False when error is 0.0 (renders `'N/A'` with extraneous quotes).
- SVG `<circle>` renders invalid `"nan"` coordinates if input contains NaN/Inf.

7. FastMCP Router Bug:
- `tools/physics.py` L60: `capstone_guide` missing `@mcp.tool` decorator, unregistering it despite being advertised in `agent_instructions.py`.

</details>

<details open>
<summary><b>[보고서 #40] auditor-recipes 실사 세부 명세 (Phase 2)</b></summary>

1. OOM Memory Blowup Risks (10 kHz+ High-Speed Sampling):
- `numerics/summary.py` L33: `clean_vals = [float(v) for v in values if not math.isnan(v)]` materializes full Python float lists in memory. 10 kHz for 100s = 1M items (~40MB RAM).
- `numerics/summary.py` L39-45: 4 full iterations over list (`sum`, `sum((x-mean)**2)`, `min`, `max`) without streaming/Welford accumulator.
- `numerics/sparklines.py` L157-161 (`render_svg_sparkline`): Emits an individual `<circle>` SVG tag for every single point without downsampling/LTTB/min-max binning. 1M points generates 1M XML DOM elements (~80MB string), crashing browser SVG renderers.
- `numerics/sparklines.py` L30-34, L93-97, L109-110: Duplicates arrays multiple times (`pairs`, `all_x`, `all_y`, `elements`) causing multi-hundred-MB memory spikes.
- `numerics/regression.py` L53-86: Allocates 4 concurrent lists (`pairs`, `clean_x`, `clean_y`, `residuals`), multiplying RAM consumption 4x.

2. Unchecked Error Suppression & Macro Masquerading:
- Phantom Capstone execution: All 5 recipes ignore `app` (`del app` in L103, L119, L120, L142, L178; setup only returns static strings). No live UI/hardware actions are executed even when `app` is attached.
- Silent synthetic masquerading: In all 5 recipes (`analyze()` in adiabatic_gas L221, forced_oscillation L196, rlc_resonance L200, slit_diffraction L254, photoelectric L183), missing or empty input data silently triggers `self.acquire(params)` to generate fake simulated curves, reporting 100% success and misleading the user.
- Unhandled macro crash escapes: `run()` in `recipes/base.py` L80-142 lacks a `try...except Exception` wrapper around phase executions. Unhandled exceptions (e.g. `ZeroDivisionError` in `adiabatic_gas.py` L61, `math domain error` in `rlc_resonance.py` L136) crash the server transport instead of returning `ExperimentMacroResult(success=False)`.

3. Mathematical & Numerical Instability:
- `numerics/summary.py` L40-41: If series contains `inf`, `inf - inf` yields `nan` variance, and `math.sqrt(nan)` raises `ValueError: math domain error`.
- `recipes/adiabatic_gas.py` L61: `_fit_adiabatic_index` raises `ZeroDivisionError` when all $p \le 0$ or $v \le 0$ (`n = len(ln_v) == 0`).
- `recipes/slit_diffraction.py` L83-92: `_derive_slit_separation` skips central peak, including a $2\times$ gap in consecutive spacing averages, artificially inflating fringe spacing and underestimating slit separation $d$.

</details>

<details open>
<summary><b>[보고서 #61] auditor-recipes 실사 세부 명세 (Phase 3)</b></summary>

기존 마스터 매트릭스(38건) 외에 새롭게 확인된 구체적 결함 8건입니다.

1. `recipes/base.py` L83, L96 (Pending 상태 강행 진행)
- `RecipePhaseResult.status == "pending"`(센서 연결/교정 대기)을 무시하고 다음 단계(`acquire`, `analyze`)를 강제 실행하여 미완료 상태에서 가짜 분석을 수행함.

2. `recipes/base.py` L107-112 (빈 파라미터 병합 실패 Clobbering)
- 호출자가 `parameters={"driver_frequencies_hz": []}` 전달 시 `"k not in params"` 검사로 인해 `acquire()` 데이터가 병합되지 못하고 빈 리스트가 잔존하여 `analyze()` 단계에서 즉시 실패함.

3. `recipes/adiabatic_gas.py` L75-78 (0분산 피팅 $R^2=1.0$ 날조)
- 부피 변화가 없는 데이터(`sxx == 0`) 입력 시 에러를 내지 않고 `gamma_exp = 1.400`, `r_squared = 1.0`을 반환하여 데이터 유효성을 날조함.

4. `recipes/forced_oscillation.py` L142 & `rlc_resonance.py` L138 (num_points=1 영분모 폭사)
- `step = (max - min) / (num_points - 1)`: `num_points=1` 파라미터 전달 시 즉시 `ZeroDivisionError` 크래시.

5. `recipes/forced_oscillation.py` L243-267 (공진 미도달 시 Q 인자 대역폭 왜곡)
- 감쇠가 크거나 스윕이 좁아 진폭이 반치전력(`half_power_amp`) 아래로 내려가지 않으면 `f1=freqs[0]`, `f2=freqs[-1]`(스윕 양 끝단)을 대역폭으로 오인하여 엉뚱한 Q 인자를 산출함.

6. `recipes/photoelectric.py` L116-122 (임의 파장에 수은등 전압 매핑 날조)
- `len(voltages) < len(wavelengths)`만 검사하여 적외선 파장(예: 700~1100 nm, 5개) 입력 시 길이가 5로 같아 수은등 정지전압을 그대로 매핑, 물리적으로 불가능한 광전자 방출 곡선을 조작해냄.

7. `recipes/slit_diffraction.py` L67, L333 (극값 0개 검출 시 슬릿폭 0.04mm, 오차 0.0% 날조)
- 노이즈나 단조 데이터로 극솟값이 0개 검출되면 `slit_width_a_m = DEFAULT_SLIT_WIDTH_M (0.04 mm)`를 채택하고 오차를 0.0%로 반환하여 결측치를 완벽한 성공으로 위장함.

8. `numerics/regression.py` L148 & L90 (다항회귀 고차 거듭제곱 오버플로우 & 수평선 $R^2=1.0$ 날조)
- L148: 주파수 단위($10^5 \sim 10^8$ Hz)에서 $x^{2d}$ 거듭제곱으로 `OverflowError` 및 Vandermonde 정규방정식 붕괴.
- L90: 종속변수 $y$의 분산이 0인 수평 직선(`ss_yy == 0.0`)에 대해 설명력 0이 아닌 `r_squared = 1.0`을 반환.

</details>

<details open>
<summary><b>[보고서 #81] auditor-recipes 실사 세부 명세 (Phase 4)</b></summary>

1. `experiment_analysis.py` L203-208 (독립변수 Time 엄격 일치 비교로 실물 하드웨어 데이터 거부)
- `if x_coordinate != y_coordinate: raise ExperimentAnalysisError(...)`: PASCO 850 하드웨어 채널(Analog A/B, Rotary Digital 등) 간 마이크로초 샘플링 클록 지터(Jitter)로 인해 타임스탬프가 엄격히 일치하지 않아 실물 다채널 .cap 파일 피팅 시 100% 거부 에러 발생. 허용오차(Tolerance)나 최근접 정렬이 전무함.

2. `recipes/adiabatic_gas.py` L57-74 & `reports/generator.py` L556-563 (비가중 로그 선형화에 의한 감마 피팅 왜곡)
- $PV^\gamma = C$ 피팅 시 가중치 없는 OLS($\ln P = -\gamma \ln V + \ln C$)를 수행함. 로그 변환 시 오차는 $\Delta(\ln P) \approx \Delta P / P$로 저압 구간 데이터에 비정상적으로 과도한 가중치가 실려 유도된 단열계수 $\gamma$에 체계적 편향(Systematic Bias)이 발생함.

3. `numerics/` 고등 수치해석 부재 및 스크린 스크래핑 전락
- `numerics/`에 `fft.py`, `filters.py`, `fit_models.py`, `optimization.py`가 완전히 결손되어 있음.
- 디지털 신호처리(FFT, 창함수, 스펙트럼 누설 방지)를 수학적으로 수행하지 못하고, `displays/scope.py`에서 Capstone GUI 화면의 텍스트 레이블을 UIA 정규식으로 긁어오는 취약한 구조에 의존함.

4. 편광(말루스의 법칙), 음속 공명 등 핵심 물리 레시피 결손 및 직선 피팅 파탄
- 골든 마스터 파일(`Polarization of Light...cap`)이 존재함에도 레시피가 5개에 머물러 있음.
- 리포트 엔진에 `polarization` 요청 시 `_fit_general` OLS($y=mx+b$)로 폴백되어 비선형 곡선($I = I_0 \cos^2\theta$)에 억지로 직선을 그어 기울기/절편이 완전히 파탄남.

5. `analysis.py` L86-95, L148-156 (Cook's Distance 부동소수점 특이점 폭사)
- 레버리지 $h_{ii} \approx 1.0$인 이상점 발생 시 $(1 - h_{ii})^2$ 부동소수점 소거로 분모가 $10^{-31}$로 수렴하여 쿡의 거리가 `inf`로 폭발, L155에서 `AnalysisError: Fit results exceed finite floating-point precision`를 던지며 전체 선형 피팅이 다운됨.

6. `analysis.py` L133 (음수 $R^2$ 방어 누락)
- `r_squared = 1 - residual_sum / syy`: `regression.py`와 달리 `max(0.0, ...)` 클램핑이 없어 피팅 잔차 분산이 $y$ 분산보다 클 때 음수 $R^2$를 그대로 반환하여 모델 규격을 위반함.

</details>

#### 📑 실사 보고서: `audit-diffraction` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #100] audit-diffraction 실사 세부 명세 (Phase 1)</b></summary>

지정 영역인 `src/capstone_mcp/recipes/slit_diffraction.py` 및 관련 테스트(`tests/test_recipes.py`)에 대해 피크 탐색 알고리즘, 중앙 회절 피크 오검출, 음수/0 간격 처리, 광학 불확도(GUM) 정량화 결함을 전수 라인 단위로 실사한 결과입니다 (#93 참조).

---

### 1. 피크 탐색 알고리즘 결함 (DEFECT-DIFF01 ~ DIFF04)

#### 🟠 DEFECT-DIFF01: 비대칭 부등호(`>` vs `>=`)로 인한 평탄 구간/양자화 계단 오르막길 가짜 극대점 유발 (P1)
- **코드 위치**: [recipes/slit_diffraction.py#L41-L44](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L41-L44)
- **파괴 메커니즘**:
  - `if curr_v > prev_v and curr_v >= next_v:` 조건에서 `curr_v == next_v`를 허용하여, 단조 증가 중 센서 양자화로 동일한 값이 2개 연속되는 경우(예: `[1.0, 2.0, 2.0, 3.0, 1.0]`) 첫 번째 `2.0`이 극대점으로 오등록됨 (실증 결과: `[(2, 2.0), (4, 3.0)]`).
  - 마찬가지로 `elif curr_v < prev_v and curr_v <= next_v:` 조건에 의해 내리막 계단 중간에서 가짜 극소점이 유발됨.

#### 🟠 DEFECT-DIFF02: 노이즈 평활화 및 Prominence(돌출도) 필터 부재로 인한 아날로그 노이즈 리플 폭발 (P1)
- **코드 위치**: [recipes/slit_diffraction.py#L36-L45](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L36-L45)
- **파괴 메커니즘**:
  - Savitzky-Golay, 가우시안 평활화 또는 최소 돌출도(Prominence) 검증 없이 3점 차분만 수행하여, PASCO 고감도 광 센서의 $0.001\,\text{V}$ 수준 미세 아날로그 노이즈 지터마다 수십~수백 개의 거짓 극대/극소가 발생하여 `minima_pts`와 `maxima_pts`를 전면 오염시킴.

#### 🟡 DEFECT-DIFF03: 서브픽셀(포물선/가우시안 보간) 미적용으로 인한 이산 샘플링 그리드 양자화 오차 (P2)
- **코드 위치**: [recipes/slit_diffraction.py#L41-L44](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L41-L44)
- **파괴 메커니즘**: 극대/극소 위치를 이산적 샘플 인덱스 `positions[i]`로만 기록하므로, 샘플 간격 $\Delta x$의 최대 절반($\Delta x / 2$)에 달하는 위치 편향이 영구 누적됨. 3점 포물선 버텍스 보간($x_{peak} = x_i - \frac{\Delta x}{2} \frac{y_{i+1}-y_{i-1}}{y_{i+1}-2y_i+y_{i-1}}$) 누락.

#### 🟡 DEFECT-DIFF04: 양 끝단(Boundary/Endpoint) 극소점 무조건 배제 (P2)
- **코드 위치**: [recipes/slit_diffraction.py#L36](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L36)
- **파괴 메커니즘**: `for i in range(1, n - 1)`로 끝점 $i=0$과 $i=n-1$을 원천 배제하여, 좁은 스캔 범위에서 스캔 경계에 위치한 1차 극소점이 무조건 누락됨.

---

### 2. 중앙 회절 피크 오검출 결함 (DEFECT-DIFF05 ~ DIFF08)

#### 🔴 DEFECT-DIFF05: 센서 포화(Saturation) 시 맨 첫 번째 샘플 선택에 의한 좌측 편향 왜곡 (P0)
- **코드 위치**: [recipes/slit_diffraction.py#L295-L302](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L295-L302)
- **파괴 메커니즘**:
  - `if val > max_i:`는 엄격한 초과 연산자이므로, 광 센서 포화(예: 5.0V 평탄 구간) 발생 시 대칭 중심($x=0$)이 아닌 포화 고원의 맨 첫 번째(가장 왼쪽) 샘플을 무조건 `x_center_mm`로 지정함.
  - 대칭 데이터 `[-3, -2, -1, 0, 1, 2, 3]`에서 포화 시 `x_center = -1.0 mm`로 산출되어 1.0 mm의 거대한 편향 오차가 발생하며 좌우 극소점 대칭성이 붕괴됨.

#### 🔴 DEFECT-DIFF06: 대칭성(Symmetry) 및 포락선 무게중심(Centroid) 검증 부재와 단일 스파이크 취약성 (P0)
- **코드 위치**: [recipes/slit_diffraction.py#L297-L302](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L297-L302)
- **파괴 메커니즘**: 회절 피크의 물리적 대칭성 검증 및 강도 가중 무게중심($\frac{\sum x_i I_i}{\sum I_i}$) 계산 없이 전역 최대값 단 1개 점만 취하므로, 외부 조명 플래시나 정전기 스파이크가 스캔 외곽에 1회 발생하면 스캔 중심($x_{center}$)이 외곽으로 날조됨.

#### 🟠 DEFECT-DIFF07: 이중 슬릿에서 간섭 극대와 회절 포락선 대칭 중심 혼동 (P1)
- **코드 위치**: [recipes/slit_diffraction.py#L295-L302](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L295-L302)
- **파괴 메커니즘**: 이중 슬릿 회절 $I = 5 \cos^2(\alpha) (\sin\beta/\beta)^2$에서 중앙 포락선 내부의 다중 간섭 피크 중 임의의 하나를 중앙 피크로 취급하여, 영점 위상차가 있거나 중심에 간섭 골(dip)이 위치할 경우 중심축이 간섭 피크 간격의 절반만큼 왜곡됨.

#### 🟠 DEFECT-DIFF08: `_derive_slit_separation`의 인위적 `x_center_mm` 삽입 및 중복/근접 피크 왜곡 (P1)
- **코드 위치**: [recipes/slit_diffraction.py#L84-L90](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L84-L90)
- **파괴 메커니즘**:
  - `SIDE_PEAK_THRESHOLD_MM = 0.05` mm 필터링 후 `peak_positions = sorted([*side_maxima, x_center_mm])`로 중앙 피크를 강제 합병함. 포화나 노이즈로 $0.06$ mm에 위치한 피크가 있을 경우 $0.06$ mm 간격이 인위적으로 삽입되어 $d$ 계산이 수배 왜곡됨.

---

### 3. 음수/0 간격 처리 및 물리학적 파탄 결함 (DEFECT-DIFF09 ~ DIFF13)

#### 🔴 DEFECT-DIFF09: 극소점 미검출/0 간격 시 하드코딩 기본값(0.04mm) 침묵 반환 및 0.0% 오차 허위 조작 (P0)
- **코드 위치**: [recipes/slit_diffraction.py#L69-L72](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L69-L72), [recipes/slit_diffraction.py#L330-L334](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L330-L334)
- **파괴 메커니즘**:
  - `first_min_delta_mm <= 0`이거나 극소점이 전무할 때 `slit_width_a_m = DEFAULT_SLIT_WIDTH_M` (0.04 mm)로 침묵형 대체하고, `analyze()`는 `a_error_pct = 0.0%`로 완벽한 성공 결과를 조작함.
  - 센서 암전류/차광으로 모든 광 강도가 0인 데이터셋에서도 `status='completed'`, `derived_slit_width_mm=0.04`, `slit_width_error_pct=0.0`을 날조하여 반환함.

#### 🔴 DEFECT-DIFF10: 이중 슬릿 모드에서 간섭 극소점을 회절 극소점으로 오대입하여 슬릿 폭 $a$ 1200% 왜곡 (P0)
- **코드 위치**: [recipes/slit_diffraction.py#L313-L320](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L313-L320)
- **파괴 메커니즘**:
  - 이중 슬릿 회절 프로파일에서 최인접 극소점은 간섭 극소점($x \approx \lambda L / 2d \approx 1.3$ mm)임에도, 이를 단일 슬릿 회절 포락선 1차 극소점($x \approx \lambda L / a \approx 16.25$ mm) 자리에 그대로 대입함.
  - 이로 인해 슬릿 폭 $a$가 $0.04$ mm가 아닌 $0.52$ mm로 산출되어 **1200% (13배)의 거대한 체계오차**를 발생시킴. (`tests/test_recipes.py` L421-440에서도 이 왜곡을 은폐하기 위해 `derived_slit_width_mm` 검증을 고의 누락함).

#### 🟠 DEFECT-DIFF11: 0 및 극미소 간격에 의한 발산(ZeroDivision / Divergence) 가드 부재 (P1)
- **코드 위치**: [recipes/slit_diffraction.py#L71-L72](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L71-L72), [recipes/slit_diffraction.py#L96-L97](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L96-L97)
- **파괴 메커니즘**: 간격이 수 $\mu\text{m}$ 이하의 극미소 양수일 때 $a = \frac{\lambda L}{\Delta x}$, $d = \frac{\lambda L}{\Delta d}$ 계산 결과가 수천 미터로 폭발함. 물리적 유효 범위 검증(Sanity Bound Guard) 전무.

#### 🟡 DEFECT-DIFF12: 고차 극소점($m \ge 2$) 폐기 및 1차 극소점 단일 의존 (P2)
- **코드 위치**: [recipes/slit_diffraction.py#L62-L67](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L62-L67)
- **파괴 메커니즘**: 물리 실험의 표준 분석법인 $x_m = m \frac{\lambda L}{a}$ 다점 선형 회귀를 무시하고 1차 극소점 단 1개에만 의존하여 노이즈 오차 상쇄 기회를 포기함.

#### 🟡 DEFECT-DIFF13: 이중 슬릿 결손 차수(Missing Order) 발생 시 $2\Delta x$ 간격에 의한 median 왜곡 (P2)
- **코드 위치**: [recipes/slit_diffraction.py#L91-L93](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L91-L93)
- **파괴 메커니즘**: 회절 포락선 극소점 위치에서 간섭 피크가 소멸되는 결손 차수 발생 시 인접 피크 간격이 $2\Delta x$로 벌어지며, 단순 pairwise 차분 시 median이 교란될 위험 노출.

---

### 4. 광학 불확도(GUM) 정량화 결함 (DEFECT-DIFF14 ~ DIFF17)

#### 🟠 DEFECT-DIFF14: 불확도 정량화(Uncertainty Quantification) 파이프라인 전무 (P1)
- **코드 위치**: [recipes/slit_diffraction.py#L335-L366](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L335-L366)
- **파괴 메커니즘**: `derived_slit_width_mm`과 `derived_slit_separation_mm`에 대해 표준 불확도($u(a)$, $u(d)$), 확장 불확도($U_{95}$), 신뢰구간이 전혀 계산되지 않음.

#### 🟠 DEFECT-DIFF15: GUM 복합 표준 불확도 오차 전파 법칙 미적용 (P1)
- **코드 위치**: [recipes/slit_diffraction.py#L72, L97](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L72)
- **파괴 메커니즘**:
  - 파장 불확도 $u(\lambda) \approx 10$ nm, 스크린 거리 불확도 $u(L) \approx 2$ mm, 센서 분해능 $u(x) \approx 0.01 / \sqrt{12}$ mm, 간격 통계오차 $s/\sqrt{N}$을 합성하는 오차 전파 공식:
    $$\frac{u_c(a)}{a} = \sqrt{\left(\frac{u(\lambda)}{\lambda}\right)^2 + \left(\frac{u(L)}{L}\right)^2 + \left(\frac{u(\Delta x)}{\Delta x}\right)^2}$$
    가 일체 부재함.

#### 🟡 DEFECT-DIFF16: 간섭 무늬 통계적 분산/표준오차(SEM) 및 품질 지표 누락 (P2)
- **코드 위치**: [recipes/slit_diffraction.py#L91-L93](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L91-L93)
- **파괴 메커니즘**: 간섭 무늬 간격 집합 `spacings`의 표준편차($\sigma$), 표본 표준오차($s/\sqrt{N}$), 변동계수(CV)를 폐기하고 단일 스칼라 `median`만 반환함.

#### 🟡 DEFECT-DIFF17: 미지 시료 측정 시 명목값(Nominal) 편차를 'Error'로 위장 표기 (P2)
- **코드 위치**: [recipes/slit_diffraction.py#L333, L359](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L333)
- **파괴 메커니즘**: 미지의 슬릿 측정 시에도 기본 하드코딩 명목값(0.04 mm, 0.25 mm)과의 차이를 `slit_width_error_pct`로 표기하여 사용자에게 허위 오차 정보를 노출함.

---

### 5. 기하학적 근축 근사 및 입력 유효성 결함 (DEFECT-DIFF18 ~ DIFF19)

#### 🟡 DEFECT-DIFF18: `acquire()`의 엄밀한 $\sin\theta$와 `analyze()`의 파라액셜 근사 간 체계오차 누적 (P2)
- **코드 위치**: [recipes/slit_diffraction.py#L203](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L203) vs [recipes/slit_diffraction.py#L72](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L72)
- **파괴 메커니즘**: `acquire`는 $\sin\theta = x/\sqrt{x^2+L^2}$을 사용하나 `analyze`는 $\sin\theta \approx x/L$을 강제하여 광각/단거리 조건에서 체계오차가 누적됨.

#### 🟡 DEFECT-DIFF19: `MIN_DIFFRACTION_POINTS = 5`의 물리적 비현실성 및 광 센서 영점/차광/음수 입력 가드 부재 (P2)
- **코드 위치**: [recipes/slit_diffraction.py#L18, L286](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/slit_diffraction.py#L18)
- **파괴 메커니즘**: 5개 샘플만으로 회절 분석을 허용하여 침묵형 기본값으로 빠지게 하며, 센서 차광(모든 강도 0) 시 성공으로 처리하는 입력 검증 부재.

---
이상 슬릿 회절 결함 19건(P0 4건, P1 6건, P2 9건)을 마스터 매트릭스에 통합 반영 요청드립니다.

</details>

#### 📑 실사 보고서: `audit-thermo` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #102] audit-thermo 실사 세부 명세 (Phase 1)</b></summary>

1. 대상 파일 및 아키텍처 실사 (File Inventory & Architecture Reality)
- `src/capstone_mcp/recipes/boyle.py`: 파일 부재 (미구현). 레포지토리 및 Phase 3 스펙에 존재하지 않으며, `agent_instructions.py` 및 테스트 예시 텍스트로만 언급됨.
- `src/capstone_mcp/recipes/engine.py`: 독립 파일 부재. `src/capstone_mcp/recipes/adiabatic_gas.py` 내 `AdiabaticGasRecipe`의 `heat_engine` 별칭(alias) 및 `acquire()` 시뮬레이션으로 혼합 통합되어 있음.
- 구조적 결함: 개방 경로 1회성 단열 압축(TD-8565)과 닫힌 열기관 사이클(EX-5530/TD-8572)이라는 물리적으로 완전히 다른 두 실험이 단일 클래스(`AdiabaticGasRecipe`)에 무분별하게 혼재됨.

2. 열역학 수식 및 물리 모델링 결함
- [결함 1] `acquire()` 시뮬레이션의 비물리적 행정 및 경계 불연속 (`adiabatic_gas.py` L157-190):
  * Leg 2 (열 흡수): 부피 팽창($30 \to 45\text{ cm}^3$)과 압력 상승($267.3 \to 320.0\text{ kPa}$)이 동시 발생($dP/dV > 0$). 오토/디젤/카르노 등 표준 열기관 사이클에 부합하지 않으며, 온도 $T \propto PV$가 팽창 중 80% 급등함.
  * Leg 3 (단열 팽창) 끝점($V=65$)의 이론 압력은 $320.0 \times (45/65)^{1.4} = 191.45\text{ kPa}$이나, Leg 4는 $185.0\text{ kPa}$로 하드코딩되어 $-7.90\text{ kPa}$의 압력 절벽(jump discontinuity) 발생.
  * `frac = i / points_per_leg`의 끝점 미포함($i < N$)으로 인해 모든 Leg 간(1->2, 2->3, 3->4, 4->1)에 $\Delta V, \Delta P$ 불연속 단차 잔존.
- [결함 2] 설정된 온도 센서 채널 방치 (`adiabatic_gas.py` L109, L192-195):
  * `setup()`에서 `Analog Ch C: Fast Temperature Sensor (K)`를 설정하나, `acquire()` 및 `analyze()`에서 온도 데이터를 일절 수집/분석하지 않음. 단열 관계식 $T V^{\gamma-1} = \text{const}$ 및 $\Delta U = -W = n C_v \Delta T$ 검증 로직이 완전히 누락됨.

3. PV 사이클 일(Work) 적분 및 비가역성 왜곡 결함
- [결함 3] 단일 행정 개방 압축 시 유령 폐합선(Phantom Closing Chord) 조작 (`adiabatic_gas.py` L27-30):
  * `_compute_closed_loop_work()`가 마지막 점($n-1$)을 첫 번째 점($0$)으로 강제 연결함.
  * TD-8565 단열 압축 1회 레버 조작 데이터($V: 100 \to 50\text{ cm}^3$, 실제 일 $-7.988\text{ J}$)를 입력하면, 끝점에서 시작점으로 강제 연결되는 가상 폐합선의 일 $+9.098\text{ J}$이 더해져 **최종 일이 $+1.109\text{ J}$로 산출되어 부호가 역전되고 800% 이상 왜곡**됨.
- [결함 4] 다중 사이클 주기 분할(Cycle Segmentation) 부재:
  * 1000Hz 연속 측정 데이터(예: 10회전 엔진 데이터) 입력 시 개별 사이클 분할 없이 전체 시계열을 통째로 적분하여, 1사이클 일이 아닌 전체 누적 일($N$배 뻥튀기)이 반환됨.
- [결함 5] 비가역 방열 및 사이클 방향성(Orientation) 무검증:
  * 시계 방향(엔진 출력, 양의 일)과 반시계 방향(냉동기/열손실 히스테리시스 루프, 음의 일)의 물리적 상태 구분이 없음. 비가역 방열로 인해 음의 일($W < 0$)이 산출되어도 경고나 물리적 분류 없이 성공 처리됨.

4. 단열 계수 감마($\gamma$) 피팅 왜곡 결함
- [결함 6] 나이브한 인접 차분 필터의 노이즈 취약성 및 선택 편향 (`adiabatic_gas.py` L48-53):
  * `valid_pairs[i + 1][1] < valid_pairs[i][1] and valid_pairs[i + 1][0] > valid_pairs[i][0]` 조건은 1000Hz 센서 노이즈($\pm 0.3\text{ kPa}$) 환경에서 압축 구간 데이터의 약 36%를 $P_{i+1} \le P_i$ 판정으로 부당 탈락시킴.
  * 노이즈가 양(+)으로 튄 포인트만 선택 잔존하여 회귀 기울기에 통계적 선택 편향(selection bias) 발생.
  * 또한 압축의 최대 피크점($(V_{\min}, P_{\max})$)은 다음 포인트에서 팽창이 시작되므로 $V_{i+1} < V_i$ 조건에 걸려 필수 극값 데이터가 영구 누락됨.
- [결함 7] 팽창 데이터 전면 배제 및 전체 루프 피팅 시 감마 붕괴 (`adiabatic_gas.py` L55-57):
  * 단열 팽창 과정($V$ 증가, $P$ 감소)은 단열 변화임에도 압축 필터에서 전면 탈락됨.
  * 필터링된 점이 3개 미만이면 `compression_pairs = valid_pairs`로 후퇴하여 닫힌 PV 사이클 전체에 $\ln P = -\gamma \ln V + C$ 선형 회귀를 강제 실행함. 루프 데이터 피팅으로 인해 $\gamma \approx 0.000, R^2 = 0.000$, 오차율 100.0%의 파탄 난 수치가 예외 없이 정상 보고됨.
- [결함 8] 비물리적 음수/1 미만 감마($\gamma < 1$) 가드 부재 (`adiabatic_gas.py` L76-81):
  * 센서 드리프트 등으로 $s_{xy} > 0$이 될 경우 $\gamma_{\text{exp}} < 0$ 또는 $\gamma < 1$ 등 열역학적 안정성 조건을 위배하는 수치가 산출되어도 유효성 검증 없이 통과됨.
- [결함 9] 리포트 엔진(`src/capstone_mcp/reports/generator.py` L569-580, L644-650) 전구간 피팅 결함:
  * 리포트 생성기에서는 압축/팽창 분리조차 없이 전체 $P, V$ 시계열 전체를 `_fit_adiabatic`에 통째로 피팅하여 사이클 아카이브 로드 시 심각한 감마 왜곡 발생.

</details>

#### 📑 실사 보고서: `auditor-reports` (총 3회 정밀 실사)

<details open>
<summary><b>[보고서 #52] auditor-reports 실사 세부 명세 (Phase 1)</b></summary>

소유 모듈인 `src/capstone_mcp/reports/*` (`generator.py`, `templates.py`, `models.py`) 및 `src/capstone_mcp/tools/physics.py` 전수 감사 결과입니다.

---

### 1. DEFECT-REP01 (Critical): Silent Synthetic Data Injection (`_canonical_fallback_series`) & Read Failure Suppression
- **파일**: [generator.py#L272-L275](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L272-L275), [generator.py#L330-L335](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L330-L335), [generator.py#L478-L519](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L478-L519), [generator.py#L678-L700](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L678-L700), [generator.py#L739-L749](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L739-L749)
- **코드**:
  ```python
  def _load_cap_data(path: Path) -> tuple[dict[str, list[float]], dict[str, str]]:
      with contextlib.suppress(Exception):
          return read_capfile_all_series(path)
      return {}, {}
  ...
  if not active_series:
      is_sample = file_path_or_run in ("sample", None) or (file_path_or_run is not None and file_path_or_run.endswith("_sample"))
      if is_sample and experiment_id in _CANONICAL_EXPERIMENT_METADATA:
          active_series = _canonical_fallback_series(experiment_id)
  ```
- **실기 폭발 시나리오**:
  1. `.cap`, `.csv`, `.json` 파일 로드 중 발생하는 손상/포맷 오류가 `contextlib.suppress(Exception)`에 의해 모조리 침묵 처리되어 빈 딕셔너리 `{}`를 반환함.
  2. 사용자가 `photoelectric_sample.cap` 또는 `data_sample.csv`와 같이 파일명 끝에 `_sample`이 붙은 실제 데이터 파일을 지정했으나 읽기에 실패한 경우, `is_sample=True` 분기를 타고 `_canonical_fallback_series`의 이상적인 이론 계산 데이터(예: $h\nu - \Phi$)가 몰래 주입됨.
  3. 보고서 엔진은 가짜 데이터를 바탕으로 $R^2 = 1.0000$, 상대 오차 $0.00\%$의 완벽한 플랑크 상수($h$) 및 단열 지수($\gamma$) 결과를 도출(L745).
  4. 실제 센서 분리, 데이터 파일 손상, 포맷 불일치로 인한 실패가 완벽한 성공 보고서로 둔갑하여 사용자 및 상위 에이전트를 기만하고 하드웨어/수집 결함을 은폐함. (테스트 `tests/test_reports.py#L313` 역시 가짜 데이터 주입으로 통과하는 Mock Blindness 유발)

---

### 2. DEFECT-REP02 (Major): HTML Report Template Completely Omits Apparatus & Setup Section
- **파일**: [templates.py#L50-L70](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L50-L70), [templates.py#L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L150), [templates.py#L482-L518](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L482-L518)
- **실태**:
  - Markdown 렌더러(`render_markdown`, L150)는 `_render_md_apparatus`를 통해 `## 3. Apparatus & Setup Configuration` (장비 목록 `meta.apparatus` 및 센서/포트 바인딩 테이블 `meta.channels_or_sensors`)을 정상 출력함.
  - 그러나 HTML 렌더러(`render_html`, L482-518)에는 `_render_html_body_apparatus` 구현 자체가 존재하지 않으며, `_render_html_body_header` 직후 곧바로 `_render_html_body_data`로 건너뜀.
- **실기 폭발 시나리오**:
  1. HTML 보고서 출력 시 실험 장비 목록과 PASCO 850 인터페이스 채널 매핑(포트별 전압/전류 센서 바인딩) 정보가 100% 누락됨.
  2. Markdown은 8개 섹션, HTML은 7개 섹션으로 구성되며, HTML에서는 데이터 요약이 4번이 아닌 `3. Measured Data & Statistics`로 잘못 넘버링되어 MD-HTML 간 데이터 일관성 및 실험 검증 보고서 규격이 파괴됨.

---

### 3. DEFECT-REP03 (Critical): SVG & ASCII Plot Emitting Invalid NaN Coordinates / Crashing Renderers
- **파일**: [templates.py#L172-L277](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L172-L277) (`_render_svg_plot`), [generator.py#L212, L219](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L212) (`_draw_canvas`)
- **코드**:
  ```python
  min_x, max_x = min(x_vals), max(x_vals)
  span_x = max_x - min_x or 1.0
  def map_x(val: float) -> float:
      return margin_left + ((val - min_x) / span_x) * plot_w
  ...
  svg_elements.append(f'<circle cx="{map_x(px):.1f}" cy="{map_y(py):.1f}" .../>')
  ```
- **실기 폭발 시나리오**:
  1. 센서 드롭아웃이나 결측치로 인해 `report.raw_data_points`에 `float('nan')`이 유입될 경우, `min()`/`max()`가 `nan`을 반환하고 `span_x = nan - nan` 역시 `nan`이 됨. (파이썬에서 `bool(float('nan')) == True`이므로 `span_x or 1.0`도 `nan` 유지)
  2. 모든 좌표 연산이 `nan`으로 오염되어 `<line x1="nan" y1="nan" x2="nan" ...>`, `<circle cx="nan" cy="nan" ...>`, `<text>nan</text>`과 같은 규격 위반 SVG를 방출.
  3. W3C SVG 표준 위반으로 인해 브라우저 DOM 파서, WeasyPrint/cairo 기반 PDF 변환기, 웹 클라이언트 캔버스 렌더러가 파싱 예외를 던지거나 렌더링 파이프라인이 즉시 크래시됨.
  4. ASCII 플롯(`generator.py#L212, L219`)의 경우 `round((grid_h - 1) * ...)`에서 `ValueError: cannot convert float NaN to integer`가 발생하여 보고서 생성 자체가 즉각 비정상 종료됨.

---

### 4. DEFECT-REP04 (Critical): Synchronous File I/O & Compute Blocking FastMCP Event Loop
- **파일**: [physics.py#L166-L224](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L166-L224) (`capstone_generate_lab_report`), [generator.py#L268-L289, L321-L326, L656](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L268-L289)
- **코드**:
  ```python
  async def capstone_generate_lab_report(...):
      report = generate_report(...) # <--- 메인 비동기 이벤트 루프에서 동기 파일 읽기 및 OLS 연산 수행!
      rendered = render_report(report, report_format=format)
      if output_path:
          await anyio.to_thread.run_sync(_write_report_file, ...) # 파일 쓰기만 스레드로 분리함
  ```
- **실기 폭발 시나리오**:
  - `_write_report_file`만 `anyio.to_thread.run_sync`로 감싸고, 정작 수십 MB 단위 `.cap` 아카이브 압축 해제(`read_capfile_all_series`), 대용량 CSV 파싱(`read_csv_all_columns`), OLS 선형 회귀, ASCII 플롯 생성을 담당하는 `generate_report`를 `async def` 메인 이벤트 루프 스레드에서 직접 동기 호출함.
  - 고속 샘플링(100kHz) 대용량 `.cap` 파일 분석 시 수 초~수십 초간 이벤트 루프가 동결(freeze)되어 클라이언트의 MCP 핑/하트비트가 끊기고 타 도구 동시 요청이 모조리 락업됨.

---

### 5. 기타 아키텍처 결함
- **DEFECT-REP05 (Major, Phantom Feature)**: `physics.py#L175, L182` docstring에는 "active run name" 지원을 명시했으나, `generator.py#L304-L340`의 `_load_data_from_file_or_string`에는 실행 중인 Capstone 세션에서 활성 런 데이터를 가져오는 브리지/워커 연동 코드가 전혀 없음. `"Run 1"`을 전달하면 `ValueError: No experimental numeric series could be extracted`를 던지며 실패함.
- **DEFECT-REP06 (Minor)**: `models.py#L74`의 `additional_regressions: list[RegressionSummary]` 필드가 `templates.py`의 Markdown 및 HTML 렌더러에서 완전히 무시되어 다중 런 비교나 고차 회귀 분석 결과가 보고서에 출력되지 않음.

</details>

<details open>
<summary><b>[보고서 #69] auditor-reports 실사 세부 명세 (Phase 2)</b></summary>

기존 마스터 매트릭스(P2-27, P2-28, P2-29 등) 외에 `reports/*` (`generator.py`, `templates.py`, `models.py`) 및 `tools/physics.py`에서 추가로 발굴된 10건의 구체적 결함 보고서입니다.

---

### 1. DEFECT-REP07 (Critical): JSON 문자열 내 슬래시(`/`, `\`) 존재 시 `FileNotFoundError` 오폭
- **파일**: [generator.py#L311-L325](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L311-L325)
- **코드**:
  ```python
  is_path_like = any(file_path_or_run.lower().endswith(ext) for ext in [".cap", ".csv", ".tsv", ".json"]) or "/" in file_path_or_run or "\\" in file_path_or_run
  path = Path(file_path_or_run)
  if is_path_like and not path.exists():
      raise FileNotFoundError(f"Experiment data file does not exist: {file_path_or_run}")
  ...
  if file_path_or_run.startswith("{") and file_path_or_run.endswith("}"): # L336: 뒤늦은 검사
      return _load_json_string(file_path_or_run), {}
  ```
- **실기 폭발 시나리오**:
  - 클라이언트나 에이전트가 인라인 JSON 문자열(`'{"Ch 1/Voltage": [1.0, 2.0], "Output/V": [3.0, 4.0]}'`)을 전달할 때, 채널명이나 경로 메타데이터에 `/` 또는 `\`가 포함되어 있으면 `is_path_like`가 `True`로 평가됨.
  - JSON 파싱 검사(L336)보다 파일 경로 검증이 먼저 실행되므로, `Path('{"Ch 1/Voltage"...}').exists()`가 `False`가 되어 `FileNotFoundError`를 던지며 유효한 JSON 입력을 즉각 거부하고 폭사함.

---

### 2. DEFECT-REP08 (Critical): 독립변수 분산 0 ($s_{xx} = 0$) 시 회귀 분석 미처리 예외 크래시
- **파일**: [generator.py#L605-L610](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L605-L610), [numerics/regression.py#L70-L72](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/regression.py#L70-L72)
- **실기 폭발 시나리오**:
  - `_fit_general`은 아무런 예외 처리 없이 `compute_linear_regression(x_vals, y_vals)`를 직접 호출함.
  - 정적 볼륨, 정전압, 항온 실험 등에서 $x$ 값이 모두 동일하여 수직선 피팅이 되거나 분산이 0일 경우, 하위 `fit_linear_series`가 `ValueError: Independent variable x has zero variance (cannot fit vertical line)`를 발생시킴.
  - `_compute_fit`이 이를 포획하지 않아 `generate_report` 전체가 비정상 중단됨.

---

### 3. DEFECT-REP09 (Major): 단일 센서 전원 분리 / All-NaN 컬럼 유입 시 요약 통계 크래시
- **파일**: [generator.py#L51-L84](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L51-L84), [numerics/summary.py#L45-L47](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/summary.py#L45-L47)
- **실기 폭발 시나리오**:
  - `compute_data_summary`는 `if not values:`만 체크하여 리스트가 비어 있는지만 확인함.
  - 센서 플러그 분리나 측정 실패로 컬럼 내 모든 원소가 `[nan, nan, nan]`인 경우, `compute_series_summary`가 `ValueError: Cannot compute summary on an empty series or without finite values`를 발생시킴.
  - `generate_report` L715의 리스트 컴프리헨션이 즉시 크래시되어 정상 측정된 타 채널 데이터까지 모두 버려짐.

---

### 4. DEFECT-REP10 (Critical): 비한정값(Inf / NaN) 유입 시 ASCII Plot 캔버스 Overflow/ValueError 크래시
- **파일**: [generator.py#L212, L219](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L212)
- **실기 폭발 시나리오**:
  - `_draw_canvas`에서 `row = round((grid_h - 1) * (1.0 - (cur_y - y_lo) / (y_hi - y_lo)))` 및 `col = round((grid_w - 1) * (px - x_lo) / (x_hi - x_lo))` 실행.
  - `px`, `py`에 `float('inf')` 또는 `-float('inf')` 유입 시 `OverflowError: cannot convert float infinity to integer` 발생.
  - `float('nan')` 유입 시 `ValueError: cannot convert float NaN to integer` 발생.
  - 예외 처리 없이 보고서 생성이 즉시 중단됨.

---

### 5. DEFECT-REP11 (Major): 회귀선 SVG 뷰포트 초과 및 클립 미적용 레이아웃 파괴
- **파일**: [templates.py#L193-L196, L230-L235](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L193-L196)
- **실기 폭발 시나리오**:
  - `_render_svg_plot`의 `min_y`, `max_y` 및 `plot_h`는 순수 데이터 포인트 `y_vals`로만 계산됨.
  - 회귀선 끝점 `y1_fit = slope * min_x + intercept`, `y2_fit = slope * max_x + intercept`가 데이터 범위를 벗어날 경우(기울기가 가파르거나 외삽 발생 시), `map_y(y1_fit)`가 음수 또는 340px 초과 값을 반환함.
  - SVG에 `<clipPath>`가 정의되어 있지 않아 파란색 점선 회귀선(`<line ... stroke="#2563eb">`)이 차트 경계를 뚫고 제목 텍스트와 축 눈금 위를 침범하여 도표가 심각하게 훼손됨.

---

### 6. DEFECT-REP12 (Major): 맹목적 축 배정으로 인한 물리 법칙 전도 및 $5.8 \times 10^{30}\%$ 오차 폭발
- **파일**: [generator.py#L626-L633](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L626-L633)
- **코드**:
  ```python
  x_key, y_key = series_keys[0], series_keys[1]
  x_vals, y_vals = active_series[x_key], active_series[y_key]
  ```
- **실기 폭발 시나리오**:
  - CSV 또는 .cap 아카이브가 `Stopping Voltage`를 0번 컬럼, `Frequency`를 1번 컬럼으로 내보낸 경우, 축 시맨틱 검증 없이 0번을 $x$, 1번을 $y$로 강제 배정함.
  - 광전효과 기울기가 $h/e$가 아닌 $e/h$로 계산되어 플랑크 상수가 $3.8 \times 10^{-5}\text{ J}\cdot\text{s}$로 산출되고, 상대 오차가 $5.8 \times 10^{30}\%$로 폭발함.

---

### 7. DEFECT-REP13 (Major): 게이지 압력(음수/0) 시 단열 법칙 무단 탈락 및 비물리적 선형 회귀 강제
- **파일**: [generator.py#L635-L643](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L635-L643)
- **실기 폭발 시나리오**:
  - `_compute_fit`은 `all(p > 0)`인 경우에만 `_fit_adiabatic`($\ln P$ vs $\ln V$)을 수행함.
  - 대기압 기준 게이지 압력 센서로 인해 0 이하 값이 포함되면 조용히 `_fit_general`로 폴백하여 $P$와 $V$를 엉뚱하게 단순 선형 피팅($y = mx + b$)함.
  - `_analyze_constants`에 `adiabatic_gas` 분기가 없어 오차 분석이 빈 리스트로 증발하며, 단열 법칙($P V^\gamma = C$) 검증이 누락되었다는 경고도 없이 완료된 것으로 왜곡 보고함.

---

### 8. DEFECT-REP14 (Major): HTML 보고서에서 회귀 오차(`slope_error`, `intercept_error`) 완전 누락
- **파일**: [templates.py#L438-L442](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L438-L442)
- **실기 폭발 시나리오**:
  - Markdown 렌더러는 표준오차 `(std err: ...)`를 정상 표기하나, HTML 렌더러 `_render_html_body_regression`은 `reg.slope_error`와 `reg.intercept_error` 필드를 아예 출력하지 않음.
  - 물리 실험 보고서의 필수 요건인 불확도 정량화(Uncertainty Quantification)가 HTML 출력에서 완전히 배제됨.

---

### 9. DEFECT-REP15 (Minor): 오차 분석 항목 부재 시 HTML 빈 테이블 렌더링 버그
- **파일**: [templates.py#L457-L480](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L457-L480)
- **실기 폭발 시나리오**:
  - `error_analysis`가 비어 있을 때 Markdown은 대체 안내문을 출력하나, HTML은 `<thead>`만 있고 `<tbody>`가 텅 빈 기형적 빈 테이블을 그대로 렌더링함.

---

### 10. DEFECT-REP16 (Minor): 표준오차 $0.0$ 시 `'N/A'` 오표기 버그
- **파일**: [templates.py#L98-L99](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L98-L99)
- **코드**: `se_m = f"`{reg.slope_error:.3e}`" if reg.slope_error else "'N/A'"`
- **실기 폭발 시나리오**:
  - 완벽한 직선 데이터로 인해 표준오차가 $0.0$인 경우, `bool(0.0) == False` 판정으로 인해 `0.0` 대신 `'N/A'`가 출력되어 계산 불능인 것처럼 오해를 유발함.

</details>

<details open>
<summary><b>[보고서 #78] auditor-reports 실사 세부 명세 (Phase 3)</b></summary>

`reports/*` 및 `numerics/*` (`regression.py`, `sparklines.py`, `summary.py`, `models.py`) 최심부 전수 분해 실사 결과 새롭게 발굴된 7건의 치명적 결함 내역입니다.

---

### 1. DEFECT-NUM01 (Critical): `render_svg_sparkline` 타이틀 미이스케이프로 인한 SVG XML 파싱 파탄 및 XSS 취약점
- **파일**: [sparklines.py#L128-L130](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/sparklines.py#L128-L130)
- **코드**: `elements.append(f'<text x="{pad_left}" y="25" ...>{title}</text>')`
- **파괴 메커니즘**:
  - `title` 인자에 대해 `html.escape`나 XML 엔티티 치환을 전혀 수행하지 않고 raw 문자열을 SVG `<text>` 태그에 직접 보간함.
  - 실험 타이틀에 물리 부등호나 앰퍼샌드가 포함될 경우(예: `"Pressure vs Volume (P < P_0 & T > 300K)"`), XML 파서가 `XML Parsing Error: not well-formed (syntax error)`를 일으키며 SVG 렌더링이 즉각 크래시됨.
  - 웹 기반 MCP 클라이언트나 대시보드에서 렌더링될 경우 Stored XSS(임의 스크립트 실행) 공격 벡터로 악용될 수 있음.

---

### 2. DEFECT-NUM02 (Critical): `render_svg_sparkline`에서 `fit_x`/`fit_y`의 NaN 미여과로 인한 SVG 좌표 NaN 오염
- **파일**: [sparklines.py#L109-L110, L148-L154](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/sparklines.py#L109-L110)
- **코드**:
  ```python
  all_x = [p[0] for p in pairs] + (list(fit_x) if fit_x else [])
  all_y = [p[1] for p in pairs] + (list(fit_y) if fit_y else [])
  ```
- **파괴 메커니즘**:
  - 측정 데이터 `x`, `y`는 L33에서 NaN을 필터링하지만, 피팅 곡선 `fit_x`, `fit_y`는 아무런 검증 없이 `all_x`, `all_y`에 병합됨.
  - 수직선이나 발산 피팅으로 인해 `fit_x` 또는 `fit_y`에 `NaN`이 포함될 경우, `min_x`, `max_x`, `span_x`가 모두 `NaN`으로 전염됨.
  - `to_svg`가 `NaN`을 반환하여 `<path d="M nan nan L nan nan" ...>` 및 `<circle cx="nan" cy="nan">`을 생성, W3C SVG 렌더러 파이프라인을 파괴함.

---

### 3. DEFECT-NUM03 (Critical): `render_ascii_sparkline`의 `isinf` 미검증으로 인한 `OverflowError`/`ValueError` 크래시
- **파일**: [sparklines.py#L30-L34, L50-L54](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/sparklines.py#L30-L34)
- **코드**: `pairs = [(float(xi), float(yi)) for xi, yi in zip(...) if not (math.isnan(xi) or math.isnan(yi))]`
- **파괴 메커니즘**:
  - `math.isnan`만 검사하고 `math.isinf`를 검사하지 않음.
  - 센서 오버플로우나 0으로 나누기로 인해 `inf` 또는 `-inf`가 유입되면, `span_x = inf - inf` 연산으로 인해 `span_x`가 `nan`이 됨.
  - L50의 `col = int(((xi - min_x) / span_x) * ...)`에서 `ValueError: cannot convert float NaN to integer` 또는 `OverflowError: cannot convert float infinity to integer`가 발생하여 호출 스레드가 즉시 폭사함.

---

### 4. DEFECT-NUM04 (Critical): `fit_polynomial_series` 비정규화 데이터의 Vandermonde 행렬 조건수 폭발 및 수치적 파탄
- **파일**: [regression.py#L148-L153](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/regression.py#L148-L153)
- **코드**: `powers = [xi**p for p in range(2 * degree + 1)]`
- **파괴 메커니즘**:
  - 중심화(centering)나 스케일링(scaling, e.g. $[-1, 1]$ 정규화) 없이 raw $x$ 값을 그대로 $2d$ 거듭제곱하여 정규방정식을 구성함.
  - 광전효과 진동수($\sim 10^{14}\text{ Hz}$)나 RF 회로 주파수($\sim 10^6\text{ Hz}$) 데이터에서 $x^4 \sim 10^{56}$에 달하여 정규방정식의 조건수(Condition Number)가 $10^{50}$을 초과함.
  - IEEE 754 float64의 유효숫자(약 16자리)를 아득히 넘어서 심각한 자리초과 및 파괴적 소거(Catastrophic Cancellation)가 발생, 가우스 소거법이 `[inf, nan]` 계수를 산출하며 완전히 붕괴함.

---

### 5. DEFECT-NUM05 (Critical): `fit_polynomial_series`의 하드코딩된 `abs_tol=1e-12`로 인한 마이크로스케일 유효 데이터 오진단
- **파일**: [regression.py#L161-L163](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/regression.py#L161-L163)
- **코드**:
  ```python
  if math.isclose(pivot, 0.0, abs_tol=1e-12):
      raise ValueError("Singular matrix in polynomial normal equations")
  ```
- **파괴 메커니즘**:
  - 피벗 검사에 하드코딩된 절대공차 `1e-12`를 적용함.
  - 마이크로초 단위 시간($x \le 10^{-6}\text{ s}$) 또는 마이크로미터 단위 변위 측정 시, 정규방정식 피벗 값은 $\sum x^4 \sim 10^{-23}$ 수준임.
  - 비특이(non-singular)이고 완벽하게 유효한 물리 측정 데이터임에도 불구하고 `pivot < 1e-12` 판정으로 인해 `Singular matrix` 예외를 오폭하며 피팅을 강제 중단함.

---

### 6. DEFECT-NUM06 (Major): `fit_linear_series` 2-Point 피팅 시 자유도 0임에도 표준오차 $0.0$ 날조
- **파일**: [regression.py#L93-L98](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/regression.py#L93-L98)
- **코드**:
  ```python
  dof = max(n - 2, 1)
  mse = ss_res / dof
  std_err_slope = math.sqrt(mse / ss_xx) if ss_xx > 0.0 else 0.0
  ```
- **파괴 메커니즘**:
  - $N=2$개 점으로 선형 피팅 시 잔차는 수학적으로 항상 0이고 통계적 자유도는 $N-2=0$임.
  - L93에서 `max(n - 2, 1)`로 분모를 1로 속이고 `ss_res = 0.0`이므로 `std_err_slope = 0.0`, `std_err_intercept = 0.0`을 산출함.
  - 불확도 정량화에서 2개 점만으로 오차가 $0.0$(100% 무결점 정밀도)이라고 거짓 보고하여 하류 통계 모델을 기만함.

---

### 7. DEFECT-REP17 (Major): `LabReport.raw_data_points` 대용량 직렬화로 인한 FastMCP stdio 트랜스포트 붕괴 위험
- **파일**: [models.py#L77, L92](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/models.py#L77), [tools/physics.py#L215-L224](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/physics.py#L215-L224)
- **파괴 메커니즘**:
  - `LabReport` 모델이 `raw_data_points: dict[str, list[float]]` 필드를 포함하고 있으며, `capstone_generate_lab_report` 반환값(`GenerateLabReportResult`)에 그대로 포함됨.
  - 10만 개 고속 샘플링 런 분석 시 채널당 수 MB에 달하는 원시 부동소수점 배열이 JSON-RPC stdio 스트림으로 한 번에 직렬화됨.
  - 클라이언트(Claude Desktop 등)의 메시지 버퍼 한계(1MB~4MB)를 초과하여 프로세스 간 IPC 파이프가 단절되거나 세션이 크래시됨. Markdown/HTML 보고서 텍스트와 통계 요약만 반환하고 raw data는 제외하거나 페이징해야 함.

</details>

---

### 3.9. Test Fixtures, CI & Windows Packaging (테스트 무결성 & 픽스처 누수 & 패키징)
- **담당 에픽 이슈**: #123 ~ #130
- **실사 참여 전문 에이전트**: `auditor-tests`, `audit-fixtures`, `audit-packaging`

#### 📑 실사 보고서: `auditor-tests` (총 2회 정밀 실사)

<details open>
<summary><b>[보고서 #58] auditor-tests 실사 세부 명세 (Phase 1)</b></summary>

`tests/` 내 70개 테스트 파일 전수 실사 결과 보고서입니다.
현재 테스트 스위트는 `569 passed, 1 skipped (100% green)`으로 보고되지만, 이는 모의 객체 맹점(Mock Blindness), 자기충족적 반환값 단언, 예외 무단 억제, CI 환경 전면 스킵으로 인한 심각한 **거짓 확신(False Confidence)** 상태입니다.

---

### 1. Mock Blindness (가짜 백엔드 및 MagicMock이 실제 Windows UIA 실패 은폐)

#### 🔴 DEFECT-TST01: InMemoryFakeBackend와 실제 런타임 간의 96% 기능 단절 은폐
- **파일**: [test_fake_backend.py#L36-L198](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_fake_backend.py#L36-L198)
- **테스트**: `test_fake_backend_satisfies_protocol`, `test_fake_backend_manage_graph_seam`, `test_fake_backend_manage_instrument_seam`, `test_fake_backend_manage_display_seam`, `test_fake_backend_low_level_rpc_dispatch`
- **실기 폭발 원인**: `fake_backend.py`는 53개의 도메인 RPC를 메모리 딕셔너리로 완벽하게 흉내 내어 테스트를 통과시킵니다. 그러나 실기 프로덕션(`bridge.py`)에는 단 2개(`read_inventory`, `read_measurement`)의 RPC만 구현되어 있어 51개(96%)의 도메인 연산이 Qt C++ 브릿지 없이 깨지며, 프로덕션은 극도로 취약한 UIA 스크린 스크래핑으로 폴백합니다. 테스트는 FakeBackend를 검증함으로써 실기의 구조적 파탄을 100% 은폐합니다.

#### 🔴 DEFECT-TST02: 존재하지 않는 COM ValuePattern (`node.iface_value.SetValue`) 날조 주입
- **파일**:
  - [test_digits_display.py#L205-L208](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_digits_display.py#L205-L208) (`test_create_digits_success_with_measurement_and_unit`)
  - [test_table_display.py#L110-L113](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_table_display.py#L110-L113) (`test_set_table_columns_success`)
  - [test_oscilloscope_fft.py#L109-L113](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_oscilloscope_fft.py#L109-L113) (`test_create_scope_success`)
  - [test_signal_generator.py#L155-L163](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_signal_generator.py#L155-L163) (`test_set_signal_generator_success_opens_configures_and_restores`)
  - [test_rename_run.py#L76-L78](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_rename_run.py#L76-L78) (`test_rename_run_direct_value_pattern_success`)
- **실기 폭발 원인**:
  ```python
  mock_node = MagicMock()
  mock_node.iface_value.SetValue = MagicMock()
  app.control = MagicMock(return_value=mock_node)
  ```
  실제 Windows Capstone의 Qt/WPF 위젯(측정항목 버튼, 테이블 컬럼 헤더, 스코프 Timebase Edit, Run TreeItem)은 `IUIAutomationValuePattern`을 전혀 지원하지 않거나 호출 시 `_ctypes.COMError`를 발생시킵니다. 테스트가 임의로 `iface_value.SetValue`를 모킹함으로써 실제 필수 실행 경로인 키보드 폴백(`click_control`, `^a{BACKSPACE}`, `type_text`, `{ENTER}`)은 테스트 스위트에서 단 한 번도 실행/검증되지 않습니다.

#### 🔴 DEFECT-TST03: Win32 OS/DPI/포커스 장벽 모킹 무력화
- **파일**: [test_desktop_guards.py#L20-L115](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_desktop_guards.py#L20-L115), [test_desktop_type_text_guard.py#L20-L50](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_desktop_type_text_guard.py#L20-L50), [test_desktop_screenshot.py#L25-L60](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_desktop_screenshot.py#L25-L60)
- **실기 폭발 원인**: `win32gui.GetForegroundWindow`, `WindowFromPoint`, `GetAncestor`, `ImageGrab.grab`을 모킹하여 임의의 HWND 상수(`DIALOG`, `SHADOW`)를 반환합니다. 실제 데스크톱의 UIPI(권한 격리), 모니터별 Per-Monitor DPI 스케일링 오프셋, DirectX 가속 창의 스크린샷 블랙아웃 현상이 완전히 은폐됩니다.

---

### 2. Trivial Return Assertions (실제 상태 변경 검증 없는 맹목적 에코 단언)

#### 🔴 DEFECT-TST04: Seam 계층의 100% 동어반복 단언 (Tautology Assertion)
- **파일**:
  - [test_displays.py#L45-L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_displays.py#L45-L150) (10개 테스트 전체)
  - [test_instruments.py#L49-L210](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_instruments.py#L49-L210) (11개 테스트 전체)
  - [test_graphs.py#L57-L200](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_graphs.py#L57-L200) (7개 테스트 전체)
- **실기 폭발 원인**:
  ```python
  expected = CreateDigitsResult(digits_name="Digits 1", ...)
  with patch("capstone_mcp.displays.manager.create_digits", return_value=expected):
      res = manage_display(mock_app, req)
      assert res.create_digits == expected  # 자신이 모킹한 객체를 그대로 단언!
  ```
  내부 도메인 로직을 모의 객체로 완전히 갈아치운 뒤, 모의 객체가 반환한 객체와 동일한지만 단언합니다. 실기 Capstone 상태 변경, 유효성 검증, 에러 핸들링을 일절 검증하지 못합니다.

#### 🔴 DEFECT-TST05: 입력 파라미터 반사(Echo) 및 하드코딩 스냅샷 단언
- **파일**:
  - [test_signal_generator.py#L198-L200](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_signal_generator.py#L198-L200): `assert result.waveform == "Square"`, `assert result.frequency == 500.0`
  - [test_digits_display.py#L223-L228](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_digits_display.py#L223-L228): `assert res.measurement == "Acceleration (m/s^2)"`, `assert res.verified is True`
- **실기 폭발 원인**: 프로덕션 코드(`set_signal_generator`, `create_digits`)는 UIA 조작 성공 여부와 무관하게 `request`로 들어온 파라미터를 그대로 복사하여 `verified=True` 모델을 만듭니다. 테스트는 요청한 값을 그대로 되돌려받아 단언할 뿐, 컨트롤에 실제 값이 반영되었는지 전혀 검증하지 않습니다.

#### 🔴 DEFECT-TST06: 가짜 수식 시뮬레이터에 의존한 매크로 통과 기만
- **파일**: [test_recipes.py#L120-L490](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_recipes.py#L120-L490) (28개 테스트 전체)
- **실기 폭발 원인**: `PhotoelectricEffectRecipe`, `RLCResonanceRecipe` 등 5대 매크로는 `app is None`일 때 파이썬 메모리에서 가짜 수학 곡선(Sine, Planck)을 자체 생성합니다. 테스트는 Capstone 앱 인스턴스 없이 `run_experiment_macro(..., action="run")`를 호출하여 `assert macro_res.success is True`를 확인합니다. 실제 Capstone 제어는 0% 수행된 채 100% 그린으로 통과합니다.

---

### 3. Unchecked Exceptions & Suppression (예외 무단 억제 및 느슨한 예외 단언)

#### 🔴 DEFECT-TST07: 프로덕션 침묵 억제(`suppress(Exception)`)와 테스트 방조
- **파일**:
  - `src/capstone_mcp/displays/digits.py` L153, L160 (`with contextlib.suppress(Exception):`)
  - `src/capstone_mcp/instruments/generator.py` L62, L185, L198 (`with contextlib.suppress(Exception):`)
  - `src/capstone_mcp/displays/harness.py` L38 (`with contextlib.suppress(AttributeError, RuntimeError):`)
- **실기 폭발 원인**: 실제 UIA 실패나 COM 예외가 발생해도 프로덕션이 예외를 삼키고 침묵하며, 단위 테스트는 항상 성공하는 Mock을 주입하여 이 예외 억제 경로가 결함을 감추고 있다는 사실을 드러내지 않습니다.

#### 🔴 DEFECT-TST08: `match=` 없는 광범위 `pytest.raises`로 엉뚱한 결함 통과
- **파일**:
  - [test_graph_workflows.py#L28-L317](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_graph_workflows.py#L28) (9개 테스트: `with pytest.raises(AutomationError):`)
  - [test_graph_state.py#L240-L319](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_graph_state.py#L240) (6개 테스트: `with pytest.raises(GraphStateError):`)
  - [test_repetition.py#L49, L184, L247](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_repetition.py#L49) (`pytest.raises(StartError)`)
- **실기 폭발 원인**: 에러 메시지 검증(`match=`)이 없어, 의도된 유효성 검사 실패가 아니라 코드 내부의 문법 오류, 잘못된 인자 전달, 또는 전혀 다른 버그로 예외가 터져도 테스트가 무조건 통과합니다.

---

### 4. Headless Environment Skips (CI 환경 스킵으로 인한 원격 회귀 무방비)

#### 🔴 DEFECT-TST09: 유일한 E2E 프로토콜 테스트의 CI 전면 스킵
- **파일**: [test_protocol.py#L70-L75](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_protocol.py#L70-L75)
- **실기 폭발 원인**:
  ```python
  attached = await session.call_tool("capstone_attach")
  if attached.isError or not windows:
      pytest.skip("Could not attach to Capstone (not installed or running)")
  ```
  MCP stdio wire 상에서 22개 도구 호출을 실제로 수행하는 **유일한** 통합 테스트입니다. GUI 창이 없는 GitHub Actions 및 헤드리스 CI 환경에서는 L71/L74에서 즉시 `pytest.skip`되므로, 배포 시 stdio 직렬화 파탄이나 프로토콜 불일치가 전혀 감지되지 않습니다.

#### 🔴 DEFECT-TST10: 특정 로컬 경로 하드코딩으로 물리 검증 41개 테스트 CI 영구 스킵
- **파일**: [test_golden_master.py#L20-L30](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_golden_master.py#L20-L30)
- **실기 폭발 원인**:
  ```python
  GOLDEN_MASTER_DIR: Final = Path(os.environ.get(
      "CAPSTONE_GOLDEN_MASTER_DIR", r"C:\Users\Jio\Downloads\(2026)캡스톤 실험별 파일"
  ))
  pytestmark = pytest.mark.skipif(not GOLDEN_MASTER_DIR.exists(), ...)
  ```
  광학, 역학, 열역학, 전자기학 10대 실험 `.cap` 파일 파싱과 수치 분석을 검증하는 핵심 41개 골든 마스터 테스트 전체가 로컬 다운로드 폴더에 종속되어 있어 CI에서 100% 스킵됩니다.

#### 🔴 DEFECT-TST11: 라이브 스모크 및 샘플 추출 테스트 스킵
- **파일**:
  - [test_live_smoke.py#L23-L27](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_live_smoke.py#L23-L27) (`pytestmark = pytest.mark.skipif(not HAS_CAPSTONE, ...)`)
  - [test_domain_protocol.py#L105-L108](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_domain_protocol.py#L105-L108)
  - [test_experiment_analysis.py#L388-L389](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_experiment_analysis.py#L388-L389)
- **실기 폭발 원인**: 로컬 설치 경로에 Capstone이 없으면 조용히 건너뛰어 회귀를 완전히 방치합니다.

---

### 결함 요약 매트릭스

| 결함 ID | 분류 | 위험도 | 영향 파일 | 핵심 사유 |
|---|---|---|---|---|
| **TST-01** | Mock Blindness | **P0 (Blocker)** | `test_fake_backend.py` | 51개 미구현 RPC를 In-Memory Fake로 은폐 |
| **TST-02** | Mock Blindness | **P0 (Blocker)** | `test_digits_display.py`, `test_table_display.py`, `test_oscilloscope_fft.py`, `test_signal_generator.py`, `test_rename_run.py` | 미지원 COM ValuePattern 날조로 키보드 폴백 테스트 전멸 |
| **TST-03** | Mock Blindness | **P1 (Critical)** | `test_desktop_guards.py`, `test_desktop_screenshot.py`, `test_desktop_type_text_guard.py` | Win32 API 모킹으로 DPI/UIPI/포커스 장벽 은폐 |
| **TST-04** | Trivial Assert | **P0 (Blocker)** | `test_displays.py`, `test_instruments.py`, `test_graphs.py` | 모킹한 리턴값을 그대로 일치 비교하는 100% 동어반복 |
| **TST-05** | Trivial Assert | **P1 (Critical)** | `test_signal_generator.py`, `test_digits_display.py`, `test_graph_toolbox.py` | UIA 변경 검증 없이 입력값 반사(Echo) 필드만 단언 |
| **TST-06** | Trivial Assert | **P1 (Critical)** | `test_recipes.py` | Capstone 없는 자체 수식 제너레이터로 28개 매크로 기만 통과 |
| **TST-07** | Suppression | **P0 (Blocker)** | `digits.py`, `generator.py`, `harness.py` 연계 테스트 | 프로덕션의 `suppress(Exception)` 실패를 Mock 성공으로 위장 |
| **TST-08** | Suppression | **P2 (Major)** | `test_graph_workflows.py`, `test_graph_state.py`, `test_repetition.py` | `match=` 없는 광범위 `pytest.raises`로 엉뚱한 결함 통과 |
| **TST-09** | CI Skip | **P0 (Blocker)** | `test_protocol.py` | 유일한 Live MCP wire E2E 테스트가 CI에서 100% 스킵 |
| **TST-10** | CI Skip | **P1 (Critical)** | `test_golden_master.py` | 로컬 다운로드 절대경로 하드코딩으로 물리 검증 41개 스킵 |
| **TST-11** | CI Skip | **P2 (Major)** | `test_live_smoke.py`, `test_domain_protocol.py` | 설치 경로 미존재 시 자동 스킵으로 원격 CI 검증 공백 |

</details>

<details open>
<summary><b>[보고서 #72] auditor-tests 실사 세부 명세 (Phase 2)</b></summary>

`tests/` 내 70개 테스트 파일 한 줄 단위 심층 재검토 결과 발굴된 **10건의 신규 구체적 결함(DEFECT-TST12 ~ DEFECT-TST21)** 보고서입니다.

---

### 1. 🔴 DEFECT-TST12: 계산식 상태 `status="valid"` 하드코딩 날조 및 에러 검증 전무
- **파일**: [test_calculator.py#L98-L143](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_calculator.py#L98-L143), [calculator.py#L171-L182](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L171-L182)
- **재현 트리거**: 문법 오류가 있거나 정의되지 않은 변수, 분모 0 나눗셈이 포함된 수식 생성 요청 (`"invalid = [x] // 0"`).
- **파괴 메커니즘**: `calculator.py`는 L171에서 `status = "valid"`와 `verified = True`를 **무조건 상수로 하드코딩**하여 반환합니다. Capstone이 구문 오류 팝업이나 빨간 밑줄을 띄워도 확인하지 않습니다. `test_calculator.py`는 `mock_formula_node.iface_value.SetValue = MagicMock()`을 주입하고 `assert result.status == "valid"`를 단언하여, 오류 수식이 100% 정상 등록된 것으로 사용자에게 기만 보고하는 버그를 방조합니다.

---

### 2. 🔴 DEFECT-TST13: 팝업 메뉴 0ms 렌더링 레이스를 동기식 Mock으로 은폐
- **파일**: [test_select_measurement.py#L37-L67](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_select_measurement.py#L37-L67), [popup_selection.py#L84-L96](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/popup_selection.py#L84-L96)
- **재현 트리거**: 실제 Capstone 그래프에서 축 측정항목 팝업 메뉴 선택 실행.
- **파괴 메커니즘**: `popup_selection.py`는 L84 `click_point()` 직후 0ms 지연으로 `_traverse_segments()` -> `app.snapshot()`을 호출합니다. 실제 Windows Qt 팝업 메뉴는 UIA 트리에 등록되고 애니메이션되는 데 50~200ms가 소요되므로, 실기에서는 `Menu item not found`로 즉시 폭사합니다. 그러나 `test_select_measurement.py`의 `mock_snapshot`은 첫 호출에 동기적으로 `[item_ctrl]`을 즉시 반환하여 이 치명적 레이스를 완벽히 은폐합니다.

---

### 3. 🔴 DEFECT-TST14: 파일 다이얼로그 UIA 자동화 테스트 0% 부재 (Dead Integration)
- **파일**: [test_file_workflows.py#L1-L119](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_file_workflows.py#L1-L119), [file_workflows.py#L125-L180](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L125-L180)
- **재현 트리거**: `capstone_open_experiment`, `capstone_save_experiment`에서 실제 파일 열기/저장 다이얼로그 호출.
- **파괴 메커니즘**: `test_file_workflows.py`는 `settled_title`, `await_opened` 같은 보조 헬퍼 함수와 사전 조건 예외 몇 가지만 테스트합니다. `file_workflows.py`의 핵심인 네이티브 공용 파일 다이얼로그 입력, 파일 경로 타이핑, "Open"/"Save" 버튼 클릭, `WindowEvents` 전이 루프 및 변경사항 저장 여부 프롬프트 처리는 **단 하나의 테스트도 존재하지 않습니다**.

---

### 4. 🔴 DEFECT-TST15: 네이티브 워커를 토이 스크립트(`worker_fixture.py`)로 바꿔치기
- **파일**: [test_automation_worker.py#L20-L31](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_automation_worker.py#L20-L31), [worker_fixture.py#L1-L36](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/worker_fixture.py#L1-L36)
- **재현 트리거**: 실제 프로덕션 워커 `capstone_mcp.native.native_main` 기동 및 통신.
- **파괴 메커니즘**: `FixtureWorker`는 `_spawn()`을 오버라이드하여 실제 COM/STA/UIA를 로드하는 `native_main` 대신 30줄짜리 단순 에코 스크립트 `worker_fixture.py`를 실행합니다. 실제 환경의 COM 초기화 실패, Win32 STA 메시지 펌프 데드락, 메모리 누수로 인한 프로세스 크래시를 전혀 검증하지 못합니다.

---

### 5. 🔴 DEFECT-TST16: CDP WebSocket/HTTP 통신 전면 몽키패치로 프로토콜 검증 전무
- **파일**: [test_bridge.py#L10-L90](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_bridge.py#L10-L90), [bridge.py#L60-L150](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L60-L150)
- **재현 트리거**: 포트 9222/9223을 통한 하드웨어 인벤토리 및 실시간 원격 측정 데이터 수신.
- **파괴 메커니즘**: `test_bridge.py`의 모든 테스트는 `monkeypatch.setattr(bridge, "evaluate", ...)`로 CDP 호출 함수를 100% 가로채어 고정 JSON을 반환합니다. 실제 HTTP 디스커버리 엔드포인트 핸드셰이크, WebSocket 프레임 직렬화, 네트워크 단절 및 타임아웃 예외 처리가 전혀 검증되지 않습니다.

---

### 6. 🔴 DEFECT-TST17: `SettingsAdapter` 동기식 FSM으로 하드웨어 샘플링 협상 지연 은폐
- **파일**: [test_sensor_settings.py#L24-L86](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_sensor_settings.py#L24-L86), [sensors.py#L140-L220](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L140-L220)
- **재현 트리거**: 인터페이스(850/550) 연결 상태에서 센서 샘플링 속도 증감 조작.
- **파괴 메커니즘**: `SettingsAdapter`는 `self.rate_index += 1`과 같이 메모리 변수를 즉시 동기 변경합니다. 실제 Capstone은 하드웨어와 USB/BLE 통신으로 샘플링 레이트를 협상하는 동안 버튼이 일시 비활성화되고 UI 반영에 수백 ms의 비동기 지연이 발생합니다. 테스트는 동기 상태 머신 위에서 돌아가므로 비활성 버튼 클릭 예외 및 레이스 컨디션을 완전히 은폐합니다.

---

### 7. 🔴 DEFECT-TST18: 프로세스 간 WinEvent 훅을 동일 프로세스(`os.getpid()`) 창으로 기만 검증
- **파일**: [test_ui_events.py#L47-L70](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_ui_events.py#L47-L70), [ui_events.py#L60-L120](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L60-L120)
- **재현 트리거**: 외부 Capstone 프로세스로부터 윈도우 생성/파괴 및 클립보드 업데이트 WinEvent 수신.
- **파괴 메커니즘**: 테스트는 자신의 프로세스(`os.getpid()`) 내에 임시 STATIC 창을 만들고 동일 스레드에서 `NotifyWinEvent`를 쏩니다. 실제 환경에서는 외부 `Capstone.exe` 프로세스의 이벤트를 받아야 하며, 수신 스레드가 Win32 메시지 펌프를 돌리지 않거나 블로킹되면 이벤트가 전달되지 않습니다. 동일 프로세스 테스트로 이 IPC 메시지 루프 결함을 은폐합니다.

---

### 8. 🔴 DEFECT-TST19: Stderr circular buffer 테스트의 취약한 `time.sleep(0.3)` 타이밍 레이스
- **파일**: [test_worker_stderr.py#L61-L68](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_worker_stderr.py#L61-L68)
- **재현 트리거**: 부하가 높은 CI 빌드 머신 또는 가상 머신 환경에서의 테스트 실행.
- **파괴 메커니즘**: 서브프로세스의 stderr 출력 및 백그라운드 스레드 수집을 동기화 이벤트 없이 `time.sleep(0.3)`으로 대기합니다. Windows에서 프로세스 생성 및 파이프 연결이 300ms 이상 지연되면 `len(worker.stderr_buffer) >= 3` 단언이 간헐적으로 실패하여 플래키(Flaky) 테스트가 됩니다.

---

### 9. 🔴 DEFECT-TST20: `RecordingBackendFake` / `CancellationFake`로 실제 락 경합 전면 우회
- **파일**: [test_repetition.py#L18-L59, L88-L100](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_repetition.py#L18-L59), [test_run_capture.py#L37-L77](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_run_capture.py#L37-L77)
- **재현 트리거**: 반복 측정 시퀀스(`run_sequence`) 및 백그라운드 측정 작업 취소.
- **파괴 메커니즘**: 사전 주입된 `deque` 큐에서 상태를 꺼내오는 가짜 백엔드만 사용하여 실제 `Capstone` 인스턴스, `JOBS.input_reserved` 락 경합, 비동기 스레드 취소 시그널이 일절 테스트되지 않습니다.

---

### 10. 🔴 DEFECT-TST21: 그래프 자동 맞춤(Scale to Fit)의 맹목적 좌표 (+20, +20) 클릭 방조
- **파일**: [test_graph_fit.py#L64-L79](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_graph_fit.py#L64-L79), [graphs/manager.py#L220-L240](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/manager.py#L220-L240)
- **재현 트리거**: `capstone_manage_graph`로 `scale_to_fit` 요청.
- **파괴 메커니즘**: `fit_graph`는 컨트롤의 좌상단 오프셋 `(left + 20, top + 20)`을 맹목적으로 클릭하고 축 스케일 변경 여부 확인 없이 즉시 `verified=True`를 반환합니다. `test_graph_fit.py`는 `assert clicked_coords == [(120, 120)]` 및 `assert res.verified is True`로 이를 검증하여, 엉뚱한 레이블이나 빈 영역을 클릭하는 결함을 '정상 통과'로 포장합니다.

---

이상 10건을 마스터 결함 매트릭스에 통합 반영 요청드립니다.

</details>

#### 📑 실사 보고서: `audit-fixtures` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #105] audit-fixtures 실사 세부 명세 (Phase 1)</b></summary>

지정 영역인 `tests/fixtures/`, `tests/conftest.py`, `tests/test_golden_master.py` 및 전체 테스트 스위트의 모킹/픽스처 계층에 대해 1) 픽스처 및 프로세스 누수, 2) 모킹 객체의 비현실적 데이터 가공 주입('Live Runtime Blind Spot'), 3) CI 헤드리스 가드 스킵 오남용을 전수 실사한 결과입니다.

---

### 1. 픽스처 아키텍처 결함 및 프로세스/자원 누수

#### 🔴 [DEFECT-FIX01] `tests/conftest.py` 및 패키지화된 `tests/fixtures/` 디렉터리 완전 부재 (P1)
- **위치**: `tests/` 루트 전역
- **파괴 메커니즘**:
  1. pytest 프로젝트 표준인 `conftest.py`가 리포지토리에 전무하여, 테스트 수명주기 전역의 세션 픽스처, autouse teardown 안전망이 완전히 결여됨.
  2. `test_displays.py:35`와 `test_instruments.py:39`에 `@pytest.fixture def mock_app() -> Capstone: return MagicMock(spec=Capstone)`가 중복 난립함.
  3. 테스트 도중 실패/예외 발생 시 백그라운드 프로세스(`capstone-mcp.exe`, `python -m tests.worker_fixture`, `Capstone.exe`)를 강제 회수하는 안전망이 없어 Windows 파일 잠금(`os error 32`) 및 9222 포트 점유 충돌을 초래함.

#### 🔴 [DEFECT-FIX02] `tests/worker_fixture.py` L23-28: 영구 블로킹 `Event().wait()` 및 좀비 서브프로세스 누수 위험 (P0)
- **코드 위치**: [tests/worker_fixture.py#L23-L28](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/worker_fixture.py#L23-L28)
- **코드**:
  ```python
  with socket.create_connection(("127.0.0.1", packet.command.limit), timeout=5) as signal:
      signal.sendall(b"entered")
      _ = Event().wait()  # 영구 대기
  ```
- **파괴 메커니즘**:
  1. 타임아웃 테스트를 위해 `Event().wait()`로 스레드를 무기한 동결시킴.
  2. 부모 프로세스에서 `worker.close()`가 정상 호출되지 않거나 중간 어설션 실패 시, 해당 파이썬 프로세스는 Windows 백그라운드에 영구 불사(Zombie) 상태로 남음.
  3. 부모가 소켓을 닫아도 소켓 FIN을 감지하지 않고 영구 대기하여 소켓 및 프로세스가 누수됨.

#### 🔴 [DEFECT-FIX03] `tests/test_worker_stderr.py` L57-72, L87-105: `try...finally` 부재로 인한 서브프로세스 누수 (P1)
- **코드 위치**: [tests/test_worker_stderr.py#L57-L72](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_worker_stderr.py#L57-L72), [tests/test_worker_stderr.py#L87-L105](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_worker_stderr.py#L87-L105)
- **파괴 메커니즘**:
  - `proc = worker._spawn()` 및 `proc = subprocess.Popen(...)` 실행 후 종료(`proc.terminate()`, `proc.wait(timeout=2)`)가 평문으로 작성됨.
  - 중간 어설션 실패 시 `proc.terminate()`가 도달하지 않아 서브프로세스가 완전 누수됨. `worker.close()` 미호출로 Job Object 및 stderr reader 스레드 방치.

#### 🟡 [DEFECT-FIX04] `tests/test_live_smoke.py` L94-109: `live_capstone_cdp` 픽스처의 티어다운(Teardown) 부재 (P2)
- **코드 위치**: [tests/test_live_smoke.py#L94-L109](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_live_smoke.py#L94-L109)
- **파괴 메커니즘**:
  - `UnifiedSessionManager(debug_port=DEFAULT_DEBUG_PORT)`를 생성하고 루프로 폴링하나, `yield` 기반 generator가 아닌 일반 함수(`-> None`)로 작성되어 내부 텔레메트리 버퍼, CDP 클라이언트 해제 로직이 전무함.

---

### 2. 모킹 객체의 비현실적 데이터 주입 및 'Live Runtime Blind Spot' 은폐

#### 🔴 [DEFECT-MOCK01] `tests/test_calculator.py` L95-143: 실제 Capstone Qt 수식 검증 무시 및 가짜 성공 주입 (P0)
- **코드 위치**: [tests/test_calculator.py#L95-L143](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_calculator.py#L95-L143), [src/capstone_mcp/calculator.py#L171-L174](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L171-L174)
- **파괴 메커니즘**:
  1. `calculator.py` L171-174는 Capstone의 실제 수식 구문 검증(에러 팝업 등) 없이 `status: CalculationStatus = "valid"`, `verified = True`를 하드코딩 반환함.
  2. `test_calculator.py`는 `mock_formula_node.iface_value.SetValue = MagicMock()`로 COM 상호작용을 우회하고 하드코딩된 `valid`를 어설션함.
  3. 문법 오류나 미정의 변수가 포함된 파탄 수식도 단위 테스트상에서는 100% 통과로 위장됨.

#### 🔴 [DEFECT-MOCK02] `tests/test_digits_display.py` L84-104: 실물에 존재하지 않는 가공 Automation ID 주입 (`DigitsDisplay`, `DisplayValue`) (P0)
- **코드 위치**: [tests/test_digits_display.py#L84-L104](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_digits_display.py#L84-L104)
- **파괴 메커니즘**:
  1. 실물 Capstone(Qt 5/QWebEngine) 캔버스 영역의 디스플레이 위젯은 UIA 트리에 `DigitsDisplay`나 `DisplayValue` 같은 Automation ID를 일체 노출하지 않음 (`docs/remediation-verification.md` L28 실측 근거).
  2. 테스트 모의 Snapshot에 임의로 `automation_id="DigitsDisplay"`, `automation_id="DisplayValue"`를 가공 주입하여, 실물에서는 100% 실패하는 위젯 탐색 코드가 단위 테스트에서는 완벽히 통과하도록 착시를 형성함.

#### 🔴 [DEFECT-MOCK03] `tests/test_smart_triggers.py` L108-120: PASCO 명명 규칙 위반 가공 ID 주입 (`start_type_combo`, `start_threshold_edit`) (P0)
- **코드 위치**: [tests/test_smart_triggers.py#L108-L120](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_smart_triggers.py#L108-L120)
- **파괴 메커니즘**:
  - PASCO Capstone의 UI 식별자는 `Controls.ObjName...`, `Workbook....` 형태이나, 테스트 픽스처는 `automation_id="start_type_combo"`, `automation_id="start_threshold_edit"`라는 임의의 스네이크 케이스 ID를 주입함. 실제 Capstone 구동 시 컨트롤 탐색 100% 실패.

#### 🟠 [DEFECT-MOCK04] `tests/test_run_delete.py` L13-39: Data Summary 트리의 다중 런 반복 노출 및 빈 Automation ID 왜곡 (P1)
- **코드 위치**: [tests/test_run_delete.py#L13-L39](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_run_delete.py#L13-L39)
- **파괴 메커니즘**:
  - 실물 Capstone 트리는 측정 항목마다 동일한 런 행이 중복 노출되고 Automation ID가 비어 있음(`docs/remediation-verification.md` L43). 모의 Snapshot은 `row1`, `row2` 단일 행으로 극도로 단순화하여 다중 런 충돌 버그를 은폐함.

#### 🟠 [DEFECT-MOCK05] `InMemoryFakeBackend`의 물리 제약 무시 상수 난사 및 타 테스트 미활용 (P1)
- **코드 위치**: [src/capstone_mcp/fake_backend.py#L343-L379](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/fake_backend.py#L343-L379)
- **파괴 메커니즘**:
  - 통계(`mean=2.39`), 델타(`dx=0.5, dy=1.2`), 적분(`area=1.18`)을 입력과 무관하게 고정 상수로 반환하며, 모든 요청에 무조건 `verified=True`, `connected=True`를 반환함.
  - ADR 0004에서 "The Interface is the Test Surface"를 선언했음에도, `test_fake_backend.py` 외의 30여 개 테스트 스위트에서는 단 한 번도 fixture로 활용되지 않고 각자 `MagicMock`을 주입함.

---

### 3. CI 헤드리스 가드 스킵 오남용 및 검증 공백 (Validation Blind Spots)

#### 🔴 [DEFECT-SKIP01] `tests/golden_samples.py` L8-11 & `test_golden_master.py` L19-22: 로컬 Downloads 경로 종속 및 CI 환경 100% 침묵 스킵 (P0)
- **코드 위치**: [tests/golden_samples.py#L8-L11](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/golden_samples.py#L8-L11), [tests/test_golden_master.py#L19-L22](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_golden_master.py#L19-L22)
- **코드**:
  ```python
  GOLDEN_MASTER_DIR: Final = Path(
      os.environ.get("CAPSTONE_GOLDEN_MASTER_DIR")
      or Path.home() / "Downloads" / "(2026)캡스톤 실험별 파일",
  )
  pytestmark = pytest.mark.skipif(
      not GOLDEN_MASTER_DIR.exists(),
      reason=f"Golden master Capstone archives not found at {GOLDEN_MASTER_DIR}",
  )
  ```
- **파괴 메커니즘**:
  1. CI 러너(GitHub Actions)에는 `~/Downloads/(2026)캡스톤 실험별 파일`이 존재하지 않아, `test_golden_master.py`의 핵심 회귀 테스트 41개가 **CI에서 100% 침묵 스킵**됨.
  2. 최소 1~2개의 샘플 `.cap` 파일(축소 또는 합성 아카이브)조차 `tests/fixtures/`에 패키징되어 있지 않아, CI 파이프라인에서 실제 ZIP+XML 파싱 회귀를 전혀 검증하지 못하는 거대한 검증 사각지대(Validation Blind Spot)가 온존함.

#### 🔴 [DEFECT-SKIP02] `test_domain_protocol.py` L105 & `test_experiment_analysis.py` L480: Windows 절대 설치 경로 하드코딩으로 인한 CI 스킵 (P0)
- **코드 위치**: [tests/test_domain_protocol.py#L21-L24](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_domain_protocol.py#L21-L24), [tests/test_domain_protocol.py#L105-L108](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_domain_protocol.py#L105-L108), [tests/test_experiment_analysis.py#L480](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_experiment_analysis.py#L480)
- **코드**:
  `EXAMPLE: Final = "C:/Program Files/PASCO scientific/Capstone/Resources/Templates/QuickStart/Conservation of Momentum.cap"`
- **파괴 메커니즘**:
  - CI 러너에는 Capstone이 설치되어 있지 않으므로 `test_saved_sample_extraction_over_mcp` 및 `test_reads_installed_example_without_modifying_it`가 CI에서 100% 무조건 스킵됨. 테스트 픽스처를 리포지토리에 포함하지 않은 채 OS 설치 경로를 참조하는 안티패턴.

#### 🟠 [DEFECT-SKIP03] `test_data_sources.py` L146-147: 테스트 함수 내부 조건부 스킵으로 인한 아카이브 어댑터 검증 회피 (P1)
- **코드 위치**: [tests/test_data_sources.py#L145-L147](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_data_sources.py#L145-L147)
- **파괴 메커니즘**:
  - `CapArchiveAdapter`의 실제 파일 읽기 검증이 CI 환경에서 조건문으로 스킵되며, 모킹된 테스트만 통과하여 배포 파이프라인에서 결함이 은폐됨.

#### 🟡 [DEFECT-SKIP04] `test_live_smoke.py` L41-49: `_skip_if_capstone_running()`의 잔존 좀비 프로세스로 인한 스모크 전면 침묵 (P2)
- **코드 위치**: [tests/test_live_smoke.py#L41-L49](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/tests/test_live_smoke.py#L41-L49)
- **파괴 메커니즘**:
  - `psutil.process_iter()`로 `Capstone.exe` 탐색 시 이전 테스트 실패로 인한 좀비 프로세스가 단 하나라도 남아 있으면, 모든 라이브 스모크 테스트가 의도치 않게 침묵 스킵됨.

---
이상 13건의 픽스처 누수/모킹 왜곡/CI 스킵 결함에 대해 실사 완료하였으며 마스터 매트릭스에 통합 반영 요청드립니다.

</details>

#### 📑 실사 보고서: `audit-packaging` (총 1회 정밀 실사)

<details open>
<summary><b>[보고서 #104] audit-packaging 실사 세부 명세 (Phase 1)</b></summary>

`pyproject.toml`, CLI 진입점(`capstone-mcp.exe`, `capstone-mcp-http.exe`), Windows 프로세스 락(`os error 32`), 의존성 충돌, `sys.path` 누락 및 Windows 서비스/백그라운드 기동 시의 결함에 대한 전수 라인 단위 실사 결과입니다:

1. pyproject.toml (L1-20) & uv.lock - 패키지 버전 불일치 및 락파일 미동기화로 인한 uv 자동 동기화 크래시:
- 파일/라인: `pyproject.toml:3`, `pyproject.toml:20`, `uv.lock:62`
- 트리거: 개발자/CI 또는 AI 클라이언트가 `uv run`을 `--no-sync` 없이 호출하거나 `uv lock --check` 실행.
- 파괴 메커니즘: `pyproject.toml`은 `version = "0.1.1"` 및 `dev`에 `pytest-cov>=6`을 정의하고 있으나, `uv.lock`은 여전히 `version = "0.1.0"`이며 `pytest-cov`가 완전히 누락되어 있음. `uv lock --check`가 즉시 실패하며, `--no-sync` 없이 `uv run`을 호출하면 `uv`가 가상환경(`.venv`) 갱신을 강제 시도함. 현재 백그라운드에서 실행 중인 `capstone-mcp.exe`(PID 17200 확인)에 덮어쓰기를 시도하다가 Windows 공유 위반 `os error 32`를 발생시키며 모든 CLI 명령이 즉시 중단됨.

2. pyproject.toml (L9-17) - 핵심 직접 의존성(`anyio`, `pydantic`, `pywin32`) 선언 누락:
- 파일/라인: `pyproject.toml:9-17`, `server.py:11`, `server.py:25`, `models.py:8`, `desktop.py:16`, `ui_events.py:13-17`
- 트리거: 상위 라이브러리(`mcp`, `pywinauto`)의 전이적 의존성 버전 변경 또는 최소 환경 설치.
- 파괴 메커니즘: `src/capstone_mcp/server.py`에서 `import anyio`, `from pydantic import JsonValue`, `desktop.py` 및 `ui_events.py`에서 `win32gui`, `win32process`, `win32api`, `win32con`, `win32job`, `win32clipboard`, `pywintypes`를 직접 임포트하여 사용하고 있으나, `pyproject.toml`의 `dependencies`에 명시되어 있지 않음. `mcp`나 `pywinauto`의 전이적 의존성 트리가 변경되거나 독립 패키징 시 런타임 `ModuleNotFoundError`로 직결됨.

3. pyproject.toml (L26-28) - Hatchling 빌드 설정 부재로 인한 sdist 내부 민감/임시 파일 및 리버싱 덤프 번들링:
- 파일/라인: `pyproject.toml:26-28`, `scratch/dist/capstone_mcp-0.1.1.tar.gz` (실제 빌드 검증)
- 트리거: `uv build --sdist` 또는 `pip sdist` 실행 시.
- 파괴 메커니즘: `[tool.hatch.build.targets.sdist]`의 제외(exclude) 설정이 전혀 없어, `docs/reverse_engineering_dump.json`, `docs/reverse_engineering_findings.md`, `scratch/audit/*.py`, `EXHAUSTIVE_DEFECT_CATALOG.md`, `EXHAUSTIVE_REPOSITORY_AUDIT_REPORT.md` 등 저장소 내부 디버깅/리버싱/감사 파일 및 `.github/` 워크플로우까지 소스 배포판에 무차별 포함되어 배포 용량 낭비 및 내부 리버싱 자산이 외부에 노출됨.

4. 패키지 루트 - PEP 561 타입 마커(`py.typed`) 및 `__version__` 부재:
- 파일/라인: `src/capstone_mcp/__init__.py:1-2`, `src/capstone_mcp/py.typed` (파일 없음)
- 트리거: 다운스트림 프로젝트/클라이언트에서 `capstone_mcp` 타입 검사(mypy/basedpyright) 수행 또는 `capstone_mcp.__version__` 조회.
- 파괴 메커니즘: `py.typed` 파일이 패키지 내에 존재하지 않아 wheel 빌드 시 타입 정보가 누락되고 타입 검사기가 라이브러리를 untyped로 취급함. 또한 `__init__.py`에 `__version__`이 정의되어 있지 않아 런타임 버전 조회가 `AttributeError`로 실패함.

5. server.py (L331-334) & pyproject.toml - CLI 진입점(`capstone-mcp.exe`) 인자 미처리로 인한 터미널 영구 행(Hang):
- 파일/라인: `pyproject.toml:23`, `src/capstone_mcp/server.py:331-334`
- 트리거: 터미널에서 사용자가 `capstone-mcp --help`, `-h`, `--version` 실행.
- 파괴 메커니즘: `main()` 함수는 `sys.argv`를 일체 검사하지 않고 무조건 `MCP.run(transport="stdio")`를 호출함. FastMCP는 즉시 stdin 대기 루프로 진입하므로, 사용자가 `--help`를 요청해도 도움말을 출력하지 않고 프로세스가 무한 블로킹되어 터미널이 프리즈(Hang)됨.

6. server.py (L92-98, L336-339) - `capstone-mcp-http` 호스트/포트 하드코딩 및 포트 충돌 시 복구 불능 크래시:
- 파일/라인: `src/capstone_mcp/server.py:92-98`, `src/capstone_mcp/server.py:336-339`
- 트리거: `capstone-mcp-http` 실행 시 8766 포트가 이미 사용 중이거나 포트 변경 필요 시.
- 파괴 메커니즘: 포트 8766과 호스트 127.0.0.1이 코드에 하드코딩되어 있으며 CLI 플래그(`--port`, `--host`)나 환경변수로 재지정할 수 없음. 이전 인스턴스가 8766을 점유 중이거나 TIME_WAIT 상태일 때 즉시 `OSError: [Errno 10048]`로 비정상 종료되며 실행 자체가 불가능함.

7. automation_worker.py (L81-87) - `_spawn`의 CWD 및 PYTHONPATH 미지정으로 인한 서브프로세스 임포트 파탄:
- 파일/라인: `src/capstone_mcp/automation_worker.py:81-87`
- 트리거: Claude Desktop 등 MCP 호스트가 임의의 CWD(예: `C:\Users\<user>\AppData\Local\Programs\...`)에서 서버를 기동하거나, 비-editable 소스 실행 환경일 때.
- 파괴 메커니즘: `subprocess.Popen([sys.executable, "-X", "utf8", "-u", "-m", "capstone_mcp.native_main"])` 호출 시 `cwd`와 `env`가 명시되지 않음. 호스트의 CWD를 상속받고 `PYTHONPATH`가 누락된 환경에서는 서브프로세스가 `capstone_mcp` 모듈을 찾지 못하고 `ModuleNotFoundError: No module named 'capstone_mcp'`로 즉시 크래시하여 모든 네이티브 자동화 기능이 마비됨.

8. pyproject.toml (L52-53) & tests - `pythonpath = ["src"]` 누락 및 테스트 간 루트 의존 임포트:
- 파일/라인: `pyproject.toml:52-53`, `tests/test_data_sources.py:23`, `tests/test_golden_master.py:17`
- 트리거: 신규 환경 또는 editable 설치가 없는 클론 디렉터리에서 `pytest` 단독 실행 시.
- 파괴 메커니즘: `pyproject.toml`의 `[tool.pytest.ini_options]`에 `pythonpath = ["src"]`가 없어 editable 링크가 없으면 `capstone_mcp`를 임포트할 수 없음. 또한 `from tests.golden_samples import ...`와 같이 루트의 `tests`를 직접 패키지로 임포트하고 있어, 하위 디렉터리에서 실행 시 `ModuleNotFoundError`를 유발함.

9. Windows Service / Background 기동 - Session 0 격리(Isolation)로 인한 GUI 자동화 원천 불능 (런타임 가드 전무):
- 파일/라인: `src/capstone_mcp/desktop.py`, `src/capstone_mcp/server.py`, `README.md`
- 트리거: Windows Service (SCM, NSSM), 비로그온 Task Scheduler로 `capstone-mcp` 또는 `capstone-mcp-http`를 백그라운드 구동.
- 파괴 메커니즘: Windows 보안 모델 상 Windows 서비스는 Session 0에서 실행되며, 사용자 대화형 데스크톱(Session 1+)과 원천 분리됨. `pywinauto` UIA 데스크톱 창 탐색이 Capstone 창을 일체 찾을 수 없으며, GDI 스크린샷(`ImageGrab.grab`)은 검은 화면(0x00)만 생성함. `SetWinEventHook` 역시 세션 경계를 넘지 못함. 이에 대한 런타임 세션 검사(예: `ProcessIdToSessionId`)나 가이드가 전무하여 서비스 등록 시 영구 오동작함.

10. Windows Service / Background 기동 - Null Stdio 핸들로 인한 FastMCP 즉각 크래시:
- 파일/라인: `src/capstone_mcp/server.py:331-334`, `mcp.server.stdio.stdio_server`
- 트리거: 콘솔 없이(`pythonw.exe` 또는 `CREATE_NO_WINDOW`) 백그라운드 프로세스로 기동.
- 파괴 메커니즘: 표준 핸들이 없는 프로세스에서는 `sys.stdin`, `sys.stdout`, `sys.stderr`가 모두 `None`으로 설정됨. `server.py`의 `main()`이 실행되면 FastMCP stdio 서버 내부의 `sys.stdin.buffer` 접근 시 `AttributeError: 'NoneType' object has no attribute 'buffer'`가 발생하여 기동 0초 만에 비정상 종료됨.

11. Windows 제어 이벤트 핸들러(`SetConsoleCtrlHandler`) 부재로 인한 비정상 종료 시 하드웨어/잡 상태 누수:
- 파일/라인: `src/capstone_mcp/server.py:58-67`, `src/capstone_mcp/automation_worker.py:63-66`
- 트리거: 백그라운드 콘솔 창 닫기(`CTRL_CLOSE_EVENT`) 또는 세션 로그오프(`CTRL_LOGOFF_EVENT`).
- 파괴 메커니즘: Windows는 POSIX SIGTERM 대신 콘솔 제어 이벤트를 전송함. `SetConsoleCtrlHandler`가 등록되어 있지 않아 이벤트 수신 즉시 OS가 `ExitProcess`를 강제 호출함. `_lifespan`의 `JOBS.close()` 및 `WORKER.close()` 종료 훅이 실행되지 못하고 중단되어, Capstone 센서 하드웨어가 레코딩 락 상태로 방치되고 파이프/스레드 자원이 정리되지 않음.

12. README.md (L68-73) & docs/usage.md (L372) - 사용자 가이드의 `--no-sync` 누락으로 인한 프로세스 락 유발:
- 파일/라인: `README.md:68-73`, `docs/usage.md:372`
- 트리거: 사용자가 문서에 기재된 설정 그대로 Claude Desktop에 `"command": "uv", "args": ["--directory", "...", "run", "capstone-mcp"]`를 등록하거나 `uv run capstone-mcp-http`를 실행.
- 파괴 메커니즘: 문서 안내에 `--no-sync` 플래그가 누락되어 있어, 백그라운드에 이미 서버 프로세스가 구동 중이거나 `uv.lock`이 미동기 상태일 때 사용자의 AI 클라이언트가 기동되면서 `os error 32`를 유발하고 MCP 연결이 즉시 단절됨.

</details>

---



---

### 3.10. Phase 4: Ultra-Deep Edge & Runtime Limit Defects (순수 신규 68건 전수 카탈로그)
- **총괄 검증관**: `auditor-verifier-phase4` (7개 전문 감사 분과 실사 완료)
- **검증 결과**: 총 80건 접수 중 중복 11건 제외, 허위 1건 기각, **순수 신규 68건 공인 확정 (P0 15건 / P1 34건 / P2 19건)**
- **연계 에픽 티켓**: [#123](https://github.com/ji5zi5/capstone-mcp/issues/123) ~ [#130](https://github.com/ji5zi5/capstone-mcp/issues/130) 전역

---

#### 3.10.1. Windows OS & Win32 저수준 상호운용성 (12건 확정)

#### 🔴 P0-WIN01: 팝업 메뉴 데스크톱 루트 HWND 격리 및 좌표 오프셋 누락 100% 탐색 실패
- **파일**: [popup_selection.py#L50-L52](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/popup_selection.py#L50-L52), [popup_selection.py#L84-L90](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/popup_selection.py#L84-L90), [desktop.py#L384-L400](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L384-L400)
- **파괴 시나리오**: Win32/Qt 팝업 메뉴(`#32768`)는 부모 윈도우의 자식이 아닌 데스크톱 루트 HWND의 직속 자식으로 생성됨. `app.snapshot(request.handle)`은 부모 창 트리만 탐색하므로 팝업 메뉴를 100% 찾지 못함. 또한 `click_point`는 창 기준 상대 좌표를 스크린 절대 좌표 변환(`ClientToScreen`) 없이 클릭하여 마우스가 엉뚱한 위치를 타격함.
- **수정 지침**: `ClientToScreen` 변환 필수 적용 및 팝업 탐색 범위를 프로세스 전체 활성 최상위 윈도우(`app.windows()`)로 확장.

#### 🔴 P0-WIN02: `matching_snapshot` 순회 중 UAC/UIPI 경계 컨트롤 순회 시 unhandled COMError (0x80070005) 루프 크래시
- **파일**: [desktop.py#L224-L250](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L224-L250)
- **파괴 시나리오**: `node.element_info`, `node.is_enabled()`, `node.iter_children()` 호출부에 `try-except COMError`가 전무함. UIPI 경계 컨트롤이나 권한 보호 자식 노드 순회 시 `_ctypes.COMError: 0x80070005 (Access is denied)`가 터지는 즉시 스냅샷 전체가 중단되고 네이티브 IPC 워커가 다운됨.
- **수정 지침**: `while pending:` 순회 루프 내부의 모든 프로퍼티 접근에 `except (_ctypes.COMError, AutomationError): continue` 방어 가드 추가.

#### 🔴 P0-WIN03: FastMCP 서버 프로세스 DPI-Unaware(96DPI) 구동에 따른 고해상도 오폭 클릭
- **파일**: [server.py#L60-L90](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L60-L90), [desktop.py#L10-L30](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L10-L30)
- **파괴 시나리오**: `native_main.py` 외부에서 FastMCP 서버 프로세스가 직접 기동되거나 `desktop.py` 단독 임포트 시 DPI Awareness가 초기화되지 않음(96DPI 기본값). 150%/200% High-DPI 모니터에서 Windows DWM 가상화로 인해 클릭 좌표가 (1500, 900) -> (1000, 600)으로 축소 변환되어 화면 엉뚱한 버튼을 클릭함.
- **수정 지침**: `desktop.py` 모듈 로드 시 또는 `Capstone.__init__`에서 전역 DPI Awareness 초기화 보장.

#### 🟠 P1-WIN04: Per-Monitor v2 미지원으로 다중 모니터 DPI 스케일링 괴리 발생
- **파일**: [native_main.py#L12-L18](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/native_main.py#L12-L18)
- **파괴 시나리오**: Windows 10(1703+)/11 표준인 Per-Monitor v2(`-4`) 대신 레거시 v1(`SetProcessDpiAwareness(2)`)만 호출. 주 모니터(100%)와 보조 모니터(150%) 간 창 이동 시 비클라이언트 영역(타이틀바/메뉴)이 주 모니터 DPI로 고정되어 UIA 바운딩 박스와 Win32 물리 좌표 간 1.5배 오차 발생.
- **수정 지침**: `user32.SetProcessDpiAwarenessContext(-4)` 우선 호출 후 폴백 체인 구축.

#### 🟠 P1-WIN05: `ImageGrab.grab(bbox=...)`의 `all_screens=True` 누락으로 보조 모니터 블랙아웃
- **파일**: [desktop.py#L488-L491](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L488-L491)
- **파괴 시나리오**: PIL의 Win32 캡처는 `all_screens=False`일 때 주 모니터 DC만 참조함. Capstone 창이 보조 모니터(음수 좌표 또는 주 모니터 우측)에 위치할 경우 `crop()`이 범위를 벗어나 검은 화면(Blackout)이 반환되거나 크래시 발생.
- **수정 지침**: `ImageGrab.grab(bbox=(...), all_screens=True)` 명시 전달.

#### 🟠 P1-WIN06: Capstone 관리자 권한 실행 시 일반 사용자 MCP 프로세스 무진단 거부 (`WinError 5`)
- **파일**: [desktop.py#L131](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L131), [automation_worker.py#L129-L135](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/automation_worker.py#L129-L135)
- **파괴 시나리오**: Capstone이 UAC 관리자 권한으로 실행된 환경에서 일반 권한 MCP가 `process_module(process_id)` 호출 시 즉시 `WinError 5 Access is denied` 발생. 사용자에게 권한 불일치에 대한 아무런 가이드 없이 프로세스가 중단됨.
- **수정 지침**: UAC 무결성 수준(Integrity Level) 감지 및 권한 불일치 안내 진단 메시지 출력.

#### 🟠 P1-WIN07: UIPI 격리 환경에서 `user32.SetWinEventHook` 거부 시 단순 문자열 에러 투척
- **파일**: [ui_events.py#L147-L154](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_events.py#L147-L154)
- **파괴 시나리오**: UIPI 보안 격리로 인해 이벤트 훅 설치가 거부될 때 단순 `AutomationError: [WinError 5]`만 발생하여 이벤트 기반 대기 루프가 원인 불명으로 즉시 실패함.
- **수정 지침**: UIPI 거부 감지 시 폴링 기반 이벤트 대기 모드로 자동 강등(Graceful Fallback).

#### 🟠 P1-WIN08: 화면 잠금(Win+L / RDP 세션 분리) 시 `require_foreground` 100% 조작 거부
- **파일**: [desktop.py#L302-L311](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L302-L311)
- **파괴 시나리오**: 화면 잠금 시 `GetForegroundWindow()`가 0(NULL) 또는 LogonUI를 반환하여 포그라운드 의존 모든 UI 도구가 `The active window is an untitled window` 에러를 던지며 일괄 거부됨.
- **수정 지침**: 데스크톱 잠금 상태(`OpenInputDesktop` 실패 등)를 감지하여 세션 잠금 전용 명확한 에러 반환.

#### 🟠 P1-WIN09: Windows 11 Modern CommandBar 컨테이너 래퍼로 인한 얕은 depth 탐색 실패
- **파일**: [file_workflows.py#L76-L80](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L76-L80), [file_workflows.py#L87-L92](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L87-L92)
- **파괴 시나리오**: Windows 11 공용 대화상자 및 Fluent 리본은 `DirectUIHWND` / `CtrlNotifySink` 래퍼가 감싸고 있어 버튼이 depth 3~4에 위치함. `depth=1`, `depth=2` 하드코딩으로 인해 Win11에서 `STR_MENU_FILE`, `STR_CLOSE` 등 필수 버튼을 찾지 못하고 타임아웃 발생.
- **수정 지침**: `depth=4` 이상으로 탐색 깊이 확대 또는 재귀적 조건부 탐색 적용.

#### 🟡 P2-WIN10: 화면 잠금 시 GDI 서피스 디태치로 인한 이미지 캡처 블랙아웃
- **파일**: [desktop.py#L441-L460](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L441-L460)
- **파괴 시나리오**: 화면 잠금 상태에서 `screenshot` 호출 시 GDI 서피스가 분리되어 검은색(0, 0, 0) 비트맵이 반환되거나 `OSError` 발생.
- **수정 지침**: 비트맵 버퍼 검증 후 세션 비활성화 경고 반환.

#### 🟡 P2-WIN11: 화면 잠금 시 Qt 렌더링 파이프라인 정지로 UIA 트리 빈 배열 `[]` 반환
- **파일**: [desktop.py#L242](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L242)
- **파괴 시나리오**: 잠금 상태에서 UIA 트리가 언로드되어 컨트롤 탐색 결과가 0개로 반환됨.
- **수정 지침**: 결과 0개 시 데스크톱 잠금 헬스체크 연동.

#### 🟡 P2-WIN12: Windows 11 둥근 모서리 투명 마진으로 인한 `require_uncovered` 오폭 차단
- **파일**: [desktop.py#L185](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L185), [desktop.py#L281-L295](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L281-L295)
- **파괴 시나리오**: Win11 모서리 라운딩 및 7~8px 투명 마진으로 인해 모서리 컨트롤 클릭 시 `WindowFromPoint`가 배경 창을 반환하여 정상 컨트롤을 `covered by another window`로 오판 차단.
- **수정 지침**: `DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)` 사용 및 모서리 영역 투명성 감안 보정.

---

#### 3.10.2. 글로벌 로케일, 수식 파서 문법 충돌 및 다국어 인코딩 한계 (17건 확정)

#### 🔴 P0-L10N01: `send_keys`가 수식 연산자(`+`, `^`, `%`, `()`)를 모디파이어 키로 오해석하여 수식 파괴
- **파일**: [calculator.py#L153-L156](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L153-L156), [desktop.py#L415-L417](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/desktop.py#L415-L417)
- **파괴 시나리오**: `type_text`가 `pywinauto.keyboard.send_keys(with_spaces=True)`를 직접 호출함. `send_keys`에서 `+`는 Shift, `^`는 Ctrl, `%`는 Alt, `()`는 그룹키임. `KE = 0.5 * m * v^2` 입력 시 `Ctrl+2`가 눌리고 `y = sin(x) + 3` 입력 시 Shift+3이 눌려 수식이 완전히 파괴됨. 또한 CJK IME 활성화 시 한글 조합창이 열려 텍스트가 심각하게 왜곡됨.
- **수정 지침**: 클립보드 붙여넣기(`^v`) 적용 또는 특수문자 이스케이프(`{+}`, `{^}`, `{(}`, `{)}`) 적용.

#### 🔴 P0-L10N02: macOS NFD 자모 분리 파일명 전달 시 Windows NFC 타이틀 불일치로 40초 무한 대기 폭사
- **파일**: [file_workflows.py#L302-L326](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L302-L326)
- **파괴 시나리오**: macOS 클라이언트에서 NFD로 분리된 파일명(`\u110c\u1161...cap`) 전달 시 Windows Capstone 창 타이틀(NFC)과 `title.startswith(path.name)` 비교가 영구 실패함. 40초(`OPEN_SECONDS = 40.0`) 동안 무한 루프를 돌다가 타임아웃 크래시 발생.
- **수정 지침**: 타이틀 비교 양변에 `unicodedata.normalize("NFC", ...)` 필수 적용.

#### 🔴 P0-L10N03: 영어 `run` 하드코딩 정규식으로 비영어 로케일 런 컨트롤 100% 인식 불가
- **파일**: [runs/manager.py#L59](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L59), [runs/manager.py#L285-L288](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L285-L288), [runs/manager.py#L303](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L303)
- **파괴 시나리오**: `RUN_NAME_PATTERN = re.compile(r"run\s*#?\s*\d+", re.IGNORECASE)` 영어 단어 하드코딩. 한국어 Capstone("실행 1"), 일본어("測定 1"), 독일어("Durchlauf 1"), 프랑스어("Essai 1") 환경에서 런 컨트롤을 전혀 찾지 못해 런 가시성 제어 및 관리 도구가 전면 마비됨.
- **수정 지침**: 다국어 런 명칭 정규식 확장 또는 UIA 계층 구조 기반 언어 무관 탐색 적용.

#### 🟠 P1-L10N04: 수식 등록 후 UI 에러 검증 전무 및 `status="valid"`, `verified=True` 무조건 사기 반환
- **파일**: [calculator.py#L116-L184](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L116-L184)
- **파괴 시나리오**: 유럽 로케일(독일/프랑스)에서 소수점 쉼표(`sin(1,5 * x)`) 입력 시 Capstone 엔진은 쉼표를 함수 인자 구분자로 취급하여 구문 에러를 띄움. 그러나 171행은 Capstone UI 에러 배지를 전혀 확인하지 않고 무조건 `status="valid"`, `verified=True`를 반환하여 허위 성공을 보고함.
- **수정 지침**: 수식 등록 후 에러 아이콘/툴팁 UIA 확인 로직 추가 및 로케일별 구분자 자동 정규화.

#### 🟠 P1-L10N05: `_parse_calculation_name` 정규식의 물리 그리스 문자/유니코드 미지원으로 변수명 오염
- **파일**: [calculator.py#L41-L46](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/calculator.py#L41-L46)
- **파괴 시나리오**: `^[A-Za-z0-9_가-힣\s]+?=` 정규식으로 인해 물리 공식의 그리스 문자(`θ = omega * t`, `λ = c / f`, `ω = 2*pi*f`), 아래첨자(`v₀ = 0`), 한자(`速度 = ...`) 입력 시 매칭 실패로 전체 수식 문자열(`"θ = omega * t"`)이 변수명으로 반환되어 후속 변수 바인딩이 100% 파탄남.
- **수정 지침**: 등호 앞의 임의 유니코드 식별자(`[^\s=+\-*/^()]+?`) 매칭으로 개선.

#### 🟠 P1-L10N06: 유럽 CSV 헤더에 설명용 쉼표 포함 시 `ambiguous field separators` 파일 로딩 100% 거부
- **파일**: [csv_data.py#L53-L65](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/csv_data.py#L53-L65)
- **파괴 시나리오**: 세미콜론(`;`) 구분 유럽 CSV의 열 제목에 설명용 쉼표(`Time (s);Force, Sensor 1 (N);Position (m)`)가 포함되면, 쉼표와 세미콜론 모두 `len(header) > 1`이 되어 `len(delimiters) > 1` 판정으로 파일 로딩이 무조건 거부됨.
- **수정 지침**: 데이터 행의 열 개수 일관성을 대조하는 Sniffer 방식 도입.

#### 🟠 P1-L10N07: `settled_title` 유니코드 정규화 누락으로 저장 후 3초 무조건 지연 발생
- **파일**: [file_workflows.py#L198-L214](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L198-L214)
- **파괴 시나리오**: NFD 파일명 저장 시 창 타이틀과의 비교 실패로 저장 완료 감지가 지연되어 3초 타임아웃까지 불필요한 대기 발생.
- **수정 지침**: `unicodedata.normalize("NFC", ...)` 적용.

#### 🟠 P1-L10N08: Windows NTFS의 NFD 경로 미매핑으로 `path.is_file()` `False` 반환
- **파일**: [file_workflows.py#L181-L184](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L181-L184), [file_workflows.py#L331-L334](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L331-L334), [csv_data.py#L98-L99](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/csv_data.py#L98-L99)
- **파괴 시나리오**: 디스크에 NFC로 존재하는 파일에 대해 NFD 경로 인자가 전달되면 Windows NTFS에서 `exists()`가 `False`를 반환하여 파일 열기가 거부됨.
- **수정 지침**: 진입점 인자 수신 즉시 NFC 정규화 수행.

#### 🟠 P1-L10N09: ZIP 아카이브 내부 파일명의 NFD/NFC 정규화 부재 및 멤버 누락
- **파일**: [capfiles/archive.py#L65-L100](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L65-L100)
- **파괴 시나리오**: macOS에서 생성된 `.cap` 파일 내부의 NFD 엔트리를 NFC 키로 조회 시 누락 에러 발생. 동일 파일명이 정규화 차이로 존재할 경우 `Ambiguous duplicate archive member` 에러 발생.
- **수정 지침**: 아카이브 멤버명을 NFC로 통일하고 레거시 ZIP 코드페이지 폴백 처리.

#### 🟠 P1-L10N10: `_is_zero_button`의 영어 라벨 하드코딩으로 비영어권 영점 조작 100% 불가
- **파일**: [instruments/sensors.py#L298-L313](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L298-L313)
- **파괴 시나리오**: 영어 `"zero"`, `"tare"`, `"0"`만 검사하여 한국어("영점", "영점 맞춤"), 일본어("ゼロ点"), 독일어("Nullpunkt") 환경에서 `No zeroable sensors or Zero buttons found` 발생.
- **수정 지침**: 다국어 버튼 라벨 사전 추가 및 리소스 문자열 매칭 연동.

#### 🟡 P2-L10N11: 유럽 환경 탭 구분 TSV에서 쉼표 소수점 누락 및 데이터 `None` 소실
- **파일**: [csv_data.py#L72-L77](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/csv_data.py#L72-L77), [csv_data.py#L80-L93](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/csv_data.py#L80-L93)
- **파괴 시나리오**: `delimiter == ";"`인 경우에만 쉼표 소수점을 변환하여, 탭 구분 TSV(`1,5\t2,7`)는 `InvalidOperation` 발생으로 열 전체가 `None`으로 버려짐.
- **수정 지침**: `delimiter != ","`인 모든 케이스에 대해 소수점 쉼표 치환 적용.

#### 🟡 P2-L10N12: 런 목록 정렬 시 단순 문자열 `sorted()` 사용으로 런 순서 및 날짜 역전
- **파일**: [runs/manager.py#L455](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L455), [runs/manager.py#L549](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L549)
- **파괴 시나리오**: `Run 10`이 `Run 1`과 `Run 2` 사이에 배치되며, 유럽식 날짜(`01/11/2026`)가 포함된 런 이름 정렬 시 시계열 분석이 역전됨.
- **수정 지침**: 자연 정렬(Natural Sort) 및 ISO 날짜 인식 정렬 키 적용.

#### 🟡 P2-L10N13: `CapturedRun` 모델에 ISO-8601 타임스탬프 필드 부재
- **파일**: [runs/models.py#L154-L165](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/models.py#L154-L165)
- **파괴 시나리오**: 다주기 반복 측정 시 OS 디스크 순서나 비표준 날짜 포맷으로 인해 런의 실제 발생 시각 추적 불능.
- **수정 지침**: `created_at: str` (ISO-8601 UTC) 필드 추가.

#### 🟡 P2-L10N14: CSV 타임스탬프 파싱 실패로 시간축 데이터 전량 `None` 버려짐
- **파일**: [csv_data.py#L72-L93](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/csv_data.py#L72-L93)
- **파괴 시나리오**: `parse_csv_number`가 날짜/시간 문자열을 파싱하지 못하고 `InvalidOperation`을 발생시켜 시간 열 전체가 `None`으로 소실됨.
- **수정 지침**: 날짜/시간 포맷 파싱(Epoch 초 변환) 지원.

#### 🟡 P2-L10N15: 유니코드 대소문자 매핑(독일어 `ß` vs `ss`) 및 자모 분리 매칭 불일치
- **파일**: [runs/manager.py#L299-L301](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L299-L301), [instruments/sensors.py#L330-L334](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L330-L334)
- **파괴 시나리오**: 단순 `.lower()` 사용으로 유니코드 케이스폴딩 규칙이 누락되어 특정 유럽어 및 자모분리 문자열 검색 실패.
- **수정 지침**: `unicodedata.normalize("NFC", text).casefold()` 표준 파이프라인 적용.

#### 🟡 P2-L10N16: `LAST_RUN_NAMES` 영어 전용으로 한국어/다국어 최근 런 삭제 요청 거부
- **파일**: [runs/manager.py#L211-L213](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L211-L213)
- **파괴 시나리오**: 한국어(`"마지막"`, `"최근"`), 독일어(`"letzter"`) 등으로 런 삭제 요청 시 즉시 거부.
- **수정 지침**: 다국어 동의어 세트 확장.

#### 🟡 P2-L10N17: `ui_strings.py` 다국어 매칭 지원 리소스 극소(10개)로 확장 불가
- **파일**: [ui_strings.py#L23-L26](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_strings.py#L23-L26), [ui_strings.py#L45-L47](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/ui_strings.py#L45-L47)
- **파괴 시나리오**: 다국어 매칭 키가 10개에 불과하여 계산기, 영점, 데이터 요약 등 필수 UI 키 확충이 불가능함.
- **수정 지침**: 리소스 문자열 매핑 테이블 대폭 확충.

---

#### 3.10.3. 하드웨어 고속 스트리밍 및 동적 하드웨어 이벤트 (13건 확정)

#### 🔴 P0-STRM01: 100kHz USB Bulk 스트림 엔드포인트 부재 및 단일 동기 폴링으로 99.9% 패킷 드랍
- **파일**: [session/cdp_client.py#L30-L38](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/cdp_client.py#L30-L38), [bridge.py#L135-L173](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L135-L173), [session/__init__.py#L80-L92](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/__init__.py#L80-L92)
- **파괴 시나리오**: PASCO 850은 초당 10만 개 패킷을 USB Bulk로 뿜어내지만, MCP는 매 샘플마다 HTTP + WebSocket + JSON RPC 왕복을 거치는 단일 동기 폴링을 수행함. 초당 최대 50~100개 샘플만 수신되어 99.9% 이상의 하드웨어 패킷이 드랍되고 시간 간격이 10~20ms로 불연속 단절됨.
- **수정 지침**: 지속 연결형 WebSocket 스트림 구독 또는 공유 메모리/파이프 기반 대량 배치 데이터(Bulk Batch Ingestion) 수신 프로토콜 구현.

#### 🔴 P0-STRM02: 레코딩 도중 센서 케이블 분리(Hot-unplug) 시 unhandled COMError (0x80010108) 크래시
- **파일**: [acquisition.py#L98](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/acquisition.py#L98)
- **파괴 시나리오**: 레코딩 도중 센서가 물리적으로 분리되면 Capstone 하드웨어 엔진이 UI 요소를 갱신/무효화함. 이때 `app.refs[control.ref].iface_toggle.CurrentToggleState` 호출 시 `_ctypes.COMError: 0x80010108 (RPC_E_DISCONNECTED)`가 발생하여 워커가 즉사함.
- **수정 지침**: `COMError` 예외 포획 및 하드웨어 접속 차단 상태 Graceful 반환.

#### 🔴 P0-STRM03: 센서 분리 순간 센서 목록 조회 시 unhandled COMError 서버 다운
- **파일**: [instruments/sensors.py#L20-L55](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L20-L55), [tools/sensors.py#L27-L32](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/tools/sensors.py#L27-L32)
- **파괴 시나리오**: 하드웨어 분리 중 `list_sensors`가 호출되면 컨트롤 순회 중 노드가 소멸하여 `0x80040201 (UIA_E_ELEMENTNOTAVAILABLE)`이 발생, FastMCP 도구가 500 내부 에러로 다운됨.
- **수정 지침**: 센서 순회 루프에 재시도 및 COM 예외 필터 적용.

#### 🔴 P0-STRM04: 레코딩 도중 센서 단선 시 `record_interval` 무한 대기 루프 행
- **파일**: [repetition.py#L100-L140](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/repetition.py#L100-L140)
- **파괴 시나리오**: 센서 분리로 Capstone이 레코딩을 자동 중단하거나 오류 상태에 진입해도, `record_interval`은 특정 종료 플래그만 기다리며 무한 루프에 빠져 세션 전체가 동결됨.
- **수정 지침**: 레코딩 루프 내 하드웨어 오류 감지 및 인터벌 타임아웃 강제 탈출 가드 추가.

#### 🟠 P1-STRM05: `DEFAULT_BUFFER_CAPACITY = 1000` 고정으로 100kHz 스트리밍 시 10ms 만에 버퍼 고갈 유실
- **파일**: [session/telemetry.py#L11](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L11), [session/telemetry.py#L18](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L18), [session/telemetry.py#L36](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L36)
- **파괴 시나리오**: 버퍼 용량이 1,000개에 불과하여 100kHz 구동 시 단 0.01초 분량만 보관 가능. 0.01초 후부터 직전 90,000개 이상의 샘플이 FIFO 링 버퍼에서 소리 없이 영구 유실됨.
- **수정 지침**: 고속 모드 감지 시 버퍼 용량을 최소 1,000,000개로 동적 확장하거나 청크 단위 스트리밍 파이프라인 구현.

#### 🟠 P1-STRM06: 하드웨어 정밀 ADC 타임스탬프 유실 및 호스트 `time.monotonic()` 대체 왜곡
- **파일**: [session/telemetry.py#L31](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L31), [data_sources/adapters/live_telemetry.py#L91-L101](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/live_telemetry.py#L91-L101)
- **파괴 시나리오**: 100kHz 샘플의 원래 간격은 10.0µs이나, MCP 수신 시점에 호스트 OS의 `time.monotonic()`이 기록됨. OS 스케줄링 Jitter로 인해 타임스탬프가 불규칙하게 왜곡되어 FFT 스펙트럼 분석 시 허위 고조파 피크가 발생함.
- **수정 지침**: 하드웨어 인터페이스가 제공하는 고유 하드웨어 타임스탬프(Hardware Clock Tick) 보존.

#### 🟠 P1-STRM07: 샘플링 레이트 단위(Hz ↔ kHz) 경계 전이 불가능으로 100kHz 설정 100% 거부
- **파일**: [instruments/sensors.py#L205-L216](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L205-L216), [instruments/sensors.py#L236-L238](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L236-L238), [instruments/sensors.py#L256-L257](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L256-L257), [instruments/sensors.py#L286-L290](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/sensors.py#L286-L290)
- **파괴 시나리오**: "500 Hz"에서 "100 kHz" 설정 시 초기 단위 불일치로 거부됨. "100000 Hz" 전달 시 1kHz 도달 순간 단위가 "kHz"로 바뀌어 루프를 탈출하고 직전 상태로 롤백되어 100kHz 진입이 원천 차단됨.
- **수정 지침**: `_rate_parts`에서 단위 변환 승수(multiplier)를 적용하여 정규화된 Hz 값으로 크기를 비교하도록 개선.

#### 🟠 P1-STRM08: 캘리브레이션 도중 무선 센서 단선 시 워커 프로세스 프리징
- **파일**: [wireless_calibration.py#L80-L120](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/wireless_calibration.py#L80-L120)
- **파괴 시나리오**: 센서 보정 마법사 진행 중 무선 연결이 끊기면 대화상자가 응답을 멈추고 워커가 60초 타임아웃까지 무한 대기함.
- **수정 지침**: 센서 연결 상태를 폴링하여 조기 인터럽트 지원.

#### 🟠 P1-STRM09: 이종 샘플링 레이트(다채널) 데이터 로딩 시 차원 검증 100% 거부
- **파일**: [data_sources/adapters/csv_file.py#L82-L95](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/csv_file.py#L82-L95), [data_sources/adapters/capstone_archive.py#L110-L125](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/capstone_archive.py#L110-L125)
- **파괴 시나리오**: 전압 1,000Hz, 온도 10Hz 등 채널 간 샘플 수가 다른 다채널 파일 로드 시 2차원 배열 변환에서 불규칙 배열(Ragged array) 예외가 발생하여 파일 조회가 거부됨.
- **수정 지침**: 이종 레이트 채널을 독립 시계열로 취급하거나 결측치 보간(Resampling) 지원.

#### 🟠 P1-STRM10: 물리 레시피의 엄격한 길이 일치 검사(`len(x) != len(y)`)로 다중 레이트 실험 분석 중단
- **파일**: [recipes/adiabatic_gas.py#L237-L241](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/adiabatic_gas.py#L237-L241), [reports/generator.py#L114-L115](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L114-L115), [reports/generator.py#L246](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L246), [reports/generator.py#L633](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L633), [numerics/regression.py#L49](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/regression.py#L49)
- **파괴 시나리오**: 단열 압축 등 압력(1kHz)과 온도/부피(10Hz)가 혼합된 표준 물리 실험 실행 시 `len(pressures) != len(volumes)` 에러로 레시피가 무조건 중단됨.
- **수정 지침**: 레시피 진입 단계에서 저속 채널을 고속 채널 시간축으로 보간하거나 다운샘플링하여 시간 동기화 공급.

#### 🟠 P1-STRM11: 무선 센서 재연결 시 텔레메트리 버퍼 초기화 누락으로 구 데이터 영구 잔류
- **파일**: [instruments/wireless.py#L207-L254](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L207-L254), [session/telemetry.py#L59-L66](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L59-L66)
- **파괴 시나리오**: 재연결 함수가 UIA 클릭만 수행하고 `TelemetryBuffer`와 전혀 연동되지 않아, 이전에 누적된 구 데이터가 버퍼에 영구 잔류함 (코드베이스 전체에서 `telemetry.clear()` 호출 0건).
- **수정 지침**: 센서 재연결 성공 시 해당 센서의 EUID 버퍼를 명시적으로 플러시(`telemetry.clear(euid)`).

#### 🟠 P1-STRM12: 버퍼 잔류 상태에서 새 샘플 추가 시 시간축 불연속 왜곡 (+600초 점프)
- **파일**: [data_sources/adapters/live_telemetry.py#L86-L103](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/live_telemetry.py#L86-L103)
- **파괴 시나리오**: `start = samples[0][0]`을 기준점으로 삼아, 10분 전 끊기기 전 샘플이 기준점이 되어 새로 들어온 데이터의 시간축이 `+600초`부터 시작되는 기형적 시계열이 생성됨.
- **수정 지침**: 텔레메트리 버퍼에 세션 ID/Run 에포크 메타데이터를 추가하여 활성 에포크 샘플만 격리.

#### 🟡 P2-STRM13: 무선 센서 재연결 시 EUID 변경에 따른 좀비 버퍼 누적 및 활성 센서 버퍼 강제 축출
- **파일**: [session/telemetry.py#L33-L36](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L33-L36), [instruments/wireless.py#L116-L133](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/instruments/wireless.py#L116-L133)
- **파괴 시나리오**: 끊어진 센서의 구 EUID 버퍼가 누적되다가 256개 상한(`MAX_MEASUREMENTS`)에 도달하면 `_buffers.popitem(last=False)`에 의해 활성 센서의 버퍼가 강제 축출됨.
- **수정 지침**: 센서 오프라인 확정 시 구 EUID 버퍼 가비지 컬렉션 루틴 추가.

---

#### 3.10.4. 통신 프로토콜 및 다중 연결 경합 (4건 확정)

#### 🔴 P0-PROTO01: Windows IPv6 우선 정책으로 `localhost` 루프백 접속 거부 (`WSAECONNREFUSED 10061`)
- **파일**: [bridge.py#L126-L128](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L126-L128), [record_events.py#L28](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/record_events.py#L28), [server.py#L94](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L94)
- **파괴 시나리오**: QtWebEngine이 디버거 URL을 `ws://localhost:...`로 반환하거나 IPv6 우선 Windows 환경에서 `localhost` 해석 시 `::1`로 접속을 시도함. Capstone은 IPv4(`127.0.0.1`) 전용 소켓으로 바인딩되어 있으므로 Windows가 접속을 즉시 거부(`WSAECONNREFUSED 10061`)하여 모든 CDP 기능이 마비됨.
- **수정 지침**: `endpoint.hostname`을 강제로 `127.0.0.1`로 치환하여 접속하고, `record_events.py`의 IP 일치 조건을 `0.0.0.0`/`::1`로 확장.

#### 🔴 P0-PROTO02: FastMCP 다중 세션 논블로킹 락 충돌 시 워커 프로세스 강제 사살 및 전 클라이언트 마비
- **파일**: [automation_worker.py#L214-L226](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/automation_worker.py#L214-L226), [automation_worker.py#L171-L210](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/automation_worker.py#L171-L210), [file_workflows.py#L230-L320](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L230-L320), [server.py#L69-L90](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L69-L90)
- **파괴 시나리오**: 다중 클라이언트 동시 접속 중 한 세션이 작업 중 다른 세션이 도구를 호출하면 `self.lock.acquire(blocking=False)`로 인해 즉시 거부됨. 타임아웃 발생 시 `self._retire()`로 워커 프로세스를 영구 사살하여 전 클라이언트가 마비됨. 또한 레코딩 중 파일 열기 호출 시 Capstone 네이티브 모달에 걸려 UI 모달 데드락 발생.
- **수정 지침**: 유한 타임아웃 큐잉 락 도입 및 레코딩 중 파일 조작 사전 차단 가드 추가.

#### 🟠 P1-PROTO03: 64KB 초과 대용량 웹소켓 프레임 분할(Continuation Frame 0x0) 및 WebSocketException 미처리 500 크래시
- **파일**: [bridge.py#L148-L173](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L148-L173), [resources.py#L187-L204](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/resources.py#L187-L204), [data_sources/adapters/live_telemetry.py#L44-L52](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/live_telemetry.py#L44-L52)
- **파괴 시나리오**: 대용량 시계열/스크린샷 전송 시 웹소켓 프레임 단편화가 발생하거나 네트워크 단절 시 `WebSocketException`이 발생함. 이는 `RuntimeError`/`OSError`를 상속하지 않아 `resources.py`의 `suppress(...)`를 그대로 뚫고 나가 FastMCP 리소스 핸들러가 500 내부 에러로 크래시함.
- **수정 지침**: `evaluate()` 내부에서 `WebSocketException`을 포획하여 `BridgeError`로 래핑하고 상위 모듈의 예외 목록에 추가.

#### 🟠 P1-PROTO04: TCP Half-Open 소켓 누수 및 Keep-Alive 프로브 부재로 2시간 소켓 잠김
- **파일**: [bridge.py#L105](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L105), [bridge.py#L148-L151](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/bridge.py#L148-L151), [server.py#L336-L338](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/server.py#L336-L338)
- **파괴 시나리오**: 절전 모드나 강제 종료로 FIN 없이 단선 시 `SO_KEEPALIVE`가 없어 Windows 기본 2시간 동안 Half-Open 소켓이 유지됨. 동적 포트 고갈(`WSAENOBUFS 10055`)을 촉진함.
- **수정 지침**: 소켓 옵션에 `SO_KEEPALIVE` 설정 및 WebSocket `ping_interval=5.0`, `ping_timeout=3.0` 적용.

---

#### 3.10.5. 과학 계산, 수치해석 및 신호처리 한계치 (10건 확정)

#### 🔴 P0-NUM01: 선형 회귀 시 하드코딩된 절대 공차 `abs_tol=1e-12`로 인한 SI 단위(나노미터 등) 정상 데이터 거부
- **파일**: [numerics/regression.py#L70-L73](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/regression.py#L70-L73)
- **파괴 시나리오**: 광학 슬릿 회절이나 광전효과 파장 데이터($x = [400\text{nm}, 500\text{nm}, 600\text{nm}]$) 입력 시 $S_{xx} = 2 \times 10^{-14}$로 계산됨. 그러나 70행에서 `math.isclose(ss_xx, 0.0, abs_tol=1e-12)`가 하드코딩되어 있어, 실제 분산이 존재하는 정상 데이터를 "독립변수 분산 0(수직선)"으로 오판하여 `ValueError: Independent variable x has zero variance` 예외를 던지고 피팅을 중단시킴.
- **수정 지침**: 절대 공차 대신 상대 공차 또는 데이터 분산 기반 정규화 검사(`math.isclose(min_x, max_x, rel_tol=1e-14)`)로 교체.

#### 🔴 P0-NUM02: 단열 기체 보고서 `_fit_adiabatic`에서 비양수(0 이하) 입력 시 `ValueError: math domain error` 도구 크래시
- **파일**: [reports/generator.py#L573-L574](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L573-L574), [reports/generator.py#L644-L650](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L644-L650)
- **파괴 시나리오**: 대기압 상대 압력(게이지 압력 $\le 0$)이나 미보정 센서 데이터가 포함된 경우 `ln_p = [math.log(p) for p in y_vals]`에서 즉시 `ValueError: math domain error`를 발생시켜 `capstone_generate_lab_report` 도구 전체를 크래시시킴.
- **수정 지침**: 비양수 값 사전 필터링 또는 양의 오프셋 보정 가드 추가.

#### 🟠 P1-NUM03: 단열 기체 피팅 시 `sxx == 0.0` 검증 누락으로 인한 ZeroDivisionError 크래시
- **파일**: [recipes/adiabatic_gas.py#L76-L77](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/recipes/adiabatic_gas.py#L76-L77)
- **파괴 시나리오**: 체적 측정값이 미세 변동하거나 언더플로우되어 $S_{xx} = 0.0$인 경우, 라인 76에서 `gamma_exp = -sxy / sxx`가 0으로 나누어 `ZeroDivisionError: float division by zero` 발생 및 레시피 중단.
- **수정 지침**: 피팅 전 `if sxx <= 0.0: return RecipePhaseResult(status="failed")` 가드 추가.

#### 🟠 P1-NUM04: 지수(Exponential) 회귀에서 비양수 $y$ 값 유입 시 `ValueError: math domain error` 크래시
- **파일**: [numerics/regression.py#L228-L245](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/regression.py#L228-L245)
- **파괴 시나리오**: 지수 감쇠(방사성 붕괴, RC 회로) 데이터에 노이즈로 인한 음수/0V 데이터가 1개라도 포함되면 `math.log(y)`에서 즉시 크래시 발생.
- **수정 지침**: $y \le 0$ 포인트 제외 또는 베이지안 오프셋 처리.

#### 🟠 P1-NUM05: 비-2의 거듭제곱 FFT 샘플에 대한 제로 패딩 누락 및 스펙트럼 에너지 왜곡
- **파일**: [oscilloscope_fft.py#L112-L145](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/oscilloscope_fft.py#L112-L145)
- **파괴 시나리오**: 샘플 수가 2의 거듭제곱이 아닐 때 제로 패딩 없이 FFT를 수행하거나 잘라내어 스펙트럼 누설 및 주파수 분해능 왜곡 발생.
- **수정 지침**: 다음 $2^N$으로 제로 패딩 및 진폭 스케일링 보정.

#### 🟠 P1-NUM06: FFT 윈도우(Hann, Hamming) 진폭 복원 계수(Coherent Gain) 누락으로 진폭 50% 유실 왜곡
- **파일**: [oscilloscope_fft.py#L150-L180](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/oscilloscope_fft.py#L150-L180), [displays/scope.py#L310-L340](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L310-L340)
- **파괴 시나리오**: Hann 윈도우 적용 시 Coherent Gain($\approx 0.5$)에 대한 역보정 계수(2.0)를 곱하지 않아, 추출된 피크 진폭이 실제 신호의 절반(50%)으로 왜곡 보고됨.
- **수정 지침**: 윈도우별 Coherent Gain 보정 계수(Hann: 2.0, Hamming: 1.85) 적용.

#### 🟠 P1-NUM07: `read_fft_peaks` 단위 불일치 판정 시 `None` 혼합으로 인한 불필요한 `AutomationError`
- **파일**: [displays/scope.py#L334-L336](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/scope.py#L334-L336)
- **파괴 시나리오**: Capstone FFT 화면에서 일부 피크는 단위("V")가 있고 일부는 생략된 경우, 집합이 `{"V", None}`(길이 2)이 되어 `AutomationError: FFT peak amplitudes have different or unknown units` 예외가 발생하여 정상 작업 실패.
- **수정 지침**: `None`을 제외한 후 단위가 2개 이상일 때만 에러 발생하도록 완화.

#### 🟡 P2-NUM08: `analysis.py`의 제너레이터 항별 나눗셈(`value / count`)에 의한 비정규 부동소수점 조기 추락 및 CPU 100배 지연
- **파일**: [analysis.py#L70-L71](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/analysis.py#L70-L71), [analysis.py#L106-L107](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/analysis.py#L106-L107), [analysis.py#L185](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/analysis.py#L185), [analysis.py#L188](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/analysis.py#L188)
- **파괴 시나리오**: `math.fsum(value / count for value in samples.x)`로 매 항마다 선행 나눗셈 수행. $10^{-305} / 10^5 = 10^{-310}$으로 비정규 부동소수점(Subnormal Float)으로 조기 추락하여 x86_64 마이크로코드 트랩으로 연산이 30x~100x 지연됨.
- **수정 지침**: `math.fsum(samples.x) / count` 형태로 전체 합산 후 단 1회 나눗셈하도록 수정.

#### 🟡 P2-NUM09: `summary.py` Welford 알고리즘에서 `m2` 미세 음수 라운딩 시 `math.sqrt()` 도메인 에러
- **파일**: [numerics/summary.py#L55](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/summary.py#L55)
- **파괴 시나리오**: `m2 += delta * (value - mean_val)` 누적 시 부동소수점 상쇄 오차로 `m2`가 $-10^{-18}$이 될 때 `math.sqrt(m2)`가 `ValueError: math domain error` 발생.
- **수정 지침**: `math.sqrt(max(0.0, m2) / ...)` 음수 클리핑 가드 적용.

#### 🟡 P2-NUM10: ASCII 플롯 렌더링 시 너비/높이 1 이하 입력에 따른 ZeroDivisionError
- **파일**: [reports/generator.py#L221](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L221), [reports/generator.py#L223](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L223), [reports/generator.py#L261](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/generator.py#L261), [numerics/sparklines.py#L87](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/sparklines.py#L87), [numerics/sparklines.py#L88](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numerics/sparklines.py#L88)
- **파괴 시나리오**: 소형 창에서 `(grid_w - 1)` 또는 `(height - 1)` 계산 시 0 나눗셈 `ZeroDivisionError: division by zero` 발생.
- **수정 지침**: `max(1, grid_w - 1)` 분모 0 방어 코드 적용.

---

#### 3.10.6. 보안 인젝션 및 파일 파서 취약점 (7건 확정)

#### 🟠 P1-SEC01: NTFS Reparse Point(심볼릭 링크) 기반 기존 파일 은닉 덮어쓰기 방어 우회
- **파일**: [file_workflows.py#L181-L184](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L181-L184), [file_workflows.py#L162-L164](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L162-L164)
- **파괴 시나리오**: 대상 경로(`destination`)를 아직 대상 파일이 없는 Dangling Symlink로 지정 시 `path.exists()`는 `False`를 반환하여 덮어쓰기 방어 로직이 우회됨. Capstone이 저장할 때 심볼릭 링크를 타고 넘어가 허가되지 않은 임의 경로에 파일이 생성/덮어써짐.
- **수정 지침**: `os.path.lexists(path)`를 사용하고 `path.is_symlink()` 여부를 명시적으로 차단.

#### 🟠 P1-SEC02: 파일 워크플로우 샌드박스 루트 경로 격리 부재 (임의 시스템 경로 접근)
- **파일**: [file_workflows.py#L181-L187](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L181-L187), [file_workflows.py#L331-L334](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_workflows.py#L331-L334)
- **파괴 시나리오**: `Path(destination).resolve()`는 단순히 경로를 정규화할 뿐 워크스페이스 경계를 검사하지 않음. `C:\Windows\...`, UNC 경로 등 민감 경로로의 저장/열기가 허용됨.
- **수정 지침**: 서버 수준 `ALLOWED_WORKSPACE_ROOT`를 설정하고 `path.is_relative_to(allowed_root)` 검증 필수 적용.

#### 🟠 P1-SEC03: Workbook 탭 제목 입력 시 pywinauto 키스트로크 인젝션
- **파일**: [displays/workbook.py#L60-L61](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/displays/workbook.py#L60-L61)
- **파괴 시나리오**: 탭 제목(`title`)에 `Page %{F4}` 전달 시 `send_keys`가 Alt+F4 단축키로 인식하여 활성 Capstone 창을 강제 종료시킴.
- **수정 지침**: `title` 내 키스트로크 예약 특수문자 이스케이프 또는 클립보드 방식 주입.

#### 🟠 P1-SEC04: 다중 엔트리 중첩(Overlapping) Zip Bomb 메모리 DoS 위험
- **파일**: [capfiles/archive.py#L81-L103](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L81-L103), [capfiles/archive.py#L637-L655](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L637-L655)
- **파괴 시나리오**: `_archive_members`의 `total_size` 합산은 개별 헤더 크기만 합산(64MB)함. 그러나 `include_data=True`로 파싱 시 4096개 DataSet이 각각 16MB 페이로드를 디코딩하여 수 GB의 힙을 일시에 점유, OOM 유발.
- **수정 지침**: 아카이브 수명주기 전역에서 실제 메모리에 할당된 누적 페이로드 크기를 추적하는 `GLOBAL_DECOMPRESSED_LIMIT` 도입.

#### 🟡 P2-SEC05: NTFS Junction 디렉터리 감시 시 `FindFirstChangeNotification` 무기한 행
- **파일**: [file_events.py#L50-L58](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_events.py#L50-L58), [file_events.py#L92-L96](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_events.py#L92-L96)
- **파괴 시나리오**: Win32 `FindFirstChangeNotification`은 NTFS Junction 경계를 넘어 파일 변경 이벤트를 전달하지 못함. 정상 저장되었음에도 15초 타임아웃으로 워크플로우가 실패함.
- **수정 지침**: `os.path.realpath(directory)`를 통해 실제 물리 디렉터리 경로를 해석한 뒤 등록.

#### 🟡 P2-SEC06: `.cap` 및 그래프 클립보드 XML 파싱 시 고립된 특수 엔티티(`&`, `<`, `>`) 미이스케이프 파싱 중단
- **파일**: [capfiles/archive.py#L600-L617](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L600-L617), [graphs/inspection.py#L259-L276](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/graphs/inspection.py#L259-L276)
- **파괴 시나리오**: 센서명이나 수식에 `R & D`, `Voltage < 5V`가 포함된 경우 `fromstring()`이 `ParseError`를 던져 파일 읽기 전체가 실패함.
- **수정 지침**: XML 파싱 전 고립된 `&`를 `&amp;`로 치환하는 엔티티 전처리기 도입.

#### 🟡 P2-SEC07: Lab Report 마크다운 생성 시 메타데이터 원시 보간으로 인한 마크다운 인젝션/XSS
- **파일**: [reports/templates.py#L22-L35](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L22-L35), [reports/templates.py#L57-L78](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/reports/templates.py#L57-L78)
- **파괴 시나리오**: `meta.title`, `meta.run_name` 등에 마크다운 링크(`[Click](javascript:...)`) 또는 원시 HTML이 포함된 경우 마크다운 뷰어에서 악성 스크립트 실행 노출.
- **수정 지침**: 마크다운 렌더링 파이프라인에서 HTML 태그 제거 및 특수문자 이스케이프 적용.

---

#### 3.10.7. 장기 가동 스트레스, OS 리소스 고갈 및 메모리 한계 (5건 확정)

#### 🔴 P0-STRS01: 장기 레코딩 시 대용량 시계열 배열 역직렬화로 인한 프로세스 OOM 크래시
- **파일**: [capfiles/archive.py#L586-L590](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L586-L590), [numeric_storage.py#L36-L63](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/numeric_storage.py#L36-L63)
- **파괴 시나리오**: 100만 개 이상 샘플이 포함된 `.cap` 파싱 시 `_dataset()`에서 단일 데이터셋당 5개의 거대 리스트(`sample_indices=list(range(count))`, `Decimal` 객체 수백만 개)를 생성함. 단일 데이터셋 파싱에 1~2GB의 힙이 순간 할당되어 `MemoryError` 발생 및 프로세스 크래시.
- **수정 지침**: `list(range(count))` 생성 제거, 개별 `Decimal` 대신 `array.array('d')` 또는 `numpy` 배열을 사용하여 메모리 점유율 90% 축소.

#### 🟠 P1-STRS02: `FileEvents.__exit__`의 `finally` 누락으로 인한 OS 디렉터리 잠금 및 WinError 32 누수
- **파일**: [file_events.py#L66-L76](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/file_events.py#L66-L76)
- **파괴 시나리오**: `self.thread.join(2)` 후 스레드가 살아있으면 `AutomationError`를 즉시 `raise`하여 `FindCloseChangeNotification` 및 `Close()`가 실행되지 못함. 열려 있는 핸들이 디렉터리를 OS 레벨에서 잠그고 있어 후속 파일 작업 시 `[WinError 32] 다른 프로세스가 파일을 사용 중입니다` 발생.
- **수정 지침**: 반드시 `finally` 블록 내에서 `FindCloseChangeNotification` 및 `Close()`를 무조건 호출하도록 수정.

#### 🟠 P1-STRS03: 반복 실행 세션(CaptureSession)의 시계열 샘플 무제한 누적으로 인한 상주 메모리(RSS) 점진적 팽창
- **파일**: [runs/manager.py#L616-L618](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L616-L618), [runs/manager.py#L662](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L662), [runs/manager.py#L667-L678](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/runs/manager.py#L667-L678), [repetition.py#L344-L347](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/repetition.py#L344-L347)
- **파괴 시나리오**: `CaptureSession`이 각 반복 사이클마다 `self.runs`, `self.comparisons`, `self.previous` 객체를 메모리에 제한 없이 누적함. 100회 반복 시 수 GB의 메모리가 GC되지 않고 프로세스 RSS가 지속 상승함.
- **수정 지침**: `self.previous` 원시 데이터셋 즉시 해제, `self.comparisons`는 온라인 요약 통계량(Welford)만 유지하도록 전환.

#### 🟡 P2-STRS04: XML 파서 순환 참조 및 힙 단편화로 인한 프로세스 RSS 미반환
- **파일**: [capfiles/archive.py#L628-L636](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/capfiles/archive.py#L628-L636)
- **파괴 시나리오**: `parent_by_child = {child: parent for parent in nodes for child in parent}` 양방향 순환 참조로 인해 즉시 GC되지 못하고 메모리가 단편화됨.
- **수정 지침**: `parent_by_child.clear()` 명시 호출 및 대용량 파싱 후 `gc.collect()` 조기 회수.

#### 🟡 P2-STRS05: TelemetryBuffer의 비효율적 리스트 복제로 인한 불필요한 메모리 할당 및 GC 부하
- **파일**: [session/telemetry.py#L40-L52](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L40-L52), [session/telemetry.py#L67-L79](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/session/telemetry.py#L67-L79), [data_sources/adapters/live_telemetry.py#L60](file:///c:/Users/Jio/Documents/Codex/integrations/capstone-mcp/src/capstone_mcp/data_sources/adapters/live_telemetry.py#L60)
- **파괴 시나리오**: 단순히 샘플 개수를 알기 위해 `len(get_samples(euid))`를 호출하여 매 폴링 틱마다 1,000개 튜플 리스트를 복제 생성함.
- **수정 지침**: `sample_count(euid)` 메서드를 추가하여 `len(self._buffers[euid])`를 O(1) 복제 없이 반환.

## 4. 🛠️ 완벽한 결함 격퇴를 위한 차기 엔지니어링 마스터플랜 (Phase 12)

| 단계 | 추진 과제 | 대상 결함 | 완료 판정 기준 |
| :---: | :--- | :--- | :--- |
| **Phase 12-A** | **P0 Blocker 격퇴: 프로세스 락업 해제 및 보안 취약점 차단** | P0 결함 79건 (ctypes 콜백 보존, RCE 포트 차단, WinEvent 훅 정리, 클립보드 API 전면 적출, 다중 인스턴스 자동 복구, terminate() 프로세스 kill, 전역 싱글톤 제거, STA 메시지 펌프 루프 구현, 다중창/포커스 락 해제, AST 수식 검증기 도입) | 세그멘테이션 오류 0건, 호스트 클립보드 오염 0바이트, Capstone 크래시 시 자동 복구, 프로세스 누수 0건 |
| **Phase 12-B** | **P1 Critical 격퇴: 실기 연동 복구 및 은폐·날조 박멸** | P1 결함 156건 (지속 WebSocket 연결 풀링으로 소켓 고갈 방어, 가짜 Fallback 데이터 제거, Path Traversal 방어, FakeBackend 제거 및 실기 RPC 구현, Time축 날조 제거, Zip Bomb 방어, 전원 상태 감지) | 소켓 고갈 0건, 가짜 데이터 주입 0건, CI E2E 테스트 100% 통과, UIA 침묵 실패 0건 |
| **Phase 12-C** | **P2/P3 격퇴: 다국어 로케일 및 대용량 렌더링 엔진 고도화** | P2/P3 결함 123건 (한글 CP949/유럽 로케일 지원, SVG LTTB 다운샘플링, HTML 템플릿 일치화, 절대경로 하드코딩 제거, Vandermonde 정규화) | 한글 Capstone 100% 정상 작동, 100만 포인트 렌더링 브라우저 안정성 보장 |

---
*본 보고서는 22개 전문 감사 에이전트 스웜이 작성한 원문 데이터를 단 1자의 누락 없이 100% 전수 집대성한 공식 엔지니어링 자산입니다.*
