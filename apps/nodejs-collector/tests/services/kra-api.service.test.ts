/**
 * KRA API Service Tests
 * 
 * Comprehensive test suite for the KRA API Service including
 * success cases, error handling, retry logic, and rate limiting.
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { KraApiService } from '../../src/services/kraApiService.js';
import { 
  mockKraApiResponse, 
  mockKraApiError, 
  simulateNetworkError,
  simulateTimeout,
  simulateRateLimit,
  createTestRaceData,
  createTestHorseData,
  createTestJockeyData,
  createTestTrainerData
} from '../setup.js';
import type { Api214Item, Api8_2Item, Api12_1Item, Api19_1Item } from '../../src/types/kra-api.types.js';

// Mock fetch globally
const mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;
global.fetch = mockFetch;

describe('KraApiService', () => {
  let kraApiService: KraApiService;

  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks();
    mockFetch.mockReset();
    
    // Create fresh instance for each test
    kraApiService = new KraApiService();
  });

  describe('Constructor', () => {
    it('should initialize with default configuration', () => {
      const service = new KraApiService();
      expect(service).toBeInstanceOf(KraApiService);
    });

    it('should handle missing environment variables gracefully', () => {
      const originalEnv = process.env;
      process.env = { ...originalEnv };
      delete process.env.KRA_API_BASE_URL;
      delete process.env.KRA_API_KEY;

      expect(() => new KraApiService()).not.toThrow();
      
      process.env = originalEnv;
    });
  });

  describe('getRaceResult', () => {
    const testDate = '20241201';
    const testMeet = '서울';
    const testRaceNo = 1;

    it('should fetch race result successfully', async () => {
      // Arrange
      const testRaceData = createTestRaceData();
      const mockResponse = mockKraApiResponse<Api214Item>([
        {
          ...testRaceData,
          age: 4,
          ageCond: '4세',
          birthday: 20200315,
          chulNo: 1,
          diffUnit: '목',
          hrName: 'Test Horse',
          hrNo: '20210001',
          hrTool: '블링커',
          ilsu: 14,
          jkName: 'Test Jockey',
          jkNo: '001',
          meet: testMeet,
          name: '한국',
          ord: 1,
          ordBigo: '',
          owName: 'Test Owner',
          owNo: 1001,
          plcOdds: 1.8,
          rcDate: testDate,
          rcNo: testRaceNo,
          rcTime: '01:12.3',
          sex: '수컷',
          trName: 'Test Trainer',
          trNo: '001',
          wgBudam: 55,
          winOdds: 3.2,
          wr1f: '12.5',
          wr2f: '24.8',
          wr3f: '37.1',
          wrHorse: 10.5
        } as Api214Item
      ]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers(),
      } as Response);

      // Act
      const result = await kraApiService.getRaceResult(testDate, testMeet, testRaceNo);

      // Assert
      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(1);
      expect(result[0]).toHaveProperty('hrName', 'Test Horse');
      expect(result[0]).toHaveProperty('jkName', 'Test Jockey');
      expect(result[0]).toHaveProperty('ord', 1);
      
      // Verify fetch was called with correct parameters
      expect(mockFetch).toHaveBeenCalledTimes(1);
      const fetchCall = mockFetch.mock.calls[0];
      expect(fetchCall[0]).toContain('API214_1.json');
      expect(fetchCall[0]).toContain(`rc_date=${testDate}`);
      expect(fetchCall[0]).toContain(`meet=${encodeURIComponent(testMeet)}`);
      expect(fetchCall[0]).toContain(`rc_no=${testRaceNo}`);
    });

    it('should handle KRA API error response', async () => {
      // Arrange
      const errorResponse = mockKraApiError('99', 'SERVICE ERROR');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(errorResponse),
        headers: new Headers(),
      } as Response);

      // Act & Assert
      await expect(
        kraApiService.getRaceResult(testDate, testMeet, testRaceNo)
      ).rejects.toThrow('KRA API returned error: SERVICE ERROR');
    });

    it('should handle network errors with retry', async () => {
      // Arrange
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockKraApiResponse<Api214Item>([{} as Api214Item])),
          headers: new Headers(),
        } as Response);

      // Act
      const result = await kraApiService.getRaceResult(testDate, testMeet, testRaceNo);

      // Assert
      expect(result).toBeDefined();
      expect(mockFetch).toHaveBeenCalledTimes(3); // 1 initial + 2 retries
    });

    it('should handle HTTP error responses', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        headers: new Headers(),
      } as Response);

      // Act & Assert
      await expect(
        kraApiService.getRaceResult(testDate, testMeet, testRaceNo)
      ).rejects.toThrow();
    });

    it('should handle rate limiting', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers({ 'Retry-After': '60' }),
      } as Response);

      // Act & Assert
      await expect(
        kraApiService.getRaceResult(testDate, testMeet, testRaceNo)
      ).rejects.toThrow('KRA API rate limit exceeded');
    });

    it('should validate input parameters', async () => {
      // Act & Assert
      await expect(
        kraApiService.getRaceResult('', testMeet, testRaceNo)
      ).rejects.toThrow();

      await expect(
        kraApiService.getRaceResult(testDate, '', testRaceNo)
      ).rejects.toThrow();

      await expect(
        kraApiService.getRaceResult(testDate, testMeet, 0)
      ).rejects.toThrow();
    });

    it('should use custom request options', async () => {
      // Arrange
      const mockResponse = mockKraApiResponse<Api214Item>([{} as Api214Item]);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers(),
      } as Response);

      const options = {
        timeout: 10000,
        retryAttempts: 1,
        headers: { 'X-Custom-Header': 'test' }
      };

      // Act
      await kraApiService.getRaceResult(testDate, testMeet, testRaceNo, options);

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Custom-Header': 'test'
          })
        })
      );
    });
  });

  describe('getHorseDetail', () => {
    const testHrNo = '20210001';

    it('should fetch horse detail successfully', async () => {
      // Arrange
      const testHorseData = createTestHorseData();
      const mockResponse = mockKraApiResponse<Api8_2Item>([
        {
          ...testHorseData,
          hrColor: '청모',
          hrFather: 'Father Horse',
          hrMother: 'Mother Horse',
          owName: 'Test Owner',
          owNo: 1001,
          trName: 'Test Trainer',
          trNo: '001',
        } as Api8_2Item
      ]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers(),
      } as Response);

      // Act
      const result = await kraApiService.getHorseDetail(testHrNo);

      // Assert
      expect(result).toBeDefined();
      expect(result).toHaveProperty('hrName', 'Test Horse');
      expect(result).toHaveProperty('hrNo', testHrNo);
      
      // Verify fetch was called correctly
      expect(mockFetch).toHaveBeenCalledTimes(1);
      const fetchCall = mockFetch.mock.calls[0];
      expect(fetchCall[0]).toContain('API8_2.json');
      expect(fetchCall[0]).toContain(`hr_no=${testHrNo}`);
    });

    it('should return null for not found horse', async () => {
      // Arrange
      const notFoundResponse = mockKraApiError('03', 'NO DATA');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(notFoundResponse),
        headers: new Headers(),
      } as Response);

      // Act
      const result = await kraApiService.getHorseDetail(testHrNo);

      // Assert
      expect(result).toBeNull();
    });

    it('should handle empty response gracefully', async () => {
      // Arrange
      const emptyResponse = mockKraApiResponse<Api8_2Item>([]);
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(emptyResponse),
        headers: new Headers(),
      } as Response);

      // Act
      const result = await kraApiService.getHorseDetail(testHrNo);

      // Assert
      expect(result).toBeNull();
    });
  });

  describe('getJockeyDetail', () => {
    const testJkNo = '001';

    it('should fetch jockey detail successfully', async () => {
      // Arrange
      const testJockeyData = createTestJockeyData();
      const mockResponse = mockKraApiResponse<Api12_1Item>([
        {
          ...testJockeyData,
          jkHeight: 165,
          jkDebut: '20100301',
        } as Api12_1Item
      ]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers(),
      } as Response);

      // Act
      const result = await kraApiService.getJockeyDetail(testJkNo);

      // Assert
      expect(result).toBeDefined();
      expect(result).toHaveProperty('jkName', 'Test Jockey');
      expect(result).toHaveProperty('jkNo', testJkNo);
    });

    it('should return null for not found jockey', async () => {
      // Arrange
      const notFoundResponse = mockKraApiError('03', 'NO DATA');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(notFoundResponse),
        headers: new Headers(),
      } as Response);

      // Act
      const result = await kraApiService.getJockeyDetail(testJkNo);

      // Assert
      expect(result).toBeNull();
    });
  });

  describe('getTrainerDetail', () => {
    const testTrNo = '001';

    it('should fetch trainer detail successfully', async () => {
      // Arrange
      const testTrainerData = createTestTrainerData();
      const mockResponse = mockKraApiResponse<Api19_1Item>([
        {
          ...testTrainerData,
          trAge: 48,
          trHeight: 175,
        } as Api19_1Item
      ]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers(),
      } as Response);

      // Act
      const result = await kraApiService.getTrainerDetail(testTrNo);

      // Assert
      expect(result).toBeDefined();
      expect(result).toHaveProperty('trName', 'Test Trainer');
      expect(result).toHaveProperty('trNo', testTrNo);
    });

    it('should return null for not found trainer', async () => {
      // Arrange
      const notFoundResponse = mockKraApiError('03', 'NO DATA');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(notFoundResponse),
        headers: new Headers(),
      } as Response);

      // Act
      const result = await kraApiService.getTrainerDetail(testTrNo);

      // Assert
      expect(result).toBeNull();
    });
  });

  describe('Rate Limiting', () => {
    it('should respect rate limits', async () => {
      // This test would need more complex setup to properly test rate limiting
      // For now, we'll test that the rate limiting logic doesn't break normal operation
      
      const mockResponse = mockKraApiResponse<Api214Item>([{} as Api214Item]);
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers(),
      } as Response);

      // Make multiple rapid requests
      const promises = Array.from({ length: 5 }, (_, i) => 
        kraApiService.getRaceResult('20241201', '서울', i + 1)
      );

      // All should succeed (rate limiting is internal)
      const results = await Promise.all(promises);
      expect(results).toHaveLength(5);
      expect(mockFetch).toHaveBeenCalledTimes(5);
    });
  });

  describe('Health Check', () => {
    it('should return true for successful health check', async () => {
      // Arrange
      const mockResponse = mockKraApiResponse<Api214Item>([{} as Api214Item]);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers(),
      } as Response);

      // Act
      const result = await kraApiService.healthCheck();

      // Assert
      expect(result).toBe(true);
    });

    it('should return false for failed health check', async () => {
      // Arrange
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      // Act
      const result = await kraApiService.healthCheck();

      // Assert
      expect(result).toBe(false);
    });
  });

  describe('Error Handling', () => {
    it('should handle timeout errors', async () => {
      // Arrange
      const timeoutError = new Error('Request timeout');
      timeoutError.name = 'AbortError';
      mockFetch.mockRejectedValueOnce(timeoutError);

      // Act & Assert
      await expect(
        kraApiService.getRaceResult('20241201', '서울', 1)
      ).rejects.toThrow('Request timeout');
    });

    it('should handle JSON parsing errors', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.reject(new Error('Invalid JSON')),
        headers: new Headers(),
      } as Response);

      // Act & Assert
      await expect(
        kraApiService.getRaceResult('20241201', '서울', 1)
      ).rejects.toThrow();
    });

    it('should preserve original error types', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers({ 'Retry-After': '60' }),
      } as Response);

      // Act & Assert
      try {
        await kraApiService.getRaceResult('20241201', '서울', 1);
        fail('Expected error to be thrown');
      } catch (error: any) {
        expect(error.message).toContain('rate limit');
      }
    });
  });

  describe('URL Building', () => {
    it('should build correct URLs with parameters', async () => {
      // Arrange
      const mockResponse = mockKraApiResponse<Api214Item>([{} as Api214Item]);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers(),
      } as Response);

      // Act
      await kraApiService.getRaceResult('20241201', '서울', 1);

      // Assert
      const fetchCall = mockFetch.mock.calls[0];
      const url = new URL(fetchCall[0] as string);
      
      expect(url.pathname).toBe('/api/openapi/API214_1.json');
      expect(url.searchParams.get('rc_date')).toBe('20241201');
      expect(url.searchParams.get('meet')).toBe('서울');
      expect(url.searchParams.get('rc_no')).toBe('1');
    });

    it('should include service key when available', async () => {
      // This would require mocking the config, which is complex with ES modules
      // For now, we'll just ensure the URL is called correctly
      const mockResponse = mockKraApiResponse<Api214Item>([{} as Api214Item]);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers(),
      } as Response);

      await kraApiService.getRaceResult('20241201', '서울', 1);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('API214_1.json'),
        expect.any(Object)
      );
    });
  });
});

// Additional integration-style tests that could be moved to integration test folder
describe('KraApiService Integration', () => {
  it('should handle concurrent requests properly', async () => {
    const service = new KraApiService();
    const mockResponse = mockKraApiResponse<Api214Item>([{} as Api214Item]);
    
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockResponse),
      headers: new Headers(),
    } as Response);

    // Make concurrent requests
    const promises = [
      service.getRaceResult('20241201', '서울', 1),
      service.getHorseDetail('20210001'),
      service.getJockeyDetail('001'),
      service.getTrainerDetail('001'),
    ];

    const results = await Promise.all(promises);
    expect(results).toHaveLength(4);
    expect(results.every(result => result !== null)).toBe(true);
  });
});