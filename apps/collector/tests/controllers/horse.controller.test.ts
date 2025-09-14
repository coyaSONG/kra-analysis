import request from 'supertest';
import { createApp } from '../../src/app.js';
import { services } from '../../src/services/index.js';

describe('HorseController routes', () => {
  const app = createApp();
  const hrNo = '0012345';

  it('GET /api/v1/horses/:hrNo returns cached horse when present', async () => {
    const cacheKey = { hrNo, meet: 'all' } as const;
    const cached = { hrNo, hrName: 'Test Horse' } as any;
    await services.cacheService.set('horse_detail', cacheKey, cached, { ttl: 60 });

    const res = await request(app).get(`/api/v1/horses/${hrNo}`).expect(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.hrNo).toBe(hrNo);
    expect(res.body.data.metadata.dataSource).toBe('cache');
  });

  it('GET /api/v1/horses/:hrNo falls back to API when cache miss', async () => {
    // Ensure cache miss for a different key
    const other = '0099999';
    // Mock service API method on singleton container
    const spy = jest
      .spyOn(services.kraApiService, 'getHorseDetail')
      .mockResolvedValue({ hrNo: other, hrName: 'API Horse' } as any);

    const res = await request(app).get(`/api/v1/horses/${other}`).expect(200);
    expect(spy).toHaveBeenCalledWith(other);
    expect(res.body.success).toBe(true);
    expect(res.body.data.hrNo).toBe(other);
    expect(res.body.data.metadata.dataSource).toBe('api');
  });
});

