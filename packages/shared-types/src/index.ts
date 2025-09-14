// 경마장 코드
export enum Meet {
  SEOUL = 1,
  JEJU = 2,
  BUSAN = 3,
}

// 경주 데이터 타입
export interface RaceData {
  date: string;
  meet: Meet;
  raceNo: number;
  horses: HorseEntry[];
}

// 말 정보
export interface HorseEntry {
  hrNo: string;
  hrName: string;
  jkNo: string;
  jkName: string;
  trNo: string;
  trName: string;
  ord?: number;
  winOdds?: number;
  plcOdds?: number;
  hrDetail?: HorseDetail;
  jkDetail?: JockeyDetail;
  trDetail?: TrainerDetail;
}

// 말 상세 정보
export interface HorseDetail {
  faHrName?: string;
  moHrName?: string;
  rcCntT?: number;
  ord1CntT?: number;
  winRateT?: string;
}

// 기수 상세 정보
export interface JockeyDetail {
  age?: string;
  debut?: string;
  ord1CntT?: number;
  winRateT?: string;
}

// 조교사 상세 정보
export interface TrainerDetail {
  meet?: string;
  ord1CntT?: number;
  winRateT?: number;
  plcRateT?: number;
}

// API 응답 타입
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}
