# fetch_events.py
import requests
import json
import re
from datetime import datetime
from supabase import create_client, Client
from typing import List, Union

# API 키 설정
FRED_API_KEY = "key"
SUPABASE_URL = "key"
SUPABASE_KEY = "key"

# Perplexity API
PERPLEXITY_API_KEY = "key"

# Supabase 클라이언트 생성
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class CompanyEventsFetcher:
    def __init__(self, api_key, supabase_client, supabase_url, supabase_key):
        self.api_key = api_key
        self.supabase = supabase_client
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.perplexity_url = "https://api.perplexity.ai/chat/completions"

    def insert_company(self, symbol: Union[str, List[str]], name: str = None):
        """
        회사 정보를 DB에 저장

        Args:
            symbol: 단일 심볼(str) 또는 심볼 리스트 (List[str])
            name: 회사명 (symbol이 str이고 새로운 회사일 때만 사용)

        Returns:
            단일 입력: company_id (int)
            리스트 입력: company_ids (List[int])
        """
        # 입력값 정규화
        if isinstance(symbol, list):
            symbols = symbol
        else:
            symbols = [symbol]

        company_ids = []

        for sym in symbols:
            try:
                # 기존 회사 확인
                response = self.supabase.table("companies").select("id").eq("symbol", sym).execute()

                if response.data:
                    company_id = response.data[0]["id"]
                    print(f"✅ 기존 회사 조회 완료 (심볼: {sym}, ID: {company_id})")
                    company_ids.append(company_id)
                    continue

                # 새 회사 추가
                comp_name = name if (not isinstance(symbol, list) and name) else sym

                new_company = self.supabase.table("companies").insert({
                    "symbol": sym,
                    "name": comp_name
                }).execute()

                company_id = new_company.data[0]["id"]
                print(f"✅ 회사 저장 완료 (심볼: {sym}, 이름: {comp_name}, ID: {company_id})")
                company_ids.append(company_id)

            except Exception as e:
                print(f"❌ 회사 저장 오류 ({sym}): {e}")
                company_ids.append(None)

        if isinstance(symbol, list):
            return company_ids
        else:
            return company_ids[0]

    def fetch_events_from_perplexity(self, symbol, company_name):
        """Perplexity API로 회사 이벤트 조회"""

        prompt = f"""
        {company_name} ({symbol})의 SEC filing과 News 찾아서 2026년 주요 이벤트와 뉴스를 조사해줘.
        이벤트와 뉴스는 해당 회사에 영향을 줄 수 있는 모든 이벤트를 찾아줘.
        항상 요청된 JSON 형식으로만 응답해. 출처(Reuters, Yahoo Finance등)를 description에 포함해.
        이벤트와 뉴스는 최대한 자연스러운 한국어로, 어렵지 않은 단어를 사용해서 한국어로 표시해줘.

        다음 카테고리로 정리해줘:
        1. 규제/정책 변화 (Legislation)
        2. 제품 출시/업데이트 (Product Launch)
        3. 실적 발표 (Earnings)
        4. 인수/합병 (M&A)
        5. 기타 주요 소식

        각 항목마다 다음 정보를 포함해줘:
        - 이벤트명
        - 설명 (2-3줄)
        - 예상 날짜 (YYYY-MM 형식, 모르면 "Unknown")
        - 현재 상태 (Not Started, In Progress, Completed)

        JSON 형식으로 반환해줘:
        {{
            "events": [
                {{
                    "type": "Legislation",
                    "title": "이벤트명",
                    "description": "설명",
                    "expected_date": "2025-06",
                    "status": "Pending"
                }}
            ]
        }}
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
                "max_tokens": 2000,
                "temperature": 0.2
            }

            print(f"🔄 Perplexity API 호출 중... ({symbol})")
            response = requests.post(self.perplexity_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            print(f"✅ API 응답 받음")

            # 응답에서 텍스트 추출
            content = data['choices'][0]['message']['content']

            # JSON 블록 추출
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                events_data = json.loads(json_match.group())
                return events_data.get('events', [])
            else:
                print(f"⚠️  JSON 형식을 찾을 수 없음")
                print(f"응답: {content[:200]}")
                return []

        except Exception as e:
            print(f"❌ Perplexity API 오류: {e}")
            return []

    def save_events_to_db(self, company_id, events):
        """이벤트를 데이터베이스에 저장"""
        if not company_id:
            print("❌ company_id가 없어서 저장 실패")
            return

        try:
            saved_count = 0
            for event in events:
                # 날짜는 YYYY-MM 형식으로 유지
                expected_date = None
                if event.get('expected_date') and event['expected_date'] not in ['TBD', 'Unknown']:
                    date_str = event['expected_date'].strip()
                    # YYYY-MM 형식 검증 (정규표현식)
                    if re.match(r'^\d{4}-\d{2}$', date_str):
                        expected_date = date_str
                    else:
                        expected_date = None

                # 이벤트 삽입
                self.supabase.table("company_events").insert({
                    "company_id": company_id,
                    "event_type": event.get('type', 'Other'),
                    "title": event.get('title', 'No title'),
                    "description": event.get('description', ''),
                    "expected_date": expected_date,  # YYYY-MM 형식
                    "status": event.get('status', 'Pending'),
                    "source": "Perplexity AI"
                }).execute()

                saved_count += 1

            print(f"✅ {saved_count}개 이벤트 저장 완료")
        except Exception as e:
            print(f"❌ DB 저장 오류: {e}")

    def fetch_and_save(self, symbols: Union[str, List[str]]):
        """
        전체 프로세스 실행 (symbol만 입력)

        Args:
            symbols: 단일 심볼(str) 또는 심볼 리스트 (List[str])
        """
        # 입력값 정규화
        if isinstance(symbols, str):
            symbol_list = [symbols]
        else:
            symbol_list = symbols

        results = []

        for sym in symbol_list:
            print(f"\n{'=' * 50}")
            print(f"🔍 {sym} 처리 중...")
            print(f"{'=' * 50}")

            # 1. 회사 정보 저장 또는 조회 (symbol만 사용)
            company_id = self.insert_company(sym)

            if not company_id:
                print(f"❌ 회사 저장 실패")
                results.append(False)
                continue

            # 2. 이벤트 조회 (symbol을 company_name으로도 사용)
            events = self.fetch_events_from_perplexity(sym, sym)

            if events:
                # 3. DB에 저장
                self.save_events_to_db(company_id, events)
                results.append(True)
            else:
                print(f"⚠️  이벤트를 찾을 수 없음")
                results.append(False)

        return results

    def display_saved_events(self, symbol: Union[str, List[str]]):
        """저장된 이벤트 조회 및 출력"""
        if isinstance(symbol, str):
            symbols = [symbol]
        else:
            symbols = symbol

        for sym in symbols:
            try:
                # 1. 먼저 company_id 조회
                company_response = self.supabase.table("companies").select("id").eq("symbol", sym).execute()

                if not company_response.data:
                    print(f"⚠️  {sym}을 찾을 수 없습니다.")
                    continue

                company_id = company_response.data[0]['id']

                # 2. 해당 company_id의 이벤트 조회
                response = self.supabase.table("company_events").select(
                    "event_type, title, description, expected_date, status"
                ).eq("company_id", company_id).execute()

                events = response.data

                print(f"\n{'=' * 50}")
                print(f"📋 {sym} 저장된 이벤트 ({len(events)}개)")
                print(f"{'=' * 50}")

                if not events:
                    print("저장된 이벤트가 없습니다.")
                    continue

                for event in events:
                    print(f"\n📌 {event['event_type']}")
                    print(f"   제목: {event['title']}")
                    print(f"   설명: {event['description']}")
                    print(f"   예상일: {event['expected_date'] if event['expected_date'] else 'TBD'}")
                    print(f"   상태: {event['status']}")
            except Exception as e:
                print(f"❌ 이벤트 조회 오류 ({sym}): {e}")

    def test_connection(self):
        """Supabase 연결 테스트"""
        try:
            response = self.supabase.table("companies").select("id").limit(1).execute()
            print(f"✅ Supabase 연결 성공!")
            return True
        except Exception as e:
            print(f"❌ Supabase 연결 실패: {e}")
            return False


# 실행
if __name__ == "__main__":
    fetcher = CompanyEventsFetcher(
        PERPLEXITY_API_KEY,
        supabase,
        SUPABASE_URL,
        SUPABASE_KEY
    )

    print("🔗 Supabase 연결 테스트 중...")
    if not fetcher.test_connection():
        print("\n⚠️  Supabase 연결에 실패했습니다.")
        print("URL과 API 키를 확인해주세요.")
        exit(1)

    # ====== 실행 ======
    # symbols만 입력하여 실행'
    symbols = ["JOBY", "COIN", "SYM"]
    nasdaq_100 = ['NVDA', 'MSFT', 'AAPL', 'GOOGL', 'AMZN', 'META', 'AVGO', 'TSLA', 'NFLX', 'COST', 'PEP', 
                  'AMD', 'CSCO', 'ADBE', 'TMUS', 'AMGN', 'INTC', 'QCOM', 'TXN', 'HON', 'SBUX', 'GILD', 'INTU', 
                  'MDLZ', 'BKNG', 'AMAT', 'ADP', 'LRCX', 'PDD', 'REGN', 'ISRG', 'MAR', 'CSX', 'PANW', 'SNPS', 'MU', 
                  'CDNS', 'MNST', 'NXPI', 'KDP', 'ORLY', 'PYPL', 'ABNB', 'FTNT', 'VRTX', 'AEP', 'ROST', 'WDAY', 
                  'PCAR', 'XEL', 'IDXX', 'CPRT', 'FAST', 'GEHC', 'MRNA', 'AXON', 'EXC', 'MCHP', 'DDOG', 'ZS', 
                  'ROP', 'CTAS', 'FANG', 'PAYX', 'LULU', 'DXCM', 'BIIB', 'ALNY', 'ON', 'ODFL', 'TTWO', 'CSGP', 
                  'WBD', 'TEAM', 'KHC', 'CEG', 'CTSH', 'ANSS', 'ILMN', 'BIDU', 'CHTR', 'EA', 'ETSY', 'INCY', 
                  'MDB', 'MRVL', 'RIVN', 'PCOR', 'LCID', 'VLTO', 'GFS', 'PLTR', 'APP', 'SHOP', 'ARM', 'CEVA', 'TTD']

    fetcher.fetch_and_save(nasdaq_100)

    # 저장된 이벤트 조회
    fetcher.display_saved_events(nasdaq_100)

    print("\n✅ 완료!")
