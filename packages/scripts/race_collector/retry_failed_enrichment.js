require('dotenv').config();
const fs = require('fs').promises;
const path = require('path');
const { getHorseDetail, getJockeyDetail, getTrainerDetail, ensureCacheDir } = require('./api_clients');

async function retryFailedEnrichment(filePath) {
    try {
        console.log(`\n📁 파일 처리: ${path.basename(filePath)}`);
        const raceData = JSON.parse(await fs.readFile(filePath, 'utf8'));
        
        // items 배열 찾기
        let horseArray;
        if (raceData.response?.body?.items?.item) {
            horseArray = Array.isArray(raceData.response.body.items.item) 
                ? raceData.response.body.items.item 
                : [raceData.response.body.items.item];
        } else if (Array.isArray(raceData)) {
            horseArray = raceData;
        } else {
            console.error('❌ 알 수 없는 데이터 구조');
            return { success: false, error: 'Unknown data structure' };
        }
        
        const horses = horseArray.filter(h => h.winOdds > 0);
        console.log(`출전 말: ${horses.length}마리`);
        
        // API 호출 제한을 위한 딜레이
        const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
        
        let retryCount = 0;
        
        // 말 정보가 없는 경우만 재시도
        console.log('\n🐎 누락된 말 정보 재수집...');
        for (const horse of horses) {
            if (!horse.hrDetail) {
                console.log(`  재시도: ${horse.hrName} (${horse.hrNo})`);
                const detail = await getHorseDetail(horse.hrNo, horse.hrName);
                if (detail) {
                    horse.hrDetail = detail;
                    retryCount++;
                }
                await delay(1500); // 더 긴 딜레이
            }
        }
        
        // 기수 정보가 없는 경우만 재시도
        console.log('\n🏇 누락된 기수 정보 재수집...');
        for (const horse of horses) {
            if (!horse.jkDetail) {
                console.log(`  재시도: ${horse.jkName} (${horse.jkNo})`);
                const detail = await getJockeyDetail(horse.jkNo, horse.jkName);
                if (detail) {
                    horse.jkDetail = detail;
                    retryCount++;
                }
                await delay(1000);
            }
        }
        
        // 조교사 정보가 없는 경우만 재시도
        console.log('\n👨‍🏫 누락된 조교사 정보 재수집...');
        for (const horse of horses) {
            if (!horse.trDetail) {
                console.log(`  재시도: ${horse.trName} (${horse.trNo})`);
                const detail = await getTrainerDetail(horse.trNo, horse.trName);
                if (detail) {
                    horse.trDetail = detail;
                    retryCount++;
                }
                await delay(1000);
            }
        }
        
        if (retryCount > 0) {
            // 파일 덮어쓰기
            await fs.writeFile(filePath, JSON.stringify(raceData, null, 2), 'utf8');
            console.log(`✅ ${retryCount}개 정보 추가 수집 완료`);
        } else {
            console.log('✅ 추가 수집할 정보 없음');
        }
        
        // 통계
        const totalHorses = horses.length;
        const horseDetails = horses.filter(h => h.hrDetail).length;
        const jockeyDetails = horses.filter(h => h.jkDetail).length;
        const trainerDetails = horses.filter(h => h.trDetail).length;
        
        console.log(`\n📊 최종 통계:`);
        console.log(`  - 말 정보: ${horseDetails}/${totalHorses}`);
        console.log(`  - 기수 정보: ${jockeyDetails}/${totalHorses}`);
        console.log(`  - 조교사 정보: ${trainerDetails}/${totalHorses}`);
        
        return { success: true, retryCount };
        
    } catch (error) {
        console.error(`❌ 처리 실패:`, error.message);
        return { success: false, error: error.message };
    }
}

// 날짜별 재시도
async function retryDayRaces(dateStr, meet = '1') {
    const meetMap = { '1': 'seoul', '2': 'jeju', '3': 'busan' };
    const venue = meetMap[meet];
    
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const raceDir = `data/races/${year}/${month}/${dateStr}/${venue}`;
    
    console.log(`\n📅 ${dateStr} ${venue} 경주 재처리`);
    console.log(`디렉토리: ${raceDir}`);
    
    try {
        const files = await fs.readdir(raceDir);
        const enrichedFiles = files.filter(f => f.endsWith('_enriched.json'));
        
        console.log(`총 ${enrichedFiles.length}개 보강된 파일 발견`);
        
        const results = [];
        const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
        
        for (let i = 0; i < enrichedFiles.length; i++) {
            const file = enrichedFiles[i];
            const filePath = path.join(raceDir, file);
            const result = await retryFailedEnrichment(filePath);
            results.push({ file, ...result });
            
            // 마지막 파일이 아니면 추가 딜레이
            if (i < enrichedFiles.length - 1) {
                console.log('\n⏱️ 다음 파일 처리까지 3초 대기...\n');
                await delay(3000);
            }
        }
        
        // 전체 통계
        const successCount = results.filter(r => r.success).length;
        const totalRetries = results.reduce((sum, r) => sum + (r.retryCount || 0), 0);
        console.log(`\n${'='.repeat(60)}`);
        console.log(`✅ 전체 완료: ${successCount}/${results.length} 파일 처리`);
        console.log(`📊 총 ${totalRetries}개 정보 추가 수집`);
        
    } catch (error) {
        console.error(`❌ 디렉토리 읽기 실패:`, error.message);
    }
}

// 메인 실행
(async () => {
    await ensureCacheDir();
    
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.log('사용법:');
        console.log('  단일 파일: node retry_failed_enrichment.js <파일경로>');
        console.log('  날짜별: node retry_failed_enrichment.js <날짜YYYYMMDD> [경마장코드]');
        console.log('예시:');
        console.log('  node retry_failed_enrichment.js data/races/2025/06/20250608/seoul/race_1_20250608_7_enriched.json');
        console.log('  node retry_failed_enrichment.js 20250608 1');
        return;
    }
    
    if (args[0].endsWith('.json')) {
        // 단일 파일 처리
        await retryFailedEnrichment(args[0]);
    } else {
        // 날짜별 처리
        const dateStr = args[0];
        const meet = args[1] || '1';
        await retryDayRaces(dateStr, meet);
    }
})();