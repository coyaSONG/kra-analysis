require('dotenv').config();
const fs = require('fs').promises;
const path = require('path');
const { ensureCacheDir, getHorseDetail, getJockeyDetail, getTrainerDetail } = require('./api_clients');

// 경주 데이터 보강
async function enrichRaceData(inputPath) {
    console.log(`\n📊 경주 데이터 보강 시작: ${path.basename(inputPath)}`);
    
    try {
        // 원본 데이터 읽기
        const raceData = JSON.parse(await fs.readFile(inputPath, 'utf8'));
        const horses = raceData.response.body.items.item;
        const horseArray = Array.isArray(horses) ? horses : [horses];
        
        console.log(`  출전마: ${horseArray.length}두`);
        
        // 고유한 기수/조교사 목록 추출
        const uniqueJockeys = new Map();
        const uniqueTrainers = new Map();
        
        horseArray.forEach(horse => {
            uniqueJockeys.set(horse.jkNo, horse.jkName);
            uniqueTrainers.set(horse.trNo, horse.trName);
        });
        
        console.log(`  고유 기수: ${uniqueJockeys.size}명`);
        console.log(`  고유 조교사: ${uniqueTrainers.size}명`);
        
        // API 호출 제한을 위한 딜레이
        const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
        
        // 각 말에 대한 상세 정보 수집
        console.log('\n🐎 말 정보 수집...');
        for (let i = 0; i < horseArray.length; i++) {
            const horse = horseArray[i];
            const detail = await getHorseDetail(horse.hrNo, horse.hrName);
            if (detail) {
                horse.hrDetail = detail;
            }
            await delay(500); // API 호출 제한 방지
        }
        
        // 기수 정보 수집
        console.log('\n🏇 기수 정보 수집...');
        const jockeyDetails = {};
        for (const [jkNo, jkName] of uniqueJockeys) {
            const detail = await getJockeyDetail(jkNo, jkName);
            if (detail) {
                jockeyDetails[jkNo] = detail;
            }
            await delay(500);
        }
        
        // 조교사 정보 수집
        console.log('\n👨‍🏫 조교사 정보 수집...');
        const trainerDetails = {};
        for (const [trNo, trName] of uniqueTrainers) {
            const detail = await getTrainerDetail(trNo, trName);
            if (detail) {
                trainerDetails[trNo] = detail;
            }
            await delay(500);
        }
        
        // 기수/조교사 정보를 각 말에 추가
        horseArray.forEach(horse => {
            if (jockeyDetails[horse.jkNo]) {
                horse.jkDetail = jockeyDetails[horse.jkNo];
            }
            if (trainerDetails[horse.trNo]) {
                horse.trDetail = trainerDetails[horse.trNo];
            }
        });
        
        // 보강된 데이터 저장
        const outputPath = inputPath.replace('_prerace.json', '_enriched.json');
        await fs.writeFile(outputPath, JSON.stringify(raceData, null, 2), 'utf8');
        
        console.log(`\n✅ 데이터 보강 완료: ${path.basename(outputPath)}`);
        
        // 통계 출력
        const enrichedHorses = horseArray.filter(h => h.hrDetail).length;
        const enrichedJockeys = horseArray.filter(h => h.jkDetail).length;
        const enrichedTrainers = horseArray.filter(h => h.trDetail).length;
        
        console.log(`  - 말 정보 추가: ${enrichedHorses}/${horseArray.length}`);
        console.log(`  - 기수 정보 추가: ${enrichedJockeys}/${horseArray.length}`);
        console.log(`  - 조교사 정보 추가: ${enrichedTrainers}/${horseArray.length}`);
        
        return {
            success: true,
            stats: {
                totalHorses: horseArray.length,
                enrichedHorses,
                enrichedJockeys,
                enrichedTrainers
            }
        };
        
    } catch (error) {
        console.error(`❌ 데이터 보강 실패:`, error.message);
        return { success: false, error: error.message };
    }
}

// 날짜별 모든 경주 보강
async function enrichDayRaces(dateStr, meet = '1') {
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const meetFolder = {'1': 'seoul', '2': 'jeju', '3': 'busan'}[meet] || `meet${meet}`;
    const raceDir = `data/races/${year}/${month}/${dateStr}/${meetFolder}`;
    
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📅 ${dateStr} ${meetFolder} 경마장 데이터 보강`);
    console.log(`${'='.repeat(60)}`);
    
    try {
        // 디렉토리의 모든 prerace 파일 찾기
        const files = await fs.readdir(raceDir);
        const preraceFiles = files.filter(f => f.endsWith('_prerace.json'));
        
        console.log(`총 ${preraceFiles.length}개 경주 발견`);
        
        const results = [];
        for (const file of preraceFiles) {
            const filePath = path.join(raceDir, file);
            const result = await enrichRaceData(filePath);
            results.push({ file, ...result });
        }
        
        // 전체 통계
        const successCount = results.filter(r => r.success).length;
        console.log(`\n${'='.repeat(60)}`);
        console.log(`✅ 전체 완료: ${successCount}/${results.length} 경주 성공`);
        
    } catch (error) {
        console.error(`❌ 디렉토리 읽기 실패:`, error.message);
    }
}

// 메인 실행
(async () => {
    // 캐시 디렉토리 생성
    await ensureCacheDir();
    
    const args = process.argv.slice(2);
    
    if (args.length === 0) {
        console.log('사용법:');
        console.log('  단일 파일: node enrich_race_data.js <파일경로>');
        console.log('  날짜별: node enrich_race_data.js <날짜YYYYMMDD> [경마장코드]');
        console.log('예시:');
        console.log('  node enrich_race_data.js data/races/2025/06/20250608/seoul/race_1_20250608_1_prerace.json');
        console.log('  node enrich_race_data.js 20250608 1');
        return;
    }
    
    if (args[0].endsWith('.json')) {
        // 단일 파일 처리
        await enrichRaceData(args[0]);
    } else {
        // 날짜별 처리
        const dateStr = args[0];
        const meet = args[1] || '1';
        await enrichDayRaces(dateStr, meet);
    }
})();