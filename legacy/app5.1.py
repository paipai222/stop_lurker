from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os

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

# ============================================
# 메인 페이지 라우트
# ============================================
@app.route('/')
def index():
    """메인 페이지 제공"""
    return render_template('index.html')

# ============================================
# 헬스 체크
# ============================================
@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({'status': 'OK', 'message': 'Server is running'}), 200

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
# 서버 실행
# ============================================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
