# Geopolitical Dashboard 단계별 설명서

이 문서는 이 저장소의 ETL 파이프라인으로 데이터를 준비하고 Tableau 대시보드를 구성하는 과정을 단계별로 설명합니다.

## 1. 준비하기

1. Python 3.10+와 `uv`가 설치되어 있어야 합니다.
2. 프로젝트 루트에서 의존성을 설치합니다.

```bash
uv sync --dev
```

3. 환경 변수 파일을 준비합니다.

```bash
cp .env.example .env
```

4. ACLED를 사용하려면 `data/raw/acled/`에 `*_aggregated_data_up_to-*.csv` 파일을 배치합니다.
   - `number_of_*.csv` 및 `.xlsx` 파일은 파이프라인에서 무시됩니다.

## 2. 데이터 웨어하우스 초기화

차원/팩트 테이블, 집계 뷰, 리스크 점수 뷰를 생성하기 위해 아래를 먼저 실행합니다.

```bash
uv run python scripts/bootstrap_db.py
uv run python scripts/seed_dimensions.py
```

실행 후 핵심 테이블:
- `dim_country`, `dim_region`, `dim_date`, `dim_event_type`, `dim_source_system`
- `fact_incident`, `fact_diplomatic_action`, `fact_risk_indicator`, `fact_news_pulse`
- `country_week_agg`, `country_month_agg`, `country_year_diplomatic`, `country_week_news`, `grs_monthly`

## 3. 파이프라인 실행(데이터 적재)

전체 소스를 적재하려면:

```bash
uv run python scripts/run_pipeline.py --sources all
```

특정 소스만 적재하려면:

```bash
uv run python scripts/run_pipeline.py --sources seed,wb,ofac
```

원천 데이터 재다운로드가 필요하면:

```bash
uv run python scripts/run_pipeline.py --sources all --full-refresh
```

GDELT 과거 백필(기간 지정) 예시:

```bash
uv run python scripts/run_pipeline.py --sources gdelt --gdelt-start-date 2020-01-01 --gdelt-end-date 2020-06-30
```

GDELT 날짜 옵션 규칙:
- `--gdelt-start-date YYYY-MM-DD`
- `--gdelt-end-date YYYY-MM-DD` (단독 사용 불가)
- `--gdelt-start-date`만 주면 종료일은 실행일(오늘)로 자동 설정
- 날짜 옵션은 `--sources`에 `gdelt`가 포함된 경우에만 사용 가능

참고:
- 사건 데이터는 `UCDP_GED(1989-01-01~2024-12-31)` + `ACLED(1996-12-28~현재)`를 병합해 사용합니다.
- `2026-03-03` 적재 기준 ACLED 최신 사건일은 `2026-02-21`입니다.
- ACLED는 주간 집계 스냅샷이며 사건 건수는 `event_count` 컬럼으로 집계됩니다.
- 파이프라인 실행 상태는 `_pipeline_state` 테이블에 기록됩니다.

### 3-1. 현재 데이터 스냅샷(`2026-03-03` 실행 기준)

아래 값은 `data/warehouse/geopolitical.duckdb`에서 직접 조회한 최신 범위입니다.

- `fact_incident`: `1989-01-01` ~ `2026-02-21` (총 사건 `3,308,883`, 사망자 `6,469,058`, 국가 `232`)
- `country_week_agg`: `1988-12-26` ~ `2026-02-16`
- `country_month_agg`: `1989-01-01` ~ `2026-02-01`
- `grs_monthly` 행 존재 범위: `1989-01-01` ~ `2026-02-01` (국가 `232`)
- `grs_monthly.grs_0_100` 비NULL 최신 월: `2024-12-01`
- `fact_diplomatic_action`: `2017-01-23` ~ `2026-03-03` (총 `18,751`건)
- `country_week_news`, `fact_news_pulse`: 현재 적재 `0`건 (`GDELT` 상태: `partial`)

재확인용 쿼리:

```bash
uv run python - <<'PY'
import duckdb
con = duckdb.connect("data/warehouse/geopolitical.duckdb", read_only=True)
print(con.execute("SELECT MIN(event_date), MAX(event_date) FROM fact_incident").fetchall())
print(con.execute("SELECT MAX(month_start) FROM grs_monthly WHERE grs_0_100 IS NOT NULL").fetchall())
print(con.execute("SELECT MIN(action_date), MAX(action_date), COUNT(*) FROM fact_diplomatic_action").fetchall())
print(con.execute("SELECT COUNT(*) FROM fact_news_pulse").fetchall())
PY
```

## 4. 품질 점검

적재 후 검증 SQL을 실행해 중복, 좌표 오류, 커버리지 갭 등을 확인합니다.

```bash
uv run python - <<'PY'
from pathlib import Path
from pipeline.db import get_connection

conn = get_connection()
sql_text = Path("sql/queries/validation.sql").read_text()
for stmt in [s.strip() for s in sql_text.split(";") if s.strip()]:
    print(conn.execute(stmt).fetchall())
PY
```

## 5. 대시보드용 핵심 데이터셋 확인

Tableau에서 주로 쓰는 뷰/테이블은 아래입니다.

1. `country_month_agg`: 월 단위 사건/사망 집계
2. `country_week_agg`: 주 단위 사건/민간인 타격 집계
3. `country_year_diplomatic`: 국가-연도 외교조치 집계
4. `country_week_news`: 뉴스 기사량/평균 톤
5. `grs_monthly`: 월별 지정학 리스크 점수(0~100)

## 6. Tableau 연결

1. Tableau Desktop에서 DuckDB 파일(`data/warehouse/geopolitical.duckdb`)에 연결합니다.
2. 위의 뷰/테이블을 데이터 소스로 추가합니다.
3. 키 필드 기준으로 관계를 설정합니다.
   - 국가: `country_iso3` 또는 `country_focus_iso3`
   - 시간: `week_start`, `month_start`, `year_start`
4. 성능을 위해 원시 팩트보다 집계 뷰를 우선 사용합니다.

## 7. 시트 구성(권장 순서, 데이터 소스 상세)

아래는 각 시트를 만들 때 **Tableau 선반 기준(Columns/Rows/Marks/Filters)** 으로 바로 따라할 수 있게 정리한 절차입니다.

공통 규칙:
- 날짜 필드는 가능하면 `연속형(Continuous)`으로 사용합니다.
- 수치 필드는 명시하지 않으면 `SUM` 집계를 기본으로 사용합니다.
- 국가 필터는 대시보드에서 한 번만 만들고 `Apply to Worksheets > All Using Related Data Sources`로 공통 적용합니다.
- 필드명이 데이터 소스별로 다를 수 있으니(`country_iso3` vs `country_focus_iso3`) 같은 의미 필드로 매핑합니다.

### 7-1. KPI 시트

목표: 최근 30일 기준 핵심 숫자(사건 수, 사망자, 제재 건수, 평균 톤) 표시

사용 데이터 소스:
- 사건/사망: `country_week_agg`
- 제재 건수: `fact_diplomatic_action` (`action_type='sanction'`)
- 평균 톤: `country_week_news`

구성 순서:
1. KPI를 한 시트에 모두 넣지 말고, 지표별로 시트를 분리합니다.
2. 각 시트는 공통으로 아래 형태를 사용합니다.
   - `Columns`: 비움
   - `Rows`: 비움
   - `Marks`: `Text`
   - `Text`: KPI 값 1개만 배치
   - `Filters`: 최신 데이터 기준 최근 30일 + (필요 시) 국가/권역
3. 계산 필드(권장)
   - `Latest Week`: `{ FIXED : MAX([week_start]) }`
   - `Latest Action Date`: `{ FIXED : MAX([action_date]) }`
4. `KPI_사건수_30일` (`country_week_agg`)
   - `Text`: `SUM([incident_count])`
   - `Filters`: `[week_start] >= DATEADD('day', -30, [Latest Week])`
5. `KPI_사망자_30일` (`country_week_agg`)
   - `Text`: `SUM([fatalities_total])`
   - `Filters`: `[week_start] >= DATEADD('day', -30, [Latest Week])`
6. `KPI_제재_30일` (`fact_diplomatic_action`)
   - `Text`: `COUNT([action_id])`
   - `Filters`: `[action_type] = 'sanction'`, `[action_date] >= DATEADD('day', -30, [Latest Action Date])`
7. `KPI_평균톤_30일` (`country_week_news`)
   - `Text`: `AVG([avg_tone])`
   - `Filters`: `[week_start] >= DATEADD('day', -30, [Latest Week])`
8. 서식(권장)
   - 숫자 포맷: 사건/사망/제재는 정수, 평균 톤은 소수점 2자리
   - 제목: `KPI | 사건 수(30일)`처럼 기간을 명시
9. 대시보드에서 4개 KPI 시트를 가로 컨테이너에 배치합니다.

권장 필드:
- `country_iso3` 또는 `country_focus_iso3` (국가 필터 연동)
- `region_code` (권역 필터 연동)

### 7-2. 지도 시트

목표: 국가 단위 위험도 + 사건 포인트 드릴다운

사용 데이터 소스:
- 국가 색상 지도: `grs_monthly`
- 사건 포인트 드릴다운: `fact_incident`
- 국가명 표시: `dim_country` (선택)

구성 순서:
1. `Map_GRS` 시트 생성: `grs_monthly`로 국가 코로플레스 맵을 만듭니다.
2. `Map_GRS` 선반 배치
   - `Columns`: 비움 (자동 생성된 `Longitude (generated)` 유지)
   - `Rows`: 비움 (자동 생성된 `Latitude (generated)` 유지)
   - `Marks`: `Map`
   - `Detail`: `country_iso3`
   - `Color`: `AVG([grs_0_100])`
   - `Filters`: `[grs_0_100]` 비NULL + `month_start`를 최신 점수 월 1개만 선택
   - 계산 필드 예시: `Latest Scored Month = { FIXED : MAX(IF NOT ISNULL([grs_0_100]) THEN [month_start] END) }`
3. `Map_Incident_Detail` 시트 생성: `fact_incident`의 `latitude`, `longitude`로 점 맵을 만듭니다.
4. `Map_Incident_Detail` 선반 배치
   - `Columns`: `AVG([longitude])`
   - `Rows`: `AVG([latitude])`
   - `Marks`: `Circle`
   - `Size`: `SUM([fatalities_best])`
   - `Color`: `[event_type]`
   - `Detail`: `[incident_id]`
   - `Filters`: `event_date` 기간, 국가(대시보드 액션으로 전달)
5. 대시보드에서 `Map_GRS` 클릭 시 `country_iso3`와 기간이 `Map_Incident_Detail`로 전달되도록 액션 필터를 설정합니다.

권장 필드:
- `grs_monthly.country_iso3`, `grs_monthly.month_start`, `grs_monthly.grs_0_100`
- `fact_incident.country_iso3`, `fact_incident.event_date`, `fact_incident.event_type`, `fact_incident.fatalities_best`

### 7-3. 타임라인 시트

목표: 월별 사건 추세와 리스크 점수 추세를 함께 비교

사용 데이터 소스:
- `country_month_agg`
- `grs_monthly`

구성 순서:
1. Tableau 관계(Relationship)로 두 소스를 연결합니다.
   - 키: `country_iso3`, `month_start`
2. `Timeline_Risk_vs_Incident` 시트를 생성합니다.
3. 선반 배치
   - `Columns`: `month_start` (Month, Continuous)
   - `Rows`: `SUM([incident_count])`
4. 같은 `Rows` 선반에 `AVG([grs_0_100])`를 추가하고 `Dual Axis`를 선택합니다.
5. `Marks` 카드(축별 분리) 설정
   - `SUM(incident_count)` 카드: `Line`, 색상 파랑
   - `AVG(grs_0_100)` 카드: `Line`, 색상 빨강
6. 필요 시 세 번째 지표 `SUM([fatalities_total])`을 추가하고 `Measure Values` 기반 다중 라인으로 전환합니다.
7. `Filters`: `month_start` 기간, 국가/권역 공통 필터 적용
   - 리스크 라인은 필요 시 `[grs_0_100]` 비NULL 필터를 추가해 공백 구간을 분리합니다.

권장 필드:
- `country_month_agg.month_start`, `incident_count`, `fatalities_total`
- `grs_monthly.month_start`, `grs_0_100`, `coverage_flag`

### 7-4. 외교 조치 시트

목표: 국가-연도 기준 외교 조치 유형 변화를 비교

사용 데이터 소스:
- 기본: `country_year_diplomatic`
- 상세 드릴다운: `fact_diplomatic_action`

구성 순서:
1. `Diplomatic_Yearly` 시트 생성
2. 선반 배치
   - `Columns`: `year_start` (Year)
   - `Rows`: `SUM([action_count])`
   - `Marks`: `Bar`
   - `Color`: `[action_type]`
   - `Filters`: 국가/권역, 연도 범위
3. `fact_diplomatic_action` 기반 상세 테이블 시트를 하나 추가합니다.
4. 상세 테이블 선반 배치
   - `Rows`: `action_date`, `instrument_name`, `legal_basis`
   - `Text`: `source_url` (또는 Tooltip에 배치)
   - `Filters`: 대시보드 액션으로 국가/연도 연동
5. 연도 막대 클릭 시 상세 테이블이 같은 국가/연도로 필터되도록 액션을 설정합니다.

권장 필드:
- `country_year_diplomatic.year_start`, `country_iso3`, `action_type`, `action_count`
- `fact_diplomatic_action.action_date`, `instrument_name`, `legal_basis`, `source_url`

### 7-5. 뉴스 패널 시트

목표: 주간 뉴스 관심도와 톤 변화를 모니터링하고 원문 링크로 이동

사용 데이터 소스:
- 추세: `country_week_news`
- 기사 목록: `fact_news_pulse`

구성 순서:
1. `News_Trend` 시트 생성
   - 참고: `2026-03-03` 기준 뉴스 테이블은 0건이라 시트가 비어 있을 수 있습니다.
2. 선반 배치
   - `Columns`: `week_start` (Week, Continuous)
   - `Rows`: `SUM([article_count])`
3. 같은 `Rows`에 `AVG([avg_tone])`를 추가하고 `Dual Axis`를 적용합니다.
4. `Marks` 카드 설정
   - `SUM(article_count)`: `Bar` 또는 `Line`
   - `AVG(avg_tone)`: `Line`
   - `Tooltip`: 주차, 기사 수, 평균 톤
5. `News_Headlines` 시트 생성: `published_at_utc`, `title`, `source_domain`, `url` 테이블을 만듭니다.
6. `News_Headlines` 선반 배치
   - `Rows`: `published_at_utc`, `title`
   - `Text`: `source_domain`
   - `Detail`: `url`
   - `Filters`: 주차/국가(상단 추세 시트에서 액션 전달)
   - `Tooltip`: `url` 표시 후 `URL Action`으로 원문 열기
7. 추세 차트에서 주차 선택 시 기사 목록이 해당 기간/국가로 필터되도록 액션을 연결합니다.

권장 필드:
- `country_week_news.week_start`, `country_focus_iso3`, `article_count`, `avg_tone`
- `fact_news_pulse.published_at_utc`, `title`, `source_domain`, `url`, `country_focus_iso3`

### 7-6. 대시보드 조립 순서

1. 상단: KPI 4개 시트
2. 중앙: `Map_GRS` + `Map_Incident_Detail`
3. 하단 좌: `Timeline_Risk_vs_Incident`
4. 하단 중: `Diplomatic_Yearly`
5. 하단 우: `News_Trend` + `News_Headlines`
6. 각 컨테이너 배치 권장
   - 루트: `Vertical`
   - 상단 KPI: `Horizontal`
   - 중앙 지도 2개: `Horizontal`
   - 하단 3패널: `Horizontal` (각 패널 내부는 필요 시 `Vertical`)
7. 필터 표시 위치 권장
   - 상단 우측: 국가, 권역, 기간
   - `Apply to Worksheets > All Using Related Data Sources` 설정으로 전체 연동
8. 액션 우선순위
   - 지도 클릭 필터 -> 타임라인/외교/뉴스
   - 타임라인 기간 선택 -> 뉴스 헤드라인
   - 외교 연도 클릭 -> 외교 상세 테이블

필수 공통 필터:
- 국가(`country_iso3`/`country_focus_iso3`)
- 권역(`region_code`)
- 기간(`event_date`, `month_start`, `week_start`, `action_date`)

운영 팁:
- 데이터 최신성은 `_pipeline_state.last_run_utc`로 확인합니다.
- 뉴스 소스(`gdelt`)를 적재하지 않았다면 뉴스 시트는 비어 있을 수 있습니다.

## 8. 운영 루틴(추천)

1. 일 1회(또는 주기)로 `run_pipeline.py` 실행
2. 실행 후 `validation.sql` 점검
3. 이상치 확인 후 Tableau 데이터 새로고침
4. 월 단위로 `grs_monthly` 추세 변화와 커버리지(`coverage_flag`) 모니터링
