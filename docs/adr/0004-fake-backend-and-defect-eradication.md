# ADR 0004: 15대 코어 부채 전수 박멸, 무부작용 인터페이스 확립 및 InMemoryFakeBackend 도입

- **상태 (Status)**: 승인됨 (Accepted)
- **일자 (Date)**: 2026-11-15
- **결정권자 (Deciders)**: 사용자, 에이전트

## 맥락 (Context)
1. Phase 10 완료 후 전수 코드베이스 정밀 감사(4대 스웜 워커 감사 및 백서 발간)를 통해 코드베이스 밑바닥에 은폐되어 있던 15대 치명적 결함(OS 전역 클립보드 오염, FastMCP 비공개 멤버 몽키패칭, pyproject.toml 타입체커 은폐, 9222 vs 9223 포트 충돌, 보고서 실패 시 가짜 합성 데이터 조작 주입, 존재하지 않는 `app.click()` 호출 등)이 명확히 규명됨.
2. 실물 Capstone 없이도 CI 및 오프라인 환경에서 53개 RPC 프로토콜과 텔레메트리, 도메인 비즈니스 로직을 완벽하게 검증할 수 있는 `InMemoryFakeBackend`가 부재하여, 테스트 스위트가 UIA 모의 객체 또는 `skipif` 회피에 과도하게 의존하고 있었음.
3. OS 전역 클립보드를 오버라이트하거나 프레임워크 비공개 멤버를 변조하는 등 예측 불가능한 파괴적 부작용(Side Effects)을 가진 코드가 잔존하여 런타임 안정성을 해치고 있었음.

## 결정 (Decision)
1. **1급 런타임 위해 요소 및 부작용의 영구 퇴출 (Side-Effect Free)**:
   - `graphs/inspection.py`의 Windows OS 전역 클립보드 탈취(`pywinauto.clipboard`) 로직을 전면 퇴출하고 CDP `Runtime.evaluate` 및 내부 상태 쿼리로 전환함.
   - `server.py`의 FastMCP 비공개 멤버 몽키패칭(`MCP._mcp_server.request_handlers`)을 제거하고 공식 인터셉터/데코레이터 패턴으로 정규화함.
   - `reports/generator.py`의 실패 시 가짜 데이터 주입(`_canonical_fallback_series`) 기만 코드를 영구 삭제하고, 파일 로드 실패 시 명확한 에러를 발생시킴.
   - 하드코딩된 실행 파일 절대 경로를 레지스트리 및 환경변수(`CAPSTONE_EXECUTABLE`) 동적 탐색기로 전환함.
2. **`InMemoryFakeBackend` 및 `ICapstoneBackend` 프로토콜 도입**:
   - 53개 네이티브 RPC 프로토콜 및 하드웨어 인벤토리, 가상 텔레메트리 틱을 완벽하게 시뮬레이션하는 `InMemoryFakeBackend`를 구축하여 CI 환경에서 실물 Capstone 없이도 도메인 로직을 100% 결정론적으로 검증함.
   - `DesktopBackend`와 `FakeBackend`가 동일한 추상 백엔드 프로토콜을 구현하도록 하여 테스트 표면과 런타임 표면을 완전히 일치시킴 (*The Interface is the Test Surface*).
3. **엄격한 정적 타입 검증 복원**:
   - `pyproject.toml`에서 무력화되어 있던 `reportAttributeAccessIssue`와 `reportCallIssue`를 즉시 `error`로 복원하고, 타입 에러를 눈가림 없이 전수 해결함.
