import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('HorseController routes', () => {
  const app = createApp();
  const hrNo = '0012345';

  it('GET /api/v1/horses/:hrNo returns 501 when endpoint is not implemented', async () => {
    const res = await request(app).get(`/api/v1/horses/${hrNo}`).expect(501);
    expect(res.body.success).toBe(false);
    expect(res.body.error).toMatchObject({
      code: 'NOT_IMPLEMENTED',
    });
  });

  it('GET /api/v1/horses/:hrNo keeps same not-implemented contract for any valid horse id', async () => {
    const other = '0099999';

    const res = await request(app).get(`/api/v1/horses/${other}`).expect(501);
    expect(res.body.success).toBe(false);
    expect(res.body.error).toMatchObject({
      code: 'NOT_IMPLEMENTED',
    });
  });
});
