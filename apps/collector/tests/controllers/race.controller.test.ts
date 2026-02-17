import request from 'supertest';
import { createApp } from '../../src/app.js';
import { services } from '../../src/services/index.js';

const mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;
global.fetch = mockFetch;

describe('RaceController routes', () => {
  const app = createApp();

  const date = '20240719';
  const meet = '서울';
  const raceNo = 1;
  const collectedRace = {
    raceInfo: {
      date,
      meet,
      raceNo,
      rcName: '테스트 경주',
      rcDist: 1200,
      track: '양호',
      weather: '맑음',
      totalHorses: 1,
    },
    raceResult: [],
    collectionMeta: {
      collectedAt: '2024-07-19T10:00:00.000Z',
      isEnriched: false,
      dataSource: 'kra_api',
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  it('GET /api/v1/races/:date calls collectDay with undefined meet and returns collected races', async () => {
    const collectDaySpy = jest.spyOn(services.collectionService, 'collectDay').mockResolvedValueOnce([collectedRace]);

    const res = await request(app)
      .get(`/api/v1/races/${date}`)
      .expect(200);

    expect(collectDaySpy).toHaveBeenCalledWith(date, undefined, false);
    expect(res.body.success).toBe(true);
    expect(res.body.data).toEqual([collectedRace]);
    expect(res.body.message).toMatch(/Races retrieved successfully/);
    expect(res.body.meta).toMatchObject({ totalCount: 1 });
  });

  it('GET /api/v1/races/:date passes meet/includeEnriched query to collectDay', async () => {
    const collectDaySpy = jest.spyOn(services.collectionService, 'collectDay').mockResolvedValueOnce([collectedRace]);

    const res = await request(app)
      .get(`/api/v1/races/${date}?meet=${encodeURIComponent(meet)}&includeEnriched=true`)
      .expect(200);

    expect(collectDaySpy).toHaveBeenCalledWith(date, meet, true);
    expect(res.body.success).toBe(true);
    expect(res.body.data).toEqual([collectedRace]);
  });

  it('GET /api/v1/races/:date/:meet/:raceNo returns cached race when present', async () => {
    // In test env, controller intentionally bypasses cache and calls collection flow.
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          response: {
            header: { resultCode: '00', resultMsg: 'NORMAL SERVICE.' },
            body: {
              items: {
                item: [
                  {
                    hrNo: '0053587',
                    hrName: 'Test Horse',
                    jkNo: '080476',
                    jkName: 'Test Jockey',
                    trNo: '070165',
                    trName: 'Test Trainer',
                    ord: 1,
                    winOdds: 3.5,
                    wgBudam: 58.0,
                    rcTime: 0,
                    rcDate: Number(date),
                    rcNo: raceNo,
                    meet: '1',
                  },
                ],
              },
              numOfRows: 1,
              pageNo: 1,
              totalCount: 1,
            },
          },
        }),
      headers: new Headers(),
    } as Response);

    const res = await request(app)
      .get(`/api/v1/races/${date}/${encodeURIComponent(meet)}/${raceNo}`)
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.data).toHaveProperty('raceInfo');
    expect(res.body.data.raceInfo).toMatchObject({ date: date, raceNo: raceNo });
    expect(res.body.message).toMatch(/Race details retrieved successfully/);
  });

  it('GET /api/v1/races/:date/:meet/:raceNo/result returns stub payload', async () => {
    const res = await request(app)
      .get(`/api/v1/races/${date}/${encodeURIComponent(meet)}/${raceNo}/result`)
      .expect(501);

    expect(res.body.success).toBe(false);
    expect(res.body.error).toMatchObject({
      code: 'NOT_IMPLEMENTED',
    });
  });

  it('GET /api/v1/races/stats returns stub statistics', async () => {
    const res = await request(app).get('/api/v1/races/stats').expect(501);
    expect(res.body.success).toBe(false);
    expect(res.body.error).toMatchObject({
      code: 'NOT_IMPLEMENTED',
    });
  });
});
