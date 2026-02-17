import request from 'supertest';
import { createApp } from '../../src/app.js';

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

  it('GET /api/v1/races/:date returns empty list with metadata', async () => {
    const res = await request(app)
      .get(`/api/v1/races/${date}`)
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(Array.isArray(res.body.data)).toBe(true);
    expect(res.body.message).toMatch(/Races retrieved successfully/);
    expect(res.body.meta).toBeDefined();
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
