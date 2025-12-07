require('dotenv').config();
const fetch = require('node-fetch');
const fs = require('fs').promises;

const API_KEY = process.env.KRA_SERVICE_KEY;
const rcDate = process.argv[2] || '20251207';
const meet = process.argv[3] || '1';

async function collectRace(rcNo) {
    const baseUrl = 'https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1';
    const url = `${baseUrl}?serviceKey=${API_KEY}&numOfRows=50&pageNo=1&meet=${meet}&rc_date=${rcDate}&rc_no=${rcNo}&_type=json`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.response?.header?.resultCode === '00' && data.response?.body?.items) {
            const year = rcDate.substring(0, 4);
            const month = rcDate.substring(4, 6);
            const meetFolder = {'1': 'seoul', '2': 'jeju', '3': 'busan'}[meet] || 'seoul';
            const dir = `data/races/${year}/${month}/${rcDate}/${meetFolder}`;
            await fs.mkdir(dir, { recursive: true });

            const outPath = `${dir}/race_${meet}_${rcDate}_${rcNo}_prerace.json`;
            await fs.writeFile(outPath, JSON.stringify(data, null, 2), 'utf8');
            const horses = Array.isArray(data.response.body.items.item)
                ? data.response.body.items.item.length
                : 1;
            console.log(`✅ ${rcNo}R: ${horses}두 저장 완료`);
            return true;
        }
        return false;
    } catch (e) {
        console.error(`❌ ${rcNo}R 실패:`, e.message);
        return false;
    }
}

(async () => {
    const meetNames = {'1': '서울', '2': '제주', '3': '부산경남'};
    console.log(`📅 ${rcDate} ${meetNames[meet]} 경마장 데이터 수집\n`);
    let count = 0;
    for (let i = 1; i <= 15; i++) {
        const success = await collectRace(i);
        if (success) count++;
        else if (i > 1) break;
        await new Promise(r => setTimeout(r, 500));
    }
    console.log(`\n✅ 총 ${count}개 경주 수집 완료`);
})();
