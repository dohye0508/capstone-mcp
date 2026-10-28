# PASCO Capstone MCP

**AI로 Capstone을 조작하고, 실험 데이터를 읽고 분석하세요.**

PASCO Capstone을 MCP 클라이언트에 연결하는 Windows용 로컬 서버입니다. 화면 조작부터 `.cap` 파일의 수치 추출, 그래프와 선형 피팅까지 26개 도구를 제공합니다.

## 주요 기능

| 기능 | 설명 |
| :--- | :--- |
| 화면 조작 | 창·컨트롤 조회, 클릭, 문자 입력, 드래그, 스크롤, 스크린샷 |
| 실험 구성 조회 | 센서 설정, 샘플링 속도, 기록 조건, 페이지 구성, 계산식 |
| 데이터 추출 | 저장된 `.cap` 파일에서 실제 수치와 데이터셋 정보 읽기 |
| 분석·시각화 | 산점도, 최소제곱 선형 피팅, 측정 결과 간 통계 비교 |
| 측정 제어 | 시작·정지, 샘플링 속도 조절, 시간·횟수를 지정한 반복 측정 |

> 파일 분석과 실제 화면 조작은 검증했습니다. **실물 센서를 연결한 측정·반복 측정은 아직 미검증입니다.**

## 설치

Windows, Python 3.12 이상, [uv](https://docs.astral.sh/uv/), PASCO Capstone이 필요합니다.

```powershell
git clone https://github.com/ji5zi5/capstone-mcp.git
cd capstone-mcp
uv sync --python 3.12
```

현재 Capstone 연결 경로는 `C:/Program Files/PASCO scientific/Capstone/Capstone.exe`입니다.

### MCP 클라이언트 연결

클라이언트 설정에 아래 항목을 추가하세요. `--directory` 뒤에는 프로젝트의 실제 경로를 넣습니다.

```json
{
  "mcpServers": {
    "capstone": {
      "command": "uv",
      "args": [
        "--directory", "C:/Projects/capstone-mcp",
        "run", "capstone-mcp"
      ]
    }
  }
}
```

기본 연결은 stdio입니다. HTTP를 사용하려면 `uv run capstone-mcp-http`로 실행하고 `http://127.0.0.1:8766/mcp`에 연결하세요.

## 사용법

연결한 AI에게 다음처럼 요청할 수 있습니다.

- “실행 중인 Capstone의 실험 설정을 확인해 줘.”
- “이 `.cap` 파일의 데이터셋을 보여 주고, 선택한 데이터로 산점도를 그려 줘.”
- “두 측정 결과의 평균과 표준편차를 비교해 줘.”

화면 조작은 **연결 → 창 조회 → 컨트롤 조회 → 조작 → 결과 확인** 순서로 진행합니다. 실제 마우스·키보드 입력에는 `allow_foreground=true`가 필요하며, 사용자의 데스크톱과 포커스를 공유합니다.

파일 분석은 Capstone에서 파일을 열거나 원본을 수정하지 않습니다. 생성한 그래프와 피팅 결과는 별도로 반환하며, Capstone 페이지를 변경하지 않습니다.

<details>
<summary><strong>도구 목록</strong></summary>

### 화면 조작

| 도구 | 용도 |
| :--- | :--- |
| `capstone_attach`, `capstone_windows` | 프로그램 연결·실행, 창과 대화상자 조회 |
| `capstone_snapshot` | 컨트롤 이름·상태·위치와 참조값 조회 |
| `capstone_action` | 클릭, 토글, 선택, 펼치기·접기, 포커스 이동 |
| `capstone_read_value`, `capstone_set_value` | 입력값 읽기·설정 |
| `capstone_screenshot` | 지정한 창을 PNG로 캡처 |
| `capstone_click`, `capstone_drag`, `capstone_scroll` | 창 기준 좌표로 마우스 조작 |
| `capstone_keys`, `capstone_type_text` | 단축키 입력, 한글·특수문자 그대로 입력 |

`capstone_attach(launch=true)`로 앱을 실행할 수 있습니다. 여러 인스턴스가 있으면 `process_id`를 지정하세요. 앱이 시작되는 중에는 창 목록이 비어 있을 수 있습니다.

`capstone_snapshot(handle)`의 `ref`는 새 조회나 조작 후 만료됩니다. `truncated=true`는 일부 컨트롤이 조회 제한 때문에 빠졌다는 뜻입니다. 좌표는 최신 스냅샷을 기준으로 계산하세요.

### 데이터와 분석

| 도구 | 용도 |
| :--- | :--- |
| `capstone_inspect_file` | 저장된 실험 구성 읽기 |
| `capstone_file_datasets` | 데이터셋 목록·ID·단위 ID·샘플 수 조회 |
| `capstone_extract_dataset` | 선택한 데이터셋의 지정 구간 추출 |
| `capstone_live_configuration` | 실행 중인 앱의 센서·측정 항목 조회 |
| `capstone_current_value` | 측정 항목의 현재 값 하나 읽기 |
| `capstone_linear_fit` | 기울기·절편·표준오차·잔차 오차·R² 계산 |
| `capstone_compare_runs` | 평균·표본 표준편차·범위·평균 차이 비교 |
| `capstone_plot` | 산점도와 선택적인 선형 피팅 선 생성 |

### 측정 제어

| 도구 | 용도 |
| :--- | :--- |
| `capstone_recording_status` | 기록 상태, 버튼 활성 여부, 표시 시간·속도 조회 |
| `capstone_set_recording` | 시작·정지 요청과 관찰한 상태 반환 |
| `capstone_step_sampling_rate` | 선택한 센서의 샘플링 속도를 한 단계 조절 |
| `capstone_repeat_acquisition` | 반복 측정 작업 시작 |
| `capstone_acquisition_job` | 작업 상태와 측정 회차 기록 조회 |
| `capstone_cancel_acquisition` | 반복 측정 취소·정지 요청 |

</details>

<details>
<summary><strong>실시간 연결과 반복 측정 설정</strong></summary>

파일 분석에는 추가 설정이 필요 없습니다. 실시간 조회와 반복 측정은 Qt 디버깅 연결을 사용합니다. 기존 작업을 저장하고 Capstone을 닫은 뒤 실행하세요.

```powershell
$env:QTWEBENGINE_REMOTE_DEBUGGING = "127.0.0.1:9223"
Start-Process "C:/Program Files/PASCO scientific/Capstone/Capstone.exe"
Remove-Item Env:QTWEBENGINE_REMOTE_DEBUGGING
```

이는 해당 설치 환경에서 확인한 내부 인터페이스이며 PASCO의 공식 API가 아닙니다. 설정 목록에 센서가 있어도 실제 연결을 뜻하지는 않습니다. 읽을 수 없는 값은 오류로 반환하며 0으로 대체하지 않습니다.

다음은 `capstone_repeat_acquisition`으로 5초 측정을 3번 수행하고 회차 사이에 2초 쉬는 예시입니다. 프로세스 ID와 창 핸들은 실제 연결 결과로 바꾸세요.

```json
{
  "plan": {
    "process_id": 1234,
    "window_handle": 5678,
    "debug_port": 9223,
    "repetitions": 3,
    "duration_seconds": 5,
    "pause_seconds": 2,
    "allow_foreground": true
  }
}
```

- 디버깅 연결과 조작할 창은 같은 프로세스에 속해야 합니다.
- 서버는 입력 전에 시작·정지 이벤트를 구독하고, 실제 이벤트 수신을 확인합니다.
- 취소 요청 후에는 작업이 종료 상태가 되었는지 확인해야 합니다.
- 반복 측정 중에는 다른 MCP 입력을 거부합니다. 실험 설정을 직접 바꾸는 것도 피하세요. 회차 사이의 표시 속도는 확인하지만 모든 물리적 조건을 보장하지는 않습니다.
- 결과는 Capstone에 남으며 **자동 저장하지 않습니다.** 파일을 저장한 뒤 해당 데이터셋을 추출해 비교하세요. 회차와 데이터셋 ID를 추측해 연결하지 않습니다.
- 회차 기록의 경과 시간은 PC에서 관찰한 시간으로, 센서 타임스탬프가 아닙니다.

샘플링 속도는 기록이 정지된 상태에서 조절합니다. `expected_sensor`에는 조회한 선택 센서 이름을 정확히 전달하며, Capstone의 증가·감소 버튼으로 한 단계씩 바꿉니다. 다른 설정은 화면 조작 도구로 접근하며 공통 센서 교정 API는 없습니다.

</details>

## 알아둘 점

- **로컬 전용:** 잠금이 해제된 데스크톱에서 사용하세요. 서버를 외부에 노출하거나 여러 클라이언트가 동시에 조작하지 않도록 합니다.
- **조작 후 확인:** 입력 전달 성공이 작업 완료는 아닙니다. `transition_pending=true`도 측정 성공을 뜻하지 않습니다.
- **데이터 구분:** 샘플 인덱스를 시간으로 간주하지 않습니다. 단위 ID도 임의로 해석하지 않으며, 같은 회차·단위의 데이터를 골라 분석해야 합니다.
- **지원 범위:** 모든 Capstone 기능과 `.cap` 저장 형식을 지원하는 것은 아닙니다. 지원하지 않는 형식과 사용할 수 없는 측정값은 오류로 구분합니다.

<details>
<summary><strong>데이터 형식과 화면 조작의 세부 제약</strong></summary>

숫자는 원문과 함께 소수 문자열로 반환하며, 독립변수 좌표와 저장 방식도 구분합니다. 종속변수 타입 7 문자열·타입 0 태그 포함 실수, 독립변수 타입 0 실수·타입 1 등간격 좌표·타입 4 인덱스를 지원합니다. 오프셋을 반영하고 결측·유효하지 않은 수치는 `null`로 구분합니다. 항목이 있는 구간 속성 예외 목록과 구형 문자열 별칭 등은 지원하지 않습니다. 배열을 해독하지 못해도 구성 조회는 가능합니다.

피팅·비교 입력의 비유한 값과 x·y 길이 불일치는 거부합니다. 최소제곱 표준오차는 독립적이고 분산이 같은 잔차를 가정한 통계량으로, 센서 교정 불확도가 아닙니다.

Capstone의 UIA InvokePattern은 대화상자가 열릴 때 접근성 조회를 막을 수 있어 `action="invoke"`는 실제 클릭을 사용합니다. 다른 UIA 패턴이 지원되지 않으면 오류를 반환합니다. 스크린샷은 지정한 창 핸들(HWND)을 캡처합니다.

Windows가 창 활성화를 거부하면 해당 창을 직접 활성화해야 합니다. 앱의 접근성 제공자가 멈추면 조회도 멈출 수 있으며, 각 조회를 별도 프로세스로 격리하는 제한 시간 처리는 없습니다. 이때는 앱 상태를 확인하고 서버를 재시작하세요.

파일 덮어쓰기와 하드웨어 출력 등 결과가 남는 조작은 사용하는 AI 클라이언트에서 사용자 의사를 확인해야 합니다.

</details>

<details>
<summary><strong>개발 및 검증</strong></summary>

```powershell
uv run basedpyright src tests scripts
uv run ruff check src tests scripts
uv run pytest -q
```

통합 테스트에는 실행 중인 Capstone과 설치된 예제 파일이 필요합니다.

- 기존 전체 35개와 이후 확장한 측정 제어 7개·반복 측정 6개를 실행해 **중복 제외 44개 테스트**를 검증했습니다. 타입·린트 검사도 통과했습니다.
- 실제 앱에서 한글·특수문자 입력, 대화상자 조작, 드래그·스크롤, 재실행, 창 캡처를 확인했습니다.
- QuickStart 파일을 읽고 Newton 실험 데이터로 산점도와 선형 피팅을 만들었습니다.
- 별도 시험 파일의 숫자 6개가 Capstone 내보내기 미리보기와 표시 정밀도 내에서 일치했습니다. 원본 템플릿은 수정하지 않았습니다.
- 시험 실험에서 샘플링 속도를 50→100→50 Hz로 변경·복원했습니다.
- 측정 불가 상태 처리와 이벤트 구독·해제를 확인했습니다. 반복 제어 테스트는 가상 시계·신호를 사용하며 **실물 측정 검증을 대신하지 않습니다.**

저장 형식과 내부 요청은 IDA 정적 분석과 실제 앱의 동작을 대조했습니다. 항상 실패를 반환하는 내부 JSON 메서드 57은 사용하지 않습니다. 서버 실행에 IDA는 필요하지 않습니다.

</details>

---

이 프로젝트는 **PASCO의 물리 실험 프로그램**을 위한 도구입니다. 같은 이름의 Capstone 디스어셈블 엔진과는 관계가 없습니다.
