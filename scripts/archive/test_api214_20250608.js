require('dotenv').config();
const fetch = require('node-fetch');
const fs = require('fs').promises;
const xml2js = require('xml2js');

const API_KEY = process.env.KRA_SERVICE_KEY;

async function collectRaceData(meet, rcDate, rcNo) {
    const baseUrl = 'https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1';
    
    // JSON 응답으로 먼저 시도
    const jsonUrl = `${baseUrl}?serviceKey=${API_KEY}&numOfRows=50&pageNo=1&meet=${meet}&rc_date=${rcDate}&rc_no=${rcNo}&_type=json`;
    
    console.log(`\n=== 경주 정보 수집: ${rcDate} ${meet === '1' ? '서울' : meet === '2' ? '제주' : '부산'} ${rcNo}R ===`);
    
    try {
        const response = await fetch(jsonUrl);
        const jsonData = await response.json();
        
        if (jsonData.response.header.resultCode === '00') {
            const items = jsonData.response.body.items;
            
            if (items && items.item) {
                const horses = Array.isArray(items.item) ? items.item : [items.item];
                
                console.log(`\n총 ${horses.length}두 출전`);
                console.log('\n번호  마명          기수      조교사    배당률  착순');
                console.log('─'.repeat(55));
                
                horses.forEach(horse => {
                    const chulNo = String(horse.chulNo || '').padStart(2, ' ');
                    const hrName = (horse.hrName || '').padEnd(12, ' ');
                    const jkName = (horse.jkName || '').padEnd(8, ' ');
                    const trName = (horse.trName || '').padEnd(8, ' ');
                    const winOdds = String(horse.winOdds || '').padStart(6, ' ');
                    const ord = String(horse.ord || '-').padStart(4, ' ');
                    
                    console.log(`${chulNo}  ${hrName}  ${jkName}  ${trName}  ${winOdds}  ${ord}`);
                });
                
                // 파일로 저장
                const fileName = `race_${meet}_${rcDate}_${rcNo}.json`;
                await fs.writeFile(
                    `data/${fileName}`,
                    JSON.stringify(jsonData, null, 2),
                    'utf8'
                );
                console.log(`\n✅ 데이터 저장 완료: data/${fileName}`);
                
                return jsonData;
            } else {
                console.log('❌ 해당 경주 데이터가 없습니다.');
            }
        } else {
            console.log(`❌ API 오류: ${jsonData.response.header.resultMsg}`);
        }
    } catch (error) {
        console.error('❌ 요청 실패:', error.message);
    }
}

async function collectAllRacesForDay(meet, rcDate) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📅 ${rcDate} ${meet === '1' ? '서울' : meet === '2' ? '제주' : '부산'} 경마장 전체 경주 수집`);
    console.log(`${'='.repeat(60)}`);
    
    const results = [];
    
    // 보통 하루에 최대 12-15경주 정도 진행
    for (let rcNo = 1; rcNo <= 15; rcNo++) {
        const result = await collectRaceData(meet, rcDate, rcNo);
        
        if (result && result.response.body.items) {
            results.push(result);
        } else {
            // 데이터가 없으면 중단 (더 이상 경주가 없음)
            break;
        }
        
        // API 호출 제한 방지를 위한 대기
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    console.log(`\n✅ 총 ${results.length}개 경주 수집 완료`);
    return results;
}

// 실행
(async () => {
    // 서울 경마장(meet=1)의 2025년 6월 8일 경주 수집
    await collectAllRacesForDay('1', '20250608');
})();