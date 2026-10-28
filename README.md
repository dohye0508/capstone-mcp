<h1 align="center">PASCO Capstone MCP</h1>

<p align="center">Capstone 조작 · 실험 데이터 추출 · 분석</p>

<p align="center">
  <a href="#설치">설치</a> &nbsp;·&nbsp;
  <a href="#mcp-설정">MCP 설정</a> &nbsp;·&nbsp;
  <a href="#사용">사용법</a>
</p>

---

## 기능

| 기능 | 내용 |
| :--- | :--- |
| **화면 조작** | 컨트롤 조회, 클릭·입력, 드래그·스크롤, 스크린샷 |
| **데이터 추출** | `.cap` 파일의 실험 설정과 수치 데이터 |
| **분석** | 산점도, 선형 피팅, 측정 결과 비교 |
| **측정 제어** | 시작·정지, 샘플링 속도, 반복 측정 |

**검증 범위** — 파일 분석·화면 조작 확인. 실물 센서 측정·반복 측정은 미검증.

## 설치

**Windows · Python 3.12+ · [uv](https://docs.astral.sh/uv/) · PASCO Capstone**

```powershell
git clone https://github.com/ji5zi5/capstone-mcp.git
cd capstone-mcp
uv sync --python 3.12
```

Capstone 경로: `C:/Program Files/PASCO scientific/Capstone/Capstone.exe`

## MCP 설정

`--directory`를 프로젝트 경로로 바꿔 클라이언트 설정에 추가합니다.

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

HTTP 연결은 `uv run capstone-mcp-http`로 실행한 뒤 `http://127.0.0.1:8766/mcp`를 사용합니다.

## 사용

앱 연결 → 창 조회 → 스냅샷 → 조작

실제 입력에는 `allow_foreground=true`가 필요합니다. 스냅샷의 참조값은 새 조회나 조작 후 만료됩니다.

<details>
<summary><strong>주요 도구</strong></summary>

| 작업 | 도구 |
| :--- | :--- |
| 앱 연결·창 조회 | `capstone_attach`, `capstone_windows` |
| 컨트롤 조회·조작 | `capstone_snapshot`, `capstone_action` |
| 실험 파일 조회 | `capstone_inspect_file`, `capstone_file_datasets` |
| 수치 추출 | `capstone_extract_dataset` |
| 그래프·피팅·비교 | `capstone_plot`, `capstone_linear_fit`, `capstone_compare_runs` |
| 실시간 조회 | `capstone_live_configuration`, `capstone_current_value` |
| 측정 상태·시작·정지 | `capstone_recording_status`, `capstone_set_recording` |
| 샘플링 속도 조절 | `capstone_step_sampling_rate` |
| 반복 측정·상태·취소 | `capstone_repeat_acquisition`, `capstone_acquisition_job`, `capstone_cancel_acquisition` |

</details>

<details>
<summary><strong>실시간 조회·반복 측정 설정</strong></summary>

기존 작업을 저장하고 Capstone을 닫은 뒤 디버깅 포트를 지정해 실행합니다. 파일 분석에는 이 설정이 필요하지 않습니다.

```powershell
$env:QTWEBENGINE_REMOTE_DEBUGGING = "127.0.0.1:9223"
Start-Process "C:/Program Files/PASCO scientific/Capstone/Capstone.exe"
Remove-Item Env:QTWEBENGINE_REMOTE_DEBUGGING
```

</details>

## 제한 사항

- 잠금이 해제된 로컬 데스크톱에서 사용합니다. 여러 클라이언트의 동시 조작은 피하세요.
- 지원하지 않는 파일 형식과 읽을 수 없는 측정값은 오류로 반환합니다.
- 그래프와 피팅 결과는 별도로 반환하며 Capstone 페이지를 수정하지 않습니다.
- 샘플 인덱스는 시간이 아닙니다. 분석할 데이터의 회차와 단위를 확인하세요.
- 시작·정지·취소 요청 후에는 실제 상태를 확인해야 합니다.
- 반복 측정 결과는 자동 저장하지 않습니다. Capstone에서 저장한 뒤 데이터를 추출하세요.
- 실시간 연결은 PASCO 공식 API가 아닌 내부 인터페이스를 사용합니다.
