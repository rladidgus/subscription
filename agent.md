# 청약 당첨 예측 및 맞춤형 전략 서비스 개발 지침

## 1. 프로젝트 개요

이 프로젝트는 사용자의 청약 가점과 민간분양 단지 데이터를 결합해, 현재 지원 가능한 단지와 미래에 준비할 단지를 추천하는 데이터 기반 청약 전략 서비스이다. 서비스는 청약 가점 자동 계산, 미래 점수 시뮬레이션, 머신러닝 기반 커트라인 예측, 단지 매칭, 맞춤형 전략 텍스트 생성을 하나의 흐름으로 제공한다.

초기 버전은 수업 프로젝트의 구현 속도와 설명 가능성을 우선한다. 이 저장소에는 백엔드 코드만 둔다. FastAPI는 JSON API 서버 역할만 담당하고, 프론트엔드 화면, 템플릿, 정적 파일은 이 프로젝트 범위에서 제외한다.

## 2. 핵심 목표

- 사용자가 입력한 나이, 무주택 기간, 부양가족 수, 청약통장 가입기간을 바탕으로 현재 청약 가점을 계산한다.
- `n년 후` 기준의 무주택 기간과 청약통장 가입기간 증가를 반영해 미래 청약 가점을 시뮬레이션한다.
- 과거 민간분양 일반공급 단지의 최저 당첨 가점 데이터를 학습해 신규 단지의 예상 커트라인을 예측한다.
- 현재 점수와 미래 점수를 기준으로 `지금 도전 가능한 단지`와 `나중에 준비할 단지`를 분리한다.
- 예측 결과와 사용자 조건을 바탕으로 LLM 또는 템플릿 기반 전략 문장을 생성한다.

## 3. 기술 스택

### Backend

- Python 3.10 이상
- FastAPI: JSON API 라우팅, 청약 점수 계산, 예측, 매칭, 전략 생성 API 제공
- Pydantic: 요청/응답 스키마 검증
- SQLAlchemy: PostgreSQL 접근 계층
- psycopg: PostgreSQL 드라이버
- Uvicorn: 로컬 API 서버 실행
- CORS Middleware: `main.py`에서 `.env`의 `CORS_ORIGINS`를 읽어 허용 출처 관리

### Data & ML

- pandas, numpy: 데이터 정제 및 피처 엔지니어링
- scikit-learn: RandomForestRegressor, Ridge Regression, 평가 지표
- xgboost: 비교 모델. 설치나 환경 제약이 있으면 선택 기능으로 둔다.
- joblib: 학습된 ML 모델 저장 및 로드

### Database

- PostgreSQL을 기본 DB로 사용한다.
- `DATABASE_URL`은 `.env`에 둔다.
- 원천 데이터와 학습 데이터는 CSV/Parquet로 관리하고, 서비스 조회용 데이터는 PostgreSQL에 적재한다.

### Strategy Generation

- 기본 구현: 규칙 기반 템플릿 전략 생성
- 선택 구현: OpenAI API를 사용해 자연어 전략 문장 생성
- API 키가 없거나 네트워크가 제한된 환경에서도 서비스가 동작하도록 템플릿 방식을 fallback으로 둔다.

## 4. 권장 폴더 구조

```text
subscription/
  README.md
  agent.md
  requirements.txt
  .env

  app/
    main.py
    api/
      score.py
      predict.py
      match.py
      strategy.py
      analysis.py
    schemas/
      score.py
      apartment.py
      prediction.py
      strategy.py
      analysis.py
    db/
      session.py
      repository.py

  services/
    score_calculator.py
    future_simulator.py
    cutoff_predictor.py
    apartment_matcher.py
    strategy_generator.py

  pipeline/
    common.py
    collect_subscription_pdf.py
    collect_public_api.py
    collect_rone.py
    preprocess.py
    build_features.py
    train_model.py
    evaluate_model.py

  data/
    raw/
      subscription_home/
      public_api/
      rone/
    interim/
    processed/
      training_dataset.csv
      apartment_candidates.csv
    sample/
      sample_training_dataset.csv
      sample_apartment_candidates.csv

  model_artifacts/
    artifacts/
      cutoff_random_forest.joblib
    reports/
      metrics.json
      feature_importance.csv

  tests/
    test_score_calculator.py
    test_future_simulator.py
    test_cutoff_predictor.py
    test_apartment_matcher.py
    test_repository.py
    test_pipeline.py
    test_api.py
```

### 4.1 폴더 및 파일 역할

루트 파일:

- `README.md`: 프로젝트 실행 방법, 설치 방법, 주요 API 사용 예시를 정리한다.
- `agent.md`: 프로젝트 개발 방향, 폴더 구조, 데이터 파이프라인, API 설계 기준을 기록하는 개발 지침 문서이다.
- `requirements.txt`: FastAPI, SQLAlchemy, psycopg, pandas, scikit-learn 등 Python 의존성을 관리한다.
- `.env`: 로컬 실행에 필요한 실제 환경변수를 저장한다. DB 주소, CORS 허용 출처, API 키를 이 파일에서 관리한다.

`app/`:

- FastAPI 백엔드 애플리케이션의 진입점과 API 계층을 둔다.
- `app/main.py`: FastAPI 앱 생성, CORS 설정, API 라우터 등록, `/health` 엔드포인트를 담당한다.
- `app/api/`: HTTP 요청을 받는 라우터 파일을 둔다. 각 파일은 요청 검증 후 `services/`의 비즈니스 로직을 호출한다.
- `app/schemas/`: Pydantic 요청/응답 모델을 둔다. API 입출력 형식을 명확히 고정하는 역할이다.
- `app/db/session.py`: `.env`의 `DATABASE_URL`을 읽어 PostgreSQL 연결 엔진과 세션을 만든다.
- `app/db/repository.py`: DB 또는 샘플 CSV에서 데이터를 읽고 저장하는 데이터 접근 함수를 둔다.

`services/`:

- API와 독립적으로 테스트 가능한 핵심 비즈니스 로직을 둔다.
- `score_calculator.py`: 현재 청약 가점을 계산한다.
- `future_simulator.py`: `n년 후` 무주택 기간과 청약통장 가입기간 증가를 반영해 미래 점수를 계산한다.
- `cutoff_predictor.py`: 학습된 모델 또는 fallback 규칙으로 단지 예상 커트라인을 반환한다.
- `apartment_matcher.py`: 현재 점수와 미래 점수 기준으로 단지를 `available_now`, `prepare_later`, `difficult`로 분류한다.
- `strategy_generator.py`: 점수와 추천 결과를 바탕으로 사용자 맞춤 전략 문장을 생성한다.

`pipeline/`:

- 서비스 실행과 분리된 데이터 수집, 정제, 학습 작업 코드를 둔다.
- `common.py`: 데이터 경로, 학습 데이터 컬럼, 공통 CSV 저장/읽기 함수를 관리한다.
- `collect_subscription_pdf.py`: 청약홈 당첨자 발표 PDF에서 실제 최저 당첨 가점을 추출한다.
- `collect_public_api.py`: 공공데이터포털 분양정보, 경쟁률, 신청현황 데이터를 수집한다.
- `collect_rone.py`: R-ONE 또는 주택가격지수 데이터를 수집한다.
- `preprocess.py`: 원천 데이터의 결측치, 지역 코드, 단지명 표기 등을 정리한다.
- `build_features.py`: 모델 학습에 사용할 피처 테이블을 만든다.
- `train_model.py`: 커트라인 예측 모델을 학습하고 산출물을 저장한다.
- `evaluate_model.py`: RMSE, MAE, MAPE와 feature importance 리포트를 생성한다.

`data/`:

- 원천 데이터, 중간 데이터, 학습/서비스용 데이터, 샘플 데이터를 보관한다.
- `data/raw/`: 외부에서 받은 원본 데이터를 그대로 저장한다.
- `data/interim/`: 정제 중간 단계의 데이터를 저장한다.
- `data/processed/`: 모델 학습과 서비스 조회에 사용할 최종 데이터를 저장한다.
- `data/sample/`: API와 테스트를 빠르게 확인하기 위한 샘플 CSV를 저장한다.

`model_artifacts/`:

- DB 모델이 아니라 머신러닝 모델 산출물을 저장하는 폴더이다.
- `model_artifacts/artifacts/`: 학습된 `.joblib` 모델 파일을 저장한다.
- `model_artifacts/reports/`: 모델 성능 지표와 feature importance 리포트를 저장한다.

`tests/`:

- 서비스 로직과 API 동작을 검증하는 테스트 코드를 둔다.
- 점수 계산, 미래 시뮬레이션, 커트라인 예측, 단지 매칭, FastAPI 엔드포인트를 각각 테스트한다.

## 5. 데이터 파이프라인

### 5.1 데이터 수집

1. 청약홈 당첨자 발표 PDF
   - 목적: 단지별 실제 최저 당첨 가점, 즉 ML 타깃 변수 수집
   - 처리: PDF에서 단지명, 지역, 공급유형, 평형, 최저 당첨 가점 추출
   - 초기 구현: 수동으로 정리한 CSV 샘플을 먼저 사용하고, 이후 PDF 파싱 자동화

2. 공공데이터포털 분양정보 API
   - 목적: 단지 기본 정보와 공급 정보 수집
   - 주요 컬럼: 단지명, 지역, 공고일, 공급유형, 일반공급 세대수, 전용면적, 분양가
   - API 키는 `.env`에 저장하고 코드에 직접 작성하지 않는다.

3. 경쟁률 및 신청현황 API
   - 목적: 단지별 수요 강도를 나타내는 보조 피처 수집
   - 주요 컬럼: 특별공급/일반공급 신청 수, 경쟁률, 공급 세대수

4. R-ONE 또는 주택가격지수 데이터
   - 목적: 지역별 주택가격 흐름을 모델 피처로 사용
   - 주요 컬럼: 지역 코드, 기준월, 주택가격지수, 변동률

### 5.2 전처리

- 단지명 정규화: 공백, 괄호, 특수문자, 블록명 표기 차이를 통일한다.
- 지역 코드 표준화: 시도/시군구명을 일관된 코드로 변환한다.
- 날짜 파생 변수 생성: 공고일에서 공급연도, 분기, 월을 생성한다.
- 결측치 처리:
  - 필수값인 커트라인, 지역, 공급 세대수는 결측 시 학습 데이터에서 제외한다.
  - 보조 피처는 중앙값 또는 지역 평균으로 대체한다.
- 학습 우선 대상:
  - 민간분양 일반공급 단지
  - 최저 당첨 가점 40점 이상 데이터
  - 데이터 수가 부족하면 기준을 30점 이상으로 완화할 수 있다.

### 5.3 학습 데이터 스키마

```text
apartment_id: 단지 고유 ID
apartment_name: 단지명
region_code: 지역 코드
region_name: 지역명
announcement_date: 모집공고일
supply_year: 공급연도
supply_quarter: 공급분기
general_supply_units: 일반공급 세대수
sale_price: 분양가
competition_rate: 경쟁률
housing_price_index: 주택가격지수
area_m2: 전용면적
cutoff_score: 실제 최저 당첨 가점
```

### 5.4 모델링

- 기본 모델: `RandomForestRegressor`
- 비교 모델: `XGBoost`
- 데이터가 적거나 모델 성능이 불안정하면 `Ridge Regression`을 fallback 모델로 사용한다.
- 학습 목표: 민간분양 일반공급 최저 당첨 가점 예측
- 주요 피처:
  - 지역 코드
  - 일반공급 세대수
  - 분양가
  - 경쟁률
  - 주택가격지수
  - 공급연도
  - 공급분기
  - 전용면적
- 평가 지표:
  - 1차 목표: `RMSE <= 5`
  - 보조 지표: `MAE`, `MAPE`
- 모델 산출물:
  - `model_artifacts/artifacts/cutoff_random_forest.joblib`
  - `model_artifacts/reports/metrics.json`
  - `model_artifacts/reports/feature_importance.csv`

## 6. 서비스 흐름

```text
사용자 정보 입력
  -> 현재 청약 가점 계산
  -> n년 후 미래 가점 시뮬레이션
  -> 신규 또는 후보 단지의 예상 커트라인 예측
  -> 현재 점수와 미래 점수로 단지 매칭
  -> 맞춤형 청약 전략 텍스트 생성
  -> FastAPI JSON API 응답 반환
```

## 7. 주요 서비스 모듈

### 7.1 `services/score_calculator.py`

사용자의 조건을 받아 청약 가점을 계산한다.

입력값:

- `age`
- `is_homeless`
- `homeless_years`
- `dependents_count`
- `subscription_account_years`
- `marital_status`

출력값:

- `total_score`
- `homeless_score`
- `dependents_score`
- `account_score`
- `warnings`

주의사항:

- 청약 가점 산식은 정책 변경 가능성이 있으므로 상수 테이블로 분리한다.
- 입력값이 점수 계산 대상이 아닌 경우 경고 메시지를 함께 반환한다.

### 7.2 `services/future_simulator.py`

현재 사용자 조건과 `years_later`를 받아 미래 점수를 계산한다.

규칙:

- 무주택자인 경우 `homeless_years += years_later`
- 청약통장 가입기간은 `subscription_account_years += years_later`
- 부양가족 수는 사용자가 별도 입력하지 않으면 현재 값을 유지한다.

### 7.3 `services/cutoff_predictor.py`

학습된 모델을 로드해 후보 단지의 예상 커트라인을 예측한다.

출력값:

- `predicted_cutoff_score`
- `model_name`
- `model_version`
- `confidence_note`

모델이 없거나 피처가 부족한 경우:

- 샘플 평균 또는 지역 평균 기반의 임시 예측값을 반환한다.
- 응답에 `confidence_note`를 포함해 임시 예측임을 명시한다.

### 7.4 `services/apartment_matcher.py`

사용자 점수와 예측 커트라인을 비교해 단지를 분류한다.

분류 기준:

- `available_now`: 현재 점수 >= 예상 커트라인
- `prepare_later`: 현재 점수 < 예상 커트라인 <= 미래 점수
- `difficult`: 미래 점수 < 예상 커트라인

각 단지는 예상 커트라인과 사용자 점수 차이를 함께 표시한다.

### 7.5 `services/strategy_generator.py`

추천 결과를 바탕으로 사용자가 이해하기 쉬운 전략 문장을 생성한다.

기본 템플릿 예시:

```text
현재 점수는 {current_score}점이고, {years_later}년 후 예상 점수는 {future_score}점입니다.
현재 기준으로는 {available_count}개 단지에 도전 가능하며,
{prepare_count}개 단지는 청약통장 가입기간과 무주택 기간을 더 확보한 뒤 준비하는 것이 좋습니다.
```

OpenAI API를 사용하는 경우:

- 사용자 개인정보를 최소화해 전달한다.
- 단지 추천 결과, 점수 차이, 지역 선호도 중심으로 프롬프트를 구성한다.
- API 실패 시 템플릿 전략으로 fallback한다.

## 8. API 인터페이스

### 8.1 `POST /score/calculate`

청약 가점을 계산한다.

요청 예시:

```json
{
  "age": 29,
  "is_homeless": true,
  "homeless_years": 3,
  "dependents_count": 1,
  "subscription_account_years": 4,
  "marital_status": "single"
}
```

응답 예시:

```json
{
  "total_score": 32,
  "homeless_score": 8,
  "dependents_score": 10,
  "account_score": 14,
  "warnings": []
}
```

### 8.2 `POST /score/simulate`

현재 점수와 미래 점수를 함께 계산한다.

요청 예시:

```json
{
  "user": {
    "age": 29,
    "is_homeless": true,
    "homeless_years": 3,
    "dependents_count": 1,
    "subscription_account_years": 4,
    "marital_status": "single"
  },
  "years_later": 3
}
```

응답 예시:

```json
{
  "current_score": 32,
  "future_score": 40,
  "years_later": 3
}
```

### 8.3 `POST /predict/cutoff`

후보 단지의 예상 커트라인을 예측한다.

요청 예시:

```json
{
  "apartment_name": "샘플 아파트",
  "region_code": "11",
  "general_supply_units": 120,
  "sale_price": 750000000,
  "competition_rate": 24.5,
  "housing_price_index": 103.2,
  "supply_year": 2026,
  "supply_quarter": 2,
  "area_m2": 84
}
```

응답 예시:

```json
{
  "apartment_name": "샘플 아파트",
  "predicted_cutoff_score": 47.2,
  "model_name": "RandomForestRegressor",
  "confidence_note": "학습 모델 기반 예측값입니다."
}
```

### 8.4 `POST /match/apartments`

사용자 현재/미래 점수와 후보 단지 예측값을 비교해 단지를 분류한다.

요청 예시:

```json
{
  "current_score": 42,
  "future_score": 50,
  "apartments": [
    {
      "apartment_id": "apt-001",
      "apartment_name": "샘플 아파트",
      "region_name": "서울",
      "predicted_cutoff_score": 47.2
    }
  ]
}
```

응답 예시:

```json
{
  "available_now": [],
  "prepare_later": [
    {
      "apartment_id": "apt-001",
      "apartment_name": "샘플 아파트",
      "score_gap": 5.2
    }
  ],
  "difficult": []
}
```

### 8.5 `POST /strategy/generate`

점수 계산, 예측, 매칭 결과를 바탕으로 맞춤형 전략 텍스트를 생성한다.

요청 예시:

```json
{
  "current_score": 42,
  "future_score": 50,
  "years_later": 3,
  "available_now_count": 2,
  "prepare_later_count": 4,
  "preferred_regions": ["서울", "경기"]
}
```

응답 예시:

```json
{
  "strategy_text": "현재 점수로는 일부 경기권 단지에 우선 도전하고, 서울 주요 단지는 3년 뒤 점수 상승을 고려해 준비하는 전략이 적합합니다."
}
```

## 9. 백엔드 API 서버 구성

이 프로젝트는 백엔드 전용 Python 프로젝트로 구현한다. FastAPI는 JSON API만 제공하며, 화면 렌더링과 프론트엔드 코드는 포함하지 않는다. 별도 프론트엔드가 붙을 수 있도록 응답 스키마를 명확히 유지하고 CORS 설정을 분리한다.

### 9.1 API 라우터 구성

권장 라우터:

```text
GET  /health                 서버 상태 확인
POST /score/calculate        현재 청약 가점 계산
POST /score/simulate         현재/미래 청약 가점 계산
POST /predict/cutoff         후보 단지 예상 커트라인 예측
POST /match/apartments       현재/미래 점수 기준 단지 분류
POST /strategy/generate      맞춤형 전략 텍스트 생성
```

### 9.2 통합 분석 API

외부 클라이언트가 여러 API를 순차 호출하지 않아도 되도록 통합 분석 API를 추가할 수 있다.

```text
POST /analysis/run
```

처리 흐름:

```text
score_calculator
  -> future_simulator
  -> cutoff_predictor
  -> apartment_matcher
  -> strategy_generator
  -> JSON 응답 반환
```

응답에는 현재 점수, 미래 점수, 예측 커트라인, 단지 분류 결과, 전략 문장을 한 번에 포함한다.

### 9.3 백엔드 입력 데이터

API 요청에서 받을 사용자 입력값:

- 나이
- 무주택 여부
- 무주택 기간
- 부양가족 수
- 청약통장 가입기간
- 혼인 여부
- 선호 지역
- 미래 시뮬레이션 기간

백엔드는 입력값 검증과 JSON 응답 생성을 담당한다. 화면 구성에 필요한 데이터는 응답 스키마에 포함하되, 화면 구현 자체는 이 저장소에 포함하지 않는다.

### 9.4 샘플 데이터 처리

- 외부 API 연동 전에는 `data/sample/sample_apartment_candidates.csv`를 사용한다.
- 샘플 데이터에는 최소 20개 이상의 단지를 넣어 지역별, 점수대별 결과가 나뉘도록 한다.
- 샘플 데이터 로딩은 서비스 계층 또는 repository 계층에서 처리한다.

## 10. 테스트 계획

### 10.1 점수 계산 테스트

- 무주택 기간별 점수가 올바르게 계산되는지 검증한다.
- 부양가족 수별 점수가 올바르게 계산되는지 검증한다.
- 청약통장 가입기간별 점수가 올바르게 계산되는지 검증한다.
- 잘못된 입력값에 대해 예외 또는 경고가 반환되는지 검증한다.

### 10.2 미래 시뮬레이션 테스트

- `years_later=3` 입력 시 무주택 기간과 가입기간이 각각 3년 증가하는지 검증한다.
- 무주택자가 아닌 경우 무주택 기간 증가를 반영하지 않는지 검증한다.

### 10.3 모델 테스트

- 샘플 학습 데이터로 모델 학습이 완료되는지 검증한다.
- 예측값이 0점 이상 84점 이하 범위에 있는지 검증한다.
- 평가 리포트에 RMSE, MAE, MAPE가 저장되는지 검증한다.

### 10.4 매칭 테스트

- 현재 점수가 커트라인 이상이면 `available_now`로 분류되는지 검증한다.
- 현재 점수는 부족하지만 미래 점수가 커트라인 이상이면 `prepare_later`로 분류되는지 검증한다.
- 미래 점수도 부족하면 `difficult`로 분류되는지 검증한다.

### 10.5 API 테스트

- 각 엔드포인트가 정상 요청에 대해 200 응답을 반환하는지 검증한다.
- 필수 필드 누락 시 422 응답을 반환하는지 검증한다.
- 모델 파일이 없을 때도 예측 API가 fallback 응답을 반환하는지 검증한다.

## 11. 구현 순서

1. `requirements.txt`와 기본 폴더 구조를 만든다.
2. `services/score_calculator.py`와 `services/future_simulator.py`를 먼저 구현한다.
3. 샘플 단지 CSV를 만들고 `apartment_matcher.py`를 구현한다.
4. `app/main.py`에서 FastAPI 앱, CORS, API 라우터를 연결한다.
5. Pydantic 요청/응답 스키마와 FastAPI JSON API 엔드포인트를 구현한다.
6. 샘플 학습 데이터로 `train_model.py`와 `cutoff_predictor.py`를 구현한다.
7. `POST /analysis/run` 통합 분석 API를 구현한다.
8. 전략 생성 모듈을 템플릿 방식으로 구현한다.
9. 선택적으로 OpenAI API 기반 전략 생성을 추가한다.
10. 테스트 코드를 작성하고 전체 흐름을 검증한다.
11. 실제 API/PDF 수집 파이프라인을 점진적으로 자동화한다.

## 12. 개발 원칙

- 먼저 시연 가능한 end-to-end 흐름을 완성한 뒤 데이터 자동화와 모델 성능을 개선한다.
- 청약 가점 산식과 정책 기준은 코드에 흩어 쓰지 말고 상수 또는 설정 파일로 관리한다.
- 모델 예측은 절대 확정 당첨 보장처럼 표현하지 않는다. 항상 `예상 커트라인`, `도전 가능성`, `전략 참고용`으로 표현한다.
- 개인정보는 저장하지 않는 것을 기본으로 한다. 저장이 필요하면 입력값 최소화와 익명화를 우선한다.
- 외부 API 키는 `.env`에 저장하고 Git에 커밋하지 않는다.
- 데이터 출처와 수집일을 기록해 결과 재현성을 확보한다.

## 13. 완료 기준

- FastAPI JSON API로 사용자 조건을 보내면 현재 점수와 미래 점수가 반환된다.
- `POST /analysis/run`이 점수 계산, 예측, 매칭, 전략 생성을 한 번에 수행한다.
- 샘플 단지 목록이 현재 가능, 미래 준비, 어려움으로 분류된다.
- 후보 단지의 예상 커트라인을 모델 또는 fallback 방식으로 반환한다.
- 추천 결과에 대한 전략 문장이 생성된다.
- 주요 서비스 로직과 API에 대한 테스트가 통과한다.
- 모델 평가 리포트에 RMSE, MAE, MAPE가 기록된다.
