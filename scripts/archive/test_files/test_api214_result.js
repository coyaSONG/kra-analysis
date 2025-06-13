require('dotenv').config();
const fetch = require('node-fetch');

const API_KEY = process.env.KRA_SERVICE_KEY;

async function testAPI214Result() {
    // 과거 경주 테스트 (2024년 12월)
    const meet = '1'; // 서울
    const rcDate = '20241228';
    const rcNo = '1';
    
    const url = `https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey=${API_KEY}&numOfRows=50&pageNo=1&meet=${meet}&rc_date=${rcDate}&rc_no=${rcNo}&_type=json`;
    
    console.log('API URL:', url);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.response.header.resultCode === '00') {
            const items = data.response.body.items.item;
            console.log('\n경주 결과:');
            
            // ord가 0이 아닌 항목만 필터링하고 정렬
            const results = items
                .filter(item => item.ord > 0)
                .sort((a, b) => a.ord - b.ord);
            
            console.log('1-3위:');
            results.slice(0, 3).forEach(item => {
                console.log(`  ${item.ord}위: ${item.chulNo}번 ${item.hrName} (기록: ${item.rcTime}초)`);
            });
            
            // 1-3위 번호만 추출
            const top3 = results.slice(0, 3).map(item => item.chulNo);
            console.log('\n1-3위 번호:', top3);
            
        } else {
            console.log('API 오류:', data.response.header.resultMsg);
        }
    } catch (error) {
        console.error('오류:', error);
    }
}

testAPI214Result();