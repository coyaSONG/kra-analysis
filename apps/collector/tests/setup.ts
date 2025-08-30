/**
 * Jest Test Setup
 * 
 * Global configuration and utilities for the Jest testing environment.
 * This file is run once before each test file.
 */

import { config } from 'dotenv';
import { expect } from '@jest/globals';
import { join } from 'path';

// Load test environment variables
config({ path: join(__dirname, '..', '.env.test') });

// Set test environment
process.env.NODE_ENV = 'test';
process.env.PORT = '0'; // Use random available port for tests
process.env.LOG_LEVEL = 'silent'; // Suppress logs during tests

// Disable Redis in tests by default (can be overridden in specific tests)
if (!process.env.REDIS_URL && !process.env.ENABLE_REDIS_IN_TESTS) {
  delete process.env.REDIS_HOST;
  delete process.env.REDIS_PORT;
  delete process.env.REDIS_PASSWORD;
}

// Mock external services by default
process.env.KRA_API_BASE_URL = 'http://mock-kra-api.test';

// Test database configuration (if using database)
process.env.DATABASE_URL = process.env.TEST_DATABASE_URL || 'sqlite::memory:';

// Increase timeout for async operations in tests
jest.setTimeout(30000);

// Global test utilities
export {}; // Ensure this file is treated as a module for TS/Jest

// Custom Jest matchers
expect.extend({
  toBeValidDate(received) {
    const pass = received instanceof Date && !isNaN(received.getTime());
    return {
      message: () => `expected ${received} to be a valid Date object`,
      pass,
    };
  },

  toBeValidUUID(received) {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    const pass = typeof received === 'string' && uuidRegex.test(received);
    return {
      message: () => `expected ${received} to be a valid UUID v4`,
      pass,
    };
  },

  toMatchKraApiResponse(received) {
    const hasRequiredFields = 
      received &&
      typeof received === 'object' &&
      'success' in received &&
      'data' in received &&
      'timestamp' in received;

    return {
      message: () => `expected ${JSON.stringify(received)} to match KRA API response format`,
      pass: hasRequiredFields,
    };
  },
});

// Global test helpers
export const createTestUser = () => ({
  id: 'test-user-001',
  email: 'test@example.com',
  apiKey: 'test-api-key-123',
});

export const createTestRaceData = () => ({
  date: '20241201',
  meet: '서울',
  raceNo: 1,
  raceName: 'Test Race',
  horses: [
    {
      chulNo: 1,
      hrNo: '20210001',
      hrName: 'Test Horse',
      jkNo: '001',
      jkName: 'Test Jockey',
      weight: 55,
    },
  ],
});

export const createTestHorseData = () => ({
  hrNo: '20210001',
  hrName: 'Test Horse',
  age: 4,
  sex: '수컷',
  birthDate: '20200315',
  country: '한국',
});

export const createTestJockeyData = () => ({
  jkNo: '001',
  jkName: 'Test Jockey',
  age: 35,
  weight: 52,
  debut: '20100301',
  license: '정기수',
});

export const createTestTrainerData = () => ({
  trNo: '001',
  trName: 'Test Trainer',
  license: '정조교사',
  stable: '1구역',
  debut: '20050301',
});

// Mock data for KRA API responses
export const mockKraApiResponse = (data: any) => ({
  response: {
    header: {
      resultCode: '00',
      resultMsg: 'NORMAL SERVICE.',
    },
    body: {
      items: {
        item: Array.isArray(data) ? data : [data],
      },
      numOfRows: Array.isArray(data) ? data.length : 1,
      pageNo: 1,
      totalCount: Array.isArray(data) ? data.length : 1,
    },
  },
});

// Error response mock
export const mockKraApiError = (code = '99', message = 'TEST ERROR') => ({
  response: {
    header: {
      resultCode: code,
      resultMsg: message,
    },
    body: {
      items: { item: [] },
      numOfRows: 0,
      pageNo: 1,
      totalCount: 0,
    },
  },
});

// Network error simulation
export const simulateNetworkError = () => {
  throw new Error('ENOTFOUND mock-kra-api.test');
};

// Timeout error simulation
export const simulateTimeout = () => {
  throw new Error('Request timeout');
};

// Rate limit error simulation
export const simulateRateLimit = () => {
  const error = new Error('Rate limit exceeded');
  (error as any).status = 429;
  throw error;
};

// Console output suppression utilities
export const suppressConsole = () => {
  jest.spyOn(console, 'log').mockImplementation(() => {});
  jest.spyOn(console, 'warn').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
  jest.spyOn(console, 'info').mockImplementation(() => {});
};

export const restoreConsole = () => {
  jest.restoreAllMocks();
};

// Async test utilities
export const waitFor = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

export const waitUntil = async (
  condition: () => boolean,
  timeout = 5000,
  interval = 100
): Promise<void> => {
  const start = Date.now();
  
  while (!condition() && Date.now() - start < timeout) {
    await waitFor(interval);
  }
  
  if (!condition()) {
    throw new Error(`Condition not met within ${timeout}ms`);
  }
};

// Test database utilities (if using database)
export const cleanupDatabase = async (): Promise<void> => {
  // Implementation would depend on your database setup
  // For now, this is a placeholder
  console.log('Database cleanup completed');
};

export const seedTestData = async (): Promise<void> => {
  // Implementation would depend on your database setup
  // For now, this is a placeholder
  console.log('Test data seeded');
};

// Cleanup after each test
afterEach(async () => {
  // Clear all mocks
  jest.clearAllMocks();
  
  // Reset environment variables that might have been modified
  process.env.NODE_ENV = 'test';
});

// Disable console logs during tests
if (process.env.NODE_ENV === 'test' && process.env.DEBUG !== 'true') {
  global.console.log = jest.fn();
  global.console.info = jest.fn();
  global.console.warn = jest.fn();
  global.console.debug = jest.fn();
}

// Export commonly used testing utilities
export {
  // Re-export for convenience
  jest,
  expect,
  describe,
  it,
  test,
  beforeAll,
  afterAll,
  beforeEach,
  afterEach,
};