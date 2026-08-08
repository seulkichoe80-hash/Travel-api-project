# 국내 여행 추천 CLI

## 프로그램 소개

날짜를 입력하면 OpenAI가 국내 여행지역 2~3곳을 추천하고 Kakao Local API가 각 지역의 맛집 5곳을 검색합니다. 두 결과로 지역별 Markdown 여행 리포트를 만듭니다. 날씨와 행사는 AI가 만든 참고용 정보이므로 출발 전에 공식 출처에서 최신 정보를 확인하세요. Python 3.10 이상이 필요합니다.

## 설치방법

프로젝트 폴더에서 가상환경을 만들고 패키지를 설치합니다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS/Linux에서는 활성화 명령으로 `source .venv/bin/activate`를 사용합니다.

## API 키 설정방법

1. `.env.example`을 복사하여 `.env` 파일을 만듭니다.
2. 아래 예시 값을 본인의 실제 키로 바꿉니다.

```dotenv
OPENAI_API_KEY=실제_OpenAI_API_키
KAKAO_REST_API_KEY=실제_Kakao_REST_API_키
```

OpenAI API 플랫폼에서 OpenAI 키를, Kakao Developers 애플리케이션에서 **REST API 키**를 발급받습니다. 같은 이름의 운영체제 환경변수를 사용해도 됩니다.

## 실행방법

```bash
python travel_planner.py --date "2026-08-15"
```

`--date`는 필수이며 `YYYY-MM-DD` 형식의 실제 날짜여야 합니다. 도움말은 `python travel_planner.py --help`로 봅니다.

같은 날짜로 다시 실행하면 저장된 결과를 사용하므로 API 비용과 시간을 절약합니다. API를 다시 호출해 결과를 갱신하려면 `--refresh`를 추가합니다.

```bash
python travel_planner.py --date "2026-08-15" --refresh
```

## 결과물 설명

실행하면 `results` 폴더가 자동 생성됩니다.

- `YYYY-MM-DD_raw.json`: `recommendation`, 지역별 `restaurants`, `errors` 원본 데이터
- `YYYY-MM-DD_travel_plan.md`: 추천 지역, 날씨, 행사, 맛집, 하루 일정 리포트

Kakao 검색이 실패하거나 결과가 0건이어도 가능한 정보로 리포트를 만들며, 문제는 `errors`에서 확인할 수 있습니다.

## 보너스 기능

- `recommended_cities`에 2~3개 지역을 저장하고 반복문으로 지역별 맛집을 검색합니다.
- 맛집 결과는 `{ "부산": [...], "제주": [...] }`처럼 지역별로 구분합니다.
- 같은 날짜의 정상 결과가 있으면 OpenAI와 Kakao API를 호출하지 않고 기존 결과를 즉시 사용합니다.

## API 키 보안 주의사항

- API 키를 Python 코드에 직접 적지 마세요.
- `.env`를 Git에 커밋하거나 다른 사람에게 보내지 마세요.
- 이 프로젝트의 `.gitignore`는 `.env`를 제외합니다.
- 키가 공개되면 즉시 폐기하고 새 키를 발급하세요.
- `.env.example`에는 예시 값만 유지하세요.


---

## 실행 결과 및 증빙자료

아래 화면은 프로그램의 구현 및 실행 결과를 단계별로 확인한 증빙자료입니다.

### 1. 프로젝트 구성

Python 실행 파일, 환경변수 예시 파일, 의존성 목록, 결과 저장 폴더 등 프로젝트의 전체 구성을 확인할 수 있습니다.

![프로젝트 구성](images/01_list.PNG)

### 2. 프로그램 정상 실행 및 API 연동

`--date` 옵션으로 여행 날짜를 입력하면 OpenAI API를 통해 여행지를 추천받고, 추천 지역을 기반으로 Kakao Local API에서 맛집을 검색한 뒤 최종 여행 리포트를 생성합니다. 실행 완료 후 원본 JSON과 Markdown 리포트의 저장 경로도 출력됩니다.

![프로그램 정상 실행](images/02_proceed.PNG)

### 3. LLM 여행지 추천 결과(JSON)

입력한 날짜를 기준으로 서울, 부산, 제주도 등 복수 지역을 추천받고, 지역별 `weather`, `events`, `reason` 정보를 JSON 형태로 구조화한 결과입니다.

![LLM 추천 JSON](images/03_raw_json.PNG)

### 4. Kakao Local API 맛집 검색 결과(JSON)

LLM이 추천한 지역을 Kakao Local API의 검색 입력값으로 사용하여 맛집 정보를 조회합니다. 각 결과에는 상호명(`name`), 주소(`address`), 카테고리(`category`), URL, 좌표(`x`, `y`)가 포함됩니다. 정상 실행 시 `errors`는 빈 배열로 저장됩니다.

![맛집 검색 JSON](images/03-1_raw_json.PNG)

### 5. 최종 Markdown 여행 리포트

LLM 추천 정보와 Kakao Local API의 맛집 정보를 결합하여 추천 지역, 추천 이유, 날씨, 행사·축제 등을 포함한 최종 여행 리포트를 생성합니다.

![최종 여행 리포트 상단](images/04_result.PNG)

지역별 맛집 정보와 1일 일정 제안까지 포함되며, 정상 실행에서는 오류 요약이 `없음`으로 표시됩니다.

![최종 여행 리포트 하단](images/04-1_result.PNG)

### 6. 잘못된 날짜 입력 예외처리

존재하지 않는 날짜인 `2026-99-99`를 입력한 테스트입니다. 프로그램은 잘못된 날짜를 감지하여 `YYYY-MM-DD` 형식의 올바른 날짜를 입력하도록 안내하고 실행을 종료합니다.

![날짜 입력 오류 처리](images/05_error.PNG)

### 7. Kakao Local API 실패 예외처리

Kakao API 인증 실패 상황을 테스트한 결과입니다. 맛집 검색이 실패해도 프로그램 전체가 중단되지 않고 최종 JSON 및 Markdown 파일까지 생성됩니다.

![API 실패 후 프로그램 완료](images/06_ApiEerror.PNG)

최종 리포트에서는 맛집을 `검색 결과 없음`으로 처리하고, `errors` 항목에 Kakao API의 `401 Unauthorized` 오류 내용을 기록합니다. 이를 통해 장소 검색 API 실패 시에도 가능한 정보로 최종 리포트를 생성하는 예외처리를 확인할 수 있습니다.

![API 실패 오류 기록](images/06-1_ApiEerror.PNG)

> **참고:** 위 API 오류 화면은 예외처리 기능을 확인하기 위한 테스트 결과이며, 정상 실행 결과에서는 `errors`가 비어 있습니다.
