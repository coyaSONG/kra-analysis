import { CacheService } from '../../src/services/cache.service.js';
import * as fs from 'fs/promises';

describe('CacheService (file fallback)', () => {
  const cacheDir = './cache-test-jest';
  let cache: CacheService;

  beforeAll(async () => {
    cache = new CacheService(cacheDir);
  });

  afterAll(async () => {
    // best-effort cleanup
    try { await fs.rm(cacheDir, { recursive: true, force: true }); } catch {}
  });

  it('set/get/exists/delete roundtrip works via file cache', async () => {
    const keyParams = { date: '20240719', meet: 1, raceNo: '1' };
    const value = { ok: true };

    await cache.set('race_result', keyParams, value, { ttl: 2 });

    const exists1 = await cache.exists('race_result', keyParams);
    expect(exists1).toBe(true);

    const got = await cache.get<typeof value>('race_result', keyParams);
    expect(got).toEqual(value);

    await cache.delete('race_result', keyParams);
    const exists2 = await cache.exists('race_result', keyParams);
    expect(exists2).toBe(false);
  });

  it('getOrSet computes and caches on miss', async () => {
    const params = { hrNo: '0012345', meet: 'all' };
    let calls = 0;
    const result = await cache.getOrSet('horse_detail', params, async () => {
      calls += 1; return { hrNo: '0012345', hrName: 'Horse' } as any;
    }, { ttl: 2 });

    expect(calls).toBe(1);
    expect(result.hrNo).toBe('0012345');

    // Second call hits cache
    const result2 = await cache.getOrSet('horse_detail', params, async () => {
      calls += 1; return { hrNo: '0012345', hrName: 'Horse-2' } as any;
    }, { ttl: 2 });

    expect(calls).toBe(1);
    expect(result2.hrName).toBe('Horse');
  });

  it('clear removes entries by pattern prefix', async () => {
    await cache.set('enriched_race', { date: '20240719', meet: 1, raceNo: '1' }, { ok: true }, { ttl: 60 });
    await cache.clear('enriched_race');
    const exists = await cache.exists('enriched_race', { date: '20240719', meet: 1, raceNo: '1' });
    expect(exists).toBe(false);
  });

  it('getStats updates hit/miss/hitRate counters', async () => {
    const stats1 = cache.getStats();
    expect(stats1).toHaveProperty('hitRate');
    // Trigger a miss
    const miss = await cache.get('race_result', { date: '20990101', meet: 1, raceNo: '1' });
    expect(miss).toBeNull();
    const stats2 = cache.getStats();
    expect(stats2.totalOperations).toBeGreaterThanOrEqual(stats1.totalOperations);
  });
});

