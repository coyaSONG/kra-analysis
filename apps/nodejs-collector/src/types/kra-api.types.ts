/**
 * KRA API Type Definitions
 * 
 * Comprehensive type definitions for Korea Racing Authority (KRA) Public APIs
 * Based on actual API responses from API214_1, API8_2, API12_1, and API19_1
 */

// ============================================================================
// Generic KRA API Response Wrapper
// ============================================================================

/**
 * Generic wrapper for all KRA API responses
 * @template T - The type of data contained in the response body items
 */
export interface KraApiResponse<T = any> {
  response: {
    header: KraApiHeader;
    body: KraApiBody<T>;
  };
}

/**
 * Standard KRA API response header
 */
export interface KraApiHeader {
  /** Result code ("00" for success) */
  resultCode: string;
  /** Result message ("NORMAL SERVICE." for success) */
  resultMsg: string;
}

/**
 * Generic KRA API response body structure
 * @template T - The type of individual items in the response
 */
export interface KraApiBody<T = any> {
  items: {
    /** Single item or array of items depending on the API */
    item: T | T[];
  };
  /** Number of rows per page */
  numOfRows: number;
  /** Current page number */
  pageNo: number;
  /** Total count of available items */
  totalCount: number;
}

// ============================================================================
// API214_1 - Race Result (경주 결과 조회)
// ============================================================================

/**
 * API214_1 Race Result Response Type
 */
export type Api214Response = KraApiResponse<Api214Item>;

/**
 * Complete race result data for a single horse entry from API214_1
 * Contains comprehensive race result information including timing, odds, and rankings
 */
export interface Api214Item {
  // Basic Information
  /** 나이 */
  age: number;
  /** 연령 조건 */
  ageCond: string;
  /** 생년월일 (YYYYMMDD format) */
  birthday: number;
  /** 출전 번호 */
  chulNo: number;
  /** 착차 단위 */
  diffUnit: string | number;
  /** 마명 */
  hrName: string;
  /** 마번 */
  hrNo: string;
  /** 마구 */
  hrTool: string;
  /** 경주 간격 (일수) */
  ilsu: number;
  /** 기수명 */
  jkName: string;
  /** 기수번호 */
  jkNo: string;
  /** 경마장 */
  meet: string;
  /** 국가 */
  name: string;
  /** 착순 */
  ord: number;
  /** 착순 비고 */
  ordBigo: string;
  /** 마주명 */
  owName: string;
  /** 마주번호 */
  owNo: number;
  /** 연승식 배당률 */
  plcOdds: number;
  /** 상금 조건 */
  prizeCond: string;
  /** 등급 */
  rank: string;
  /** 등급 변동 */
  rankRise: number;
  /** 레이팅 */
  rating: number;
  /** 경주일 (YYYYMMDD format) */
  rcDate: number;
  /** 경주 요일 */
  rcDay: string;
  /** 경주 거리 */
  rcDist: number;
  /** 경주명 */
  rcName: string;
  /** 경주번호 */
  rcNo: number;
  /** 주파 기록 */
  rcTime: number;
  /** 성별 */
  sex: string;
  /** 조교사명 */
  trName: string;
  /** 조교사번호 */
  trNo: string;
  /** 마장 상태 */
  track: string;
  /** 날씨 */
  weather: string;
  /** 부담중량 */
  wgBudam: number;
  /** 부담중량 비고 */
  wgBudamBigo: string;
  /** 마체중 */
  wgHr: string;
  /** 기수 감량 */
  wgJk: number;
  /** 단승식 배당률 */
  winOdds: number;

  // Busan Track Section Times (부산 구간 기록)
  /** 부산 1F 누적 시간 */
  buG1fAccTime: number;
  /** 부산 1F 순위 */
  buG1fOrd: number;
  /** 부산 2F 누적 시간 */
  buG2fAccTime: number;
  /** 부산 2F 순위 */
  buG2fOrd: number;
  /** 부산 3F 누적 시간 */
  buG3fAccTime: number;
  /** 부산 3F 순위 */
  buG3fOrd: number;
  /** 부산 4F 누적 시간 */
  buG4fAccTime: number;
  /** 부산 4F 순위 */
  buG4fOrd: number;
  /** 부산 6F 누적 시간 */
  buG6fAccTime: number;
  /** 부산 6F 순위 */
  buG6fOrd: number;
  /** 부산 8F 누적 시간 */
  buG8fAccTime: number;
  /** 부산 8F 순위 */
  buG8fOrd: number;
  /** 부산 S1F 누적 시간 */
  buS1fAccTime: number;
  /** 부산 S1F 순위 */
  buS1fOrd: number;
  /** 부산 S1F 구간 시간 */
  buS1fTime: number;

  // Busan Section Times
  /** 부산 10F-8F 구간 시간 */
  bu_10_8fTime: number;
  /** 부산 1F 골 시간 */
  bu_1fGTime: number;
  /** 부산 2F 골 시간 */
  bu_2fGTime: number;
  /** 부산 3F 골 시간 */
  bu_3fGTime: number;
  /** 부산 4F-2F 구간 시간 */
  bu_4_2fTime: number;
  /** 부산 6F-4F 구간 시간 */
  bu_6_4fTime: number;
  /** 부산 8F-6F 구간 시간 */
  bu_8_6fTime: number;

  // Race Conditions & Prize Money
  /** 부담 */
  budam: string;
  /** 부가 1 */
  buga1: number;
  /** 부가 2 */
  buga2: number;
  /** 부가 3 */
  buga3: number;
  /** 1등 상금 */
  chaksun1: number;
  /** 2등 상금 */
  chaksun2: number;
  /** 3등 상금 */
  chaksun3: number;
  /** 4등 상금 */
  chaksun4: number;
  /** 5등 상금 */
  chaksun5: number;

  // Jeju Track Section Times (제주 구간 기록)
  /** 제주 1F 골 시간 */
  jeG1fTime: number;
  /** 제주 3F 골 시간 */
  jeG3fTime: number;
  /** 제주 S1F 시간 */
  jeS1fTime: number;
  /** 제주 1C 시간 */
  je_1cTime: number;
  /** 제주 2C 시간 */
  je_2cTime: number;
  /** 제주 3C 시간 */
  je_3cTime: number;
  /** 제주 4C 시간 */
  je_4cTime: number;

  // Seoul Track Section Times (서울 구간 기록)
  /** 서울 1F 누적 시간 */
  seG1fAccTime: number;
  /** 서울 3F 누적 시간 */
  seG3fAccTime: number;
  /** 서울 S1F 누적 시간 */
  seS1fAccTime: number;
  /** 서울 1C 누적 시간 */
  se_1cAccTime: number;
  /** 서울 2C 누적 시간 */
  se_2cAccTime: number;
  /** 서울 3C 누적 시간 */
  se_3cAccTime: number;
  /** 서울 4C 누적 시간 */
  se_4cAccTime: number;

  // Section Rankings
  /** 서울/제주 1F 골 순위 */
  sjG1fOrd: number;
  /** 서울/제주 3F 골 순위 */
  sjG3fOrd: number;
  /** 서울/제주 S1F 순위 */
  sjS1fOrd: number;
  /** 서울/제주 1C 순위 */
  sj_1cOrd: number;
  /** 서울/제주 2C 순위 */
  sj_2cOrd: number;
  /** 서울/제주 3C 순위 */
  sj_3cOrd: number;
  /** 서울/제주 4C 순위 */
  sj_4cOrd: number;
}

// ============================================================================
// API8_2 - Horse Information (경주마 정보 조회)
// ============================================================================

/**
 * API8_2 Horse Information Response Type
 */
export type Api8_2Response = KraApiResponse<Api8_2Item>;

/**
 * Detailed horse information from API8_2
 * Contains bloodline, performance statistics, and ownership details
 */
export interface Api8_2Item {
  /** 생년월일 (YYYYMMDD format) */
  birthday: number;
  /** 총 획득 상금 */
  chaksunT: number;
  /** 부마명 */
  faHrName: string;
  /** 부마번호 */
  faHrNo: string;
  /** 마필 최종 거래금액 */
  hrLastAmt: string;
  /** 마명 */
  hrName: string;
  /** 마번 */
  hrNo: string;
  /** 소속 */
  meet: string;
  /** 모마명 */
  moHrName: string;
  /** 모마번호 */
  moHrNo: string;
  /** 국가 */
  name: string;
  /** 총 1착 횟수 */
  ord1CntT: number;
  /** 올해 1착 횟수 */
  ord1CntY: number;
  /** 총 2착 횟수 */
  ord2CntT: number;
  /** 올해 2착 횟수 */
  ord2CntY: number;
  /** 총 3착 횟수 */
  ord3CntT: number;
  /** 올해 3착 횟수 */
  ord3CntY: number;
  /** 마주명 */
  owName: string;
  /** 마주번호 */
  owNo: number;
  /** 등급 */
  rank: string;
  /** 레이팅 */
  rating: number;
  /** 총 출전 횟수 */
  rcCntT: number;
  /** 올해 출전 횟수 */
  rcCntY: number;
  /** 성별 */
  sex: string;
  /** 조교사명 */
  trName: string;
  /** 조교사번호 */
  trNo: string;
}

// ============================================================================
// API12_1 - Jockey Information (기수 정보 조회)
// ============================================================================

/**
 * API12_1 Jockey Information Response Type
 */
export type Api12_1Response = KraApiResponse<Api12_1Item>;

/**
 * Detailed jockey information from API12_1
 * Contains career statistics, personal details, and performance metrics
 */
export interface Api12_1Item {
  /** 나이 */
  age: number;
  /** 생년월일 (YYYYMMDD format) */
  birthday: number;
  /** 데뷔일 (YYYYMMDD format) */
  debut: number;
  /** 기수명 */
  jkName: string;
  /** 기수번호 */
  jkNo: string;
  /** 소속 */
  meet: string;
  /** 총 1착 횟수 */
  ord1CntT: number;
  /** 올해 1착 횟수 */
  ord1CntY: number;
  /** 총 2착 횟수 */
  ord2CntT: number;
  /** 올해 2착 횟수 */
  ord2CntY: number;
  /** 총 3착 횟수 */
  ord3CntT: number;
  /** 올해 3착 횟수 */
  ord3CntY: number;
  /** 구분 (프리기수, 전속기수 등) */
  part: string;
  /** 총 출전 횟수 */
  rcCntT: number;
  /** 올해 출전 횟수 */
  rcCntY: number;
  /** 특별 날짜 */
  spDate: string;
  /** 기타 체중 */
  wgOther: number;
  /** 파트 체중 */
  wgPart: number;
}

// ============================================================================
// API19_1 - Trainer Information (조교사 정보 조회)
// ============================================================================

/**
 * API19_1 Trainer Information Response Type
 */
export type Api19_1Response = KraApiResponse<Api19_1Item>;

/**
 * Detailed trainer information from API19_1
 * Contains career statistics, performance rates, and professional details
 */
export interface Api19_1Item {
  /** 나이 (문자열, "-"일 수 있음) */
  age: string;
  /** 생년월일 (문자열, "-"일 수 있음) */
  birthday: string;
  /** 소속 */
  meet: string;
  /** 총 1착 횟수 */
  ord1CntT: number;
  /** 올해 1착 횟수 */
  ord1CntY: number;
  /** 총 2착 횟수 */
  ord2CntT: number;
  /** 올해 2착 횟수 */
  ord2CntY: number;
  /** 총 3착 횟수 */
  ord3CntT: number;
  /** 올해 3착 횟수 */
  ord3CntY: number;
  /** 파트 */
  part: number;
  /** 총 연승률 */
  plcRateT: number;
  /** 올해 연승률 */
  plcRateY: number;
  /** 총 쿼니엘라율 */
  qnlRateT: number;
  /** 올해 쿼니엘라율 */
  qnlRateY: number;
  /** 총 출전 횟수 */
  rcCntT: number;
  /** 올해 출전 횟수 */
  rcCntY: number;
  /** 시작일 (YYYYMMDD format) */
  stDate: number;
  /** 조교사명 */
  trName: string;
  /** 조교사번호 */
  trNo: string;
  /** 총 승률 */
  winRateT: number;
  /** 올해 승률 */
  winRateY: number;
}

// ============================================================================
// Enriched Race Data Types (for internal processing)
// ============================================================================

/**
 * Enriched race data combining multiple API responses
 * Used internally for comprehensive race analysis
 */
export interface EnrichedRaceData {
  /** Race basic information */
  raceInfo: {
    date: string;
    meet: string;
    raceNo: number;
    rcName: string;
    rcDist: number;
    track: string;
    weather: string;
  };
  /** Horses with detailed information */
  horses: EnrichedHorseEntry[];
}

/**
 * Enriched horse entry combining race result with detailed info
 */
export interface EnrichedHorseEntry extends Api214Item {
  /** Detailed horse information from API8_2 */
  horseDetail?: Api8_2Item;
  /** Detailed jockey information from API12_1 */
  jockeyDetail?: Api12_1Item;
  /** Detailed trainer information from API19_1 */
  trainerDetail?: Api19_1Item;
  
  /** Computed performance metrics */
  performanceMetrics?: {
    /** Horse win rate percentage */
    horseWinRate: number;
    /** Jockey win rate percentage */
    jockeyWinRate: number;
    /** Trainer win rate percentage */
    trainerWinRate: number;
    /** Combined performance score */
    combinedScore: number;
  };
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Union type for all KRA API response types
 */
export type KraApiResponseUnion = 
  | Api214Response 
  | Api8_2Response 
  | Api12_1Response 
  | Api19_1Response;

/**
 * Union type for all KRA API item types
 */
export type KraApiItemUnion = 
  | Api214Item 
  | Api8_2Item 
  | Api12_1Item 
  | Api19_1Item;

/**
 * Enum for KRA API endpoints
 */
export enum KraApiEndpoint {
  RACE_RESULT = 'API214_1',
  HORSE_INFO = 'API8_2',
  JOCKEY_INFO = 'API12_1',
  TRAINER_INFO = 'API19_1'
}

/**
 * Enum for meet (track) codes
 */
export enum KraMeet {
  SEOUL = '서울',
  BUSAN = '부산경남',
  JEJU = '제주'
}

/**
 * Type guard to check if response is API214 (Race Result)
 */
export function isApi214Response(response: KraApiResponseUnion): response is Api214Response {
  const firstItem = Array.isArray(response.response.body.items.item) 
    ? response.response.body.items.item[0]
    : response.response.body.items.item;
  return Boolean(firstItem && 'ord' in firstItem && 'hrName' in firstItem && 'rcTime' in firstItem);
}

/**
 * Type guard to check if response is API8_2 (Horse Info)
 */
export function isApi8_2Response(response: KraApiResponseUnion): response is Api8_2Response {
  const item = response.response.body.items.item;
  const firstItem = Array.isArray(item) ? item[0] : item;
  return Boolean(firstItem && 'faHrName' in firstItem && 'moHrName' in firstItem);
}

/**
 * Type guard to check if response is API12_1 (Jockey Info)
 */
export function isApi12_1Response(response: KraApiResponseUnion): response is Api12_1Response {
  const item = response.response.body.items.item;
  const firstItem = Array.isArray(item) ? item[0] : item;
  return Boolean(firstItem && 'debut' in firstItem && 'part' in firstItem);
}

/**
 * Type guard to check if response is API19_1 (Trainer Info)
 */
export function isApi19_1Response(response: KraApiResponseUnion): response is Api19_1Response {
  const item = response.response.body.items.item;
  const firstItem = Array.isArray(item) ? item[0] : item;
  return Boolean(firstItem && 'stDate' in firstItem && 'plcRateT' in firstItem);
}