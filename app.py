from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import traceback
import json
from datetime import datetime

# 커스텀 모듈 import
try:
    from company_events_fetcher import CompanyEventsFetcher, supabase, PERPLEXITY_API_KEY
except ImportError:
    print("⚠️ company_events_fetcher 모듈을 찾을 수 없습니다.")
    supabase = None
    PERPLEXITY_API_KEY = None

# ✅ 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_FILE)

# 템플릿 및 정적 파일 경로 설정
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Flask 앱 초기화
app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR,
            static_url_path='/static')

CORS(app)

print("=" * 50)
print("✅ Flask 앱 초기화 완료")
print("=" * 50)


# ============================================
# 헬퍼 함수
# ============================================
def map_event_type(event_type):
    """DB의 event_type을 HTML의 카테고리로 매핑"""
    mapping = {
        'Product Launch': '제품 출시',
        'Legislation': '규제/정책',
        'Earnings': '실적',
        'M&A': '기타',
        'Other': '기타'
    }
    return mapping.get(event_type, '기타')


def map_status(status):
    """상태명 정규화"""
    status_mapping = {
        'Pending': '대기중',
        'In Progress': '진행중',
        'Not Started': '대기중',
        'Completed': '완료'
    }
    return status_mapping.get(status, 'Pending')


def get_icon_for_category(category):
    """카테고리별 이모지 아이콘 반환 (한글 카테고리명 기반)"""
    icons = {
        '제품 출시': '🚀',
        '규제/정책': '⚖️',
        '실적': '📊',
        '기타': '📦'
    }
    return icons.get(category, '📌')


# ============================================
# 메인 페이지 라우트
# ============================================
@app.route('/')
def index():
    """메인 페이지 제공"""
    return render_template('index.html')


# ============================================
# API 엔드포인트 - 회사 이벤트
# ============================================

@app.route('/api/events', methods=['GET'])
def get_events():
    """
    Supabase에서 이벤트 조회 (검색 & 필터링 기능)
    쿼리 파라미터:
    - company: ticker 또는 회사명 기준 검색 (부분 일치 지원)
    - category: 카테고리별 필터링 (product-launch, legislation, earnings, etc)
    """
    try:
        # Supabase 연결 체크
        if supabase is None:
            return jsonify({'error': 'Supabase not connected'}), 503

        # 쿼리 파라미터에서 검색어와 카테고리 받기
        search_query = request.args.get('company', '').strip()
        category_filter = request.args.get('category', '').strip()

        print(f"🔍 검색어: '{search_query}', 카테고리 필터: '{category_filter}'")

        # ✅ 페이지네이션을 사용하여 모든 데이터 가져오기
        all_events = []
        page_size = 1000
        offset = 0

        while True:
            response = supabase.table("company_events").select(
                "id, company_id, event_type, title, description, expected_date, status, "
                "companies(id, symbol, name)"
            ).range(offset, offset + page_size - 1).execute()

            if not response.data:
                break

            all_events.extend(response.data)

            # 마지막 페이지인지 확인
            if len(response.data) < page_size:
                break

            offset += page_size

        print(f"📊 총 조회된 이벤트: {len(all_events)}개")

        # 검색어와 카테고리 필터링 (파이썬 레벨)
        filtered_events = []

        for event in all_events:
            if not event.get('companies'):
                continue

            comp_data = event['companies']
            symbol = comp_data.get('symbol', '').upper()
            name = comp_data.get('name', '').upper()
            event_category = map_event_type(event['event_type'])

            # 검색어 필터 확인
            search_match = True
            if search_query:
                query_upper = search_query.upper()
                search_match = query_upper in symbol or query_upper in name

            # 카테고리 필터 확인
            category_match = True
            if category_filter and category_filter != 'all':
                # 프론트에서 보내는 영문을 한글로 매핑
                category_mapping = {
                    'product-launch': '제품 출시',
                    'legislation': '규제/정책',
                    'earnings': '실적',
                    'etc': '기타',
                    'mna': '기타',
                    'other': '기타'
                }
                korean_category = category_mapping.get(category_filter, category_filter)
                category_match = event_category == korean_category

            # 두 필터 모두 통과해야 결과에 추가
            if search_match and category_match:
                filtered_events.append(event)

        # ✅ 날짜순 정렬 (과거→미래)
        def sort_key(event):
            date_str = event.get('expected_date')
            if not date_str or date_str == 'TBD':
                return ('9999-12-31', '')
            try:
                return (date_str, '')
            except:
                return ('9999-12-31', '')

        filtered_events.sort(key=sort_key)

        print(f"✅ 필터링 결과: {len(filtered_events)}개 이벤트 (시간순 정렬 완료)")

        # 프론트엔드용 포맷팅
        formatted_events = []
        for event in filtered_events:
            comp_info = event.get('companies') or {}
            company_symbol = comp_info.get('symbol', 'Unknown')
            company_name = comp_info.get('name', 'Unknown')

            formatted_events.append({
                'id': event['id'],
                'category': map_event_type(event['event_type']),
                'company': company_symbol,
                'companyName': company_name,
                'icon': get_icon_for_category(map_event_type(event['event_type'])),
                'title': event['title'],
                'description': event['description'],
                'date': event['expected_date'] if event['expected_date'] else 'TBD',
                'status': map_status(event['status'])
            })

        return jsonify(formatted_events)

    except Exception as e:
        print(f"❌ Error in get_events: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'error_type': type(e).__name__}), 500
@app.route('/api/fetch-events', methods=['POST'])
def fetch_events_endpoint():
    """Perplexity API로 이벤트 데이터를 가져와 저장"""
    try:
        data = request.json
        symbols = data.get('symbols', [])

        if not symbols:
            return jsonify({'error': 'symbols 필드가 필요합니다'}), 400

        if isinstance(symbols, str):
            symbols = [symbols]

        fetcher = CompanyEventsFetcher(PERPLEXITY_API_KEY, supabase)
        results = fetcher.fetch_and_save(symbols)

        all_events = supabase.table("company_events").select("*").execute()

        return jsonify({
            'status': 'success',
            'message': f'{len(symbols)}개 회사 데이터 수집 완료',
            'results': results,
            'total_events': len(all_events.data)
        }), 200

    except Exception as e:
        print(f"❌ Error in fetch_events_endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/fetch-single', methods=['POST'])
def fetch_single_event():
    """단일 회사의 이벤트 데이터를 가져와 저장"""
    try:
        data = request.json
        symbol = data.get('symbol')

        if not symbol:
            return jsonify({'error': 'symbol 필드가 필요합니다'}), 400

        fetcher = CompanyEventsFetcher(PERPLEXITY_API_KEY, supabase)
        fetcher.fetch_and_save(symbol)

        return jsonify({
            'status': 'success',
            'message': f'{symbol} 데이터 수집 완료',
            'symbol': symbol
        }), 200

    except Exception as e:
        print(f"❌ Error in fetch_single_event: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/events', methods=['POST'])
def create_event():
    """새로운 이벤트 수동 생성"""
    try:
        data = request.json
        required_fields = ['company_id', 'event_type', 'title']

        if not all(field in data for field in required_fields):
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
        return jsonify({'message': 'Event created successfully', 'data': response.data}), 201

    except Exception as e:
        print(f"❌ Error in create_event: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    """이벤트 수정"""
    try:
        data = request.json
        response = supabase.table("company_events").update(data).eq("id", event_id).execute()
        return jsonify({'message': 'Event updated successfully', 'data': response.data})
    except Exception as e:
        print(f"❌ Error in update_event: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    """이벤트 삭제"""
    try:
        response = supabase.table("company_events").delete().eq("id", event_id).execute()
        return jsonify({'message': 'Event deleted successfully'})
    except Exception as e:
        print(f"❌ Error in delete_event: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============================================
# API 엔드포인트 - 경제지표
# ============================================

@app.route('/api/economic-indicators', methods=['GET'])
def get_economic_indicators():
    """
    경제지표 조회 API
    """
    try:
        if supabase is None:
            return jsonify({'error': 'Supabase not connected'}), 503

        # 쿼리 파라미터 받기
        min_date = request.args.get('minDate', '').strip()
        max_date = request.args.get('maxDate', '').strip()
        year_month = request.args.get('month', '').strip()
        limit = request.args.get('limit', 10, type=int)

        print(f"🔍 경제지표 조회: minDate={min_date}, maxDate={max_date}, month={year_month}, limit={limit}")

        # 쿼리 빌더 시작
        query = supabase.table("econ_calendar").select(
            "id, announcement_date, day, indicator, previous_value, consensus, category, market_impact"
        )

        if min_date:
            query = query.gte("announcement_date", min_date)

        if max_date:
            query = query.lte("announcement_date", max_date)

        if not min_date and not max_date:
            if not year_month:
                today = datetime.now()
                year_month = today.strftime("%Y-%m")
            query = query.gte("announcement_date", f"{year_month}-01").lte(
                "announcement_date", f"{year_month}-31"
            )

        # 정렬 및 제한
        response = query.order("announcement_date", desc=False).limit(limit).execute()

        indicators = response.data

        print(f"✅ 경제지표 조회 완료: {len(indicators)}개")

        formatted_indicators = []
        for ind in indicators:
            formatted_indicators.append({
                'id': ind.get('id'),
                'announcement_date': ind.get('announcement_date'),
                'day': ind.get('day', ''),
                'indicator': ind.get('indicator'),
                'previous_value': ind.get('previous_value') or '-',
                'consensus': ind.get('consensus') or '-',
                'category': ind.get('category') or 'Other',
                'market_impact': ind.get('market_impact') or ''
            })

        return jsonify({
            'status': 'success',
            'count': len(formatted_indicators),
            'indicators': formatted_indicators
        }), 200

    except Exception as e:
        print(f"❌ Error in get_economic_indicators: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'error_type': type(e).__name__}), 500


# ============================================
# API 엔드포인트 - 마켓 스냅샷 (수정된 로직)
# ============================================

@app.route('/api/market-snapshot', methods=['GET'])
def get_market_snapshot():
    """
    Supabase nyse_snapshot 테이블에서
    각 심볼별(SP500, NASDAQ, US20Y, BTC, VIX, GOLD) 최신 데이터를 조회하여 합침
    """
    try:
        if supabase is None:
            return jsonify({'error': 'Supabase not connected'}), 503

        # DB에 저장된 실제 심볼명 리스트 (로그 확인됨: SP500)
        target_symbols = ['SP500', 'NASDAQ', 'US20Y', 'BTC', 'VIX', 'GOLD']

        final_data = {}
        latest_update = None

        print("🔍 마켓 스냅샷 개별 조회 시작...")

        for symbol in target_symbols:
            try:
                # 각 심볼별로 가장 최신(updated_at 기준) 1개를 가져옴
                resp = supabase.table("nyse_snapshot") \
                    .select("*") \
                    .eq('symbol', symbol) \
                    .order('updated_at', desc=True) \
                    .limit(1) \
                    .execute()

                # 프론트엔드용 소문자 키 (sp500, nasdaq...)
                key_map = symbol.lower()

                if resp.data and len(resp.data) > 0:
                    row = resp.data[0]

                    final_data[key_map] = {
                        "value": row.get('price'),  # DB 컬럼: price
                        "change": row.get('change'),  # DB 컬럼: change
                        "changepct": row.get('change_percent')  # DB 컬럼: change_percent
                    }

                    # 가장 최근 업데이트 시간 추적
                    current_update = row.get('updated_at')
                    if current_update:
                        if latest_update is None or current_update > (latest_update or ""):
                            latest_update = current_update
                else:
                    # 데이터가 없는 경우 빈 값 처리
                    final_data[key_map] = {"value": None, "change": None, "changepct": None}

            except Exception as e:
                print(f"⚠️ {symbol} 조회 실패: {e}")
                final_data[symbol.lower()] = {"value": None, "change": None, "changepct": None}

        print("🔥 [DEBUG] 최종 조합된 데이터:", final_data)

        return jsonify({
            "status": "success",
            "updatedat": latest_update,
            "data": final_data
        }), 200

    except Exception as e:
        print(f"❌ Error in get_market_snapshot: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# 헬스 체크
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    if supabase is None:
        return jsonify({'status': 'WARNING', 'message': 'Supabase not connected'}), 200
    return jsonify({'status': 'OK', 'message': 'Server is running', 'supabase': 'connected'}), 200


# 에러 핸들링
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('index.html'), 200


@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('index.html'), 500


# ============================================
# 서버 실행 (Render 배포용 설정)
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Server Starting...")
    print("=" * 50)

    # Render 또는 클라우드 환경에서 제공하는 PORT 사용 (기본값 5000)
    # Render에서 PORT 환경변수 감지
    # 배포 환경에서는 debug=False로 설정
    # host='0.0.0.0'은 외부 접속을 허용하기 위해 필수
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
