"""
Flask 백엔드 (Render 배포용 수정 버전)
company_events_fetcher.py 모듈을 import해서 사용합니다.
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import traceback

# 커스텀 모듈 import
try:
    from company_events_fetcher import CompanyEventsFetcher, supabase, PERPLEXITY_API_KEY
except ImportError:
    print("⚠️ company_events_fetcher 모듈을 찾을 수 없습니다.")
    supabase = None
    PERPLEXITY_API_KEY = None

# ✅ 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, '../.env')
load_dotenv(ENV_FILE)

# 템플릿 및 정적 파일 경로 설정
TEMPLATE_DIR = os.path.join(BASE_DIR, '../templates')
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
def get_events():
    """
    Supabase에서 이벤트 조회 (검색 기능 강화)
    쿼리 파라미터:
    - company: ticker 또는 회사명 기준 검색 (부분 일치 지원)
    """
    try:
        # Supabase 연결 체크
        if supabase is None:
            return jsonify({'error': 'Supabase not connected'}), 503

        # 쿼리 파라미터에서 검색어 받기
        search_query = request.args.get('company', '').strip()

        # company_events와 companies 테이블 JOIN해서 전체 조회
        response = supabase.table("company_events").select(
            "id, company_id, event_type, title, description, expected_date, status, "
            "companies(id, symbol, name)"
        ).execute()

        events = response.data

        # 검색어가 있으면 파이썬 레벨에서 필터링
        if search_query:
            query_upper = search_query.upper()
            filtered_events = []

            for event in events:
                if not event.get('companies'):
                    continue

                comp_data = event['companies']
                symbol = comp_data.get('symbol', '').upper()
                name = comp_data.get('name', '').upper()

                # 검색어가 심볼이나 이름에 포함되어 있으면 결과에 추가
                if query_upper in symbol or query_upper in name:
                    filtered_events.append(event)

            events = filtered_events

        # 프론트엔드용 포맷팅
        formatted_events = []
        for event in events:
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
    port = int(os.environ.get("PORT", 5000))

    # 배포 환경에서는 debug=False로 설정
    # host='0.0.0.0'은 외부 접속을 허용하기 위해 필수
    app.run(host='0.0.0.0', port=port, debug=False)
