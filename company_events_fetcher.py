"""
회사 이벤트 데이터 수집 및 저장 모듈
Perplexity API로 이벤트를 조회하고 Supabase DB에 저장합니다.
"""

from supabase import create_client, Client
from dotenv import load_dotenv
import os
import requests
import json
import re
from typing import List, Union
from datetime import datetime

SP500 = ["INTU","INVH","IP","IPG","IQV","IR","IRM","ISRG","IT","ITW","IVZ","J","JBHT","JBL","JCI","JKHY","JNJ","JNPR","JPM","K","KDP","KEY","KEYS","KHC","KIM","KKR","KLAC","KMB","KMI","KMX","KO","KR","KVUE","L","LDOS","LEN","LH","LHX","LII","LIN","LKQ","LLY","LMT","LNT","LOW","LRCX","LULU","LUV","LVS","LW","LYB","LYV","MA","MAA","MAR","MAS","MCD","MCHP","MCK","MCO","MDLZ","MDT","MET","META","MGM","MHK","MKC","MKTX","MLM","MMC","MMM","MNST","MO","MOH","MOS","MPC","MPWR","MRK","MRNA","MS","MSCI","MSFT","MSI","MTB","MTCH","MTD","MU","NCLH","NDAQ","NDSN","NEE","NEM","NFLX","NI","NKE","NOC","NOW","NRG","NSC","NTAP","NTRS","NUE","NVDA","NVR","NWS","NWSA","NXPI","O","ODFL","OKE","OMC","ON","ORCL","ORLY","OTIS","OXY","PANW","PARA","PAYC","PAYX","PCAR","PCG","PEG","PEP","PFE","PFG","PG","PGR","PH","PHM","PKG","PLD","PLTR","PM","PNC","PNR","PNW","PODD","POOL","PPG","PPL","PRU","PSA","PSX","PTC","PWR","PYPL","QCOM","RCL","REG","REGN","RF","RJF","RL","RMD","ROK","ROL","ROP","ROST","RSG","RTX","RVTY","SBAC","SBUX","SCHW","SHW","SJM","SLB","SMCI","SNA","SNPS","SO","SOLV","SPG","SPGI","SRE","STE","STLD","STT","STX","STZ","SW","SWK","SWKS","SYF","SYK","SYY","T","TAP","TDG","TDY","TECH","TEL","TER","TFC","TGT","TJX","TKO","TMO","TMUS","TPL","TPR","TRGP","TRMB","TROW","TRV","TSCO","TSLA","TSN","TT","TTWO","TXN","TXT","TYL","UAL","UBER","UDR","UHS","ULTA","UNH","UNP","UPS","URI","USB","V","VICI","VLO","VLTO","VMC","VRSK","VRSN","VRTX","VST","VTR","VTRS","VZ","WAB","WAT","WBA","WBD","WDAY","WDC","WEC","WELL","WFC","WM","WMB","WMT","WRB","WSM","WST","WTW","WY","WYNN","XEL","XOM","XYL","YUM","ZBH","ZBRA","ZTS"]




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
# CompanyEventsFetcher 클래스
# ============================================
class CompanyEventsFetcher:
    """Perplexity API를 사용하여 회사 이벤트를 조회하고 DB에 저장하는 클래스"""

    def __init__(self, api_key, supabase_client):
        """
        Args:
            api_key (str): Perplexity API 키
            supabase_client (Client): Supabase 클라이언트
        """
        self.api_key = api_key
        self.supabase = supabase_client
        self.perplexity_url = "https://api.perplexity.ai/chat/completions"

    def insert_company(self, symbol: Union[str, List[str]], name: str = None):
        """
        회사 정보를 DB에 저장 또는 기존 회사 조회

        Args:
            symbol (str or list): 회사 티커 심볼 (단일 또는 리스트)
            name (str): 회사명 (선택사항)

        Returns:
            int or list: company_id (단일 심볼) 또는 company_id 리스트
        """
        if isinstance(symbol, list):
            symbols = symbol
        else:
            symbols = [symbol]

        company_ids = []

        for sym in symbols:
            try:
                # 기존 회사 확인
                # 기존 회사 존재시 symbol 추가 skip
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
        """
        Perplexity API로 회사 이벤트 조회

        Args:
            symbol (str): 회사 티커 심볼
            company_name (str): 회사명

        Returns:
            list: 이벤트 정보 리스트 (JSON 형식)
        """

        prompt = f"""
        {company_name} ({symbol})의 SEC filing과 News 찾아서 2026년 2월 주요 이벤트와 뉴스를 조사해줘.
        이벤트와 뉴스는 해당 회사에 영향을 줄 수 있는 모든 이벤트를 찾아줘.
        항상 요청된 JSON 형식으로만 응답해. 출처(Reuters, Yahoo Finance등)를 description에 포함해.
        이벤트와 뉴스는 최대한 자연스러운 한국어로 번역해서 description 을 작성해.

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
        """
        이벤트를 데이터베이스에 저장

        Args:
            company_id (int): 회사 ID
            events (list): 저장할 이벤트 리스트

        Returns:
            int: 저장된 이벤트 개수
        """
        if not company_id:
            print("❌ company_id가 없어서 저장 실패")
            return 0

        try:
            saved_count = 0
            for event in events:
                # 날짜는 YYYY-MM 형식으로 유지
                expected_date = None
                if event.get('expected_date') and event['expected_date'] not in ['TBD', 'Unknown']:
                    date_str = event['expected_date'].strip()
                    # YYYY-MM 형식 검증
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
                    "expected_date": expected_date,
                    "status": event.get('status', 'Pending'),
                    "source": "Perplexity AI"
                }).execute()

                saved_count += 1

            print(f"✅ {saved_count}개 이벤트 저장 완료")
            return saved_count
        except Exception as e:
            print(f"❌ DB 저장 오류: {e}")
            return 0

    def fetch_and_save(self, symbols: Union[str, List[str]]):
        """
        전체 프로세스 실행 (회사 저장 → 이벤트 조회 → DB 저장)

        Args:
            symbols (str or list): 조회할 회사 티커 심볼 (단일 또는 리스트)

        Returns:
            list: 각 심볼별 처리 결과 (True/False)
        """
        if isinstance(symbols, str):
            symbol_list = [symbols]
        else:
            symbol_list = symbols

        results = []

        for sym in symbol_list:
            print(f"\n{'=' * 50}")
            print(f"🔍 {sym} 처리 중...")
            print(f"{'=' * 50}")

            # 1. 회사 정보 저장 또는 조회
            company_id = self.insert_company(sym)

            if not company_id:
                print(f"❌ 회사 저장 실패")
                results.append(False)
                continue

            # 2. 이벤트 조회
            events = self.fetch_events_from_perplexity(sym, sym)

            if events:
                # 3. DB에 저장
                self.save_events_to_db(company_id, events)
                results.append(True)
            else:
                print(f"⚠️  이벤트를 찾을 수 없음")
                results.append(False)

        return results


# ============================================
# 스탠드얼론 실행 코드
# ============================================
if __name__ == "__main__":
    """
    이 파일을 직접 실행할 때의 코드
    
    사용 예시:
    python company_events_fetcher.py
    
    또는 다른 파일에서 import해서 사용:
    from company_events_fetcher import CompanyEventsFetcher, supabase
    
    fetcher = CompanyEventsFetcher(api_key, supabase)
    fetcher.fetch_and_save(['AAPL', 'MSFT'])
    """


    print("=" * 50)
    print("🚀 Company Events Fetcher 시작")
    print("=" * 50)

    # Perplexity API 키 확인
    if not PERPLEXITY_API_KEY:
        print("❌ PERPLEXITY_API_KEY가 설정되지 않았습니다.")
        exit(1)

    # CompanyEventsFetcher 인스턴스 생성
    fetcher = CompanyEventsFetcher(PERPLEXITY_API_KEY, supabase)

    # 조회할 회사 심볼 (여기서 수정해서 사용)
    symbols_to_fetch = ['COIN','JOBY','ACHR']  # 예시: Apple, Microsoft

    print(f"\n📊 조회할 회사: {symbols_to_fetch}")
    print("=" * 50)

    # 데이터 수집 및 저장 실행
    results = fetcher.fetch_and_save(SP500) # 또는 symbols_to_fetch 로 manual ticker 가능

    print("\n" + "=" * 50)
    print("✅ 처리 완료")
    print(f"결과: {results}")
    print("=" * 50)
