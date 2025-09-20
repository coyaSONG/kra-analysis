/**
 * Simple API Test
 * 
 * Basic test to verify core API functionality
 */

import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';
import request from 'supertest';
import { Application } from 'express';
import { createApp } from '../src/app.js';
import { Server } from 'http';

describe('Simple API Tests', () => {
  let app: Application;
  let server: Server;

  beforeAll(async () => {
    // Create Express application
    app = createApp();
    
    // Start server on random port
    server = app.listen(0);
    
    // Wait for server to be ready
    await new Promise(resolve => setTimeout(resolve, 100));
  });

  afterAll(async () => {
    if (server) {
      await new Promise<void>((resolve) => {
        server.close(() => resolve());
      });
    }
  });

  describe('Health Check', () => {
    it('should return healthy or degraded status', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.body.success).toBe(true);
      // In test environment, status can be 'degraded' due to external services
      expect(['healthy', 'degraded']).toContain(response.body.data.status);
    });
  });

  describe('API Info', () => {
    it('should return API information', async () => {
      const response = await request(app)
        .get('/api')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.version).toBe('v1');
    });
  });

  describe('Validation Tests', () => {
    it('should validate date format', async () => {
      const response = await request(app)
        .get('/api/v1/races/invalid-date/서울/1')
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBeDefined();
    });

    it('should validate horse ID format', async () => {
      const response = await request(app)
        .get('/api/v1/horses/123') // Too short
        .expect(400);

      expect(response.body.success).toBe(false);
    });

    it('should validate jockey ID format', async () => {
      const response = await request(app)
        .get('/api/v1/jockeys/12345') // Too short (should be 6 digits)
        .expect(400);

      expect(response.body.success).toBe(false);
    });

    it('should validate trainer ID format', async () => {
      const response = await request(app)
        .get('/api/v1/trainers/12345') // Too short (should be 6 digits)
        .expect(400);

      expect(response.body.success).toBe(false);
    });
  });

  describe('404 Handling', () => {
    it('should handle unknown routes', async () => {
      const response = await request(app)
        .get('/api/v1/nonexistent')
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.message).toContain('not found');
    });
  });
});