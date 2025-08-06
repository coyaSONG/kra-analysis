export declare enum Meet {
    SEOUL = 1,
    JEJU = 2,
    BUSAN = 3
}
export interface RaceData {
    date: string;
    meet: Meet;
    raceNo: number;
    horses: HorseEntry[];
}
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
export interface HorseDetail {
    faHrName?: string;
    moHrName?: string;
    rcCntT?: number;
    ord1CntT?: number;
    winRateT?: string;
}
export interface JockeyDetail {
    age?: string;
    debut?: string;
    ord1CntT?: number;
    winRateT?: string;
}
export interface TrainerDetail {
    meet?: string;
    ord1CntT?: number;
    winRateT?: number;
    plcRateT?: number;
}
export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
}
//# sourceMappingURL=index.d.ts.map