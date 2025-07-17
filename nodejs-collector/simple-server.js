const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const { promisify } = require('util');
const path = require('path');

const app = express();
const execPromise = promisify(exec);

// 미들웨어
app.use(cors());
app.use(express.json());

// 프로젝트 루트 경로 (scripts 폴더가 있는 곳)
const PROJECT_ROOT = path.resolve(__dirname, '..');

// 헬스체크
app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'nodejs-data-collector' });
});

// 데이터 수집 엔드포인트
app.post('/collect', async (req, res) => {
    const { date, meet } = req.body;
    
    if (!date || !meet) {
        return res.status(400).json({ 
            error: 'date와 meet 파라미터가 필요합니다' 
        });
    }
    
    try {
        console.log(`수집 시작: ${date} / 경마장 ${meet}`);
        
        // 기존 Node.js 스크립트 실행
        const scriptPath = path.join(PROJECT_ROOT, 'scripts/race_collector/collect_and_preprocess.js');
        const { stdout, stderr } = await execPromise(
            `node "${scriptPath}" ${date} ${meet}`,
            { cwd: PROJECT_ROOT }
        );
        
        if (stderr) {
            console.error('스크립트 에러:', stderr);
        }
        
        res.json({ 
            success: true,
            message: '데이터 수집 완료',
            output: stdout
        });
        
    } catch (error) {
        console.error('수집 실패:', error);
        res.status(500).json({ 
            success: false,
            error: error.message 
        });
    }
});

// 데이터 보강 엔드포인트
app.post('/enrich', async (req, res) => {
    const { date, meet } = req.body;
    
    if (!date || !meet) {
        return res.status(400).json({ 
            error: 'date와 meet 파라미터가 필요합니다' 
        });
    }
    
    try {
        console.log(`보강 시작: ${date} / 경마장 ${meet}`);
        
        const scriptPath = path.join(PROJECT_ROOT, 'scripts/race_collector/enrich_race_data.js');
        const { stdout, stderr } = await execPromise(
            `node "${scriptPath}" ${date} ${meet}`,
            { cwd: PROJECT_ROOT }
        );
        
        if (stderr) {
            console.error('스크립트 에러:', stderr);
        }
        
        res.json({ 
            success: true,
            message: '데이터 보강 완료',
            output: stdout
        });
        
    } catch (error) {
        console.error('보강 실패:', error);
        res.status(500).json({ 
            success: false,
            error: error.message 
        });
    }
});

// 경주 결과 조회 엔드포인트
app.post('/result', async (req, res) => {
    const { date, meet, raceNo } = req.body;
    
    if (!date || !meet || !raceNo) {
        return res.status(400).json({ 
            error: 'date, meet, raceNo 파라미터가 필요합니다' 
        });
    }
    
    try {
        const meetNames = {'1': '서울', '2': '제주', '3': '부산경남'};
        const meetName = meetNames[meet.toString()] || meet;
        
        console.log(`결과 조회: ${date} / ${meetName} / ${raceNo}R`);
        
        const scriptPath = path.join(PROJECT_ROOT, 'scripts/race_collector/get_race_result.js');
        const { stdout, stderr } = await execPromise(
            `node "${scriptPath}" ${date} ${meetName} ${raceNo}`,
            { cwd: PROJECT_ROOT }
        );
        
        if (stderr) {
            console.error('스크립트 에러:', stderr);
        }
        
        res.json({ 
            success: true,
            message: '결과 조회 완료',
            output: stdout
        });
        
    } catch (error) {
        console.error('결과 조회 실패:', error);
        res.status(500).json({ 
            success: false,
            error: error.message 
        });
    }
});

const PORT = process.env.PORT || 3001;

app.listen(PORT, () => {
    console.log(`Node.js 데이터 수집 API가 포트 ${PORT}에서 실행 중입니다`);
    console.log(`프로젝트 루트: ${PROJECT_ROOT}`);
});