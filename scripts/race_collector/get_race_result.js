require('dotenv').config();
const fetch = require('node-fetch');
const fs = require('fs').promises;

const API_KEY = process.env.KRA_SERVICE_KEY;

if (!API_KEY) {
    console.error('❌ API 키가 설정되지 않았습니다. .env 파일을 확인하세요.');
    process.exit(1);
}

/**
 * 경마장 이름을 API 코드로 변환
 */
function getMeetCode(meetName) {
    const meetCodes = {
        '서울': '1',
        '제주': '2',
        '부산경남': '3',
        '부산': '3',  // 부산도 3번으로 매핑
        '1': '1',    // 이미 코드인 경우
        '2': '2',
        '3': '3'
    };
    
    return meetCodes[meetName] || '1';
}

/**
 * API214_1을 통해 경주 결과 가져오기
 */
async function fetchRaceResult(meet, rcDate, rcNo) {
    const meetCode = getMeetCode(meet);
    const baseUrl = 'https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1';
    const jsonUrl = `${baseUrl}?serviceKey=${API_KEY}&numOfRows=50&pageNo=1&meet=${meetCode}&rc_date=${rcDate}&rc_no=${rcNo}&_type=json`;
    
    try {
        const response = await fetch(jsonUrl);
        const jsonData = await response.json();
        
        if (jsonData.response.header.resultCode === '00') {
            if (jsonData.response.body.items) {
                return jsonData;
            }
        } else {
            console.error(`❌ API 오류: ${jsonData.response.header.resultMsg}`);
        }
        return null;
    } catch (error) {
        console.error(`❌ API 호출 실패 (${meet}/${rcDate}/${rcNo}R):`, error.message);
        return null;
    }
}

/**
 * 경주 결과에서 1-2-3위 출주번호 추출
 */
function extractTop3(raceData) {
    try {
        const items = raceData.response.body.items.item;
        const horses = Array.isArray(items) ? items : [items];
        
        // 기권/제외마 필터링 (winOdds가 0인 경우)
        const validHorses = horses.filter(horse => horse.winOdds > 0);
        
        // ord 필드가 있고 0보다 큰 말들만 필터링
        const finishedHorses = validHorses.filter(horse => horse.ord && horse.ord > 0);
        
        if (finishedHorses.length === 0) {
            console.log('⚠️ 아직 경주가 완료되지 않았거나 결과가 없습니다.');
            return null;
        }
        
        // ord 순으로 정렬
        finishedHorses.sort((a, b) => a.ord - b.ord);
        
        // 1-2-3위 출주번호 추출
        const top3 = [];
        for (let i = 0; i < Math.min(3, finishedHorses.length); i++) {
            top3.push(finishedHorses[i].chulNo);
        }
        
        return top3;
        
    } catch (error) {
        console.error(`❌ 결과 추출 오류: ${error.message}`);
        return null;
    }
}

/**
 * 결과를 파일로 저장
 */
async function saveResult(top3, rcDate, meet, rcNo) {
    try {
        // 캐시 디렉토리 생성
        const cacheDir = 'data/cache/results';
        await fs.mkdir(cacheDir, { recursive: true });
        
        // 파일명 생성
        const filename = `top3_${rcDate}_${meet}_${rcNo}.json`;
        const filepath = `${cacheDir}/${filename}`;
        
        // JSON 배열로 저장
        await fs.writeFile(filepath, JSON.stringify(top3), 'utf8');
        
        console.log(`✅ 결과 저장: ${filepath}`);
        console.log(`📊 1-2-3위: [${top3.join(', ')}]`);
        
        return filepath;
        
    } catch (error) {
        console.error(`❌ 파일 저장 실패: ${error.message}`);
        return null;
    }
}

/**
 * 메인 함수
 */
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length < 3) {
        console.log('사용법: node get_race_result.js [날짜] [경마장] [경주번호]');
        console.log('예시: node get_race_result.js 20250615 서울 1');
        process.exit(1);
    }
    
    const rcDate = args[0];
    const meet = args[1];
    const rcNo = args[2];
    
    console.log(`\n🏇 경주 결과 수집: ${rcDate} ${meet} ${rcNo}경주`);
    console.log('─'.repeat(50));
    
    // 1. API 호출
    const raceData = await fetchRaceResult(meet, rcDate, rcNo);
    if (!raceData) {
        console.error('❌ 경주 데이터를 가져올 수 없습니다.');
        process.exit(1);
    }
    
    // 2. 1-2-3위 추출
    const top3 = extractTop3(raceData);
    if (!top3) {
        console.error('❌ 경주 결과를 추출할 수 없습니다.');
        process.exit(1);
    }
    
    // 3. 파일 저장
    const savedFile = await saveResult(top3, rcDate, meet, rcNo);
    if (!savedFile) {
        console.error('❌ 결과 저장에 실패했습니다.');
        process.exit(1);
    }
    
    console.log('✅ 경주 결과 수집 완료');
}

// 스크립트 실행
if (require.main === module) {
    main().catch(error => {
        console.error('❌ 예기치 않은 오류:', error.message);
        process.exit(1);
    });
}

module.exports = {
    fetchRaceResult,
    extractTop3,
    saveResult,
    getMeetCode
};