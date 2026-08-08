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
