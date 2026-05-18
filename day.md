# 개발 진행 순서

이 문서는 `agent.md`의 개발 지침과 현재 코드 상태를 기준으로, 백엔드에서 무엇부터 구현할지 정리한 작업 로드맵이다. 날짜별 일정표가 아니라 개발 순서 기준으로 관리한다.

## 현재 상태 요약

- FastAPI 스켈레톤과 기본 API 라우터는 있다.
- `/health`, `/score/calculate`, `/score/simulate`, `/predict/cutoff`, `/match/apartments`, `/strategy/generate` 라우터가 분리되어 있다.
- 점수 계산, 미래 시뮬레이션, 단지 매칭, 전략 생성은 임시 구현 수준이다.
- 커트라인 예측은 아직 ML 모델이 아니라 `baseline-fallback` 규칙 기반으로 동작한다.
- PostgreSQL 연결 설정은 있으나 실제 테이블 설계와 repository 구현은 미완성이다.
- 데이터 수집/전처리 파이프라인은 기본 동작한다.
  - ApplyHome 로컬 CSV를 기존 표준 데이터셋으로 변환할 수 있다.
  - `public_apartment_supply.csv`, `apt_competition.csv`, `subscription_cutoffs.csv`, `training_dataset.csv` 생성이 가능하다.
  - R-ONE 주택가격지수는 현재 샘플 수준이라 지역별 실제 지수 보강이 필요하다.
- 학습, 평가 파이프라인은 아직 실제 ML 모델 생성 단계까지 구현되지 않았다.
- 프론트엔드는 이 저장소 범위가 아니며, 백엔드 JSON API만 구현한다.

## 최근 완료된 내용

### ApplyHome CSV 데이터 접목

사용자가 추가한 ApplyHome CSV를 기존 프로젝트의 데이터 파이프라인에서 사용할 수 있도록 반영했다.

- `pipeline/import_applyhome_csv.py`를 추가했다.
- `/Users/gim-yanghyeon/Downloads` 또는 `APPLYHOME_CSV_DIR`에 있는 ApplyHome CSV를 자동 감지한다.
- `applyhome_apartment_mart.csv`가 있으면 우선 사용하고, 없으면 아래 APT 원천 파일을 조인한다.
  - `apt_lttot_pblanc_detail.csv`
  - `apt_lttot_pblanc_model.csv`
  - `apt_lttot_pblanc_competition.csv`
- `apt_lttot_pblanc_score.csv`의 `LWET_SCORE`를 최저 당첨가점으로 사용한다.
- ApplyHome 지역명을 기존 R-ONE 지역코드 체계에 맞게 변환한다.
- 기존 수집 함수와 연결했다.
  - `collect_public_api()`는 API 키가 없을 때 ApplyHome CSV를 우선 사용한다.
  - `collect_subscription_pdf()`는 당첨가점 CSV가 있으면 `subscription_cutoffs.csv`를 생성한다.
- 전처리에서 주택가격지수 결측이 모두 비어 있는 경우 `100.0`을 fallback으로 사용하도록 보정했다.

### 생성된 데이터

- `data/raw/public_api/public_apartment_supply.csv`
  - 14,042행
- `data/raw/public_api/apt_competition.csv`
  - 14,070행
- `data/raw/subscription_home/subscription_cutoffs.csv`
  - 6,323행
- `data/processed/training_dataset.csv`
  - 6,832행

### 검증 결과

- `python3 -m compileall -q subscription/pipeline subscription/tests/test_pipeline.py` 통과
- ApplyHome CSV 변환 스모크 테스트 통과
- `pipeline.import_applyhome_csv -> pipeline.preprocess -> pipeline.build_features` 실행 성공
- 최종 `training_dataset.csv`의 주요 학습 컬럼 결측 없음
  - `competition_rate`
  - `housing_price_index`
  - `cutoff_score`
- 현재 로컬 Python 환경에는 `pytest`가 설치되어 있지 않아 전체 테스트 실행은 보류 상태이다.

## 1단계: 실행 환경 및 기본 API 점검

### 목표

로컬에서 백엔드 프로젝트가 실행되고, 기본 API와 테스트가 동작하는 상태를 먼저 만든다.

### 해야 할 일

- conda 환경을 활성화한다.
  - `conda activate subscription`
- 의존성을 설치한다.
  - `pip install -r requirements.txt`
- `.env`에 필요한 값을 확인한다.
  - `APP_NAME`
  - `DATABASE_URL`
  - `CORS_ORIGINS`
  - `PUBLIC_DATA_API_KEY`
  - `OPENAI_API_KEY`
- 테스트 실행이 가능한지 확인한다.
  - `pytest`
- API 서버 실행을 확인한다.
  - `uvicorn app.main:app --reload`
- 기본 API를 확인한다.
  - `GET /health`
  - `POST /score/calculate`
  - `POST /score/simulate`

### 완료 기준

- `pytest`가 실행된다.
- `/health`가 `{"status": "ok"}`를 반환한다.
- 점수 계산 API가 200 응답과 JSON 결과를 반환한다.

### 관련 파일

- `requirements.txt`
- `.env`
- `app/main.py`
- `app/api/score.py`
- `tests/test_api.py`

## 2단계: 청약 점수 계산 로직 정교화

### 목표

현재 임시 점수 계산식을 실제 청약 가점 기준에 가깝게 보정한다.

### 해야 할 일

- 무주택 기간 점수표를 상수로 분리한다.
- 부양가족 수 점수표를 상수로 분리한다.
- 청약통장 가입기간 점수표를 상수로 분리한다.
- 입력값이 점수 계산 대상이 아닌 경우 `warnings`에 사유를 담는다.
- 미래 시뮬레이션에서 무주택 기간과 청약통장 가입기간 증가 규칙을 명확히 검증한다.

### 완료 기준

- `ScoreResponse`가 총점과 항목별 점수를 일관되게 반환한다.
- 총점은 84점을 넘지 않는다.
- 무주택자가 아닌 사용자의 무주택 기간 점수는 0점으로 처리된다.
- 점수 계산 테스트와 미래 시뮬레이션 테스트가 통과한다.

### 관련 파일

- `services/score_calculator.py`
- `services/future_simulator.py`
- `app/schemas/score.py`
- `tests/test_score_calculator.py`
- `tests/test_future_simulator.py`

## 3단계: 통합 분석 API 추가

### 목표

외부 클라이언트가 여러 API를 순차 호출하지 않아도 되도록, 한 번의 요청으로 점수 계산부터 전략 생성까지 수행하는 API를 만든다.

### 해야 할 일

- `POST /analysis/run` 엔드포인트를 추가한다.
- 분석 요청/응답 Pydantic schema를 추가한다.
- 처리 흐름을 하나로 연결한다.
  - 현재 점수 계산
  - 미래 점수 계산
  - 후보 단지 커트라인 예측
  - 단지 매칭
  - 전략 문장 생성
- 기존 개별 API는 유지한다.

### 완료 기준

- `POST /analysis/run`이 현재 점수, 미래 점수, 예측 커트라인, 단지 분류, 전략 문장을 한 번에 반환한다.
- 후보 단지가 비어 있어도 명확한 빈 결과를 반환한다.
- 통합 API 테스트가 추가되고 통과한다.

### 관련 파일

- `app/main.py`
- `app/api/`
- `app/schemas/`
- `services/`
- `tests/test_api.py`

## 4단계: PostgreSQL 데이터 구조 및 repository 구현

### 목표

서비스에서 사용할 단지 후보 데이터와 학습/예측 데이터를 PostgreSQL 또는 CSV에서 안정적으로 읽을 수 있게 만든다.

### 해야 할 일

- 먼저 CSV 기반 repository를 안정화한다.
  - `data/sample/sample_apartment_candidates.csv`
  - `data/processed/apartment_candidates.csv`
- PostgreSQL 테이블 설계는 데이터 컬럼이 확정된 뒤 진행한다.
- repository 함수 역할을 분리한다.
  - 후보 단지 목록 조회
  - 학습 데이터 조회
  - 예측 결과 저장 또는 조회
- `DATABASE_URL` 기반 연결이 정상 동작하는지 확인한다.

### 완료 기준

- repository에서 샘플 단지 CSV를 읽어 list 또는 DataFrame으로 반환한다.
- 파일이 없거나 컬럼이 부족할 때 명확한 예외 또는 fallback을 제공한다.
- PostgreSQL 연결 설정이 `.env`의 `DATABASE_URL`을 사용한다.

### 관련 파일

- `app/db/session.py`
- `app/db/repository.py`
- `data/sample/sample_apartment_candidates.csv`
- `data/processed/apartment_candidates.csv`

## 5단계: 샘플 데이터 기반 매칭 흐름 완성

### 목표

실제 외부 데이터 수집 전에도 샘플 데이터만으로 end-to-end 추천 흐름을 확인할 수 있게 만든다.

### 해야 할 일

- 샘플 후보 단지 데이터를 최소 20개 이상으로 늘린다.
- 지역, 예상 커트라인, 점수대가 다양하게 나오도록 샘플을 구성한다.
- repository에서 읽은 후보 단지를 예측/매칭 입력으로 변환한다.
- 매칭 결과를 `available_now`, `prepare_later`, `difficult`로 안정적으로 분류한다.

### 완료 기준

- 샘플 데이터만으로 통합 분석 API가 정상 응답한다.
- 각 분류 목록에 들어가는 데이터 구조가 API 응답 schema와 일치한다.
- 매칭 테스트가 현재 점수/미래 점수 경계값을 검증한다.

### 관련 파일

- `data/sample/sample_apartment_candidates.csv`
- `services/apartment_matcher.py`
- `services/cutoff_predictor.py`
- `app/db/repository.py`
- `tests/test_apartment_matcher.py`

## 6단계: 데이터 수집/전처리 파이프라인 구현

### 목표

공공데이터, ApplyHome CSV, 청약홈 당첨가점, R-ONE 데이터를 수집하고 학습 가능한 형태로 정제한다.

### 진행 상태

- 완료: ApplyHome APT CSV를 기존 표준 스키마로 변환하는 로컬 import 파이프라인을 추가했다.
- 완료: APT 분양 기본정보, 주택형/분양가, 일반청약 경쟁률, 당첨가점 CSV를 학습 데이터로 연결했다.
- 완료: `data/processed/training_dataset.csv` 생성까지 확인했다.
- 진행 필요: R-ONE 지역별 주택가격지수 데이터를 실제 지역코드 전체로 보강해야 한다.
- 진행 필요: 오피스텔, 공공지원 민간임대, 취소 후 재공급, 잔여세대 데이터는 현재 모델에 섞지 않고 별도 모델 또는 별도 기능으로 분리해야 한다.

### 해야 할 일

- ApplyHome CSV import 경로를 유지보수한다.
  - `applyhome_apartment_mart.csv` 우선 사용
  - 원천 3개 파일 detail/model/competition 조인 fallback 유지
  - score CSV 기반 `subscription_cutoffs.csv` 생성 유지
- 공공데이터포털 API 수집 로직은 API 키가 있을 때 사용할 수 있도록 유지한다.
- R-ONE 또는 주택가격지수 데이터 수집 로직을 실제 데이터로 보강한다.
- 원천 데이터를 `data/raw/`에 저장한다.
- 정제 결과를 `data/interim/`과 `data/processed/`에 저장한다.
- 단지명, 지역 코드, 날짜, 분양가, 경쟁률, 당첨가점 컬럼을 표준화한다.
- 현재 제외한 비APT/특수 청약 파일의 활용 방식을 별도 설계한다.
  - `urbty_ofctl_lttot_pblanc_competition.csv`
  - `pbl_pvt_rent_lttot_pblanc_competition.csv`
  - `canc_respl_lttot_pblanc_competition.csv`
  - `remndr_lttot_pblanc_competition.csv`

### 완료 기준

- 각 수집 스크립트가 실행 가능한 함수 또는 CLI 형태를 가진다.
- `data/processed/training_dataset.csv`가 학습 데이터 스키마를 만족한다.
- 필수 컬럼 누락과 결측치 처리 규칙이 코드에 반영된다.
- ApplyHome CSV만으로 학습 데이터 재생성이 가능하다.
- R-ONE 주택가격지수가 주요 지역코드에 대해 채워진다.

### 관련 파일

- `pipeline/import_applyhome_csv.py`
- `pipeline/collect_public_api.py`
- `pipeline/collect_subscription_pdf.py`
- `pipeline/collect_rone.py`
- `pipeline/preprocess.py`
- `pipeline/build_features.py`
- `data/raw/`
- `data/processed/training_dataset.csv`

## 7단계: ML 학습/평가/예측 모델 연결

### 목표

규칙 기반 fallback 예측을 실제 학습 모델 기반 예측으로 교체한다.

### 진행 상태

- 완료: 모델 학습에 사용할 `data/processed/training_dataset.csv`를 실제 ApplyHome 기반 데이터로 만들 수 있다.
- 진행 필요: 현재 `pipeline/train_model.py`는 모델 파일 경로만 생성하는 수준이다.
- 진행 필요: `pipeline/evaluate_model.py`와 `services/cutoff_predictor.py`를 실제 모델 기반으로 연결해야 한다.

### 해야 할 일

- 새로 생성된 `training_dataset.csv`를 기준으로 학습/검증 split을 구성한다.
- `RandomForestRegressor` 기반 학습 코드를 구현한다.
- 데이터가 적을 때 사용할 `Ridge Regression` fallback을 준비한다.
- 평가 지표를 계산한다.
  - RMSE
  - MAE
  - MAPE
- 학습된 모델을 `model_artifacts/artifacts/`에 저장한다.
- 평가 리포트를 `model_artifacts/reports/`에 저장한다.
- `services/cutoff_predictor.py`에서 모델 파일이 있으면 로드하고, 없으면 fallback 예측을 사용한다.

### 완료 기준

- `pipeline/train_model.py` 실행 시 모델 파일이 생성된다.
- `pipeline/evaluate_model.py` 실행 시 metrics와 feature importance 리포트가 생성된다.
- `predict_cutoff`가 모델 기반 예측과 fallback 예측을 모두 처리한다.
- 예측값은 0점 이상 84점 이하로 제한된다.

### 관련 파일

- `pipeline/train_model.py`
- `pipeline/evaluate_model.py`
- `services/cutoff_predictor.py`
- `model_artifacts/artifacts/`
- `model_artifacts/reports/`
- `tests/test_cutoff_predictor.py`

## 8단계: 테스트 및 문서 정리

### 목표

백엔드 API와 서비스 로직이 안정적으로 동작하는지 확인하고, 실행 방법을 문서화한다.

### 해야 할 일

- 로컬 환경에 테스트 의존성을 설치한다.
  - `pip install -r requirements.txt`
- 전체 테스트를 정리한다.
  - 점수 계산 테스트
  - 미래 시뮬레이션 테스트
  - 커트라인 예측 테스트
  - 단지 매칭 테스트
  - API 테스트
  - ApplyHome CSV 변환 테스트
- `README.md`에 실행 방법을 추가한다.
- `.env` 필수 값 목록을 문서화한다.
- `APPLYHOME_CSV_DIR` 사용 방법을 문서화한다.
- 주요 API 요청/응답 예시를 문서화한다.
- `agent.md`와 실제 파일 구조가 계속 일치하는지 확인한다.

### 완료 기준

- `pytest`가 통과한다.
- `README.md`만 보고 로컬 서버를 실행할 수 있다.
- `agent.md`, `day.md`, 실제 파일 구조가 서로 충돌하지 않는다.
- 프론트엔드 작업이 백엔드 로드맵에 섞여 있지 않다.

### 관련 파일

- `tests/`
- `README.md`
- `agent.md`
- `day.md`

## 우선순위 요약

1. 로컬 환경에 `pytest`를 포함한 의존성 설치 후 전체 테스트 실행
2. ApplyHome 기반 `training_dataset.csv` 품질 점검
3. R-ONE 주택가격지수 실제 데이터 보강
4. ML 학습/평가/예측 모델 연결
5. `services/cutoff_predictor.py`를 모델 기반 예측으로 교체
6. CSV 기반 repository와 통합 분석 API가 새 데이터셋을 사용하도록 점검
7. 비APT/특수 청약 파일 활용 범위 별도 설계
8. README, agent.md, day.md 문서 정리
