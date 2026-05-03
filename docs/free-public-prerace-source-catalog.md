# 무료 공개 출전표 원천 소스 카탈로그

이 문서는 `출전표 확정 시점 이전`에 인증 없이 접근 가능한 공식 KRA 웹 소스를 운영 카탈로그로 고정한다. 코드 기준선은 `apps/api/infrastructure/prerace_sources/` 이다.

## 목적

- API 키 없이도 안정적으로 원천 응답을 가져올 수 있는 공개 소스를 명시한다.
- 소스별 역할을 `hard-required`, `soft-required`, `supporting`으로 나눈다.
- 이후 파서/정규화/리비전 저장 단계가 동일한 커넥터 계약 위에서 동작하게 한다.

## 공통 계약

- 모든 소스는 `PublicSourceSpec`으로 식별한다.
- 모든 커넥터는 `BasePublicSourceConnector.fetch_raw()`를 구현한다.
- 반환값은 `RawSourceResponse`이며 아래 메타데이터를 반드시 포함한다.
  - `spec.source_id`
  - `requested_url`
  - `status_code`
  - `headers`
  - `body`
  - `fetched_at`
  - `encoding`

## 소스 목록

| source_id | 역할 | 공개 URL | tier | 비고 |
| --- | --- | --- | --- | --- |
| `entry_meeting_list` | 일자별 출전정보 목록 | `/chulmainfo/ChulmaDetailInfoList.do` | `hard_required` | 오늘의경주 PDF 링크 포함 |
| `entry_race_card` | 경주별 상세 출전표 | `/chulmainfo/chulmaDetailInfoChulmapyo.do` | `hard_required` | `meet`, `rcDate`, `rcNo` 폼 전송 |
| `entry_change_bulletin` | 말취소/기수변경 공지 | `/raceFastreport/ChulmapyoChange.do` | `hard_required` | 직전 변경 반영용 |
| `track_status` | 경주로 상태/함수율 | `/chulmainfo/trackView.do` | `hard_required` | 당일 수시 갱신 |
| `horse_profile` | 경주마 프로필 | `/racehorse/ProfileHorsenameKinds.do` | `soft_required` | `hrNo` 기반 |
| `horse_training_state` | 경주마 조교 상태 | `/racehorse/profileTrainState.do` | `soft_required` | `hrNo` 기반 |
| `jockey_active_list` | 현역 기수 목록 | `/jockey/ProfileJockeyListActive.do` | `soft_required` | 프로필 진입점 |
| `trainer_profile_list` | 조교사 목록 | `/trainer/profileTrainerList.do` | `soft_required` | 프로필 진입점 |
| `owner_profile_list` | 마주 목록 | `/owner/profileOwnerList.do` | `soft_required` | 프로필 진입점 |

## 운영 원칙

1. `requires_auth`는 항상 `false`여야 한다.
2. 원천 응답은 파싱 전 단계에서 그대로 보존할 수 있어야 한다.
3. 공개 페이지 인코딩은 UTF-8 고정으로 가정하지 않고, `euc-kr` fallback을 지원한다.
4. hard-required 소스는 실패 시 재시도 후 명시적 오류를 반환해야 한다.
5. soft-required 소스는 향후 파서 단계에서 빈 블록으로 강등할 수 있지만, 원천 fetch 실패 로그는 남겨야 한다.
