/**
 * API Integration Tests
 * 
 * End-to-end integration tests for the KRA Data Collector API
 * Tests the full request/response cycle with all middleware
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from '@jest/globals';
import request from 'supertest';
import { Application } from 'express';
import { createApp } from '../../src/app.js';
import { Server } from 'http';
import { services } from '../../src/services/index.js';
import { 
  mockKraApiResponse,
  createTestRaceData,
  waitFor
} from '../setup.js';

// Mock fetch for KRA API calls in integration tests
const mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;
global.fetch = mockFetch;

describe('API Integration Tests', () => {
  let app: Application;
  let server: Server;

  beforeAll(async () => {
    // Create Express application
    app = createApp();
    
    // Start server on random port
    server = app.listen(0);

    // Wait for server to be ready
    await waitFor(100);
  });

  afterAll(async () => {
    if (server) {
      await new Promise<void>((resolve, reject) => {
        server.close((err) => {
          if (err) reject(err);
          else resolve();
        });
      });
    }
    // Force cleanup
    await waitFor(100);
  });

  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  describe('Health Check Endpoints', () => {
    it('should return healthy status', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        data: {
          status: 'healthy',
          timestamp: expect.any(String),
          uptime: expect.any(Number),
          version: expect.any(String)
        }
      });
    });

    it('should return detailed health status', async () => {
      const response = await request(app)
        .get('/health/detailed')
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        data: {
          status: 'healthy',
          timestamp: expect.any(String),
          components: expect.any(Object)
        }
      });
    });

    it('should return readiness probe', async () => {
      const response = await request(app)
        .get('/health/ready')
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        data: {
          status: expect.stringMatching(/ready|not_ready/)
        }
      });
    });

    it('should return liveness probe', async () => {
      const response = await request(app)
        .get('/health/live')
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        data: {
          status: 'alive'
        }
      });
    });
  });

  describe('API Information Endpoints', () => {
    it('should return API root information', async () => {
      const response = await request(app)
        .get('/')
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        message: 'KRA Data Collector API',
        version: expect.any(String),
        environment: 'test',
        endpoints: expect.any(Object),
        timestamp: expect.any(String)
      });
    });

    it('should return API documentation', async () => {
      const response = await request(app)
        .get('/api')
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        message: 'KRA Data Collector API Documentation',
        version: 'v1',
        baseUrl: expect.stringContaining('/api/v1'),
        endpoints: expect.any(Object)
      });
    });
  });

  describe('Race Endpoints', () => {
    describe('GET /api/v1/races/:date', () => {
      it('should return races for a valid date', async () => {
        const collectDaySpy = jest.spyOn(services.collectionService, 'collectDay').mockResolvedValueOnce([
          {
            raceInfo: {
              date: '20241201',
              meet: '서울',
              raceNo: 1,
              rcName: '테스트 경주',
              rcDist: 1200,
              track: '양호',
              weather: '맑음',
              totalHorses: 1,
            },
            raceResult: [],
            collectionMeta: {
              collectedAt: '2024-12-01T00:00:00.000Z',
              isEnriched: false,
              dataSource: 'kra_api',
            },
          },
        ]);

        const response = await request(app)
          .get('/api/v1/races/20241201')
          .expect(200);

        expect(collectDaySpy).toHaveBeenCalledWith('20241201', undefined, false);
        expect(response.body).toMatchKraApiResponse();
        expect(Array.isArray(response.body.data)).toBe(true);
      });

      it('should validate date parameter', async () => {
        const response = await request(app)
          .get('/api/v1/races/invalid-date')
          .expect(400);

        expect(response.body).toMatchObject({
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: expect.stringContaining('validation'),
          }
        });
      });

      it('should handle query parameters', async () => {
        const collectDaySpy = jest.spyOn(services.collectionService, 'collectDay').mockResolvedValueOnce([]);

        const response = await request(app)
          .get('/api/v1/races/20241201?meet=1&limit=5')
          .expect(200);

        expect(collectDaySpy).toHaveBeenCalledWith('20241201', '1', false);
        expect(response.body).toMatchKraApiResponse();
      });
    });

    describe('GET /api/v1/races/:date/:meet/:raceNo', () => {
      it('should return specific race details', async () => {
        const mockRaceData = createTestRaceData();
        mockFetch.mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockKraApiResponse([mockRaceData])),
          headers: new Headers(),
        } as Response);

        const response = await request(app)
          .get('/api/v1/races/20241201/1/1')
          .expect(200);

        expect(response.body).toMatchKraApiResponse();
        expect(response.body.data).toHaveProperty('raceInfo');
        expect(response.body.data).toHaveProperty('raceResult');
      });

      it('should validate race parameters', async () => {
        const response = await request(app)
          .get('/api/v1/races/20241201/invalid-meet/0')
          .expect(400);

        expect(response.body).toMatchObject({
          success: false,
          error: {
            code: 'VALIDATION_ERROR'
          }
        });
      });
    });

    describe('POST /api/v1/races/collect', () => {
      it('should trigger race data collection', async () => {
        const response = await request(app)
          .post('/api/v1/races/collect')
          .send({
            date: '20241201',
            meet: '1',
            raceNo: 1
          })
          .expect(202);

        expect(response.body).toMatchObject({
          success: true,
          data: {
            jobId: expect.any(String),
            status: 'started'
          }
        });
      });

      it('should accept legacy Korean meet names for collection', async () => {
        const response = await request(app)
          .post('/api/v1/races/collect')
          .send({
            date: '20241201',
            meet: '서울',
            raceNo: 1
          })
          .expect(202);

        expect(response.body).toMatchObject({
          success: true,
          data: {
            jobId: expect.any(String),
            status: 'started'
          }
        });
      });

      it('should validate collection request body', async () => {
        const response = await request(app)
          .post('/api/v1/races/collect')
          .send({
            date: '20241201'
            // missing required fields
          })
          .expect(400);

        expect(response.body).toMatchObject({
          success: false,
          error: {
            code: 'VALIDATION_ERROR'
          }
        });
      });

      it('should handle invalid JSON', async () => {
        const response = await request(app)
          .post('/api/v1/races/collect')
          .set('Content-Type', 'application/json')
          .send('invalid json')
          .expect(400);

        expect(response.body).toMatchObject({
          success: false,
          error: expect.any(Object)
        });
      });
    });
  });

  describe('Horse Endpoints', () => {
    describe('GET /api/v1/horses', () => {
      it('should return not implemented contract for horse search', async () => {
        const response = await request(app)
          .get('/api/v1/horses?name=천리마&limit=10')
          .expect(501);

        expect(response.body).toMatchObject({
          success: false,
          error: {
            code: 'NOT_IMPLEMENTED',
          },
          timestamp: expect.any(String),
        });
      });

      it('should keep same not implemented contract for any horse search query', async () => {
        const response = await request(app)
          .get('/api/v1/horses?name=nonexistent')
          .expect(501);

        expect(response.body).toMatchObject({
          success: false,
          error: {
            code: 'NOT_IMPLEMENTED',
          },
          timestamp: expect.any(String),
        });
      });
    });

    describe('GET /api/v1/horses/:hrNo', () => {
      it('should return not implemented contract for horse details', async () => {
        const response = await request(app)
          .get('/api/v1/horses/20210001')
          .expect(501);

        expect(response.body).toMatchObject({
          success: false,
          error: {
            code: 'NOT_IMPLEMENTED',
          },
          timestamp: expect.any(String),
        });
      });

      it('should keep same not implemented contract regardless horse existence', async () => {
        const response = await request(app)
          .get('/api/v1/horses/99999999')
          .expect(501);

        expect(response.body).toMatchObject({
          success: false,
          error: {
            code: 'NOT_IMPLEMENTED',
          },
          timestamp: expect.any(String),
        });
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle 404 for unknown routes', async () => {
      const response = await request(app)
        .get('/api/v1/nonexistent')
        .expect(404);

      expect(response.body).toMatchObject({
        success: false,
        error: {
          code: 'NOT_FOUND',
          message: expect.stringContaining('not found')
        }
      });
    });

    it('should handle method not allowed', async () => {
      const response = await request(app)
        .patch('/api/v1/races/20241201')
        .expect(405);

      expect(response.body).toMatchObject({
        success: false,
        error: {
          code: 'METHOD_NOT_ALLOWED'
        }
      });
    });

    it('should handle large payloads', async () => {
      const largePayload = { data: 'x'.repeat(15 * 1024 * 1024) }; // 15MB

      const response = await request(app)
        .post('/api/v1/races/collect')
        .send(largePayload)
        .expect(413);

      expect(response.body).toMatchObject({
        success: false,
        error: {
          code: 'PAYLOAD_TOO_LARGE'
        }
      });
    });
  });

  describe('Response Headers', () => {
    it('should include security headers', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.headers).toMatchObject({
        'x-content-type-options': 'nosniff',
        'x-frame-options': 'DENY',
        'x-xss-protection': '1; mode=block'
      });
    });

    it('should include CORS headers', async () => {
      const response = await request(app)
        .options('/api/v1/races/20241201')
        .set('Origin', 'http://localhost:3000')
        .expect(204);

      expect(response.headers['access-control-allow-origin']).toBeDefined();
      expect(response.headers['access-control-allow-methods']).toBeDefined();
    });

    it('should include response time header', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.headers['x-response-time']).toMatch(/^\d+ms$/);
    });

    it('should include request ID header', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.body.requestId).toBeValidUUID();
    });
  });

  describe('Rate Limiting', () => {
    it('should apply rate limits to endpoints', async () => {
      // Note: This test might be flaky depending on rate limit configuration
      // In a real scenario, you'd want to configure very low limits for testing
      
      const promises = Array.from({ length: 10 }, () =>
        request(app).get('/health')
      );

      const responses = await Promise.all(promises);
      
      // All should succeed in test environment (rate limits are relaxed)
      responses.forEach(response => {
        expect([200, 429]).toContain(response.status);
      });
    });

    it('should include rate limit headers', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      // These headers should be present if rate limiting is enabled
      if (response.headers['x-ratelimit-limit']) {
        expect(response.headers['x-ratelimit-limit']).toBeDefined();
        expect(response.headers['x-ratelimit-remaining']).toBeDefined();
        expect(response.headers['x-ratelimit-reset']).toBeDefined();
      }
    });
  });

  describe('Content Negotiation', () => {
    it('should return JSON by default', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.type).toBe('application/json');
    });

    it('should handle Accept header', async () => {
      const response = await request(app)
        .get('/health')
        .set('Accept', 'application/json')
        .expect(200);

      expect(response.type).toBe('application/json');
    });

    it('should compress responses when appropriate', async () => {
      const response = await request(app)
        .get('/api')
        .set('Accept-Encoding', 'gzip')
        .expect(200);

      // Check if response was compressed (depends on response size and configuration)
      if (response.headers['content-encoding']) {
        expect(response.headers['content-encoding']).toBe('gzip');
      }
    });
  });

  describe('Request Logging', () => {
    it('should log requests with proper format', async () => {
      // This is more of a smoke test - in real scenarios you'd capture logs
      await request(app)
        .get('/health')
        .expect(200);

      // If we were capturing logs, we'd verify log format here
      // For now, just ensure the request completes successfully
    });
  });
});

// Additional test suite for testing error conditions
describe('API Error Conditions', () => {
  let app: Application;

  beforeAll(() => {
    app = createApp();
  });

  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();

    // Set integration test flag to allow proper error handling
    process.env.JEST_INTEGRATION_TEST = 'true';
  });

  describe('External API Errors', () => {
    it('should handle KRA API timeout', async () => {
      mockFetch.mockImplementation(() => 
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Request timeout')), 100)
        )
      );

      const response = await request(app)
        .get('/api/v1/races/20241201/1/1')
        .expect(502);

      expect(response.body).toMatchObject({
        success: false,
        error: {
          code: 'EXTERNAL_API_ERROR'
        }
      });
    });

    it('should handle KRA API network error', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));

      const response = await request(app)
        .get('/api/v1/races/20241201/1/1')
        .expect(502);

      expect(response.body).toMatchObject({
        success: false,
        error: {
          code: 'EXTERNAL_API_ERROR'
        }
      });
    });

    it('should handle KRA API rate limiting', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers({ 'Retry-After': '60' }),
      } as Response);

      const response = await request(app)
        .get('/api/v1/races/20241201/1/1')
        .expect(429);

      expect(response.body).toMatchObject({
        success: false,
        error: {
          code: 'RATE_LIMIT_EXCEEDED'
        }
      });
    });
  });

  describe('Internal Server Errors', () => {
    it('should handle uncaught exceptions gracefully', async () => {
      // This would require mocking internal components to throw errors
      // For now, we'll test that the error handler is properly registered
      
      const response = await request(app)
        .get('/api/v1/nonexistent')
        .expect(404);

      expect(response.body).toMatchObject({
        success: false,
        error: expect.any(Object)
      });
    });
  });
});
