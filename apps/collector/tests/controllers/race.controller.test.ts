import request from 'supertest';
import { createApp } from '../../src/app.js';
import { services } from '../../src/services/index.js';

describe('RaceController routes', () => {
  const app = createApp();

  const date = '20240719';
  const meet = '서울';
  const raceNo = 1;

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
    // Pre-populate cache so controller follows cache-hit branch
    const cacheKey = { date, meet, raceNo: String(raceNo) };
    const cached = {
      race_date: date,
      meet,
      race_no: raceNo,
      horses: [],
    };
    await services.cacheService.set('race_result', cacheKey, cached, { ttl: 60 });

    const res = await request(app)
      .get(`/api/v1/races/${date}/${encodeURIComponent(meet)}/${raceNo}`)
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.data).toMatchObject({ race_date: date, race_no: raceNo });
    expect(res.body.message).toMatch(/Race details retrieved successfully/);
  });

  it('GET /api/v1/races/:date/:meet/:raceNo/result returns stub payload', async () => {
    const res = await request(app)
      .get(`/api/v1/races/${date}/${encodeURIComponent(meet)}/${raceNo}/result`)
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.data).toHaveProperty('message');
  });

  it('GET /api/v1/races/stats returns stub statistics', async () => {
    const res = await request(app).get('/api/v1/races/stats').expect(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data).toHaveProperty('totalRaces');
  });
});

