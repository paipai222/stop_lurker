# Company Events Fetcher 사용 가이드

## 📋 개요

Perplexity API를 사용하여 회사의 주요 이벤트를 조회하고 Supabase DB에 저장하는 모듈입니다.

### 파일 구성

```
project/
├── company_events_fetcher.py  # Perplexity 조회 + DB 저장 모듈 (스탠드얼론 실행 가능)
├── app.py                      # Flask 백엔드 (수정된 버전)
├── .env                        # 환경 변수 파일
└── README.md                   # 이 파일
```

---

## 🚀 사용 방법

### 1️⃣ **스탠드얼론 실행** (별도 .py 파일에서)

`company_events_fetcher.py`를 별도로 실행할 수 있습니다:

```bash
python company_events_fetcher.py
```

**코드 수정 방법:**

`company_events_fetcher.py`의 맨 아래 스탠드얼론 섹션에서 조회할 회사를 수정합니다:

```python
if __name__ == "__main__":
    # ...
    
    # 조회할 회사 심볼 (여기서 수정해서 사용)
    symbols_to_fetch = ['AAPL', 'MSFT', 'GOOGL']  # ← 여기 수정
    
    # ...
    results = fetcher.fetch_and_save(symbols_to_fetch)
```

---

### 2️⃣ **Flask 앱에서 import해서 사용**

Flask 앱 (`app.py`)에서 자동으로 import되어 사용됩니다:

```python
from company_events_fetcher import CompanyEventsFetcher, supabase, PERPLEXITY_API_KEY

# API 엔드포인트에서 사용
fetcher = CompanyEventsFetcher(PERPLEXITY_API_KEY, supabase)
results = fetcher.fetch_and_save(['AAPL', 'MSFT'])
```

---

### 3️⃣ **다른 파일에서 import해서 사용**

```python
from company_events_fetcher import CompanyEventsFetcher, supabase, PERPLEXITY_API_KEY

# 인스턴스 생성
fetcher = CompanyEventsFetcher(PERPLEXITY_API_KEY, supabase)

# 단일 회사 조회
fetcher.fetch_and_save('AAPL')

# 여러 회사 조회
fetcher.fetch_and_save(['AAPL', 'MSFT', 'GOOGL'])
```

---

## 🔧 주요 메서드

### `CompanyEventsFetcher` 클래스

#### `__init__(api_key, supabase_client)`
- **목적**: 초기화
- **매개변수**:
  - `api_key` (str): Perplexity API 키
  - `supabase_client` (Client): Supabase 클라이언트

#### `insert_company(symbol, name=None)`
- **목적**: 회사 정보를 DB에 저장 또는 기존 회사 조회
- **매개변수**:
  - `symbol` (str or list): 회사 티커 심볼
  - `name` (str, 선택): 회사명
- **반환**: company_id (int) 또는 company_id 리스트 (list)

```python
# 단일 회사
company_id = fetcher.insert_company('AAPL')

# 여러 회사
company_ids = fetcher.insert_company(['AAPL', 'MSFT'])
```

#### `fetch_events_from_perplexity(symbol, company_name)`
- **목적**: Perplexity API로 회사 이벤트 조회
- **매개변수**:
  - `symbol` (str): 회사 티커 심볼
  - `company_name` (str): 회사명
- **반환**: 이벤트 정보 리스트 (list)

```python
events = fetcher.fetch_events_from_perplexity('AAPL', 'Apple Inc.')
# 반환 형식:
# [
#   {
#     'type': 'Product Launch',
#     'title': '이벤트명',
#     'description': '설명',
#     'expected_date': '2026-02',
#     'status': 'Pending'
#   },
#   ...
# ]
```

#### `save_events_to_db(company_id, events)`
- **목적**: 이벤트를 데이터베이스에 저장
- **매개변수**:
  - `company_id` (int): 회사 ID
  - `events` (list): 저장할 이벤트 리스트
- **반환**: 저장된 이벤트 개수 (int)

```python
saved_count = fetcher.save_events_to_db(company_id, events)
print(f"저장됨: {saved_count}개")
```

#### `fetch_and_save(symbols)`
- **목적**: 전체 프로세스 실행 (회사 저장 → 이벤트 조회 → DB 저장)
- **매개변수**:
  - `symbols` (str or list): 조회할 회사 티커 심볼
- **반환**: 각 심볼별 처리 결과 (list of bool)

```python
# 단일 회사
results = fetcher.fetch_and_save('AAPL')

# 여러 회사
results = fetcher.fetch_and_save(['AAPL', 'MSFT', 'GOOGL'])
# 반환: [True, True, False] (성공, 성공, 실패)
```

---

## 📦 필수 환경 변수 (.env 파일)

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
PERPLEXITY_API_KEY=your-perplexity-api-key
```

---

## 🔄 데이터 흐름

```
1. insert_company(symbol)
   ↓
   DB 확인 → 기존이면 조회, 신규면 저장 (company_id 반환)
   ↓
2. fetch_events_from_perplexity(symbol, name)
   ↓
   Perplexity API 호출 → JSON 추출 → 이벤트 리스트 반환
   ↓
3. save_events_to_db(company_id, events)
   ↓
   company_events 테이블에 삽입 (저장된 개수 반환)
```

---

## 💾 DB 스키마

### `companies` 테이블
```
- id: bigint (PK)
- symbol: text (회사 티커, 유니크)
- name: text (회사명)
```

### `company_events` 테이블
```
- id: bigint (PK)
- company_id: bigint (FK → companies.id)
- event_type: text (Legislation, Product Launch, Earnings, M&A, Other)
- title: text (이벤트명)
- description: text (설명)
- expected_date: text (YYYY-MM 형식)
- status: text (Pending, In Progress, Completed, Not Started)
- source: text (Perplexity AI)
- created_at: timestamp
```

---

## ⚙️ 실행 예제

### 예제 1: 단일 회사 조회

```python
from company_events_fetcher import CompanyEventsFetcher, supabase, PERPLEXITY_API_KEY

fetcher = CompanyEventsFetcher(PERPLEXITY_API_KEY, supabase)
result = fetcher.fetch_and_save('AAPL')

if result[0]:
    print("✅ Apple 이벤트 저장 완료!")
else:
    print("❌ Apple 이벤트 저장 실패")
```

### 예제 2: 여러 회사 일괄 조회

```python
from company_events_fetcher import CompanyEventsFetcher, supabase, PERPLEXITY_API_KEY

companies = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']

fetcher = CompanyEventsFetcher(PERPLEXITY_API_KEY, supabase)
results = fetcher.fetch_and_save(companies)

# 결과 확인
for company, success in zip(companies, results):
    status = "✅" if success else "❌"
    print(f"{status} {company}")
```

### 예제 3: 스탠드얼론 실행

```bash
# company_events_fetcher.py 수정
# symbols_to_fetch = ['AAPL', 'MSFT']

python company_events_fetcher.py
```

**출력:**
```
==================================================
🚀 Company Events Fetcher 시작
==================================================

📊 조회할 회사: ['AAPL', 'MSFT']
==================================================
==================================================
🔍 AAPL 처리 중...
==================================================
✅ 기존 회사 조회 완료 (심볼: AAPL, ID: 1)
🔄 Perplexity API 호출 중... (AAPL)
✅ API 응답 받음
✅ 5개 이벤트 저장 완료

==================================================
🔍 MSFT 처리 중...
==================================================
✅ 회사 저장 완료 (심볼: MSFT, 이름: MSFT, ID: 2)
🔄 Perplexity API 호출 중... (MSFT)
✅ API 응답 받음
✅ 4개 이벤트 저장 완료

==================================================
✅ 처리 완료
결과: [True, True]
==================================================
```

---

## ⚠️ 주의사항

1. **API 호출 시간**: Perplexity API 호출에 10-30초 소요
2. **속도**: 여러 회사 조회 시 순차 처리 (병렬 처리 아님)
3. **에러 처리**: API 실패 시 해당 회사는 False 반환, 계속 진행
4. **날짜 형식**: YYYY-MM 형식만 인식, 다른 형식은 NULL 저장

---

## 🐛 문제 해결

### 문제: Perplexity API 연결 실패

```
❌ Perplexity API 오류: [Errno 111] Connection refused
```

**해결:**
- PERPLEXITY_API_KEY 확인
- 인터넷 연결 확인
- Perplexity API 서버 상태 확인

### 문제: Supabase 연결 실패

```
❌ Supabase 클라이언트 연결 실패: ...
```

**해결:**
- SUPABASE_URL, SUPABASE_KEY 확인
- .env 파일 경로 확인
- Supabase 프로젝트 활성화 확인

### 문제: JSON 파싱 실패

```
⚠️  JSON 형식을 찾을 수 없음
```

**해결:**
- Perplexity 응답 형식 확인
- 프롬프트 다시 확인
- temperature 값 조정 (현재 0.2)

---

## 📝 로그 해석

| 로그 | 의미 |
|------|------|
| ✅ | 성공 |
| ❌ | 실패 |
| 🔄 | 진행 중 |
| ⚠️ | 경고 |
| 🔍 | 조회/검색 |
| 📊 | 데이터 |
| 📡 | 통신 |

---

## 📞 지원

문제가 있으면 로그를 확인하고 다음을 체크하세요:

1. API 키 설정
2. 인터넷 연결
3. Supabase 데이터베이스 구조
4. 회사 심볼 유효성 (예: AAPL, MSFT)
