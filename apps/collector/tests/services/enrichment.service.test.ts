import { describe, it, expect, jest } from '@jest/globals';
import { EnrichmentService } from '../../src/services/enrichment.service.js';

describe('EnrichmentService forceRefresh behavior', () => {
  it('forceRefresh=true deletes horse detail cache before refetch', async () => {
    const mockKraApiService = {
      getHorseDetail: jest.fn().mockResolvedValue({ hrNo: '0012345', hrName: 'Horse' }),
      getJockeyDetail: jest.fn().mockResolvedValue(null),
      getTrainerDetail: jest.fn().mockResolvedValue(null),
    };

    const mockCacheService = {
      delete: jest.fn().mockResolvedValue(undefined),
      getOrSet: jest.fn(async (_keyType: string, _keyParams: Record<string, string>, computeFn: () => Promise<unknown>) => {
        return computeFn();
      }),
      set: jest.fn().mockResolvedValue(undefined),
      get: jest.fn().mockResolvedValue(null),
    };

    const service = new EnrichmentService(mockKraApiService as any, mockCacheService as any);

    await service.enrichRaceData(
      [
        {
          hrNo: '0012345',
          rcName: 'Test Race',
          rcDist: 1200,
          track: 'Dirt',
          weather: 'Sunny',
        } as any,
      ],
      '20240101',
      '서울',
      1,
      {
        includeHorseDetails: true,
        includeJockeyDetails: false,
        includeTrainerDetails: false,
        calculateMetrics: false,
        concurrency: 1,
        useCache: true,
        forceRefresh: true,
      }
    );

    expect(mockCacheService.delete).toHaveBeenCalledWith('horse_detail', { hrNo: '0012345' });
    expect(mockKraApiService.getHorseDetail).toHaveBeenCalledWith('0012345');
  });
});
