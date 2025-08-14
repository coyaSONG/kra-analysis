import rateLimit, { type RateLimitRequestHandler } from 'express-rate-limit';
import slowDown from 'express-slow-down';
import type { Request, Response } from 'express';
import { createClient as createRedisClient } from 'redis';
import logger from '../utils/logger.js';

/**
 * Redis client for rate limiting (optional)
 * Falls back to memory store if Redis is unavailable
 */
let redisClient: any = null;
let redisErrorLogged = false;

// Try to initialize Redis client if available
try {
  const redisUrl = process.env.REDIS_URL;
  if (redisUrl) {
    redisClient = createRedisClient({
      url: redisUrl,
      socket: {
        connectTimeout: 5000,
        reconnectStrategy: false, // Disable reconnection to prevent continuous errors
      },
    });

    redisClient.on('error', (err: Error) => {
      if (!redisErrorLogged) {
        logger.warn('Redis client error for rate limiting:', err.message);
        logger.info('Falling back to memory store for rate limiting');
        redisErrorLogged = true;
      }
      redisClient = null; // Fall back to memory store
    });

    redisClient.connect().catch((err: Error) => {
      if (!redisErrorLogged) {
        logger.warn('Redis connection failed for rate limiting:', err.message);
        logger.info('Using memory store for rate limiting');
        redisErrorLogged = true;
      }
      redisClient = null;
    });
  } else {
    logger.info('Redis not configured for rate limiting, using memory store');
  }
} catch (error) {
  logger.info('Redis not configured for rate limiting, using memory store');
}

/**
 * Custom rate limit store using Redis or memory fallback
 */
class RateLimitStore {
  private memoryStore: Map<string, { count: number; resetTime: number }> = new Map();

  async increment(key: string, windowMs: number): Promise<{ totalHits: number; timeToExpiry: number }> {
    if (redisClient) {
      try {
        const multi = redisClient.multi();
        multi.incr(key);
        multi.expire(key, Math.ceil(windowMs / 1000));
        const results = await multi.exec();

        const totalHits = results[0] as number;
        const ttl = await redisClient.ttl(key);
        const timeToExpiry = ttl > 0 ? ttl * 1000 : windowMs;

        return { totalHits, timeToExpiry };
      } catch (error) {
        logger.warn('Redis operation failed, falling back to memory store:', error);
        // Fall through to memory store
      }
    }

    // Memory store fallback
    const now = Date.now();
    const resetTime = now + windowMs;
    const existing = this.memoryStore.get(key);

    if (!existing || existing.resetTime <= now) {
      this.memoryStore.set(key, { count: 1, resetTime });
      return { totalHits: 1, timeToExpiry: windowMs };
    } else {
      existing.count++;
      return { totalHits: existing.count, timeToExpiry: existing.resetTime - now };
    }
  }

  async decrement(key: string): Promise<void> {
    if (redisClient) {
      try {
        await redisClient.decr(key);
        return;
      } catch (error) {
        logger.warn('Redis decrement failed:', error);
      }
    }

    // Memory store fallback
    const existing = this.memoryStore.get(key);
    if (existing && existing.count > 0) {
      existing.count--;
    }
  }

  async resetKey(key: string): Promise<void> {
    if (redisClient) {
      try {
        await redisClient.del(key);
        return;
      } catch (error) {
        logger.warn('Redis reset failed:', error);
      }
    }

    // Memory store fallback
    this.memoryStore.delete(key);
  }

  // Cleanup old entries from memory store periodically
  startCleanup(): void {
    setInterval(() => {
      const now = Date.now();
      for (const [key, value] of this.memoryStore.entries()) {
        if (value.resetTime <= now) {
          this.memoryStore.delete(key);
        }
      }
    }, 60000); // Clean up every minute
  }
}

const rateLimitStore = new RateLimitStore();
rateLimitStore.startCleanup();

/**
 * Custom error handler for rate limits
 */
const rateLimitHandler = (req: Request, res: Response): void => {
  logger.warn(`Rate limit exceeded for IP: ${req.ip}, Path: ${req.path}`);

  const retryAfterSeconds = 60;

  res.set('Retry-After', retryAfterSeconds.toString()).status(429).json({
    success: false,
    error: 'You have exceeded the request rate limit. Please try again later.',
    retryAfter: retryAfterSeconds,
  });
};

/**
 * General rate limiter for read operations (100 requests per minute)
 */
export const generalRateLimit: RateLimitRequestHandler = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 100, // Limit each IP to 100 requests per windowMs
  message: {
    success: false,
    error: 'Too many requests from this IP, please try again later.',
    retryAfter: 60,
  },
  standardHeaders: true,
  legacyHeaders: false,

  // Custom store
  store: {
    async increment(key: string): Promise<{ totalHits: number; timeToExpiry: number; resetTime: Date }> {
      const result = await rateLimitStore.increment(key, 60000);
      return {
        ...result,
        resetTime: new Date(Date.now() + result.timeToExpiry),
      };
    },
    async decrement(key: string): Promise<void> {
      return rateLimitStore.decrement(key);
    },
    async resetKey(key: string): Promise<void> {
      return rateLimitStore.resetKey(key);
    },
  },

  // Custom handler
  handler: rateLimitHandler,

  // Skip successful requests in some cases
  skip: (req: Request): boolean => {
    // Skip rate limiting for health checks
    return req.path === '/health' || req.path === '/status';
  },
});

/**
 * Strict rate limiter for write operations (10 requests per minute)
 */
export const strictRateLimit: RateLimitRequestHandler = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 10, // Limit each IP to 10 requests per windowMs
  message: {
    success: false,
    error: 'Too many write requests from this IP, please try again later.',
    retryAfter: 60,
  },
  standardHeaders: true,
  legacyHeaders: false,

  store: {
    async increment(key: string): Promise<{ totalHits: number; timeToExpiry: number; resetTime: Date }> {
      const result = await rateLimitStore.increment(key, 60000);
      return {
        ...result,
        resetTime: new Date(Date.now() + result.timeToExpiry),
      };
    },
    async decrement(key: string): Promise<void> {
      return rateLimitStore.decrement(key);
    },
    async resetKey(key: string): Promise<void> {
      return rateLimitStore.resetKey(key);
    },
  },

  handler: rateLimitHandler,
});

/**
 * API collection rate limiter (20 requests per minute for data collection endpoints)
 */
export const apiCollectionRateLimit: RateLimitRequestHandler = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 20, // Limit each IP to 20 requests per windowMs
  message: {
    success: false,
    error: 'Too many API collection requests, please try again later.',
    retryAfter: 60,
  },
  standardHeaders: true,
  legacyHeaders: false,

  store: {
    async increment(key: string): Promise<{ totalHits: number; timeToExpiry: number; resetTime: Date }> {
      const result = await rateLimitStore.increment(key, 60000);
      return {
        ...result,
        resetTime: new Date(Date.now() + result.timeToExpiry),
      };
    },
    async decrement(key: string): Promise<void> {
      return rateLimitStore.decrement(key);
    },
    async resetKey(key: string): Promise<void> {
      return rateLimitStore.resetKey(key);
    },
  },

  handler: rateLimitHandler,
});

/**
 * Gradual slowdown middleware for additional protection
 * Slows down requests as they approach rate limits
 */
export const gradualSlowDown = slowDown({
  windowMs: 1 * 60 * 1000, // 1 minute
  delayAfter: 50, // Allow 50 requests at full speed
  delayMs: (used: number, _req: Request) => {
    const delayAfter = 50; // Default delay after value
    const maxDelay = 5000; // Maximum 5 second delay
    const delayIncrement = 100; // Start with 100ms delay

    // Exponentially increase delay
    const multiplier = Math.pow(2, Math.max(0, used - delayAfter - 1));
    return Math.min(maxDelay, delayIncrement * multiplier);
  },

  // Skip certain paths
  skip: (req: Request): boolean => {
    return req.path === '/health' || req.path === '/status';
  },
});

/**
 * Create a custom rate limiter with specific options
 */
export const createRateLimit = (options: {
  windowMs: number;
  max: number;
  message?: string;
  keyPrefix?: string;
  skipPaths?: string[];
}): RateLimitRequestHandler => {
  return rateLimit({
    windowMs: options.windowMs,
    max: options.max,
    message: {
      success: false,
      error: options.message || 'Rate limit exceeded',
      retryAfter: Math.ceil(options.windowMs / 1000),
    },
    standardHeaders: true,
    legacyHeaders: false,

    store: {
      async increment(key: string): Promise<{ totalHits: number; timeToExpiry: number; resetTime: Date }> {
        const result = await rateLimitStore.increment(key, options.windowMs);
        return {
          ...result,
          resetTime: new Date(Date.now() + result.timeToExpiry),
        };
      },
      async decrement(key: string): Promise<void> {
        return rateLimitStore.decrement(key);
      },
      async resetKey(key: string): Promise<void> {
        return rateLimitStore.resetKey(key);
      },
    },

    handler: rateLimitHandler,

    skip: (req: Request): boolean => {
      return options.skipPaths?.includes(req.path) || false;
    },
  });
};

/**
 * Cleanup function to close Redis connection
 */
export const cleanup = async (): Promise<void> => {
  if (redisClient) {
    try {
      await redisClient.quit();
      logger.info('Redis rate limit connection closed');
    } catch (error) {
      logger.warn('Error closing Redis rate limit connection:', error);
    }
  }
};

// Graceful shutdown
process.on('SIGTERM', cleanup);
process.on('SIGINT', cleanup);
