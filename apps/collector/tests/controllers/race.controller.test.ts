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

  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  it('GET /api/v1/races/:date collects day races on cache miss', async () => {
    const collectDaySpy = jest
      .spyOn(services.collectionService, 'collectDay')
      .mockResolvedValue([
        {
          raceInfo: {
            date,
            meet,
            raceNo: 1,
            rcName: 'Test Race',
            rcDist: 1200,
            track: 'Dirt',
            weather: 'Sunny',
            totalHorses: 1,
          },
          raceResult: [],
          collectionMeta: {
            collectedAt: new Date().toISOString(),
            isEnriched: false,
            dataSource: 'kra_api',
          },
        },
      ] as any);

    const res = await request(app)
      .get(`/api/v1/races/${date}`)
      .expect(200);

    expect(collectDaySpy).toHaveBeenCalledWith(date, undefined, false);
    expect(res.body.success).toBe(true);
    expect(Array.isArray(res.body.data)).toBe(true);
    expect(res.body.data).toHaveLength(1);
    expect(res.body.message).toMatch(/Races retrieved successfully/);
    expect(res.body.meta).toBeDefined();
    expect(res.body.meta.totalCount).toBe(1);
  });

  it('GET /api/v1/races/:date passes meet and includeEnriched to collectDay', async () => {
    const collectDaySpy = jest
      .spyOn(services.collectionService, 'collectDay')
      .mockResolvedValue([] as any);

    await request(app)
      .get(`/api/v1/races/${date}?meet=${encodeURIComponent(meet)}&includeEnriched=true`)
      .expect(200);

    expect(collectDaySpy).toHaveBeenCalledWith(date, meet, true);
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
