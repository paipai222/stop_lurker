# Flask back-end
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from datetime import datetime
import requests
import json
import re
from typing import List, Union

# 환경 변수 로드
load_dotenv(r'C:\project\fishon\.env')

# 기본 디렉토리 설정 (절대 경로)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Flask 앱 초기화
app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR,
            static_url_path='/static')
CORS(app)

# ============================================
# API 키 및 Supabase 설정
# ============================================
print("=" * 50)
print("🔍 API 키 및 Supabase 환경 변수 확인")
print("=" * 50)

SUPABASE_URL = "ur_supabase_url"
#SUPABASE KEY 를 SERVICE ROLE 로 변경 (FLASK BACKEND PURPOSE)
SUPABASE_KEY = "ur supabase_service_role_key"
PERPLEXITY_API_KEY = "ur_perplexity_api_key"

print(f"✅ SUPABASE_URL: {SUPABASE_URL}")
print(f"✅ SUPABASE_KEY: {SUPABASE_KEY[:30]}...")
print(f"✅ PERPLEXITY_API_KEY: {PERPLEXITY_API_KEY[:20]}...")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase 클라이언트 연결 성공")
except Exception as e:
    print(f"❌ Supabase 클라이언트 연결 실패: {str(e)}")
    supabase = None

print("=" * 50)


# ============================================
# CompanyEventsFetcher 클래스
# ============================================
class CompanyEventsFetcher:
    def __init__(self, api_key, supabase_client):
        self.api_key = api_key
        self.supabase = supabase_client
        self.perplexity_url = "https://api.perplexity.ai/chat/completions"

    def insert_company(self, symbol: Union[str, List[str]], name: str = None):
        """회사 정보를 DB에 저장"""
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
        """전체 프로세스 실행"""
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
# 메인 페이지 라우트
# ============================================
@app.route('/')
def index():
    """메인 페이지 제공"""
    return render_template('index.html')


# ============================================
# API 엔드포인트
# ============================================

@app.route('/api/events', methods=['GET'])
@app.route('/api/events', methods=['GET'])
def get_events():
    """
    Supabase에서 이벤트 조회
    쿼리 파라미터:
    - company: ticker 기준 필터링 (선택사항)
    """
    try:
        print("=" * 50)
        print("📡 /api/events 호출됨")
        print("=" * 50)

        if supabase is None:
            return jsonify({'error': 'Supabase not connected'}), 503

        # 쿼리 파라미터에서 회사 필터 받기
        company_filter = request.args.get('company', None)

        print(f"🔍 요청 파라미터 - company: {company_filter}")

        # company_events와 companies 테이블 JOIN해서 조회
        response = supabase.table("company_events").select(
            "id, company_id, event_type, title, description, expected_date, status, "
            "companies(id, symbol, name)"
        ).execute()

        events = response.data

        # company 파라미터가 있으면 필터링
        if company_filter:
            print(f"🔍 {company_filter}로 필터링 중...")
            filtered_events = [
                event for event in events
                if event['companies'] and
                   event['companies']['symbol'].upper() == company_filter.upper()
            ]
            events = filtered_events
            print(f"✅ 필터링 결과: {len(events)}개 이벤트")
        else:
            print(f"✅ 전체 조회: {len(events)}개 이벤트")

        # HTML/JavaScript가 기대하는 형식으로 변환
        formatted_events = []
        for event in events:
            company_symbol = event['companies']['symbol'] if event['companies'] else 'Unknown'
            company_name = event['companies']['name'] if event['companies'] else 'Unknown'

            formatted_events.append({
                'id': event['id'],
                'category': map_event_type(event['event_type']),
                'company': company_symbol,
                'icon': get_icon_for_category(map_event_type(event['event_type'])),
                'title': event['title'],
                'description': event['description'],
                'date': event['expected_date'] if event['expected_date'] else 'TBD',
                'status': map_status(event['status']),
                'companyName': company_name
            })

        print(f"✅ 포맷팅 완료: {len(formatted_events)}개 이벤트")
        return jsonify(formatted_events)

    except Exception as e:
        print(f"❌ Error in get_events: {str(e)}")
        print(f"❌ 에러 타입: {type(e).__name__}")
        print("❌ 전체 에러:")
        traceback.print_exc()
        return jsonify({'error': str(e), 'error_type': type(e).__name__}), 500


@app.route('/api/fetch-events', methods=['POST'])
def fetch_events_endpoint():
    """Perplexity API로 이벤트 데이터를 가져와 저장"""
    try:
        print("=" * 50)
        print("📡 /api/fetch-events 호출됨")
        print("=" * 50)

        # 요청에서 symbols 받기
        data = request.json
        symbols = data.get('symbols', [])

        if not symbols:
            return jsonify({'error': 'symbols 필드가 필요합니다'}), 400

        if isinstance(symbols, str):
            symbols = [symbols]

        print(f"🔍 요청 symbols: {symbols}")

        # CompanyEventsFetcher 인스턴스 생성
        fetcher = CompanyEventsFetcher(PERPLEXITY_API_KEY, supabase)

        # 데이터 수집 및 저장
        results = fetcher.fetch_and_save(symbols)

        # 저장된 이벤트 조회
        all_events = supabase.table("company_events").select("*").execute()

        return jsonify({
            'status': 'success',
            'message': f'{len(symbols)}개 회사 데이터 수집 완료',
            'symbols_processed': symbols,
            'results': results,
            'total_events': len(all_events.data)
        }), 200

    except Exception as e:
        print(f"❌ Error in fetch_events_endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/fetch-single', methods=['POST'])
def fetch_single_event():
    """단일 회사의 이벤트 데이터를 가져와 저장"""
    try:
        print("=" * 50)
        print("📡 /api/fetch-single 호출됨")
        print("=" * 50)

        data = request.json
        symbol = data.get('symbol')

        if not symbol:
            return jsonify({'error': 'symbol 필드가 필요합니다'}), 400

        print(f"🔍 요청 symbol: {symbol}")

        fetcher = CompanyEventsFetcher(PERPLEXITY_API_KEY, supabase)
        fetcher.fetch_and_save(symbol)

        return jsonify({
            'status': 'success',
            'message': f'{symbol} 데이터 수집 완료',
            'symbol': symbol
        }), 200

    except Exception as e:
        print(f"❌ Error in fetch_single_event: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/events/month/<int:year>/<int:month>', methods=['GET'])
def get_events_by_month(year, month):
    """특정 월의 이벤트만 조회"""
    try:
        print(f"📡 /api/events/month/{year}/{month} 호출됨")

        response = supabase.table("company_events").select(
            "id, company_id, event_type, title, description, expected_date, status, "
            "companies(symbol, name)"
        ).execute()

        events = response.data
        month_events = []

        for event in events:
            if event['expected_date']:
                date_parts = event['expected_date'].split('-')
                if len(date_parts) >= 2:
                    try:
                        event_year = int(date_parts[0])
                        event_month = int(date_parts[1])

                        if event_year == year and event_month == month:
                            company_symbol = event['companies']['symbol'] if event['companies'] else 'Unknown'
                            month_events.append({
                                'id': event['id'],
                                'category': map_event_type(event['event_type']),
                                'company': company_symbol,
                                'icon': get_icon_for_category(map_event_type(event['event_type'])),
                                'title': event['title'],
                                'description': event['description'],
                                'date': event['expected_date'],
                                'status': map_status(event['status'])
                            })
                    except ValueError:
                        continue

        print(f"✅ {year}년 {month}월: {len(month_events)}개 이벤트")
        return jsonify(month_events)
    except Exception as e:
        print(f"❌ Error in get_events_by_month: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/events', methods=['POST'])
def create_event():
    """새로운 이벤트 생성"""
    try:
        print("📝 POST /api/events 호출됨")
        data = request.json
        print(f"🔍 요청 데이터: {data}")

        required_fields = ['company_id', 'event_type', 'title']
        if not all(field in data for field in required_fields):
            print(f"❌ 필수 필드 누락: {required_fields}")
            return jsonify({'error': 'Missing required fields'}), 400

        new_event = {
            'company_id': data.get('company_id'),
            'event_type': data.get('event_type'),
            'title': data.get('title'),
            'description': data.get('description', ''),
            'expected_date': data.get('expected_date'),
            'status': data.get('status', 'Pending')
        }

        response = supabase.table("company_events").insert(new_event).execute()

        print(f"✅ 이벤트 생성 완료: {response.data}")

        return jsonify({
            'message': 'Event created successfully',
            'data': response.data
        }), 201

    except Exception as e:
        print(f"❌ Error in create_event: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    """이벤트 수정"""
    try:
        print(f"✏️ PUT /api/events/{event_id} 호출됨")
        data = request.json

        response = supabase.table("company_events").update(data).eq("id", event_id).execute()

        print(f"✅ 이벤트 수정 완료: {event_id}")

        return jsonify({
            'message': 'Event updated successfully',
            'data': response.data
        })

    except Exception as e:
        print(f"❌ Error in update_event: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    """이벤트 삭제"""
    try:
        print(f"🗑️ DELETE /api/events/{event_id} 호출됨")

        response = supabase.table("company_events").delete().eq("id", event_id).execute()

        print(f"✅ 이벤트 삭제 완료: {event_id}")

        return jsonify({'message': 'Event deleted successfully'})

    except Exception as e:
        print(f"❌ Error in delete_event: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============================================
# 헬퍼 함수
# ============================================

def map_event_type(event_type):
    """DB의 event_type을 HTML의 카테고리로 매핑"""
    mapping = {
        'Product Launch': 'product-launch',
        'Legislation': 'legislation',
        'Earnings': 'earnings',
        'M&A': 'mna',
        'Other': 'other'
    }
    return mapping.get(event_type, 'other')


def map_status(status):
    """상태명 정규화"""
    status_mapping = {
        'Pending': 'Pending',
        'In Progress': 'In Progress',
        'Not Started': 'Not Started',
        'Completed': 'Completed'
    }
    return status_mapping.get(status, 'Pending')


def get_icon_for_category(category):
    """카테고리별 이모지 아이콘 반환"""
    icons = {
        'product-launch': '🚀',
        'legislation': '⚖️',
        'earnings': '📊',
        'mna': '🤝',
        'other': '📢'
    }
    return icons.get(category, '📌')


# ============================================
# 헬스 체크 및 디버그 API
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    print("💚 /api/health 호출됨")
    if supabase is None:
        return jsonify({'status': 'WARNING', 'message': 'Server running but Supabase not connected'}), 200
    return jsonify({'status': 'OK', 'message': 'Server is running', 'supabase': 'connected'}), 200


@app.route('/api/debug/tables', methods=['GET'])
def debug_tables():
    """데이터베이스 테이블 데이터 확인"""
    try:
        print("🔍 데이터베이스 구조 확인 요청")

        # 1. company_events 테이블 데이터
        print("\n📊 company_events 테이블:")
        events_raw = supabase.table("company_events").select("*").execute()
        print(f"   데이터 개수: {len(events_raw.data)}")

        # 2. companies 테이블 데이터
        print("\n📊 companies 테이블:")
        companies_raw = supabase.table("companies").select("*").execute()
        print(f"   데이터 개수: {len(companies_raw.data)}")
        print(f"   샘플: {companies_raw.data[:3] if companies_raw.data else 'Empty'}")

        return jsonify({
            'company_events_count': len(events_raw.data),
            'companies_count': len(companies_raw.data),
            'companies_sample': companies_raw.data[:3] if companies_raw.data else [],
            'events_by_company': len(events_raw.data)
        }), 200
    except Exception as e:
        print(f"❌ 디버그 오류: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ============================================
# 에러 핸들링
# ============================================

@app.errorhandler(404)
def not_found(error):
    print(f"⚠️ 404 Not Found: {request.path}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('index.html'), 200


@app.errorhandler(500)
def internal_error(error):
    print(f"🔴 500 Internal Server Error: {error}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('index.html'), 500


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Flask 서버 시작 중...")
    print("=" * 50)
    print(f"📁 Base Directory: {BASE_DIR}")
    print(f"📁 Template Folder: {TEMPLATE_DIR}")
    print(f"📁 Static Folder: {STATIC_DIR}")
    print(f"✅ Templates 존재: {os.path.exists(TEMPLATE_DIR)}")
    print(f"✅ Static 존재: {os.path.exists(STATIC_DIR)}")
    print("=" * 50)
    print("📍 접속 주소: http://localhost:5000")
    print("📍 데이터 수집: POST http://localhost:5000/api/fetch-events")
    print("=" * 50)
    app.run(debug=True, port=5000, host='0.0.0.0')
