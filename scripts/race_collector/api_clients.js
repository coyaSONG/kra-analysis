require('dotenv').config();
const fetch = require('node-fetch');
const fs = require('fs').promises;
const path = require('path');

const API_KEY = process.env.KRA_SERVICE_KEY;
const CACHE_DIR = 'data/cache';
const CACHE_EXPIRY = 7 * 24 * 60 * 60 * 1000; // 7일

// 캐시 디렉토리 생성
async function ensureCacheDir() {
    await fs.mkdir(CACHE_DIR, { recursive: true });
    await fs.mkdir(`${CACHE_DIR}/horses`, { recursive: true });
    await fs.mkdir(`${CACHE_DIR}/jockeys`, { recursive: true });
    await fs.mkdir(`${CACHE_DIR}/trainers`, { recursive: true });
}

// 캐시 확인
async function getFromCache(type, id) {
    try {
        const cachePath = `${CACHE_DIR}/${type}/${id}.json`;
        const stats = await fs.stat(cachePath);
        
        // 캐시 만료 확인
        if (Date.now() - stats.mtime.getTime() > CACHE_EXPIRY) {
            return null;
        }
        
        const data = await fs.readFile(cachePath, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        return null;
    }
}

// 캐시 저장
async function saveToCache(type, id, data) {
    const cachePath = `${CACHE_DIR}/${type}/${id}.json`;
    await fs.writeFile(cachePath, JSON.stringify(data, null, 2), 'utf8');
}

// API8_2 - 경주마 상세정보
async function getHorseDetail(hrNo, hrName) {
    // 캐시 확인
    const cached = await getFromCache('horses', hrNo);
    if (cached) {
        console.log(`  📦 캐시 사용: 말 ${hrName} (${hrNo})`);
        return cached;
    }
    
    const url = `https://apis.data.go.kr/B551015/API8_2/raceHorseInfo_2?ServiceKey=${API_KEY}&pageNo=1&numOfRows=10&hr_no=${hrNo}&_type=json`;
    
    try {
        console.log(`  🔍 API 호출: 말 ${hrName} (${hrNo})`);
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.response.header.resultCode === '00' && data.response.body.items) {
            const horse = data.response.body.items.item;
            
            // 필요한 정보만 추출
            const horseDetail = {
                // 혈통 정보
                faHrName: horse.faHrName || '',
                faHrNo: horse.faHrNo || '',
                moHrName: horse.moHrName || '',
                moHrNo: horse.moHrNo || '',
                
                // 성적 통계
                rcCntT: horse.rcCntT || 0,
                ord1CntT: horse.ord1CntT || 0,
                ord2CntT: horse.ord2CntT || 0,
                ord3CntT: horse.ord3CntT || 0,
                rcCntY: horse.rcCntY || 0,
                ord1CntY: horse.ord1CntY || 0,
                ord2CntY: horse.ord2CntY || 0,
                ord3CntY: horse.ord3CntY || 0,
                
                // 기타 정보
                chaksunT: horse.chaksunT || 0,
                rating: horse.rating || 0,
                hrLastAmt: horse.hrLastAmt || '',
                
                // 계산된 통계
                winRateT: horse.rcCntT > 0 ? (horse.ord1CntT / horse.rcCntT * 100).toFixed(1) : 0,
                plcRateT: horse.rcCntT > 0 ? ((horse.ord1CntT + horse.ord2CntT) / horse.rcCntT * 100).toFixed(1) : 0,
                winRateY: horse.rcCntY > 0 ? (horse.ord1CntY / horse.rcCntY * 100).toFixed(1) : 0
            };
            
            // 캐시 저장
            await saveToCache('horses', hrNo, horseDetail);
            return horseDetail;
        }
    } catch (error) {
        console.error(`  ❌ 말 정보 조회 실패 (${hrNo}):`, error.message);
    }
    
    return null;
}

// API12_1 - 기수 정보
async function getJockeyDetail(jkNo, jkName) {
    // 캐시 확인
    const cached = await getFromCache('jockeys', jkNo);
    if (cached) {
        console.log(`  📦 캐시 사용: 기수 ${jkName} (${jkNo})`);
        return cached;
    }
    
    const url = `https://apis.data.go.kr/B551015/API12_1/jockeyInfo_1?serviceKey=${API_KEY}&numOfRows=100&pageNo=1&jk_no=${jkNo}&_type=json`;
    
    try {
        console.log(`  🔍 API 호출: 기수 ${jkName} (${jkNo})`);
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.response.header.resultCode === '00' && data.response.body.items) {
            const jockey = data.response.body.items.item;
            
            // 필요한 정보만 추출
            const jockeyDetail = {
                // 기본 정보
                age: jockey.age || '',
                birthday: jockey.birthday || '',
                debut: jockey.debut || '',
                part: jockey.part || '',
                
                // 성적 통계
                ord1CntT: parseInt(jockey.ord1CntT) || 0,
                ord2CntT: parseInt(jockey.ord2CntT) || 0,
                ord3CntT: parseInt(jockey.ord3CntT) || 0,
                rcCntT: parseInt(jockey.rcCntT) || 0,
                ord1CntY: parseInt(jockey.ord1CntY) || 0,
                ord2CntY: parseInt(jockey.ord2CntY) || 0,
                ord3CntY: parseInt(jockey.ord3CntY) || 0,
                rcCntY: parseInt(jockey.rcCntY) || 0,
                
                // 계산된 통계
                winRateT: jockey.rcCntT > 0 ? (jockey.ord1CntT / jockey.rcCntT * 100).toFixed(1) : 0,
                plcRateT: jockey.rcCntT > 0 ? ((jockey.ord1CntT + jockey.ord2CntT) / jockey.rcCntT * 100).toFixed(1) : 0,
                winRateY: jockey.rcCntY > 0 ? (jockey.ord1CntY / jockey.rcCntY * 100).toFixed(1) : 0
            };
            
            // 캐시 저장
            await saveToCache('jockeys', jkNo, jockeyDetail);
            return jockeyDetail;
        }
    } catch (error) {
        console.error(`  ❌ 기수 정보 조회 실패 (${jkNo}):`, error.message);
    }
    
    return null;
}

// API19_1 - 조교사 정보
async function getTrainerDetail(trNo, trName) {
    // 캐시 확인
    const cached = await getFromCache('trainers', trNo);
    if (cached) {
        console.log(`  📦 캐시 사용: 조교사 ${trName} (${trNo})`);
        return cached;
    }
    
    const url = `https://apis.data.go.kr/B551015/API19_1/trainerInfo_1?ServiceKey=${API_KEY}&pageNo=1&numOfRows=10&tr_no=${trNo}&_type=json`;
    
    try {
        console.log(`  🔍 API 호출: 조교사 ${trName} (${trNo})`);
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.response.header.resultCode === '00' && data.response.body.items) {
            const trainer = data.response.body.items.item;
            
            // 필요한 정보만 추출
            const trainerDetail = {
                // 기본 정보
                meet: trainer.meet || '',
                part: trainer.part || 0,
                stDate: trainer.stDate || 0,
                
                // 성적 통계
                rcCntT: trainer.rcCntT || 0,
                ord1CntT: trainer.ord1CntT || 0,
                ord2CntT: trainer.ord2CntT || 0,
                ord3CntT: trainer.ord3CntT || 0,
                winRateT: trainer.winRateT || 0,
                plcRateT: trainer.plcRateT || 0,
                qnlRateT: trainer.qnlRateT || 0,
                
                rcCntY: trainer.rcCntY || 0,
                ord1CntY: trainer.ord1CntY || 0,
                ord2CntY: trainer.ord2CntY || 0,
                ord3CntY: trainer.ord3CntY || 0,
                winRateY: trainer.winRateY || 0,
                plcRateY: trainer.plcRateY || 0,
                qnlRateY: trainer.qnlRateY || 0
            };
            
            // 캐시 저장
            await saveToCache('trainers', trNo, trainerDetail);
            return trainerDetail;
        }
    } catch (error) {
        console.error(`  ❌ 조교사 정보 조회 실패 (${trNo}):`, error.message);
    }
    
    return null;
}

module.exports = {
    ensureCacheDir,
    getHorseDetail,
    getJockeyDetail,
    getTrainerDetail
};