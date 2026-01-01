"""
경제 캘린더 데이터 수집 및 저장 모듈
Perplexity API로 경제지표를 조회하고 Supabase DB에 저장합니다.
"""

from supabase import create_client, Client
from dotenv import load_dotenv
import os
import requests
import json
import re
from typing import List, Union
from datetime import datetime
from dateutil.relativedelta import relativedelta

# .env 파일 로드
load_dotenv()

# ============================================
# Supabase 및 API 키 설정
# ============================================
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

# 필수 환경 변수 검증
if not SUPABASE_URL:
    raise ValueError("❌ SUPABASE_URL이 설정되지 않았습니다. .env 파일을 확인하세요.")
if not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
if not PERPLEXITY_API_KEY:
    raise ValueError("❌ PERPLEXITY_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

# Supabase 클라이언트 초기화
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase 클라이언트 연결 성공")
except Exception as e:
    print(f"❌ Supabase 클라이언트 연결 실패: {str(e)}")
    raise


# ============================================
# EconomicCalendarFetcher 클래스
# ============================================
class EconomicCalendarFetcher:
    """Perplexity API를 사용하여 경제지표를 조회하고 DB에 저장하는 클래스"""

    def __init__(self, api_key, supabase_client):
        """
        Args:
            api_key (str): Perplexity API 키
            supabase_client (Client): Supabase 클라이언트
        """
        self.api_key = api_key
        self.supabase = supabase_client
        self.perplexity_url = "https://api.perplexity.ai/chat/completions"

    def get_next_month_date_range(self):
        """
        다음달의 시작일과 마지막날을 반환

        Returns:
            tuple: (시작일 YYYY-MM-DD, 마지막날 YYYY-MM-DD)
        """
        today = datetime.now()
        next_month = today + relativedelta(months=1)

        first_day = next_month.replace(day=1)
        last_day = next_month.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)

        return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")

    def fetch_econ_indicators_from_perplexity(self, year_month: str = None):
        """
        Perplexity API로 경제지표 조회 (기본값: 다음달)

        Args:
            year_month (str): 조회할 연월 (예: "2026-01"). None이면 다음달 자동 설정

        Returns:
            list: 경제지표 정보 리스트 (JSON 형식)
        """

        if not year_month:
            next_month = datetime.now() + relativedelta(months=1)
            year_month = next_month.strftime("%Y-%m")

        year, month = year_month.split("-")
        korean_month = f"{year}년 {int(month)}월"

        prompt = f"""
{korean_month} 미국 경제 캘린더 데이터를 JSON 형식으로 정확히 파싱하고 구조화해줘.

각 항목마다 다음 정보를 포함해줘:
- 발표일자 (YYYY-MM-DD 형식)
- 요일 (한글)
- 지표명 (영문 약어 포함, 예: "ISM Manufacturing PMI")
- 컨센서스 예상치 (숫자/퍼센트 그대로)
- 이전달 실적 (Previous Value)
- 카테고리 (ISM/고용/CPI/판매/GDP 등)
- 주식시장 영향 설명 (예: "긍정적 영향 예상 - 강한 고용지표는 경제성장을 의미하며 주식시장에 긍정적")

Pandas DataFrame으로 변환 가능한 완전한 JSON 배열로 출력해줘:

{{
    "indicators": [
        {{
            "date": "2026-01-03",
            "day": "금",
            "indicator": "ISM Manufacturing PMI",
            "consensus": "48.2",
            "previous": "47.2",
            "category": "ISM",
            "market_impact": "긍정적 영향 예상 - 제조업 활동 개선은 경제성장 신호"
        }}
    ]
}}

주의사항:
1. 테이블 형식 그대로 변환하지 말고 표준화된 JSON 객체 배열로 만들어줘
2. 날짜는 반드시 YYYY-MM-DD 형식
3. 요일은 한글 (월, 화, 수, 목, 금, 토, 일)
4. 시장 영향은 2-3 문장으로 상세히 작성
5. JSON만 반환해 (마크다운 코드블록 제외)
"""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 3000,
                "temperature": 0.2
            }

            print(f"🔄 Perplexity API 호출 중... ({year_month})")
            response = requests.post(self.perplexity_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()

            data = response.json()
            print(f"✅ API 응답 받음")

            # 응답에서 텍스트 추출
            content = data['choices'][0]['message']['content']

            # JSON 블록 추출 (마크다운 코드블록 제거)
            content_cleaned = content.replace('``````', '').strip()
            json_match = re.search(r'\{[\s\S]*\}', content_cleaned)  # 이제 content_cleaned가 정의됨

            if json_match:
                indicators_data = json.loads(json_match.group())
                return indicators_data.get('indicators', [])
            else:
                print(f"⚠️  JSON 형식을 찾을 수 없음")
                print(f"응답: {content[:500]}")
                return []

        except Exception as e:
            print(f"❌ Perplexity API 오류: {e}")
            return []

    def save_indicators_to_db(self, indicators: List[dict]):
        """
        경제지표를 데이터베이스에 저장

        Args:
            indicators (list): 저장할 경제지표 리스트
                예: [
                    {
                        "date": "2026-01-03",
                        "day": "금",
                        "indicator": "ISM Manufacturing PMI",
                        "consensus": "48.2",
                        "previous": "47.2",
                        "category": "ISM",
                        "market_impact": "..."
                    }
                ]

        Returns:
            int: 저장된 지표 개수
        """
        if not indicators:
            print("❌ 저장할 경제지표가 없습니다.")
            return 0

        try:
            saved_count = 0
            for indicator in indicators:
                # 필수 필드 검증
                required_fields = ['date', 'indicator', 'consensus', 'previous']
                if not all(field in indicator for field in required_fields):
                    print(f"⚠️  필수 필드 누락: {indicator}")
                    continue

                # Supabase 저장 순서: 발표일자, 지표, 이전달 실적, 다음달 컨센서스, 주식시장 영향
                self.supabase.table("econ_calendar").insert({
                    "announcement_date": indicator.get('date'),
                    "day": indicator.get('day', ''),
                    "indicator": indicator.get('indicator'),
                    "previous_value": indicator.get('previous'),
                    "consensus": indicator.get('consensus'),
                    "category": indicator.get('category', 'Other'),
                    "market_impact": indicator.get('market_impact', ''),
                    "created_at": datetime.now().isoformat()
                }).execute()

                saved_count += 1
                print(f"  ✓ {indicator.get('date')} - {indicator.get('indicator')}")

            print(f"\n✅ {saved_count}개 경제지표 저장 완료")
            return saved_count

        except Exception as e:
            print(f"❌ DB 저장 오류: {e}")
            return 0

    def fetch_and_save(self, year_month: str = None):
        """
        전체 프로세스 실행 (API 조회 → DB 저장)

        Args:
            year_month (str): 조회할 연월 (예: "2026-01"). None이면 다음달 자동 설정

        Returns:
            bool: 성공 여부
        """
        print(f"\n{'=' * 60}")
        print(f"🚀 경제 캘린더 데이터 수집 시작")
        print(f"{'=' * 60}")

        if not year_month:
            next_month = datetime.now() + relativedelta(months=1)
            year_month = next_month.strftime("%Y-%m")

        # 1. Perplexity API로 경제지표 조회
        indicators = self.fetch_econ_indicators_from_perplexity(year_month)

        if not indicators:
            print("❌ 경제지표를 조회할 수 없습니다.")
            return False

        print(f"\n📊 조회된 지표: {len(indicators)}개")
        for ind in indicators:
            print(f"  • {ind.get('date')} ({ind.get('day')}) - {ind.get('indicator')}")

        # 2. DB에 저장
        saved_count = self.save_indicators_to_db(indicators)

        print(f"\n{'=' * 60}")
        if saved_count > 0:
            print(f"✅ 처리 완료 ({saved_count}개 지표 저장)")
            return True
        else:
            print(f"❌ 저장된 지표가 없습니다.")
            return False


# ============================================
# Supabase 테이블 초기화 (필요시 실행)
# ============================================
def initialize_econ_calendar_table():
    """
    econ_calendar 테이블이 없으면 생성 (선택사항)

    이미 Supabase에 테이블이 있으면 실행할 필요 없음.
    SQL로 미리 만들어두는 것을 권장합니다.
    """
    try:
        # Supabase SQL 실행 (RPC 또는 Admin API 필요)
        # 일단 테이블 조회 시도
        result = supabase.table("econ_calendar").select("*", count="exact").limit(1).execute()
        print("✅ econ_calendar 테이블이 이미 존재합니다.")
        return True
    except Exception as e:
        print(f"⚠️  econ_calendar 테이블 확인 불가: {e}")
        print("💡 Supabase 대시보드에서 SQL로 다음을 실행해주세요:")
        create_table_sql = """
CREATE TABLE IF NOT EXISTS econ_calendar (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    announcement_date DATE NOT NULL,
    day VARCHAR(10),
    indicator VARCHAR(255) NOT NULL,
    previous_value VARCHAR(50),
    consensus VARCHAR(50),
    category VARCHAR(100),
    market_impact TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(announcement_date, indicator)
);
        """
        print(create_table_sql)
        return False


# ============================================
# 스탠드얼론 실행 코드
# ============================================
if __name__ == "__main__":
    """
    이 파일을 직접 실행할 때의 코드

    사용 예시:
    python econ_calendar_fetcher.py

    또는 다른 파일에서 import해서 사용:
    from econ_calendar_fetcher import EconomicCalendarFetcher, supabase

    fetcher = EconomicCalendarFetcher(PERPLEXITY_API_KEY, supabase)
    fetcher.fetch_and_save()  # 다음달 자동 설정
    # 또는
    fetcher.fetch_and_save("2026-02")  # 특정 연월 지정
    """

    print("=" * 60)
    print("🚀 Economic Calendar Fetcher 시작")
    print("=" * 60)

    # Perplexity API 키 확인
    if not PERPLEXITY_API_KEY:
        print("❌ PERPLEXITY_API_KEY가 설정되지 않았습니다.")
        exit(1)

    # 테이블 초기화 확인
    initialize_econ_calendar_table()

    # EconomicCalendarFetcher 인스턴스 생성
    fetcher = EconomicCalendarFetcher(PERPLEXITY_API_KEY, supabase)

    # 경제지표 조회 및 저장 (다음달 자동 설정)
    result = fetcher.fetch_and_save()

    # 특정 연월 지정하려면:
    # result = fetcher.fetch_and_save("2026-02")

    # 여러 달 반복하려면:
    # for month in ["2026-01", "2026-02", "2026-03"]:
    #     fetcher.fetch_and_save(month)

    print("\n" + "=" * 60)
    if result:
        print("✅ 경제 캘린더 데이터 수집 완료!")
    else:
        print("❌ 경제 캘린더 데이터 수집 실패!")
    print("=" * 60)
