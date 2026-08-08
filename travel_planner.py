"""날짜에 맞는 국내 여행지와 맛집을 추천하는 CLI 프로그램."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from openai import OpenAI

RESULTS_DIR = Path(__file__).resolve().parent / "results"
KAKAO_LOCAL_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
CITY_ALIASES = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "제주특별자치도": "제주도",
    "경기도": "경기", "강원특별자치도": "강원", "충청북도": "충북",
    "충청남도": "충남", "전북특별자치도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남",
}
RECOMMENDATION_SCHEMA = {
    "name": "travel_recommendation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "recommended_cities": {
                "type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 3
            },
            "city_details": {
                "type": "array",
                "minItems": 2,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "weather": {"type": "string"},
                        "events": {"type": "array", "items": {"type": "string"}},
                        "reason": {"type": "string"},
                    },
                    "required": ["city", "weather", "events", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["recommended_cities", "city_details"],
        "additionalProperties": False,
    },
}


def valid_date(value: str) -> str:
    """YYYY-MM-DD 형식과 실제 달력 날짜를 검사한다."""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "날짜는 YYYY-MM-DD 형식의 올바른 날짜여야 합니다. 예: 2026-08-15"
        ) from exc
    if parsed.strftime("%Y-%m-%d") != value:
        raise argparse.ArgumentTypeError("날짜 형식은 YYYY-MM-DD여야 합니다.")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 국내 여행 추천 리포트를 만듭니다.")
    parser.add_argument("--date", required=True, type=valid_date, help="여행 날짜 (YYYY-MM-DD)")
    parser.add_argument("--refresh", action="store_true", help="저장된 결과를 무시하고 API를 다시 호출")
    return parser.parse_args()


def check_api_keys() -> tuple[str, str]:
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    kakao_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    missing = []
    if not openai_key:
        missing.append("OPENAI_API_KEY")
    if not kakao_key:
        missing.append("KAKAO_REST_API_KEY")
    if missing:
        print(f"오류: 다음 API 키가 없습니다: {', '.join(missing)}", file=sys.stderr)
        print(".env.example을 .env로 복사한 뒤 실제 키를 입력하세요.", file=sys.stderr)
        print("API 키는 코드나 Git 저장소에 올리지 마세요.", file=sys.stderr)
        raise SystemExit(1)
    return openai_key, kakao_key


def normalize_city_name(city: str) -> str:
    """긴 행정구역명이나 세부 지역명을 검색하기 좋은 대표 지역명으로 바꾼다."""
    if not isinstance(city, str) or not city.strip():
        raise ValueError(f"도시 이름은 비어 있지 않은 문자열이어야 합니다: {city!r}")
    cleaned = " ".join(city.strip().split())
    if cleaned in CITY_ALIASES:
        return CITY_ALIASES[cleaned]
    for official_name, short_name in CITY_ALIASES.items():
        if cleaned.startswith(official_name + " "):
            return short_name
    return cleaned


def validate_recommendation(recommendation: dict[str, Any]) -> dict[str, Any]:
    """추천 JSON의 필수 키, 자료형, 도시 개수와 상세정보 일치를 검사한다."""
    required = {"recommended_cities", "city_details"}
    missing = required - recommendation.keys()
    if missing:
        raise ValueError(f"추천 JSON 필수 키 누락: {', '.join(sorted(missing))}")
    cities = recommendation["recommended_cities"]
    details = recommendation["city_details"]
    if not isinstance(cities, list) or not isinstance(details, list):
        raise ValueError("recommended_cities와 city_details는 리스트여야 합니다.")
    if not 2 <= len(cities) <= 3:
        raise ValueError(f"추천 도시 개수는 2~3개여야 합니다. 현재: {len(cities)}개")

    normalized_cities = [normalize_city_name(city) for city in cities]
    normalized_details = []
    for index, detail in enumerate(details):
        detail_required = {"city", "weather", "events", "reason"}
        if not isinstance(detail, dict):
            raise ValueError(f"city_details[{index}]는 객체여야 합니다.")
        detail_missing = detail_required - detail.keys()
        if detail_missing:
            raise ValueError(
                f"city_details[{index}] 필수 키 누락: {', '.join(sorted(detail_missing))}"
            )
        if not isinstance(detail["weather"], str) or not isinstance(detail["reason"], str):
            raise ValueError(f"city_details[{index}]의 weather와 reason은 문자열이어야 합니다.")
        if not isinstance(detail["events"], list) or not all(
            isinstance(event, str) for event in detail["events"]
        ):
            raise ValueError(f"city_details[{index}].events는 문자열 리스트여야 합니다.")
        normalized_detail = dict(detail)
        normalized_detail["city"] = normalize_city_name(detail["city"])
        normalized_details.append(normalized_detail)

    detail_cities = [item["city"] for item in normalized_details]
    if normalized_cities != detail_cities:
        raise ValueError(
            f"도시와 상세정보 순서 불일치: cities={normalized_cities}, details={detail_cities}"
        )
    if len(set(normalized_cities)) != len(normalized_cities):
        raise ValueError(f"중복 추천 도시가 있습니다: {normalized_cities}")
    recommendation["recommended_cities"] = normalized_cities
    recommendation["city_details"] = normalized_details
    return recommendation


def request_recommendation(client: "OpenAI", travel_date: str, errors: list[str]) -> dict[str, Any] | None:
    """여행 추천 JSON을 요청하고 파싱 실패 시 한 번만 다시 요청한다."""
    prompt = (
        f"여행 날짜는 {travel_date}입니다. 서로 다른 대한민국 국내 여행지역 2~3곳을 추천하세요. "
        "recommended_cities와 city_details의 도시 이름 및 순서는 반드시 서로 일치해야 합니다. "
        "날씨는 계절적 예상임을 명확히 하고, 행사 정보가 불확실하면 사전 확인이 필요하다고 쓰세요. "
        "모든 값은 한국어로 작성하세요."
    )
    for attempt in range(2):
        try:
            retry_instruction = ""
            if attempt == 1:
                retry_instruction = (
                    " 이전 응답은 검증에 실패했습니다. JSON 이외의 문장은 쓰지 말고, "
                    "필수 키·자료형·도시 순서를 스키마와 정확히 일치시키세요."
                )
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": (
                        "당신은 국내 여행 플래너입니다. 지정된 JSON 형식만 반환하세요."
                        + retry_instruction
                    )},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_schema", "json_schema": RECOMMENDATION_SCHEMA},
                temperature=0.7,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM 응답 내용이 비어 있습니다.")
            return validate_recommendation(json.loads(content))
        except (json.JSONDecodeError, ValueError, TypeError, KeyError, IndexError) as exc:
            errors.append(f"여행 추천 JSON 파싱 실패 ({attempt + 1}/2): {exc}")
            if attempt == 0:
                print("추천 JSON 파싱에 실패해 한 번 더 요청합니다.")
        except Exception as exc:
            errors.append(f"OpenAI 여행 추천 요청 실패: {exc}")
            return None
    return None


def search_kakao_restaurants(city: str, api_key: str, errors: list[str]) -> list[dict[str, str]]:
    """Kakao Local API에서 추천 도시의 맛집 다섯 곳을 검색한다."""
    import requests

    try:
        response = requests.get(
            KAKAO_LOCAL_URL,
            headers={"Authorization": f"KakaoAK {api_key}"},
            params={"query": f"{city} 맛집", "size": 5, "sort": "accuracy"},
            timeout=10,
        )
        response.raise_for_status()
        documents = response.json().get("documents", [])
        return [
            {
                "name": item.get("place_name", ""),
                "address": item.get("road_address_name") or item.get("address_name", ""),
                "category": item.get("category_name", ""),
                "url": item.get("place_url", ""),
                "x": item.get("x", ""),
                "y": item.get("y", ""),
            }
            for item in documents[:5]
        ]
    except (requests.RequestException, ValueError, KeyError) as exc:
        errors.append(f"Kakao 맛집 검색 실패 ({city}): {exc}")
        return []


RestaurantProvider = Callable[[str, str, list[str]], list[dict[str, str]]]
RESTAURANT_PROVIDERS: dict[str, RestaurantProvider] = {
    "kakao": search_kakao_restaurants,
}


def search_restaurants(city: str, api_key: str, errors: list[str]) -> list[dict[str, str]]:
    """환경변수로 선택한 맛집 검색 제공자를 호출한다."""
    provider_name = os.getenv("MAP_PROVIDER", "kakao").lower()
    provider = RESTAURANT_PROVIDERS.get(provider_name)
    if provider is None:
        errors.append(
            f"지원하지 않는 지도 제공자입니다: {provider_name}. "
            f"사용 가능: {', '.join(RESTAURANT_PROVIDERS)}"
        )
        return []
    return provider(city, api_key, errors)


def fallback_report(travel_date: str, recommendation: dict[str, Any] | None,
                    restaurants: dict[str, list[dict[str, str]]], errors: list[str]) -> str:
    """LLM 요청이 실패해도 저장할 기본 Markdown을 만든다."""
    rec = recommendation or {}
    cities = rec.get("recommended_cities") or []
    details = {item["city"]: item for item in rec.get("city_details", [])}

    def city_section(city: str, field: str) -> str:
        detail = details.get(city, {})
        if field == "events":
            return "\n".join(f"- {event}" for event in detail.get(field, [])) or "- 확인된 정보 없음"
        return detail.get(field, "정보 없음")

    reasons = "\n\n".join(f"### {city}\n{city_section(city, 'reason')}" for city in cities)
    weather = "\n\n".join(f"### {city}\n{city_section(city, 'weather')}" for city in cities)
    events = "\n\n".join(f"### {city}\n{city_section(city, 'events')}" for city in cities)
    place_sections = []
    for city in cities:
        places = [f"- [{r['name']}]({r['url']}) — {r['address']} ({r['category']})"
                  for r in restaurants.get(city, [])]
        place_sections.append(f"### {city}\n" + ("\n".join(places) or "- 검색 결과 없음"))
    schedules = "\n\n".join(
        f"### {city}\n오전에는 대표 관광지를 방문하고, 점심에는 추천 맛집을 이용한 뒤 "
        "오후에는 주변 명소와 행사를 둘러보세요. 운영시간과 이동시간은 미리 확인하세요."
        for city in cities
    )
    return f"""# {travel_date} 국내 여행 추천 리포트

## 추천 지역
{', '.join(cities) or '추천 정보를 만들지 못했습니다.'}

## 추천 이유
{reasons or '정보 없음'}

## 날씨 요약
{weather or '정보 없음'}

## 행사/축제
{events or '- 확인된 정보 없음'}

## 맛집 추천
{chr(10).join(place_sections) or '- 검색 결과 없음'}

## 1일 일정 제안
{schedules or '상세 일정은 현지 운영시간과 이동시간을 확인하여 조정하세요.'}

## 오류 요약(errors)
{chr(10).join(f'- {error}' for error in errors) or '- 없음'}
"""


def create_markdown_report(client: "OpenAI", travel_date: str, recommendation: dict[str, Any],
                           restaurants: dict[str, list[dict[str, str]]], errors: list[str]) -> str:
    """추천 정보와 맛집 목록으로 최종 Markdown 리포트를 요청한다."""
    headings = ["## 추천 지역", "## 추천 이유", "## 날씨 요약", "## 행사/축제",
                "## 맛집 추천", "## 1일 일정 제안", "## 오류 요약(errors)"]
    data = {"recommendation": recommendation, "restaurants": restaurants, "errors": errors}
    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "주어진 데이터만 사용해 실용적인 한국어 Markdown 여행 리포트를 작성하세요."},
                {"role": "user", "content": (
                    f"제목은 '# {travel_date} 국내 여행 추천 리포트'로 작성하세요.\n"
                    f"반드시 포함할 소제목: {', '.join(headings)}\n"
                    "각 소제목 아래 내용을 추천 지역별 ### 제목으로 구분하세요. "
                    "오류가 없으면 '없음'이라고 쓰고 맛집이 0곳이어도 소제목을 유지하세요.\n"
                    f"입력 데이터:\n{json.dumps(data, ensure_ascii=False, indent=2)}"
                )},
            ],
            temperature=0.5,
        )
        report = response.choices[0].message.content or ""
        if not report or any(heading not in report for heading in headings):
            raise ValueError("필수 Markdown 항목이 누락되었습니다.")
        return report
    except Exception as exc:
        errors.append(f"OpenAI 최종 리포트 생성 실패: {exc}")
        return fallback_report(travel_date, recommendation, restaurants, errors)


def save_results(travel_date: str, recommendation: dict[str, Any] | None,
                 restaurants: dict[str, list[dict[str, str]]], errors: list[str], report: str) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RESULTS_DIR / f"{travel_date}_raw.json"
    report_path = RESULTS_DIR / f"{travel_date}_travel_plan.md"
    raw_data = {"recommendation": recommendation, "restaurants": restaurants, "errors": errors}
    raw_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report.rstrip() + "\n", encoding="utf-8")
    return raw_path, report_path


def load_cached_results(travel_date: str) -> tuple[Path, Path] | None:
    """새 형식의 원본 결과가 있으면 API 호출 없이 결과를 사용한다."""
    raw_path = RESULTS_DIR / f"{travel_date}_raw.json"
    report_path = RESULTS_DIR / f"{travel_date}_travel_plan.md"
    if not raw_path.exists():
        return None
    try:
        raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
        recommendation = raw_data["recommendation"]
        cities = recommendation["recommended_cities"]
        restaurants = raw_data["restaurants"]
        errors = raw_data["errors"]
        if not 2 <= len(cities) <= 3 or not isinstance(restaurants, dict):
            return None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    if not report_path.exists():
        report = fallback_report(travel_date, recommendation, restaurants, errors)
        report_path.write_text(report.rstrip() + "\n", encoding="utf-8")
    return raw_path, report_path


def main() -> None:
    args = parse_args()
    if not args.refresh:
        cached_paths = load_cached_results(args.date)
        if cached_paths:
            print(f"{args.date}의 저장된 결과를 사용합니다. API를 호출하지 않았습니다.")
            print(f"원본 데이터: {cached_paths[0]}")
            print(f"여행 리포트: {cached_paths[1]}")
            return
    try:
        from dotenv import load_dotenv
        from openai import OpenAI
    except ImportError:
        print("필수 패키지가 없습니다. 먼저 'python -m pip install -r requirements.txt'를 실행하세요.", file=sys.stderr)
        raise SystemExit(1)
    load_dotenv()
    openai_key, kakao_key = check_api_keys()
    errors: list[str] = []
    client = OpenAI(api_key=openai_key)
    print(f"{args.date} 여행지를 추천받는 중입니다...")
    recommendation = request_recommendation(client, args.date, errors)
    restaurants: dict[str, list[dict[str, str]]] = {}
    if recommendation:
        for city in recommendation["recommended_cities"]:
            print(f"{city} 맛집을 검색하는 중입니다...")
            restaurants[city] = search_restaurants(city, kakao_key, errors)
        print("여행 리포트를 만드는 중입니다...")
        report = create_markdown_report(client, args.date, recommendation, restaurants, errors)
    else:
        errors.append("추천 지역이 없어 맛집 검색과 LLM 리포트 생성을 건너뛰었습니다.")
        report = fallback_report(args.date, recommendation, restaurants, errors)
    raw_path, report_path = save_results(args.date, recommendation, restaurants, errors, report)
    print("완료되었습니다.")
    print(f"원본 데이터: {raw_path}")
    print(f"여행 리포트: {report_path}")


if __name__ == "__main__":
    main()
