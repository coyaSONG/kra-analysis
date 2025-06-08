require('dotenv').config();
const fetch = require('node-fetch');
const fs = require('fs').promises;
const xml2js = require('xml2js');

const API_KEY = process.env.KRA_SERVICE_KEY;

async function testAPI8_2() {
    console.log('=== API8_2 (경주마 상세정보) 테스트 시작 ===\n');

    // 테스트할 말 이름들
    const testHorses = ['올라운드원', '메니피', '파워블레이드'];

    for (const horseName of testHorses) {
        console.log(`\n테스트 대상 말: ${horseName}`);
        
        // JSON 응답 테스트
        try {
            const jsonUrl = `https://apis.data.go.kr/B551015/API8_2/raceHorseInfo_2?ServiceKey=${API_KEY}&pageNo=1&numOfRows=10&hr_name=${encodeURIComponent(horseName)}&_type=json`;
            console.log('JSON API 호출 중...');
            
            const jsonResponse = await fetch(jsonUrl);
            const jsonData = await jsonResponse.json();
            
            if (horseName === '올라운드원') {
                // 첫 번째 테스트 결과만 저장
                await fs.writeFile(
                    'examples/api8_2_response.json',
                    JSON.stringify(jsonData, null, 2),
                    'utf8'
                );
                console.log('✅ JSON 응답 저장 완료: examples/api8_2_response.json');
            }
            
            // 응답 분석
            if (jsonData.response && jsonData.response.body && jsonData.response.body.items) {
                const items = jsonData.response.body.items.item;
                const horses = Array.isArray(items) ? items : [items];
                
                console.log(`\n찾은 말 수: ${horses.length}`);
                
                horses.forEach((horse, index) => {
                    console.log(`\n--- 말 정보 ${index + 1} ---`);
                    console.log(`마명: ${horse.hrName}`);
                    console.log(`마번: ${horse.hrNo}`);
                    console.log(`성별: ${horse.sex}`);
                    console.log(`생년월일: ${horse.birthday}`);
                    console.log(`등급: ${horse.rank}`);
                    console.log(`출생지: ${horse.birth}`);
                    console.log(`조교사: ${horse.trName} (${horse.trNo})`);
                    console.log(`마주: ${horse.owName} (${horse.owNo})`);
                    console.log(`부마: ${horse.faHrName} (${horse.faHrNo})`);
                    console.log(`모마: ${horse.moHrName} (${horse.moHrNo})`);
                    console.log(`통산 성적: ${horse.rcCntT}전 ${horse.ord1CntT}승 ${horse.ord2CntT}착 ${horse.ord3CntT}착`);
                    console.log(`최근1년 성적: ${horse.rcCntY}전 ${horse.ord1CntY}승 ${horse.ord2CntY}착 ${horse.ord3CntY}착`);
                    console.log(`통산상금: ${horse.chaksunT}원`);
                    console.log(`레이팅: ${horse.rating}`);
                    console.log(`최근거래가: ${horse.price}원`);
                });
            }
            
        } catch (error) {
            console.error(`JSON API 오류: ${error.message}`);
        }
        
        // XML 응답 테스트
        try {
            const xmlUrl = `https://apis.data.go.kr/B551015/API8_2/raceHorseInfo_2?ServiceKey=${API_KEY}&pageNo=1&numOfRows=10&hr_name=${encodeURIComponent(horseName)}`;
            console.log('\nXML API 호출 중...');
            
            const xmlResponse = await fetch(xmlUrl);
            const xmlText = await xmlResponse.text();
            
            if (horseName === '올라운드원') {
                // 첫 번째 테스트 결과만 저장
                await fs.writeFile(
                    'examples/api8_2_response.xml',
                    xmlText,
                    'utf8'
                );
                console.log('✅ XML 응답 저장 완료: examples/api8_2_response.xml');
            }
            
            // XML 파싱
            const parser = new xml2js.Parser({ explicitArray: false, ignoreAttrs: true });
            const result = await parser.parseStringPromise(xmlText);
            
            if (result.response && result.response.header) {
                console.log(`\nAPI 응답 상태: ${result.response.header.resultCode} - ${result.response.header.resultMsg}`);
            }
            
        } catch (error) {
            console.error(`XML API 오류: ${error.message}`);
        }
    }
    
    console.log('\n=== 모든 필드 목록 ===');
    console.log(`
    기본 정보:
    - hrName: 마명
    - hrNo: 마번
    - birth: 출생지
    - sex: 성별
    - birthday: 생년월일
    - rank: 등급
    - meet: 시행경마장명
    
    관계자 정보:
    - trName/trNo: 조교사명/번호
    - owName/owNo: 마주명/번호
    - faHrName/faHrNo: 부마명/번호
    - moHrName/moHrNo: 모마명/번호
    
    성적 통계:
    - rcCntT: 통산총출주회수
    - ord1CntT/ord2CntT/ord3CntT: 통산 1/2/3착 회수
    - rcCntY: 최근1년총출주회수
    - ord1CntY/ord2CntY/ord3CntY: 최근1년 1/2/3착 회수
    
    기타:
    - chaksunT: 통산착순상금
    - rating: 레이팅
    - price: 최근거래가
    `);
}

// 실행
testAPI8_2().catch(console.error);