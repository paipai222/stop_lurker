# test_supabase_connection.py
import sys
import traceback

print("=" * 60)
print("🔍 Supabase 연결 테스트")
print("=" * 60)

# 1. 라이브러리 임포트 테스트
print("\n1️⃣ 라이브러리 임포트 테스트...")
try:
    from supabase import create_client, Client
    print("✅ supabase 라이브러리 임포트 성공")
except Exception as e:
    print(f"❌ supabase 임포트 실패: {e}")
    traceback.print_exc()
    sys.exit(1)

# 2. 연결 정보
print("\n2️⃣ 연결 정보 확인...")
SUPABASE_URL = "https://hinbnwvgdwolvoobrahh.supabase.co"
SUPABASE_KEY = "sb_publishable_ErYV_iUeSANJ1Ecm11GE_w_p0Z9_wDF"

print(f"   URL: {SUPABASE_URL}")
print(f"   KEY (처음 20자): {SUPABASE_KEY[:20]}...")

# 3. 클라이언트 생성 테스트
print("\n3️⃣ 클라이언트 생성 시도...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"✅ 클라이언트 생성 성공")
    print(f"   타입: {type(supabase)}")
    print(f"   객체: {supabase}")
except Exception as e:
    print(f"❌ 클라이언트 생성 실패")
    print(f"   에러 타입: {type(e).__name__}")
    print(f"   에러 메시지: {str(e)}")
    print("\n📋 전체 에러:")
    traceback.print_exc()
    sys.exit(1)

# 4. 간단한 쿼리 테스트
print("\n4️⃣ 데이터베이스 쿼리 테스트...")
try:
    response = supabase.table("companies").select("*").limit(1).execute()
    print(f"✅ 쿼리 성공!")
    print(f"   반환된 행 수: {len(response.data)}")
    if response.data:
        print(f"   샘플 데이터: {response.data[0]}")
except Exception as e:
    print(f"❌ 쿼리 실패")
    print(f"   에러 타입: {type(e).__name__}")
    print(f"   에러 메시지: {str(e)}")
    print("\n📋 전체 에러:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ 모든 테스트 통과!")
print("=" * 60)
