require('dotenv').config();
const fetch = require('node-fetch');
const fs = require('fs').promises;
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);

const API_KEY = process.env.KRA_SERVICE_KEY;

async function collectRaceData(meet, rcDate, rcNo) {
    const baseUrl = 'https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1';
    const jsonUrl = `${baseUrl}?serviceKey=${API_KEY}&numOfRows=50&pageNo=1&meet=${meet}&rc_date=${rcDate}&rc_no=${rcNo}&_type=json`;
    
    try {
        const response = await fetch(jsonUrl);
        const jsonData = await response.json();
        
        if (jsonData.response.header.resultCode === '00') {
            if (jsonData.response.body.items) {
                return jsonData;
            }
        }
        return null;
    } catch (error) {
        console.error(`❌ API 호출 실패 (${meet}/${rcDate}/${rcNo}R):`, error.message);
        return null;
    }
}

async function collectAndPreprocessDay(meet, rcDate) {
    const meetNames = {'1': '서울', '2': '제주', '3': '부산경남'};
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📅 ${rcDate} ${meetNames[meet]} 경마장 데이터 수집 및 전처리`);
    console.log(`${'='.repeat(60)}`);
    
    const results = [];
    
    // 데이터 수집
    for (let rcNo = 1; rcNo <= 15; rcNo++) {
        process.stdout.write(`\n${rcNo}R 수집 중... `);
        
        const data = await collectRaceData(meet, rcDate, rcNo);
        
        if (data) {
            const horses = Array.isArray(data.response.body.items.item) 
                ? data.response.body.items.item 
                : [data.response.body.items.item];
            
            console.log(`✅ ${horses.length}두 출전`);
            
            // 임시 파일로 저장 (전처리를 위해)
            const tempFileName = `temp_race_${meet}_${rcDate}_${rcNo}.json`;
            const tempFilePath = `/tmp/${tempFileName}`;
            await fs.writeFile(tempFilePath, JSON.stringify(data, null, 2), 'utf8');
            
            // 바로 전처리 실행
            const year = rcDate.substring(0, 4);
            const month = rcDate.substring(4, 6);
            const meetFolder = {'1': 'seoul', '2': 'jeju', '3': 'busan'}[meet] || `meet${meet}`;
            const raceDir = `data/races/${year}/${month}/${rcDate}/${meetFolder}`;
            
            // 디렉토리 생성
            await fs.mkdir(raceDir, { recursive: true });
            
            const preracePath = `${raceDir}/race_${meet}_${rcDate}_${rcNo}_prerace.json`;
            
            try {
                // Python 스크립트로 개별 파일 전처리
                const { stdout } = await execPromise(
                    `python3 race_collector/smart_preprocess_races.py "${tempFilePath}"`
                );
                
                // 임시 파일 삭제
                await fs.unlink(tempFilePath);
                
                console.log(`📋 전처리 완료 → ${preracePath}`);
            } catch (error) {
                console.error(`❌ 전처리 실패: ${error.message}`);
                // 임시 파일 삭제
                try { await fs.unlink(tempFilePath); } catch {}
            }
            
            results.push({
                raceNo: rcNo,
                horses: horses.length,
                processed: true
            });
        } else {
            console.log('❌ 데이터 없음');
            break;
        }
        
        // API 호출 제한 방지
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    if (results.length > 0) {
        console.log(`\n✅ ${results.length}개 경주 수집 및 전처리 완료`);
    }
    
    return results;
}

// 실행
(async () => {
    const args = process.argv.slice(2);
    
    if (args.length >= 1) {
        // 특정 날짜 수집
        const rcDate = args[0];
        const meet = args[1] || '1';
        
        console.log(`특정 날짜 수집: ${rcDate} (경마장: ${meet})`);
        await collectAndPreprocessDay(meet, rcDate);
    } else {
        // 오늘 날짜 수집
        const today = new Date();
        const rcDate = today.getFullYear() + 
            String(today.getMonth() + 1).padStart(2, '0') + 
            String(today.getDate()).padStart(2, '0');
        
        console.log(`오늘 날짜 수집: ${rcDate}`);
        await collectAndPreprocessDay('1', rcDate);
    }
})();