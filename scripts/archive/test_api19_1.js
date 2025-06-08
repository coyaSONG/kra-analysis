require('dotenv').config();
const fetch = require('node-fetch');
const fs = require('fs').promises;
const xml2js = require('xml2js');

const API_KEY = process.env.KRA_SERVICE_KEY;

async function testAPI19_1() {
    console.log('=== API19_1 (조교사 상세정보) 테스트 시작 ===\n');

    // 테스트할 조교사들
    const testTrainers = ['안우성', '강성오', '문현철'];

    for (const trainerName of testTrainers) {
        console.log(`\n테스트 대상 조교사: ${trainerName}`);
        
        // JSON 응답 테스트
        try {
            const jsonUrl = `https://apis.data.go.kr/B551015/API19_1/trainerInfo_1?ServiceKey=${API_KEY}&pageNo=1&numOfRows=10&tr_name=${encodeURIComponent(trainerName)}&_type=json`;
            console.log('JSON API 호출 중...');
            
            const jsonResponse = await fetch(jsonUrl);
            const jsonData = await jsonResponse.json();
            
            if (trainerName === '안우성') {
                // 첫 번째 테스트 결과만 저장
                await fs.writeFile(
                    'examples/api19_1_response.json',
                    JSON.stringify(jsonData, null, 2),
                    'utf8'
                );
                console.log('✅ JSON 응답 저장 완료: examples/api19_1_response.json');
            }
            
            // 응답 분석
            if (jsonData.response && jsonData.response.body && jsonData.response.body.items) {
                const items = jsonData.response.body.items.item;
                const trainers = Array.isArray(items) ? items : [items];
                
                console.log(`\n찾은 조교사 수: ${trainers.length}`);
                
                trainers.forEach((trainer, index) => {
                    console.log(`\n--- 조교사 정보 ${index + 1} ---`);
                    console.log(`조교사명: ${trainer.trName}`);
                    console.log(`조교사번호: ${trainer.trNo}`);
                    console.log(`나이: ${trainer.age}`);
                    console.log(`생년월일: ${trainer.birthday}`);
                    console.log(`데뷔일: ${trainer.debut}`);
                    console.log(`소속: ${trainer.meet}`);
                    console.log(`소속조: ${trainer.part}`);
                    
                    console.log(`\n통산 성적:`);
                    console.log(`  출주: ${trainer.rcCntT}회`);
                    console.log(`  1착: ${trainer.ord1CntT}회`);
                    console.log(`  2착: ${trainer.ord2CntT}회`);
                    console.log(`  3착: ${trainer.ord3CntT}회`);
                    console.log(`  승률: ${trainer.winRateT}%`);
                    console.log(`  복승률: ${trainer.plcRateT}%`);
                    console.log(`  연승률: ${trainer.showRateT}%`);
                    
                    console.log(`\n최근 1년 성적:`);
                    console.log(`  출주: ${trainer.rcCntY}회`);
                    console.log(`  1착: ${trainer.ord1CntY}회`);
                    console.log(`  2착: ${trainer.ord2CntY}회`);
                    console.log(`  3착: ${trainer.ord3CntY}회`);
                    console.log(`  승률: ${trainer.winRateY}%`);
                    console.log(`  복승률: ${trainer.plcRateY}%`);
                    console.log(`  연승률: ${trainer.showRateY}%`);
                });
            }
            
        } catch (error) {
            console.error(`JSON API 오류: ${error.message}`);
        }
        
        // XML 응답 테스트
        try {
            const xmlUrl = `https://apis.data.go.kr/B551015/API19_1/trainerInfo_1?ServiceKey=${API_KEY}&pageNo=1&numOfRows=10&tr_name=${encodeURIComponent(trainerName)}`;
            console.log('\nXML API 호출 중...');
            
            const xmlResponse = await fetch(xmlUrl);
            const xmlText = await xmlResponse.text();
            
            if (trainerName === '안우성') {
                // 첫 번째 테스트 결과만 저장
                await fs.writeFile(
                    'examples/api19_1_response.xml',
                    xmlText,
                    'utf8'
                );
                console.log('✅ XML 응답 저장 완료: examples/api19_1_response.xml');
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
    - trName: 조교사명
    - trNo: 조교사번호
    - age: 나이
    - birthday: 생년월일
    - debut: 데뷔일자
    - meet: 소속 경마장
    - part: 소속조
    
    통산 성적:
    - rcCntT: 통산 출주횟수
    - ord1CntT: 통산 1착 횟수
    - ord2CntT: 통산 2착 횟수
    - ord3CntT: 통산 3착 횟수
    - winRateT: 통산 승률
    - plcRateT: 통산 복승률
    - showRateT: 통산 연승률
    
    최근 1년 성적:
    - rcCntY: 최근1년 출주횟수
    - ord1CntY: 최근1년 1착 횟수
    - ord2CntY: 최근1년 2착 횟수
    - ord3CntY: 최근1년 3착 횟수
    - winRateY: 최근1년 승률
    - plcRateY: 최근1년 복승률
    - showRateY: 최근1년 연승률
    `);
}

// 실행
testAPI19_1().catch(console.error);