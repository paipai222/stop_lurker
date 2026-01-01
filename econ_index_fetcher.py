import os
import yfinance as yf
from supabase import create_client, Client
from dotenv import load_dotenv

# ✅ 1. .env 파일 로드 (이 코드가 없어서 URL을 못 찾았던 것)
load_dotenv()

# ✅ 2. 환경 변수 가져오기
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")  # 또는 SUPABASE_KEY

# ✅ 3. URL/Key 유효성 검사 (디버깅용)
if not url or not key:
    raise ValueError("❌ 환경 변수 오류: SUPABASE_URL 또는 SUPABASE_SERVICE_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

# ✅ 4. 클라이언트 생성
try:
    supabase: Client = create_client(url, key)
    print("✅ Supabase 연결 성공!")
except Exception as e:
    print(f"❌ Supabase 연결 실패: {e}")
    exit(1)

# 티커 매핑
tickers = {
    'SP500': '^GSPC',
    'NASDAQ': '^IXIC',
    'US20Y': '^TYX',  # 20년물 데이터가 없을 경우 30년물(^TYX) 사용
    'BTC': 'BTC-USD',
    'VIX': '^VIX',
    'GOLD': 'GC=F'
}

data_list = []

print("🔄 데이터 수집 시작...")

for symbol_name, ticker in tickers.items():
    try:
        t = yf.Ticker(ticker)
        # 당일 데이터 가져오기
        hist = t.history(period="5d")  # 넉넉하게 5일치 조회 (주말/휴일 고려)

        if len(hist) > 0:
            current_price = hist['Close'].iloc[-1]

            # 전일 종가 계산 (데이터가 2개 이상일 때만)
            if len(hist) > 1:
                prev_close = hist['Close'].iloc[-2]
            else:
                prev_close = current_price  # 데이터가 하나뿐이면 변동 없음 처리

            change = current_price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

            data_list.append({
                "symbol": symbol_name,
                "price": round(float(current_price), 2),
                "change": round(float(change), 2),
                "change_percent": round(float(change_pct), 2),
                "updated_at": "now()"  # Supabase가 인식하는 현재 시간
            })
            print(f"   Fetched {symbol_name}: {round(current_price, 2)} (Change: {round(change_pct, 2)}%)")
        else:
            print(f"⚠️ {symbol_name}: 데이터 없음")

    except Exception as e:
        print(f"❌ Error fetching {symbol_name}: {e}")

# 데이터 업서트 (Insert or Update)
if data_list:
    try:
        response = supabase.table("nyse_snapshot").upsert(data_list).execute()
        print(f"✅ 업데이트 완료: {len(data_list)}개 데이터 저장됨")
    except Exception as e:
        print(f"❌ DB 저장 실패: {e}")
else:
    print("⚠️ 저장할 데이터가 없습니다.")
