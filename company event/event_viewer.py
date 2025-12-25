# view_events.py
from supabase import create_client, Client

# API 키 설정
SUPABASE_URL = "ur url"
SUPABASE_KEY = "ur key"

# Supabase 클라이언트 생성
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class EventViewer:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def view_company_events(self, symbol):
        """특정 회사의 저장된 이벤트 조회"""
        try:
            # company_id 조회
            company_response = self.supabase.table("companies").select("id, name").eq("symbol", symbol).execute()

            if not company_response.data:
                print(f"❌ '{symbol}' 회사를 찾을 수 없습니다.")
                return

            company_id = company_response.data[0]["id"]
            company_name = company_response.data[0]["name"]

            # 이벤트 조회
            events_response = self.supabase.table("company_events").select(
                "id, event_type, title, description, expected_date, status, created_at"
            ).eq("company_id", company_id).order("expected_date", desc=False).execute()

            events = events_response.data

            # 출력
            print(f"\n{'=' * 60}")
            print(f"📊 {company_name} ({symbol}) - 저장된 이벤트")
            print(f"{'=' * 60}")
            print(f"총 {len(events)}개 이벤트\n")

            if not events:
                print("저장된 이벤트가 없습니다.")
                return

            # 카테고리별로 그룹화
            events_by_type = {}
            for event in events:
                event_type = event['event_type']
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                events_by_type[event_type].append(event)

            # 카테고리별 출력
            for event_type in sorted(events_by_type.keys()):
                print(f"\n📌 {event_type}")
                print(f"{'-' * 60}")

                for event in events_by_type[event_type]:
                    print(f"  제목: {event['title']}")
                    print(f"  설명: {event['description']}")
                    print(f"  예상일: {event['expected_date'] if event['expected_date'] else 'TBD'}")
                    print(f"  상태: {event['status']}")
                    print(f"  저장일: {event['created_at'][:10]}")
                    print()

        except Exception as e:
            print(f"❌ 이벤트 조회 오류: {e}")

    def view_all_companies(self):
        """저장된 모든 회사 조회"""
        try:
            companies_response = self.supabase.table("companies").select("id, symbol, name").execute()
            companies = companies_response.data

            print(f"\n{'=' * 60}")
            print(f"📊 저장된 모든 회사")
            print(f"{'=' * 60}\n")

            if not companies:
                print("저장된 회사가 없습니다.")
                return

            for company in companies:
                # 각 회사별 이벤트 수
                events_response = self.supabase.table("company_events").select(
                    "id", count="exact"
                ).eq("company_id", company["id"]).execute()
                event_count = len(events_response.data)

                print(f"🏢 {company['symbol']} - {company['name']}")
                print(f"   이벤트 수: {event_count}개\n")

        except Exception as e:
            print(f"❌ 회사 조회 오류: {e}")

    def search_events_by_type(self, event_type):
        """특정 유형의 이벤트 검색"""
        try:
            events_response = self.supabase.table("company_events").select(
                "companies(symbol, name), event_type, title, description, expected_date, status"
            ).eq("event_type", event_type).order("expected_date", desc=False).execute()

            events = events_response.data

            print(f"\n{'=' * 60}")
            print(f"🔍 '{event_type}' 유형 이벤트 검색 결과")
            print(f"{'=' * 60}\n")

            if not events:
                print(f"'{event_type}' 유형의 이벤트가 없습니다.")
                return

            print(f"총 {len(events)}개 이벤트\n")

            for event in events:
                company = event['companies']
                print(f"🏢 {company['symbol']} - {company['name']}")
                print(f"   제목: {event['title']}")
                print(f"   설명: {event['description']}")
                print(f"   예상일: {event['expected_date'] if event['expected_date'] else 'TBD'}")
                print(f"   상태: {event['status']}")
                print()

        except Exception as e:
            print(f"❌ 이벤트 검색 오류: {e}")


# 실행
if __name__ == "__main__":
    viewer = EventViewer(supabase)

    print("🔎 이벤트 조회 도구\n")
    print("옵션:")
    print("1. 특정 회사 이벤트 조회")
    print("2. 모든 회사 조회")
    print("3. 특정 유형의 이벤트 검색")

    choice = input("\n선택 (1-3): ").strip()

    if choice == "1":
        symbol = input("회사 심볼 입력 (예: SYM): ").strip().upper()
        viewer.view_company_events(symbol)

    elif choice == "2":
        viewer.view_all_companies()

    elif choice == "3":
        print("\n가능한 이벤트 유형:")
        print("- Legislation")
        print("- Product Launch")
        print("- Earnings")
        print("- M&A")
        print("- Other")
        event_type = input("\n검색할 이벤트 유형: ").strip()
        viewer.search_events_by_type(event_type)

    else:
        print("❌ 잘못된 선택입니다.")
