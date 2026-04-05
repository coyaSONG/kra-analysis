# Candidate H: Deep Policy Module 분리와 마이그레이션

이 ExecPlan은 살아 있는 문서다. 구현이 진행되면 `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`를 반드시 갱신한다.

이 문서는 저장소 루트의 `.agent/PLANS.md` 규약을 따른다. 이후 구현자는 이 파일만 읽고도 작업을 이어갈 수 있어야 한다.

## Purpose / Big Picture

이 변경이 끝나면 v2 API 라우터는 더 이상 원시 API 키 문자열을 사용자 식별자로 전달하지 않는다. 대신 `AuthenticatedPrincipal`이라는 명시적 호출자 객체를 받고, 인증(authentication), 권한(authority 판단), 사용량 회계(accounting)는 각각 분리된 내부 서비스가 담당한다. 결과적으로 같은 요청에서 인증과 카운터 증가가 섞여 두 번 실행되거나, 라우터와 미들웨어가 서로 다른 기준으로 호출자를 해석하는 문제가 사라진다.

구현 후에는 `/api/v2/collection/*`와 `/api/v2/jobs/*` 경로가 동일한 정책 모듈을 통해 호출자를 해석한다. 권한 부족은 일관되게 403, 인증 실패는 401, 일일 한도나 속도 제한 초과는 429로 응답하며, 요청당 사용량 이벤트가 별도 회계 계층에서 기록된다. 이 동작은 pytest와 HTTP 요청 시나리오로 검증한다.

## Progress

- [x] (2026-03-19 22:39 KST) `apps/api/dependencies/auth.py`, `apps/api/middleware/rate_limit.py`, `apps/api/routers/collection_v2.py`, `apps/api/routers/jobs_v2.py`, `apps/api/services/job_service.py`, `apps/api/models/database_models.py`를 읽고 현재 인증/권한/사용량 흐름을 파악했다.
- [x] (2026-03-19 22:39 KST) 세 가지 인터페이스 후보를 비교했고, 외부에는 작은 facade를 두되 내부는 인증·권한·회계를 분리하는 Candidate H를 최종안으로 선택했다.
- [x] (2026-03-19 22:39 KST) `AuthenticatedPrincipal` 중심 인터페이스, 코드 스케치, 단계별 마이그레이션, 하위호환 전략을 이 문서에 정리했다.
- [x] (2026-03-20 03:31 KST) 정책 모듈 구현과 기존 `dependencies/auth.py` 래퍼 연결 완료. `policy/` 패키지에 `principal.py`, `authentication.py`, `authorization.py`, `accounting.py`가 추가됐고 `require_action()`은 `authenticate -> authorize -> reserve`를 수행하며 `request.state`에 principal/action/reservation을 남긴다. `require_api_key_record()`를 추가해 레거시 helper가 검증을 한 번만 수행하도록 정리했고 `jobs_v2`, `collection_v2`는 `principal.owner_ref`를 서비스에 전달한다. `usage_events` 모델, migration, `PolicyAccountingMiddleware`가 추가돼 policy-guarded 요청의 append-only usage event가 기록된다.
- [x] 라우터와 서비스의 `str` 기반 사용자 식별 제거 및 `AuthenticatedPrincipal` 기반 호출 경로 전환.
- [x] 사용량 회계 이중쓰기와 최종 레거시 제거.

## Surprises & Discoveries

- Observation: `require_api_key()`는 반환 타입이 `str`인데 `require_permissions()`는 `APIKey` 객체를 기대한다. 표준 FastAPI `Depends` 흐름으로는 타입과 의미가 맞지 않는다.
  Evidence: `apps/api/dependencies/auth.py`에서 `require_api_key`는 문자열을 반환하고, 같은 파일의 `require_permissions`는 `api_key_obj.permissions`를 읽는다.

- Observation: `verify_api_key()`가 인증과 사용량 증가를 동시에 수행한다. 이 함수가 재사용되면 같은 요청에서 인증과 카운터 증가가 결합된 채 다시 실행될 수 있다.
  Evidence: `apps/api/dependencies/auth.py`에서 DB 조회 뒤 `last_used_at`, `total_requests`, `today_requests`를 직접 갱신하고 `commit()`까지 수행한다.

- Observation: 리소스 접근 헬퍼는 현재 런타임 경로와 소유자 규약이 다르다.
  Evidence: `apps/api/routers/collection_v2.py`는 작업 생성 시 `user_id=api_key` 문자열을 `Job.created_by`에 저장한다. 반면 `apps/api/dependencies/auth.py`의 `check_resource_access()`는 `Job.created_by == api_key.name`을 비교한다.

- Observation: v2 런타임은 사실상 API key 전용인데 JWT 경로는 테스트 중심으로만 남아 있다.
  Evidence: `apps/api/routers/*.py`에서 실제로 사용하는 인증 의존성은 `require_api_key`뿐이고, JWT 관련 함수는 테스트 파일들에서만 직접 호출된다.

- Observation: 속도 제한은 인증된 주체가 아니라 헤더 문자열 또는 IP에 묶여 있다.
  Evidence: `apps/api/middleware/rate_limit.py`의 `_get_client_id()`는 `x-api-key` 헤더 또는 IP 주소만 사용한다.

- Observation: jobs 라우터는 owner 규약을 바꾸지 않고도 principal 타입을 먼저 받을 수 있었다.
  Evidence: `jobs_v2.py`를 `require_principal()` 기반으로 바꾼 뒤에도 integration tests가 raw API key 기반 ownership 계약을 유지한 채 통과했다.

- Observation: 레거시 resource access helper는 같은 요청에서 검증을 두 번 실행해 usage 카운터를 이중 증가시킬 수 있었다.
  Evidence: `require_resource_access()`가 `require_api_key` dependency 뒤에 `verify_api_key()`를 다시 호출했다. `require_api_key_record()` 도입 후 `tests/unit/test_auth_resource_access.py::test_require_resource_access_verifies_db_key_once`로 요청당 1회 증가를 고정했다.

- Observation: owner migration 과도기에는 `Job.created_by`와 `Prediction.created_by`를 raw key와 key name 둘 다로 읽어야 했다.
  Evidence: 기존 테스트는 환경 키 이름 `"Environment Key"`를 owner로 저장했고, 새 principal 경로는 raw key를 owner로 사용한다. `check_resource_access()`가 두 표현 모두 허용해야 테스트와 활성 경로가 동시에 유지된다.

- Observation: usage accounting은 dependency finalizer보다 middleware finalize가 더 자연스럽다.
  Evidence: response status와 path를 함께 기록하려면 dependency 내부보다 app-level finalize 지점이 필요했고, `PolicyAccountingMiddleware`를 추가한 뒤 `tests/integration/test_policy_accounting.py`에서 `jobs.list`/`jobs.read` 요청의 usage event가 append-only로 기록됐다.

## Decision Log

- Decision: `AuthenticatedPrincipal`을 라우터와 서비스가 공유하는 유일한 호출자 표현으로 채택한다.
  Rationale: 현재는 원시 API 키 문자열, `APIKey` ORM 객체, JWT payload dict가 섞여 있어서 호출자 의미가 일관되지 않다. 하나의 안정된 타입이 필요하다.
  Date/Author: 2026-03-19 / Codex

- Decision: 공개 인터페이스는 작은 facade로 유지하고, 내부 구현은 `authentication`, `authorization`, `accounting` 세 서비스로 분리한다.
  Rationale: 깊은 모듈은 외부 메서드 수를 줄이고 내부 복잡도를 숨기는 것이 유리하다. 동시에 요구사항상 인증·권한·회계는 명확히 분리되어야 한다.
  Date/Author: 2026-03-19 / Codex

- Decision: 초기 단계에서는 기존 `api_keys` 테이블의 `permissions`, `rate_limit`, `daily_limit`, `today_requests`, `total_requests`를 읽어오되, 회계의 정본(source of truth)은 점진적으로 append-only 이벤트 테이블로 옮긴다.
  Rationale: 바로 스키마를 뒤집기보다 읽기 호환성을 유지한 채 이중쓰기부터 시작하는 편이 안전하다.
  Date/Author: 2026-03-19 / Codex

- Decision: 라우터는 권한 이름(`read`, `write`, `admin`) 대신 액션 이름(`jobs.read`, `jobs.cancel`, `collection.collect`)을 선언하고, 매핑은 정책 모듈 내부로 숨긴다.
  Rationale: 외부 인터페이스를 사용 사례 중심으로 바꾸면 향후 권한 모델이 바뀌어도 라우터 코드는 안정적으로 유지된다.
  Date/Author: 2026-03-19 / Codex

- Decision: 첫 구현 절편에서는 `owner_ref`를 raw API key와 동일하게 유지한다.
  Rationale: jobs ownership 계약과 기존 데이터가 이미 raw key 문자열에 묶여 있으므로, principal 타입 도입과 owner 규약 전환을 같은 단계에 묶지 않는 편이 안전하다.
  Date/Author: 2026-03-20 / Codex

## Outcomes & Retrospective

현재 단계의 산출물은 구현 계획과 인터페이스 설계다. 가장 중요한 성과는 v2 런타임의 실제 결합 지점을 확인했고, 특히 인증과 사용량 증가가 한 함수에 합쳐져 있으며 작업 소유자 규약도 불일치한다는 점을 명확히 했다는 것이다. 구현 시 가장 큰 위험은 기존 테스트들이 원시 API 키 문자열에 암묵적으로 의존하고 있다는 점이며, 따라서 래퍼 기반의 점진적 전환이 필요하다.

## Context and Orientation

현재 활성 런타임은 `apps/api/main_v2.py`이고, 공개 라우터는 `apps/api/routers/collection_v2.py`와 `apps/api/routers/jobs_v2.py`다. 두 라우터는 모두 `apps/api/dependencies/auth.py`의 `require_api_key()`에 의존한다. 이 함수는 API 키를 검증할 뿐 아니라 DB 사용량 카운터까지 증가시킨다. 즉 인증과 회계가 분리되어 있지 않다.

`apps/api/services/job_service.py`는 `create_job(..., user_id: str, ...)`처럼 문자열 기반 식별자를 받으며, `Job.created_by`에 그대로 저장한다. 이 값은 현재 API 키 문자열이다. 한편 같은 `auth.py` 안의 `check_resource_access()`는 `APIKey.name`으로 소유권을 확인한다. 같은 “호출자”를 가리키는 값이 경로마다 다르다.

이 문서에서 “principal”은 인증된 호출자다. 사람 사용자, API key 소유 주체, 내부 서비스 계정 같은 모든 호출자를 공통 방식으로 표현하는 객체다. “authorization”은 principal이 특정 액션을 수행해도 되는지 판단하는 단계다. “usage accounting”은 요청 수, 비용 단위, 제한 초과 여부, 이벤트 기록을 다루는 단계다. deep module은 이 세 가지를 내부에서 처리하지만, 라우터에는 작고 안정된 인터페이스만 보여 주는 모듈을 뜻한다.

## Interface Candidates

첫 번째 후보는 초소형 단일 메서드 인터페이스다. 예를 들어 `policy.enforce(request, action="jobs.read") -> AuthenticatedPrincipal` 하나만 두고, 내부에서 인증, 권한, 회계를 모두 처리한다. 이 방식은 사용하기 쉽지만 회계만 따로 재시도하거나, 인증만 테스트하기 어렵다. 요구사항이 “분리”를 강조하므로 내부 관찰성과 테스트 분리가 약하다.

두 번째 후보는 세 서비스가 모두 외부에 노출되는 방식이다. 예를 들어 `authenticate()`, `authorize()`, `reserve_usage()`, `record_usage()`를 라우터와 미들웨어가 직접 조합한다. 분리는 명확하지만 각 라우터가 정책 조합을 다시 배워야 하므로 shallow module이 되기 쉽다. 현재 저장소처럼 FastAPI dependency와 middleware가 섞여 있는 구조에서는 오히려 실수 여지가 커진다.

세 번째 후보가 최종안인 Candidate H다. 외부에는 `require_principal()`과 `require_action(...)` 정도의 작은 진입점만 보여 주고, 내부에서는 `PrincipalAuthenticator`, `PolicyAuthorizer`, `UsageAccountant`가 독립적으로 동작한다. 라우터는 “누가 왔는가”와 “무슨 액션을 하려는가”만 선언하고, 인증 자격 증명 해석, 리소스 소유권, 일일 한도, 이벤트 기록은 내부로 숨긴다. 이 방식이 가장 깊다.

## Plan of Work

우선 `apps/api/policy/` 패키지를 새로 만든다. 이 패키지는 `principal.py`, `authentication.py`, `authorization.py`, `accounting.py`, `dependencies.py`, `legacy.py`로 나눈다. `principal.py`는 호출자 표현과 액션/리소스/한도 타입을 정의한다. `authentication.py`는 API key와 JWT를 읽어 principal로 변환한다. `authorization.py`는 액션과 리소스를 받아 허용 여부를 판단한다. `accounting.py`는 속도 제한, 일일 한도, 이벤트 기록을 처리한다. `dependencies.py`는 FastAPI용 진입점이며, `legacy.py`는 기존 `dependencies/auth.py` 함수 시그니처를 유지하는 어댑터다.

다음으로 `apps/api/dependencies/auth.py`를 즉시 삭제하지 말고 얇은 래퍼로 바꾼다. `verify_api_key()`는 더 이상 카운터를 증가시키지 않고 `PrincipalAuthenticator.authenticate_api_key()`를 호출하게 한다. `require_api_key()`는 내부적으로 `require_principal()`을 사용하되 기존 반환 타입인 문자열 API key를 유지한다. 이 래퍼는 하위호환을 위한 임시 계층이며 새 코드는 직접 사용하지 않는다.

그 다음 `apps/api/routers/collection_v2.py`와 `apps/api/routers/jobs_v2.py`를 principal 기반으로 옮긴다. 예를 들어 `api_key: str = Depends(require_api_key)` 대신 `principal: AuthenticatedPrincipal = Depends(require_action("jobs.read"))`처럼 바꾼다. 서비스 계층도 문자열 `user_id`를 받지 않고 `owner_ref` 또는 `principal`을 받게 바꾼다. `Job.created_by`는 당장 제거하지 않고, 새 helper 함수 `principal.owner_ref`를 통해 안정된 값으로 채운다.

회계는 두 단계로 나눈다. 요청 시작 전에는 한도와 속도 제한을 확인하는 `reserve_usage()`를 호출하고, 응답 후에는 `record_usage()`로 결과 이벤트를 남긴다. 초기에는 기존 `APIKey.today_requests`와 `APIKey.total_requests`를 계속 업데이트하되, 동시에 새 `usage_events` 테이블에 append-only 이벤트를 기록한다. 이중쓰기가 안정화되면 카운터 컬럼은 projection으로만 남기거나 제거할 수 있다.

마지막으로 레거시 헬퍼를 걷어낸다. `require_permissions`, `require_admin`, `require_write`, `check_resource_access`, `require_resource_access`는 모두 `require_action()`과 리소스 resolver로 치환한다. JWT helper는 유지하되 principal 생성기로 위임하고, 테스트도 payload dict 대신 principal을 기준으로 갱신한다.

## Interfaces and Dependencies

최종 상태에서 다음 타입과 함수가 존재해야 한다.

`apps/api/policy/principal.py`에 아래 타입을 정의한다.

    from dataclasses import dataclass, field
    from typing import Any, Literal, Mapping

    PrincipalType = Literal["api_key", "user", "service"]
    AuthMethod = Literal["api_key", "jwt"]
    PolicyAction = Literal[
        "collection.collect",
        "collection.collect_async",
        "collection.status.read",
        "collection.result.collect",
        "jobs.list",
        "jobs.read",
        "jobs.cancel",
    ]

    @dataclass(frozen=True, slots=True)
    class PolicyLimits:
        rate_limit_per_minute: int | None = None
        daily_request_limit: int | None = None

    @dataclass(frozen=True, slots=True)
    class AuthenticatedPrincipal:
        principal_id: str
        principal_type: PrincipalType
        subject_id: str
        owner_ref: str
        display_name: str | None
        auth_method: AuthMethod
        credential_id: str
        permissions: frozenset[str]
        limits: PolicyLimits
        attributes: Mapping[str, Any] = field(default_factory=dict)

`owner_ref`는 서비스 계층과 영속 저장이 사용하는 안정된 문자열이다. 원시 API key 전체를 저장하지 않는다. DB 기반 API key라면 `api_key:{id}`, 환경 변수 기반 키라면 `env_key:{sha256_prefix}`, JWT 사용자라면 `user:{sub}` 규약을 사용한다.

같은 파일에 리소스와 사용량 타입을 둔다.

    @dataclass(frozen=True, slots=True)
    class ResourceRef:
        resource_type: Literal["job", "race", "prediction"]
        resource_id: str

    @dataclass(frozen=True, slots=True)
    class UsageReservation:
        bucket_key: str
        reserved_units: int
        window_seconds: int

    @dataclass(frozen=True, slots=True)
    class UsageEvent:
        principal_id: str
        owner_ref: str
        action: PolicyAction
        units: int
        outcome: Literal["accepted", "rejected", "completed", "failed"]
        request_id: str | None
        resource: ResourceRef | None = None

`apps/api/policy/authentication.py`에는 principal을 만드는 서비스가 있어야 한다.

    class PrincipalAuthenticator:
        async def authenticate_request(
            self, request: Request, db: AsyncSession
        ) -> AuthenticatedPrincipal:
            ...

        async def authenticate_api_key(
            self, presented_key: str, db: AsyncSession
        ) -> AuthenticatedPrincipal:
            ...

        async def authenticate_bearer_token(
            self, token: str, db: AsyncSession
        ) -> AuthenticatedPrincipal:
            ...

이 서비스는 인증만 수행한다. 사용량 카운터를 증가시키지 않는다. DB commit도 하지 않는다.

`apps/api/policy/authorization.py`에는 액션과 리소스를 판단하는 서비스가 있어야 한다.

    class PolicyAuthorizer:
        async def authorize(
            self,
            principal: AuthenticatedPrincipal,
            action: PolicyAction,
            resource: ResourceRef | None,
            db: AsyncSession,
        ) -> None:
            ...

내부 규칙은 다음과 같이 시작한다. `collection.status.read`와 `jobs.list`는 `read`, `collection.collect*`와 `collection.result.collect`와 `jobs.cancel`은 `write`, 관리자 전용 액션이 생기면 `admin`으로 매핑한다. `jobs.read`와 `jobs.cancel`은 권한 검사 뒤에 소유권 검사도 함께 한다. 소유권은 `Job.created_by == principal.owner_ref`로 판단한다.

`apps/api/policy/accounting.py`에는 한도와 기록을 담당하는 서비스가 있어야 한다.

    class UsageAccountant:
        async def reserve(
            self,
            principal: AuthenticatedPrincipal,
            action: PolicyAction,
            units: int,
        ) -> UsageReservation:
            ...

        async def commit(
            self,
            reservation: UsageReservation,
            event: UsageEvent,
            db: AsyncSession,
        ) -> None:
            ...

        async def rollback(
            self,
            reservation: UsageReservation,
            reason: str,
        ) -> None:
            ...

`reserve()`는 Redis를 사용해 속도 제한과 일일 제한을 먼저 확인한다. `commit()`은 `usage_events`에 이벤트를 추가하고, 마이그레이션 단계에서는 기존 `api_keys.total_requests`와 `api_keys.today_requests`도 함께 갱신한다. 회계 저장 실패는 로그를 남기되 초기 단계에서는 요청 결과를 뒤집지 않는 fail-open을 택한다. 단, 한도 초과 판단 자체는 fail-closed여야 한다.

외부에 보이는 facade는 `apps/api/policy/dependencies.py`에 둔다.

    async def require_principal(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> AuthenticatedPrincipal:
        ...

    def require_action(
        action: PolicyAction,
        *,
        resource_type: str | None = None,
        resource_id_param: str | None = None,
        usage_units: int = 1,
    ):
        async def dependency(
            request: Request,
            db: AsyncSession = Depends(get_db),
        ) -> AuthenticatedPrincipal:
            ...
        return dependency

`require_action()`은 내부에서 `authenticate -> authorize -> reserve` 순서로 실행하고 `request.state.principal`, `request.state.policy_action`, `request.state.usage_reservation`를 채운다. 응답 후 `commit/rollback`은 별도 middleware 또는 dependency finalizer로 마무리한다.

최상위 조립용 facade는 선택적으로 `apps/api/policy/module.py`에 둘 수 있다.

    class PolicyModule:
        def __init__(
            self,
            authenticator: PrincipalAuthenticator,
            authorizer: PolicyAuthorizer,
            accountant: UsageAccountant,
        ) -> None:
            ...

        async def enforce(
            self,
            request: Request,
            action: PolicyAction,
            db: AsyncSession,
            resource: ResourceRef | None = None,
            usage_units: int = 1,
        ) -> AuthenticatedPrincipal:
            ...

이 facade는 테스트에서 조립 지점을 단순하게 만들기 위한 것이며, 라우터는 `require_action()`만 보면 된다.

## Code Sketch

라우터 사용 형태는 다음과 같이 바뀐다.

    @router.get("/")
    async def list_jobs(
        principal: AuthenticatedPrincipal = Depends(require_action("jobs.list")),
        db: AsyncSession = Depends(get_db),
    ):
        jobs, total_count = await job_service.list_jobs_with_total(
            db=db,
            owner_ref=principal.owner_ref,
            ...
        )

작업 조회는 리소스 접근 규칙을 action dependency에 숨긴다.

    @router.get("/{job_id}")
    async def get_job(
        job_id: str,
        principal: AuthenticatedPrincipal = Depends(
            require_action("jobs.read", resource_type="job", resource_id_param="job_id")
        ),
        db: AsyncSession = Depends(get_db),
    ):
        job = await job_service.get_job(job_id, db, owner_ref=principal.owner_ref)
        ...

기존 래퍼는 다음처럼 유지한다.

    async def require_api_key(
        x_api_key: str | None = Header(None, alias="X-API-Key"),
        db: AsyncSession = Depends(get_db),
    ) -> str:
        principal = await authenticator.authenticate_api_key(x_api_key, db)
        return x_api_key

이 래퍼는 “문자열 키가 필요한 기존 코드”만 위해 남긴다. 신규 코드는 절대 사용하지 않는다.

서비스 계층도 명시적으로 바꾼다.

    async def create_job(
        self,
        job_type: str,
        parameters: dict[str, Any],
        owner_ref: str,
        db: AsyncSession,
    ) -> Job:
        job = Job(
            type=job_type,
            parameters=parameters,
            status="pending",
            created_by=owner_ref,
        )

## Phases

### Phase 0: 보호막 테스트 추가

구현 전 현재 행태를 고정하는 테스트를 추가한다. 최소한 다음을 커버해야 한다. API key 인증은 성공하지만 인증만으로 `today_requests`가 증가하지 않는 새 경로 테스트, `jobs.read`가 자기 소유 작업만 볼 수 있는 테스트, 환경 변수 API key와 DB API key가 모두 `AuthenticatedPrincipal`로 정규화되는 테스트, 사용량 기록 실패가 요청을 500으로 만들지 않는 테스트다. 이 단계의 목표는 리팩터링 중 의미를 잃지 않는 것이다.

### Phase 1: policy 패키지와 principal 도입

`apps/api/policy/`를 추가하고 `AuthenticatedPrincipal`, authenticator, authorizer, accountant의 빈 뼈대를 구현한다. `dependencies/auth.py`는 이 모듈을 호출하는 thin wrapper로 바꾼다. 이 단계에서는 기존 라우터 시그니처를 유지해도 된다. 핵심은 인증과 회계의 분리를 코드 수준에서 먼저 만드는 것이다.

### Phase 2: 라우터를 principal 기반으로 전환

`collection_v2.py`와 `jobs_v2.py`를 `require_action()` 사용 방식으로 바꾼다. `JobService`는 더 이상 `user_id: str`를 받지 않고 `owner_ref: str`를 받는다. 필요한 경우 `list_jobs_with_total`, `get_job`, `cancel_job`의 필터 명도 함께 정리한다. 이 단계가 끝나면 활성 v2 라우터에서 원시 API key 문자열 전달은 제거된다.

### Phase 3: 회계 이중쓰기와 이벤트 정본 도입

새 SQL migration으로 `usage_events` 테이블을 추가한다. 이 테이블은 최소한 `id`, `principal_id`, `owner_ref`, `action`, `units`, `outcome`, `request_id`, `resource_type`, `resource_id`, `created_at` 컬럼을 가져야 한다. `UsageAccountant.commit()`은 이 테이블에 append-only 기록을 남기고, 동시에 기존 `api_keys` 카운터도 유지한다. 운영 안정성이 확인되면 대시보드나 관리 쿼리는 이 테이블 기반으로 바꾼다.

### Phase 4: 레거시 제거와 권한 모델 정리

`require_permissions`, `require_admin`, `require_write`, `check_resource_access`, `require_resource_access`를 deprecated 표시 후 제거한다. 테스트도 principal/action 중심으로 정리한다. 마지막으로 `require_api_key()` 문자열 래퍼를 내부 전용으로 축소하거나 삭제한다.

## Backward Compatibility

하위호환의 핵심은 “호출자는 바꾸되 외부 계약은 급격히 깨지지 않게 한다”이다. 이를 위해 첫째, `apps/api/dependencies/auth.py` 파일 경로는 유지한다. 기존 import가 깨지지 않도록 함수 이름도 일단 유지하되 내부 구현만 새 policy 모듈로 위임한다.

둘째, DB 스키마는 additive하게 바꾼다. `jobs.created_by`와 `api_keys.*` 카운터 컬럼은 당장 제거하지 않는다. 새 모듈은 `created_by`에 `principal.owner_ref`를 쓰고, 레거시 데이터와 비교가 필요하면 읽기 시점에 “구 문자열 API key”와 “새 owner_ref” 둘 다 매칭하는 과도기 헬퍼를 둔다. 운영 데이터에 이미 원시 API key가 들어 있을 가능성이 있으므로, 이중 매칭 기간이 필요하다.

셋째, 권한 의미는 유지하고 표현만 바꾼다. 기존 `read`, `write`, `admin` 값은 그대로 `AuthenticatedPrincipal.permissions`에 담는다. 라우터는 액션 이름만 선언하고, 내부 authorizer가 기존 permission으로 매핑한다. 즉 외부 사용 사례는 더 명확해지지만 저장된 권한 데이터는 바로 변경하지 않는다.

넷째, JWT helper는 삭제하지 않고 principal 기반 어댑터로 남긴다. 실제 런타임은 API key 위주지만 테스트와 향후 사용자 기반 인증 확장을 위해 함수 시그니처는 유지한다.

다섯째, 회계는 dual-write로 이동한다. 새 `usage_events`가 정본이 되기 전까지는 기존 `today_requests`와 `total_requests`를 계속 갱신한다. 그래야 관리 화면, 테스트, 운영 스크립트가 즉시 깨지지 않는다.

## Concrete Steps

작업 디렉터리는 저장소 루트 `/Users/chsong/Developer/Personal/kra-analysis`다.

1. 현재 테스트 상태를 확인한다.

       pnpm -F @apps/api test

   예상 결과는 기존 테스트 통과다. 이 결과를 기준선으로 기록한다.

2. policy 패키지와 테스트 파일을 추가한다.

       mkdir -p apps/api/policy apps/api/tests/unit/policy

3. principal, authenticator, authorizer, accountant, dependencies, legacy adapter를 구현한다.

4. 라우터와 `JobService`를 `principal.owner_ref` 기반으로 전환한다.

5. 마이그레이션 SQL을 추가하고 회계 dual-write를 구현한다.

6. 정책 관련 테스트만 먼저 빠르게 돌린다.

       cd apps/api
       uv run pytest -q tests/unit/test_auth*.py tests/unit/policy

7. 전체 API 테스트를 돌린다.

       pnpm -F @apps/api test

## Validation and Acceptance

이 계획이 완료되면 다음을 검증해야 한다.

인증 검증: 유효한 `X-API-Key`로 `/api/v2/jobs/`를 호출하면 200이 반환되고, 응답 처리 후에만 사용량 이벤트가 기록된다. 인증 실패 키는 401을 반환한다.

권한 검증: `write` 권한이 없는 키로 `POST /api/v2/collection/async`를 호출하면 403이 반환된다. `read` 권한만 있는 키로 `GET /api/v2/jobs/`는 허용된다.

소유권 검증: 다른 principal의 `owner_ref`로 생성된 job을 조회하거나 취소하려 하면 403 또는 404 정책 중 하나로 일관되게 차단된다. 이 저장소에서는 정보 노출을 줄이기 위해 404를 선택해도 된다. 단, 전 경로에서 동일해야 한다.

회계 검증: `usage_events`에는 요청 하나당 하나의 완료 이벤트가 생기고, 실패 요청은 `outcome="failed"` 또는 `outcome="rejected"`로 남는다. Redis 장애 시 rate limit 저장 실패는 경고 로그를 남기되, 한도 판단을 할 수 없는 경우 초기 단계에서는 fail-open으로 처리한다.

회귀 검증: 기존 `dependencies.auth` import 경로를 사용하는 단위 테스트가 계속 통과해야 한다. 특히 JWT helper 테스트와 API key 테스트는 유지되어야 한다.

## Idempotence and Recovery

이 계획의 대부분은 additive 변경이므로 반복 실행에 안전해야 한다. `apps/api/policy/` 추가와 래퍼 도입은 여러 번 적용해도 문제 없어야 한다. Redis 기반 회계나 새 migration이 절반만 적용된 경우에는 migration을 되돌리기보다, dual-write를 끄는 feature flag를 두고 우선 읽기 경로만 유지하는 편이 안전하다.

만약 principal 전환 중 라우터가 깨지면 `dependencies/auth.py` 래퍼를 통해 기존 문자열 기반 경로로 일시 복귀할 수 있어야 한다. 이 복귀 경로는 레거시 제거 완료 전까지 유지한다.

## Artifacts and Notes

현재 구조에서 특히 중요한 관찰은 다음과 같다.

    require_api_key() -> str
    create_job(..., user_id=api_key)
    check_resource_access(..., api_key.name)

위 세 줄은 “같은 호출자”가 문자열 API key와 API key 이름 두 표현으로 동시에 존재함을 보여 준다. Candidate H의 목적은 이 불일치를 `AuthenticatedPrincipal.owner_ref` 하나로 수렴시키는 것이다.

## Note

2026-03-19에 생성한 초안이다. 현재 코드 조사 결과를 바탕으로 Candidate H를 최종 설계안으로 기록했고, 구현자가 바로 이어서 작업할 수 있도록 인터페이스, 단계, 하위호환 전략을 모두 포함했다.
