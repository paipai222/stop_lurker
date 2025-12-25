# app.py (새로운 파일)
from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import create_client, Client
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Supabase 클라이언트
SUPABASE_URL = "https://hinbnwvgdwolvoobrahh.supabase.co"
SUPABASE_KEY = "ur key"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/api/events', methods=['GET'])
def get_events():
    """Supabase에서 모든 이벤트 조회"""
    try:
        # 회사와 이벤트 조인
        response = supabase.table("company_events").select(
            "id, company_id, event_type, title, description, expected_date, status, "
            "companies(symbol, name)"
        ).execute()
        
        events = response.data
        
        # 데이터 변환 (HTML/JS가 기대하는 형식으로)
        formatted_events = []
        for event in events:
            company_symbol = event['companies']['symbol'] if event['companies'] else 'Unknown'
            
            formatted_events.append({
                'id': event['id'],
                'category': map_event_type(event['event_type']),
                'company': company_symbol,
                'icon': get_icon_for_category(map_event_type(event['event_type'])),
                'title': event['title'],
                'description': event['description'],
                'date': event['expected_date'] if event['expected_date'] else 'TBD',
                'status': map_status(event['status'])
            })
        
        return jsonify(formatted_events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def map_event_type(event_type):
    """DB의 event_type을 HTML의 카테고리로 변환"""
    mapping = {
        'Legislation': 'legislation',
        'Product Launch': 'product-launch',
        'Earnings': 'earnings',
        'M&A': 'mna',
        'Other': 'other'
    }
    return mapping.get(event_type, 'other')

def map_status(status):
    """상태 명칭 정규화"""
    status_mapping = {
        'Pending': 'Pending',
        'In Progress': 'In Progress',
        'Not Started': 'Not Started',
        'Completed': 'Completed'
    }
    return status_mapping.get(status, 'Pending')

def get_icon_for_category(category):
    """카테고리별 아이콘 반환"""
    icons = {
        'product-launch': '🚀',
        'legislation': '⚖️',
        'earnings': '📊',
        'mna': '🤝',
        'other': '📢'
    }
    return icons.get(category, '📌')

@app.route('/api/events/month/<int:year>/<int:month>', methods=['GET'])
def get_events_by_month(year, month):
    """특정 월의 이벤트만 조회"""
    try:
        response = supabase.table("company_events").select(
            "id, company_id, event_type, title, description, expected_date, status, "
            "companies(symbol, name)"
        ).execute()
        
        events = response.data
        month_events = []
        
        for event in events:
            if event['expected_date']:
                event_year, event_month = event['expected_date'].split('-')
                if int(event_year) == year and int(event_month) == month:
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
        
        return jsonify(month_events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
