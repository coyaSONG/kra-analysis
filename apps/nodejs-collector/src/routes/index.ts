/**
 * Main Router
 *
 * Combines all route modules with proper prefixing and organization
 */

import { Router, type Router as ExpressRouter } from 'express';
import type { Application } from 'express';

// Route imports
import raceRoutes from './race.routes.js';
import horseRoutes from './horse.routes.js';
import jockeyRoutes from './jockey.routes.js';
import trainerRoutes from './trainer.routes.js';
import healthRoutes from './health.routes.js';
import collectionRoutes from './collection.js';

// Utils
import logger from '../utils/logger.js';
import { appConfig } from '../config/index.js';

/**
 * Create and configure main router with all route modules
 */
export const createRoutes = (): ExpressRouter => {
  const router: ExpressRouter = Router();

  // API v1 routes with proper prefixing
  router.use('/api/v1/races', raceRoutes);
  router.use('/api/v1/horses', horseRoutes);
  router.use('/api/v1/jockeys', jockeyRoutes);
  router.use('/api/v1/trainers', trainerRoutes);

  // Health and monitoring routes (no versioning)
  router.use('/health', healthRoutes);

  // Legacy collection routes (maintain backward compatibility)
  router.use('/api/collection', collectionRoutes);

  // Root endpoint with comprehensive API documentation
  router.get('/', (req, res) => {
    res.json({
      success: true,
      message: 'KRA Data Collector API',
      version: process.env.npm_package_version || '1.0.0',
      environment: appConfig.nodeEnv,
      timestamp: new Date().toISOString(),
      endpoints: {
        // API v1 endpoints
        races: '/api/v1/races',
        horses: '/api/v1/horses',
        jockeys: '/api/v1/jockeys',
        trainers: '/api/v1/trainers',

        // Health endpoints
        health: '/health',
        ready: '/health/ready',
        live: '/health/live',
        metrics: '/health/metrics',
        version: '/health/version',

        // Legacy endpoints
        collection: '/api/collection',
      },
      documentation: {
        swagger: '/docs',
        postman: '/api/postman-collection',
        openapi: '/api/openapi.json',
      },
      support: {
        contact: 'dev@example.com',
        issues: 'https://github.com/example/kra-analysis/issues',
        docs: 'https://docs.example.com/kra-api',
      },
    });
  });

  // API documentation endpoint
  router.get('/api', (req, res) => {
    res.json({
      success: true,
      message: 'KRA Data Collector API Documentation',
      version: 'v1',
      baseUrl: `${req.protocol}://${req.get('host')}/api/v1`,
      endpoints: {
        races: {
          base: '/races',
          methods: {
            'GET /:date': 'Get races by date',
            'GET /:date/:meet/:raceNo': 'Get specific race details',
            'POST /collect': 'Trigger race data collection',
            'POST /enrich': 'Trigger race data enrichment',
            'GET /:date/:meet/:raceNo/result': 'Get race result',
            'GET /stats': 'Get race statistics',
          },
        },
        horses: {
          base: '/horses',
          methods: {
            'GET /': 'Search horses',
            'GET /:hrNo': 'Get horse details',
            'GET /:hrNo/history': 'Get horse racing history',
            'GET /:hrNo/performance': 'Get horse performance analytics',
            'GET /top/performers': 'Get top performing horses',
            'GET /stats': 'Get horse statistics',
          },
        },
        jockeys: {
          base: '/jockeys',
          methods: {
            'GET /': 'Search jockeys',
            'GET /:jkNo': 'Get jockey details',
            'GET /:jkNo/stats': 'Get jockey statistics',
            'GET /:jkNo/performance': 'Get jockey performance',
            'GET /:jkNo/races': 'Get jockey races',
            'GET /top/performers': 'Get top jockeys',
            'GET /rankings': 'Get jockey rankings',
          },
        },
        trainers: {
          base: '/trainers',
          methods: {
            'GET /': 'Search trainers',
            'GET /:trNo': 'Get trainer details',
            'GET /:trNo/stats': 'Get trainer statistics',
            'GET /:trNo/specialization': 'Get trainer specialization',
            'GET /:trNo/performance': 'Get trainer performance',
            'GET /:trNo/horses': 'Get trainer horses',
            'GET /top/performers': 'Get top trainers',
            'GET /rankings': 'Get trainer rankings',
          },
        },
      },
    });
  });

  logger.info('All routes configured successfully', {
    routes: ['races', 'horses', 'jockeys', 'trainers', 'health', 'collection'],
    version: 'v1',
  });

  return router;
};

/**
 * Register routes on Express application
 */
export const registerRoutes = (app: Application): void => {
  // Health and monitoring routes (no versioning)
  app.use('/health', healthRoutes);

  // API v1 routes with proper prefixing
  app.use('/api/v1/races', raceRoutes);
  app.use('/api/v1/horses', horseRoutes);
  app.use('/api/v1/jockeys', jockeyRoutes);
  app.use('/api/v1/trainers', trainerRoutes);

  // Legacy collection routes (maintain backward compatibility)
  app.use('/api/collection', collectionRoutes);

  // Root endpoint
  app.get('/', (req, res) => {
    res.json({
      success: true,
      message: 'KRA Data Collector API',
      version: process.env.npm_package_version || '1.0.0',
      environment: appConfig.nodeEnv,
      timestamp: new Date().toISOString(),
      endpoints: {
        races: '/api/v1/races',
        horses: '/api/v1/horses',
        jockeys: '/api/v1/jockeys',
        trainers: '/api/v1/trainers',
        health: '/health',
        collection: '/api/collection',
      },
    });
  });

  // API documentation endpoint
  app.get('/api', (req, res) => {
    res.json({
      success: true,
      message: 'KRA Data Collector API Documentation',
      version: 'v1',
      baseUrl: `${req.protocol}://${req.get('host')}/api/v1`,
    });
  });

  logger.info('Routes registered directly on application');
};

// Default export for backward compatibility
const router = createRoutes();
export default router;
