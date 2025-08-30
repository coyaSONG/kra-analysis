import type { Application } from 'express';
import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import {
  errorHandler,
  notFoundHandler,
  requestLogger,
  detailedRequestLogger,
  performanceLogger,
  healthCheckLogger,
  generalRateLimit,
  strictRateLimit,
  apiCollectionRateLimit,
  gradualSlowDown,
  optionalAuth,
  requireAuth,
  requirePermission,
  requireAnyPermission,
  configureEndpointAccess,
} from './index.js';
import logger from '../utils/logger.js';

/**
 * Middleware configuration options
 */
export interface MiddlewareConfig {
  /** Enable detailed request logging */
  detailedLogging?: boolean;
  /** Enable performance monitoring */
  performanceMonitoring?: boolean;
  /** Enable rate limiting */
  rateLimiting?: {
    enabled: boolean;
    general?: boolean;
    strict?: boolean;
    apiCollection?: boolean;
    gradualSlowDown?: boolean;
  };
  /** Authentication configuration */
  auth?: {
    enabled: boolean;
    defaultMode?: 'public' | 'private' | 'optional';
    requireAuthForAdmin?: boolean;
  };
  /** CORS configuration */
  cors?: {
    enabled: boolean;
    origin?: string | string[] | boolean;
    credentials?: boolean;
    methods?: string[];
    allowedHeaders?: string[];
  };
  /** Security headers configuration */
  security?: {
    enabled: boolean;
    helmetOptions?: any;
  };
  /** Health check paths */
  healthPaths?: string[];
}

/**
 * Default middleware configuration
 */
const DEFAULT_CONFIG: MiddlewareConfig = {
  detailedLogging: true,
  performanceMonitoring: true,
  rateLimiting: {
    enabled: true,
    general: true,
    strict: true,
    apiCollection: true,
    gradualSlowDown: true,
  },
  auth: {
    enabled: true,
    defaultMode: 'optional',
    requireAuthForAdmin: true,
  },
  cors: {
    enabled: true,
    origin: process.env.NODE_ENV === 'development' ? true : process.env.ALLOWED_ORIGINS?.split(','),
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key', 'X-Request-ID'],
  },
  security: {
    enabled: true,
    helmetOptions: {
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          scriptSrc: ["'self'"],
          imgSrc: ["'self'", 'data:', 'https:'],
        },
      },
    },
  },
  healthPaths: ['/health', '/status', '/ping'],
};

/**
 * Register global middleware
 */
export const registerGlobalMiddleware = (app: Application, config: Partial<MiddlewareConfig> = {}): void => {
  const mergedConfig = { ...DEFAULT_CONFIG, ...config };

  logger.info('Registering middleware with configuration:', mergedConfig);

  // Trust proxy (for rate limiting and IP detection)
  if (process.env.NODE_ENV === 'production') {
    app.set('trust proxy', 1);
  }

  // Security headers
  if (mergedConfig.security?.enabled) {
    app.use(helmet(mergedConfig.security.helmetOptions));
    logger.info('Security middleware (helmet) registered');
  }

  // CORS
  if (mergedConfig.cors?.enabled) {
    app.use(
      cors({
        origin: mergedConfig.cors.origin,
        credentials: mergedConfig.cors.credentials,
        methods: mergedConfig.cors.methods,
        allowedHeaders: mergedConfig.cors.allowedHeaders,
      })
    );
    logger.info('CORS middleware registered');
  }

  // Body parsing (Express 4.16+ has built-in body parser)
  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true, limit: '10mb' }));

  // Health check logging (minimal)
  if (mergedConfig.healthPaths && mergedConfig.healthPaths.length > 0) {
    mergedConfig.healthPaths.forEach((path) => {
      app.use(path, healthCheckLogger);
    });
    logger.info(`Health check logging registered for paths: ${mergedConfig.healthPaths.join(', ')}`);
  }

  // Request logging
  if (mergedConfig.detailedLogging) {
    app.use(detailedRequestLogger);
    logger.info('Detailed request logging registered');
  } else {
    app.use(requestLogger);
    logger.info('Basic request logging registered');
  }

  // Performance monitoring
  if (mergedConfig.performanceMonitoring) {
    app.use(performanceLogger);
    logger.info('Performance monitoring registered');
  }

  // Authentication (global, but can be overridden per route)
  if (mergedConfig.auth?.enabled) {
    const authMiddleware = configureEndpointAccess(mergedConfig.auth.defaultMode);
    app.use(authMiddleware);
    logger.info(`Authentication middleware registered with mode: ${mergedConfig.auth.defaultMode}`);
  }

  // Rate limiting
  if (mergedConfig.rateLimiting?.enabled) {
    // Global rate limiting with gradual slowdown
    if (mergedConfig.rateLimiting.gradualSlowDown) {
      app.use(gradualSlowDown);
      logger.info('Gradual slowdown middleware registered');
    }

    // General rate limiting (applied globally unless overridden)
    if (mergedConfig.rateLimiting.general) {
      app.use(generalRateLimit);
      logger.info('General rate limiting registered');
    }

    logger.info('Rate limiting middleware registered');
  }
};

/**
 * Register API-specific middleware for specific routes
 */
export const registerApiMiddleware = (app: Application, config: Partial<MiddlewareConfig> = {}): void => {
  const mergedConfig = { ...DEFAULT_CONFIG, ...config };

  // API Collection specific rate limiting
  if (mergedConfig.rateLimiting?.apiCollection) {
    app.use('/api/v1/collection*', apiCollectionRateLimit);
    app.use('/api/collection*', apiCollectionRateLimit);
    logger.info('API collection rate limiting registered');
  }

  // Strict rate limiting for write operations
  if (mergedConfig.rateLimiting?.strict) {
    app.use('/api/*/admin*', strictRateLimit);
    app.use('/admin*', strictRateLimit);
    logger.info('Strict rate limiting registered for admin routes');
  }

  // Require authentication for admin routes
  if (mergedConfig.auth?.requireAuthForAdmin) {
    app.use('/api/*/admin*', requireAuth);
    app.use('/admin*', requireAuth);
    logger.info('Required authentication registered for admin routes');
  }
};

/**
 * Register error handling middleware (should be last)
 */
export const registerErrorHandling = (app: Application): void => {
  // 404 handler
  app.use(notFoundHandler);

  // Global error handler
  app.use(errorHandler);

  logger.info('Error handling middleware registered');
};

/**
 * Register all middleware with default configuration
 * NOTE: This does NOT register error handlers - those must be registered
 * AFTER all routes are registered
 */
export const registerAllMiddleware = (app: Application, config: Partial<MiddlewareConfig> = {}): void => {
  registerGlobalMiddleware(app, config);
  registerApiMiddleware(app, config);
  // NOTE: Error handling is NOT registered here - it must be done after routes

  logger.info('All middleware registered successfully');
};

/**
 * Middleware registration helper for specific route groups
 */
export const createRouteMiddleware = (options: {
  auth?: 'public' | 'private' | 'optional';
  rateLimit?: 'general' | 'strict' | 'api-collection' | 'none';
  validation?: any[];
  permissions?: string[];
}) => {
  const middleware: any[] = [];

  // Authentication
  if (options.auth === 'private') {
    middleware.push(requireAuth);
  } else if (options.auth === 'optional') {
    middleware.push(optionalAuth);
  }
  // 'public' means no auth middleware

  // Rate limiting
  if (options.rateLimit === 'strict') {
    middleware.push(strictRateLimit);
  } else if (options.rateLimit === 'api-collection') {
    middleware.push(apiCollectionRateLimit);
  } else if (options.rateLimit === 'general') {
    middleware.push(generalRateLimit);
  }
  // 'none' means no rate limiting

  // Validation
  if (options.validation) {
    middleware.push(...options.validation);
  }

  // Permissions (requires auth to be enabled)
  if (options.permissions && options.permissions.length > 0) {
    if (options.auth !== 'private') {
      logger.warn('Permissions specified but auth is not private. Adding requireAuth middleware.');
      middleware.push(requireAuth);
    }
    // Add permission middleware based on requirements
    if (options.permissions.length === 1) {
      const firstPermission = options.permissions[0];
      if (firstPermission) {
        middleware.push(requirePermission(firstPermission));
      }
    } else {
      middleware.push(requireAnyPermission(options.permissions));
    }
  }

  return middleware;
};

/**
 * Quick middleware configurations for common scenarios
 */
export const middlewarePresets = {
  // Public API endpoints
  public: () =>
    createRouteMiddleware({
      auth: 'public',
      rateLimit: 'general',
    }),

  // Private API endpoints requiring authentication
  private: () =>
    createRouteMiddleware({
      auth: 'private',
      rateLimit: 'general',
    }),

  // Admin endpoints with strict rate limiting
  admin: () =>
    createRouteMiddleware({
      auth: 'private',
      rateLimit: 'strict',
      permissions: ['admin'],
    }),

  // Data collection endpoints
  collection: (validation?: any[]) =>
    createRouteMiddleware({
      auth: 'optional',
      rateLimit: 'api-collection',
      validation,
    }),

  // Write operations with stricter controls
  write: (validation?: any[]) =>
    createRouteMiddleware({
      auth: 'private',
      rateLimit: 'strict',
      validation,
      permissions: ['write'],
    }),

  // Read-only operations
  read: (validation?: any[]) =>
    createRouteMiddleware({
      auth: 'optional',
      rateLimit: 'general',
      validation,
    }),
};

export default registerAllMiddleware;
