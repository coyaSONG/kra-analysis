import request from 'supertest';
import { createApp } from '../../src/app.js';
import { services } from '../../src/services/index.js';

describe('HorseController routes', () => {
  const app = createApp();
  const hrNo = '0012345';

  it('GET /api/v1/horses/:hrNo returns horse data successfully', async () => {
    const res = await request(app).get(`/api/v1/horses/${hrNo}`).expect(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.horse.hrNo).toBe(hrNo);
    expect(res.body.data.horse.metadata).toBeDefined();
  });

  it('GET /api/v1/horses/:hrNo works with different horse numbers', async () => {
    const other = '0099999';

    const res = await request(app).get(`/api/v1/horses/${other}`).expect(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.horse.hrNo).toBe(other);
    expect(res.body.data.horse.metadata).toBeDefined();
  });
});

