#!/usr/bin/env node
/**
 * API214_1을 통해 경주 결과를 가져와서 캐시에 저장
 * Python의 SSL 문제를 우회하기 위한 Node.js 스크립트
 */

require('dotenv').config();
const fetch = require('node-fetch');
const fs = require('fs').promises;
const path = require('path');

const API_KEY = process.env.KRA_SERVICE_KEY;
const BASE_URL = 'https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1';
const CACHE_DIR = 'data/cache/results';

// 캐시 디렉토리 생성
async function ensureCacheDir() {
    await fs.mkdir(CACHE_DIR, { recursive: true });
}

async function fetchRaceResult(meet, rcDate, rcNo) {
    const meetCodes = {
        '서울': '1',
        '제주': '2',
        '부산경남': '3'
    };
    
    const meetCode = meetCodes[meet] || '1';
    
    const url = `${BASE_URL}?serviceKey=${API_KEY}&numOfRows=50&pageNo=1&meet=${meetCode}&rc_date=${rcDate}&rc_no=${rcNo}&_type=json`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.response.header.resultCode === '00') {
            return data;
        } else {
            console.error(`API 오류: ${data.response.header.resultMsg}`);
            return null;
        }
    } catch (error) {
        console.error(`결과 가져오기 실패 (${meet} ${rcDate} ${rcNo}경주):`, error.message);
        return null;
    }
}

function extractTop3(data) {
    try {
        let items = data.response.body.items.item;
        
        // 단일 결과인 경우 배열로 변환
        if (!Array.isArray(items)) {
            items = [items];
        }
        
        // ord가 0이 아닌 항목만 필터링하고 정렬
        const results = items
            .filter(item => item.ord > 0)
            .sort((a, b) => a.ord - b.ord);
        
        // 1-3위 번호만 추출
        return results.slice(0, 3).map(item => item.chulNo);
    } catch (error) {
        console.error('결과 추출 오류:', error);
        return [];
    }
}

// 전체 결과 저장 함수 제거 (사용하지 않음)

async function getRaceResultWithCache(meet, rcDate, rcNo) {
    await ensureCacheDir();
    
    // top3 결과 파일 경로
    const simpleFile = path.join(CACHE_DIR, `top3_${rcDate}_${meet}_${rcNo}.json`);
    
    // 캐시 확인
    try {
        const cached = await fs.readFile(simpleFile, 'utf-8');
        const top3 = JSON.parse(cached);
        console.log(`캐시 사용: ${simpleFile}`);
        return top3;
    } catch (error) {
        // 캐시 없음
    }
    
    // API 호출
    console.log(`API 호출: ${meet} ${rcDate} ${rcNo}경주`);
    const data = await fetchRaceResult(meet, rcDate, rcNo);
    
    if (data) {
        const top3 = extractTop3(data);
        if (top3 && top3.length > 0) {
            // 1-3위 결과만 저장
            await fs.writeFile(simpleFile, JSON.stringify(top3), 'utf-8');
            console.log(`결과 저장: ${simpleFile}`);
        }
        return top3;
    }
    
    return null;
}

// 명령행 인자 처리
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length < 3) {
        console.log('사용법: node fetch_and_save_results.js <경마장> <날짜> <경주번호>');
        console.log('예시: node fetch_and_save_results.js 서울 20241228 1');
        process.exit(1);
    }
    
    const [meet, rcDate, rcNo] = args;
    
    console.log(`\n경주 결과 가져오기: ${meet} ${rcDate} ${rcNo}경주`);
    const top3 = await getRaceResultWithCache(meet, rcDate, parseInt(rcNo));
    
    if (top3 && top3.length > 0) {
        console.log(`✅ 1-3위: [${top3.join(', ')}]`);
    } else {
        console.log('❌ 결과를 가져올 수 없습니다.');
    }
}

// 모듈로 사용할 수 있도록 export
module.exports = {
    getRaceResultWithCache,
    extractTop3
};

// 직접 실행시
if (require.main === module) {
    main().catch(console.error);
}