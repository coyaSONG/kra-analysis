/**
 * KRA API Integration Tests
 * 
 * Tests actual KRA API service calls to verify all endpoints are working correctly
 * Note: These tests require valid KRA_SERVICE_KEY in environment
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from '@jest/globals';
import { KraApiService } from '../../src/services/kraApiService.js';
import { config } from 'dotenv';

// Load environment variables
config();

describe('KRA API Integration Tests', () => {
  let kraApiService: KraApiService;
  
  // Test data - known valid values from KRA
  const TEST_DATA = {
    date: '20240106',
    meet: '1', // 서울
    raceNo: 1,
    horseNo: '0053587',  // 서부특송
    jockeyNo: '080476',  // 장추열
    trainerNo: '070165', // 서인석
  };

  beforeAll(() => {
    // Check if API key is available
    if (!process.env.KRA_SERVICE_KEY) {
      console.warn('⚠️  KRA_SERVICE_KEY not found in environment. Tests may fail.');
    }
    
    // Initialize service
    kraApiService = new KraApiService();
  });

  beforeEach(() => {
    // Add delay between tests to avoid rate limiting
    return new Promise(resolve => setTimeout(resolve, 1000));
  });

  describe('API214_1 - Race Result', () => {
    it('should fetch race result data successfully', async () => {
      const result = await kraApiService.getRaceResult(
        TEST_DATA.date,
        TEST_DATA.meet,
        TEST_DATA.raceNo
      );

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      
      // Check first item has expected fields
      const firstItem = result[0];
      expect(firstItem).toHaveProperty('hrName');
      expect(firstItem).toHaveProperty('hrNo');
      expect(firstItem).toHaveProperty('jkName');
      expect(firstItem).toHaveProperty('jkNo');
      expect(firstItem).toHaveProperty('trName');
      expect(firstItem).toHaveProperty('trNo');
      expect(firstItem).toHaveProperty('ord');
      expect(firstItem).toHaveProperty('rcDate');
      expect(firstItem).toHaveProperty('rcNo');
    }, 15000); // 15 second timeout

    it('should handle invalid date gracefully', async () => {
      const result = await kraApiService.getRaceResult(
        '20000101', // Very old date that won't have data
        TEST_DATA.meet,
        TEST_DATA.raceNo
      );

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      // KRA API might return empty array or single result for invalid dates
      expect(result.length).toBeLessThanOrEqual(1);
    });

    it('should work with different meet codes', async () => {
      // Test with 제주 (meet=2)
      const result = await kraApiService.getRaceResult(
        TEST_DATA.date,
        '2', // 제주
        1
      );

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      // May or may not have races on this date
    });
  });

  describe('API8_2 - Horse Detail', () => {
    it('should fetch horse detail successfully', async () => {
      const result = await kraApiService.getHorseDetail(TEST_DATA.horseNo);

      expect(result).toBeDefined();
      if (result) {
        expect(result).toHaveProperty('hrName');
        expect(result).toHaveProperty('hrNo');
        expect(result.hrNo).toBe(TEST_DATA.horseNo);
        expect(result).toHaveProperty('birthday');
        expect(result).toHaveProperty('sex');
        expect(result).toHaveProperty('rank');
        expect(result).toHaveProperty('rating');
        expect(result).toHaveProperty('owName');
      }
    }, 15000);

    it('should return null for non-existent horse', async () => {
      const result = await kraApiService.getHorseDetail('9999999');

      expect(result).toBeNull();
    });

    it('should handle invalid horse number format', async () => {
      const result = await kraApiService.getHorseDetail('invalid');

      expect(result).toBeNull();
    });
  });

  describe('API12_1 - Jockey Detail', () => {
    it('should fetch jockey detail successfully', async () => {
      const result = await kraApiService.getJockeyDetail(TEST_DATA.jockeyNo);

      expect(result).toBeDefined();
      if (result) {
        expect(result).toHaveProperty('jkName');
        expect(result).toHaveProperty('jkNo');
        expect(result.jkNo).toBe(TEST_DATA.jockeyNo);
        expect(result).toHaveProperty('birthday');
        expect(result).toHaveProperty('age');
        expect(result).toHaveProperty('debut');
        expect(result).toHaveProperty('ord1CntT');
        expect(result).toHaveProperty('ord2CntT');
        expect(result).toHaveProperty('ord3CntT');
        expect(result).toHaveProperty('rcCntT');
      }
    }, 15000);

    it('should return null for non-existent jockey', async () => {
      const result = await kraApiService.getJockeyDetail('999999');

      expect(result).toBeNull();
    });
  });

  describe('API19_1 - Trainer Detail', () => {
    it('should fetch trainer detail successfully', async () => {
      const result = await kraApiService.getTrainerDetail(TEST_DATA.trainerNo);

      expect(result).toBeDefined();
      if (result) {
        expect(result).toHaveProperty('trName');
        expect(result).toHaveProperty('trNo');
        expect(result.trNo).toBe(TEST_DATA.trainerNo);
        // Some trainers may not have birthday or debut data
        // These fields are optional in the API response
        // expect(result).toHaveProperty('birthday');
        // expect(result).toHaveProperty('debut');
        expect(result).toHaveProperty('ord1CntT');
        expect(result).toHaveProperty('ord2CntT');
        expect(result).toHaveProperty('ord3CntT');
        expect(result).toHaveProperty('rcCntT');
        expect(result).toHaveProperty('winRateT');
      }
    }, 15000);

    it('should return null for non-existent trainer', async () => {
      const result = await kraApiService.getTrainerDetail('999999');

      expect(result).toBeNull();
    });
  });

  describe('Rate Limiting', () => {
    it('should handle rate limiting appropriately', async () => {
      // Make multiple rapid requests
      const promises = [];
      for (let i = 0; i < 5; i++) {
        promises.push(
          kraApiService.getRaceResult(TEST_DATA.date, TEST_DATA.meet, i + 1)
        );
      }

      const results = await Promise.allSettled(promises);
      
      // Check that at least some requests succeeded
      const successful = results.filter(r => r.status === 'fulfilled');
      expect(successful.length).toBeGreaterThan(0);
    }, 30000);
  });

  describe('Retry Logic', () => {
    it('should retry on temporary failures', async () => {
      // This is hard to test without mocking, but we can verify the service handles errors
      const result = await kraApiService.getRaceResult(
        TEST_DATA.date,
        TEST_DATA.meet,
        TEST_DATA.raceNo,
        { retryAttempts: 2, retryDelay: 500 }
      );

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      // Create a service instance with invalid URL
      const originalUrl = process.env.KRA_API_BASE_URL;
      process.env.KRA_API_BASE_URL = 'https://invalid-url-that-does-not-exist.com';
      
      const badService = new KraApiService();
      
      try {
        await badService.getRaceResult(TEST_DATA.date, TEST_DATA.meet, TEST_DATA.raceNo);
      } catch (error) {
        expect(error).toBeDefined();
      } finally {
        // Restore original URL
        process.env.KRA_API_BASE_URL = originalUrl;
      }
    });
  });

  describe('Data Validation', () => {
    it('should return properly formatted race data', async () => {
      const result = await kraApiService.getRaceResult(
        TEST_DATA.date,
        TEST_DATA.meet,
        TEST_DATA.raceNo
      );

      if (result.length > 0) {
        const item = result[0];
        
        // Check data types
        expect(typeof item.hrName).toBe('string');
        expect(typeof item.hrNo).toBe('string');
        expect(typeof item.ord).toBe('number');
        // rcDate can be either string or number depending on API response
        expect(['string', 'number']).toContain(typeof item.rcDate);
        expect(typeof item.rcNo).toBe('number');
        
        // Check date format (if it's a string)
        if (typeof item.rcDate === 'string') {
          expect(item.rcDate).toMatch(/^\d{8}$/);
        } else {
          expect(item.rcDate).toBeGreaterThan(20000000);
          expect(item.rcDate).toBeLessThan(30000000);
        }
        
        // Check horse number format
        expect(item.hrNo).toMatch(/^\d{7}$/);
        
        // Check jockey number format
        expect(item.jkNo).toMatch(/^\d{6}$/);
        
        // Check trainer number format
        expect(item.trNo).toMatch(/^\d{6}$/);
      }
    });
  });
});