/**
 * Express Application Configuration
 *
 * Creates and configures the Express application with all middleware,
 * routes, and error handling in the proper order
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import type { Application } from 'express';

// Middleware imports
import { requestLogger, errorHandler, notFoundHandler, registerAllMiddleware } from './middleware/index.js';

// Routes
import { registerRoutes } from './routes/index.js';

// Utils
import logger from './utils/logger.js';
import { getRedisClient } from './utils/redis.js';
import { appConfig } from './config/index.js';

/**
 * Create and configure Express application
 */
export const createApp = (): Application => {
  const app = express();

  // Trust proxy settings for production deployment
  if (appConfig.nodeEnv === 'production') {
    app.set('trust proxy', 1);
  }

  // Security middleware (must be first)
  app.use(
    helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          scriptSrc: ["'self'"],
          imgSrc: ["'self'", 'data:', 'https:'],
          connectSrc: ["'self'"],
          fontSrc: ["'self'"],
          objectSrc: ["'none'"],
          mediaSrc: ["'self'"],
          frameSrc: ["'none'"],
        },
      },
      crossOriginEmbedderPolicy: false, // Allow embedding for API documentation
    })
  );

  // CORS configuration
  app.use(
    cors({
      origin: (origin, callback) => {
        // Allow requests with no origin (mobile apps, curl, etc.)
        if (!origin) return callback(null, true);

        const allowedOrigins = appConfig.corsOrigins || ['*'];

        if (allowedOrigins.includes('*') || allowedOrigins.includes(origin)) {
          callback(null, true);
        } else {
          callback(new Error('Not allowed by CORS'));
        }
      },
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
      allowedHeaders: [
        'Origin',
        'X-Requested-With',
        'Content-Type',
        'Accept',
        'Authorization',
        'X-API-Key',
        'X-Request-ID',
        'X-Forwarded-For',
      ],
      exposedHeaders: ['X-Total-Count', 'X-Page-Count', 'X-Current-Page', 'X-Per-Page', 'X-Response-Time'],
    })
  );

  // Compression middleware
  app.use(
    compression({
      filter: (req, res) => {
        if (req.headers['x-no-compression']) {
          return false;
        }
        return compression.filter(req, res);
      },
      level: 6,
      threshold: 1024,
    })
  );

  // Request parsing middleware
  app.use(
    express.json({
      limit: '10mb',
      verify: (req, res, buf) => {
        // Store raw body for webhook verification if needed
        (req as any).rawBody = buf;
      },
    })
  );

  app.use(
    express.urlencoded({
      extended: true,
      limit: '10mb',
    })
  );

  // Request logging middleware (before custom middleware)
  app.use(requestLogger);

  // Custom middleware registration (auth, rate limiting, etc.)
  registerAllMiddleware(app);

  // Initialize Redis connection (with error handling)
  try {
    const redisClient = getRedisClient();
    if (redisClient && redisClient.status === 'ready') {
      logger.info('Redis client initialized and connected');

      // Optional: Set up Redis event handlers
      redisClient.on('error', (err) => {
        logger.error('Redis client error', { error: err });
      });

      redisClient.on('connect', () => {
        logger.info('Redis client connected');
      });

      redisClient.on('disconnect', () => {
        logger.warn('Redis client disconnected');
      });
    } else {
      logger.warn('Redis client not available or not connected');
    }
  } catch (error) {
    logger.error('Failed to initialize Redis client', { error });
  }

  // Register all routes BEFORE error handlers
  registerRoutes(app);

  // Error handling middleware (must be last, AFTER routes)
  app.use(notFoundHandler);
  app.use(errorHandler);

  logger.info('Express application created and configured', {
    environment: appConfig.nodeEnv,
    features: {
      cors: true,
      helmet: true,
      compression: true,
      redis: !!getRedisClient(),
      logging: true,
      errorHandling: true,
    },
  });

  return app;
};

/**
 * Graceful shutdown handler
 */
export const gracefulShutdown = async (app: Application): Promise<void> => {
  logger.info('Starting graceful shutdown...');

  try {
    // Close Redis connections
    const redisClient = getRedisClient();
    if (redisClient && redisClient.status === 'ready') {
      await redisClient.quit();
      logger.info('Redis connection closed');
    }

    logger.info('Graceful shutdown completed');
  } catch (error) {
    logger.error('Error during graceful shutdown', { error });
    throw error;
  }
};

export default createApp;
