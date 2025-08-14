/**
 * Health Routes
 *
 * System health, readiness, and monitoring endpoints
 */

import { Router, type Router as ExpressRouter, type Request, type Response, type NextFunction } from 'express';
import * as os from 'os';
import {
  // Rate limiting
  generalRateLimit,

  // Logging
  healthCheckLogger,
} from '../middleware/index.js';
import { controllerRegistry } from '../controllers/index.js';
import { getRedisClient } from '../utils/redis.js';
import { services } from '../services/index.js';
import logger from '../utils/logger.js';
import { appConfig } from '../config/index.js';
import type { LoggingRequest } from '../middleware/logging.middleware.js';

const router: ExpressRouter = Router();

/**
 * Health check response interface
 */
interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  uptime: number;
  components: {
    redis: {
      status: 'up' | 'down';
      latency?: number;
    };
    controllers: Record<string, boolean>;
    kraApi: {
      status: 'up' | 'down' | 'unknown';
      latency?: number;
    };
    services: {
      collection: boolean;
      enrichment: boolean;
      cache: boolean;
    };
  };
  metrics?: {
    memory: {
      used: number;
      total: number;
      percentage: number;
    };
    process: {
      pid: number;
      uptime: number;
    };
  };
}

/**
 * GET /health
 * Basic health check endpoint
 */
router.get(
  '/',
  generalRateLimit,
  healthCheckLogger,
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const startTime = Date.now();
      // Security/CX headers expected by tests
      res.setHeader('X-XSS-Protection', '1; mode=block');

      // Basic health indicators
      const response: HealthCheckResponse = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || '1.0.0',
        uptime: process.uptime(),
        components: {
          redis: { status: 'down' },
          controllers: {},
          kraApi: { status: 'unknown' },
          services: {
            collection: false,
            enrichment: false,
            cache: false,
          },
        },
      };

      // Check Redis connection
      try {
        const redisClient = getRedisClient();
        if (redisClient && redisClient.status === 'ready') {
          const redisStart = Date.now();
          await redisClient.ping();
          response.components.redis = {
            status: 'up',
            latency: Date.now() - redisStart,
          };
        }
      } catch (error) {
        logger.warn('Redis health check failed', { error });
        response.components.redis.status = 'down';
      }

      // Check controller health
      try {
        response.components.controllers = await controllerRegistry.healthCheck();
      } catch (error) {
        logger.warn('Controller health check failed', { error });
        response.status = 'degraded';
      }

      // Check service availability
      try {
        response.components.services = {
          collection: typeof services.collection?.collectRace === 'function',
          enrichment: typeof services.enrichment?.enrichRaceData === 'function',
          cache: typeof services.cache?.get === 'function',
        };
      } catch (error) {
        logger.warn('Service health check failed', { error });
        response.status = 'degraded';
      }

      // Determine overall status
      const hasFailures =
        response.components.redis.status === 'down' ||
        Object.values(response.components.controllers).some((status) => !status) ||
        Object.values(response.components.services).some((status) => !status);

      if (hasFailures && response.status === 'healthy') {
        response.status = 'degraded';
      }

      // Set appropriate HTTP status
      const httpStatus = response.status === 'healthy' ? 200 : response.status === 'degraded' ? 200 : 503;

      // Response time header
      const responseTime = Date.now() - startTime;
      res.setHeader('X-Response-Time', `${responseTime}ms`);

      res.status(httpStatus).json({
        success: response.status !== 'unhealthy',
        data: response,
        requestId: (req as LoggingRequest).requestId,
        meta: {
          responseTime,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * GET /health/ready
 * Readiness check - more comprehensive than health check
 */
router.get(
  '/ready',
  generalRateLimit,
  healthCheckLogger,
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const startTime = Date.now();
      const checks: Record<string, boolean> = {};

      // Redis readiness
      try {
        const redisClient = getRedisClient();
        if (redisClient && redisClient.status === 'ready') {
          await redisClient.ping();
          await redisClient.setex('readiness_check', 60, Date.now().toString());
          await redisClient.get('readiness_check');
          checks.redis = true;
        } else {
          checks.redis = false;
        }
      } catch (error) {
        logger.warn('Redis readiness check failed', { error });
        checks.redis = false;
      }

      // KRA API readiness (light check)
      try {
        // This would be a minimal API test - we'll simulate for now
        // In real implementation, you might want to call a lightweight KRA API endpoint
        checks.kraApi = true; // Set to true for now, implement actual check as needed
      } catch (error) {
        logger.warn('KRA API readiness check failed', { error });
        checks.kraApi = false;
      }

      // Service readiness
      checks.services = Object.values(services).every((service) => service != null);

      // Controller readiness
      const controllerHealth = await controllerRegistry.healthCheck();
      checks.controllers = Object.values(controllerHealth).every((status) => status);

      // Overall readiness
      const isReady = Object.values(checks).every((check) => check);

      const response = {
        ready: isReady,
        status: isReady ? ('ready' as const) : ('not_ready' as const),
        timestamp: new Date().toISOString(),
        checks,
        environment: appConfig.nodeEnv,
        responseTime: Date.now() - startTime,
      };

      res.status(isReady ? 200 : 503).json({
        success: isReady,
        data: response,
        requestId: (req as LoggingRequest).requestId,
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * GET /health/detailed
 * Detailed health information including metrics
 */
router.get(
  '/detailed',
  generalRateLimit,
  healthCheckLogger,
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const startTime = Date.now();

      // Build on basic health
      const controllers = await controllerRegistry.healthCheck();
      const redisClient = getRedisClient();
      let redisStatus: 'up' | 'down' = 'down';
      if (redisClient) {
        try {
          await redisClient.ping();
          redisStatus = 'up';
        } catch {
          redisStatus = 'down';
        }
      }

      const response: HealthCheckResponse = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || '1.0.0',
        uptime: process.uptime(),
        components: {
          redis: { status: redisStatus },
          controllers,
          kraApi: { status: 'unknown' },
          services: {
            collection: typeof services.collection?.collectRace === 'function',
            enrichment: typeof services.enrichment?.enrichRaceData === 'function',
            cache: typeof services.cache?.get === 'function',
          },
        },
        metrics: {
          memory: {
            used: process.memoryUsage().heapUsed,
            total: process.memoryUsage().heapTotal,
            percentage: Math.round((process.memoryUsage().heapUsed / process.memoryUsage().heapTotal) * 10000) / 100,
          },
          process: {
            pid: process.pid,
            uptime: process.uptime(),
          },
        },
      };

      // Response time header
      const responseTime = Date.now() - startTime;
      res.setHeader('X-Response-Time', `${responseTime}ms`);
      res.setHeader('X-XSS-Protection', '1; mode=block');

      res.status(200).json({
        success: true,
        data: response,
        requestId: (req as LoggingRequest).requestId,
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * GET /health/live
 * Liveness check - minimal check to see if service is running
 */
router.get(
  '/live',
  // No rate limiting on liveness check
  async (req: Request, res: Response): Promise<void> => {
    res.status(200).json({
      success: true,
      data: {
        status: 'alive',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        pid: process.pid,
      },
    });
  }
);

/**
 * GET /health/metrics
 * System metrics endpoint
 */
router.get(
  '/metrics',
  generalRateLimit,
  healthCheckLogger,
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const memoryUsage = process.memoryUsage();

      const metrics = {
        timestamp: new Date().toISOString(),
        process: {
          pid: process.pid,
          uptime: process.uptime(),
          version: process.version,
          platform: process.platform,
          arch: process.arch,
        },
        memory: {
          rss: memoryUsage.rss,
          heapUsed: memoryUsage.heapUsed,
          heapTotal: memoryUsage.heapTotal,
          external: memoryUsage.external,
          arrayBuffers: memoryUsage.arrayBuffers,
        },
        system: {
          loadavg: os.loadavg(),
          cpuUsage: process.cpuUsage(),
        },
        controllers: controllerRegistry.getStats(),
        environment: {
          nodeEnv: appConfig.nodeEnv,
          nodeVersion: process.version,
          port: appConfig.port,
        },
      };

      res.json({
        success: true,
        data: metrics,
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * GET /health/version
 * Version and build information
 */
router.get('/version', generalRateLimit, async (req: Request, res: Response): Promise<void> => {
  const versionInfo = {
    version: process.env.npm_package_version || '1.0.0',
    name: process.env.npm_package_name || 'kra-nodejs-collector',
    description: process.env.npm_package_description || 'KRA Horse Racing Data Collector',
    environment: appConfig.nodeEnv,
    nodeVersion: process.version,
    buildDate: process.env.BUILD_DATE || new Date().toISOString(),
    gitCommit: process.env.GIT_COMMIT || 'unknown',
    gitBranch: process.env.GIT_BRANCH || 'unknown',
  };

  res.json({
    success: true,
    data: versionInfo,
  });
});

export default router;
