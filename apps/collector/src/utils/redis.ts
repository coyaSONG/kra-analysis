import { Redis } from 'ioredis';
import { appConfig } from '../config/index.js';
import logger from './logger.js';

let redisClient: Redis | null = null;

export const getRedisClient = (): Redis | null => {
  if (redisClient) return redisClient;

  const url = process.env.REDIS_URL?.trim();
  const host = process.env.REDIS_HOST || appConfig.redis?.host || 'localhost';
  const port = parseInt(process.env.REDIS_PORT || String(appConfig.redis?.port || 6379), 10);
  const password = process.env.REDIS_PASSWORD ?? appConfig.redis?.password;

  try {
    if (url) {
      // Prefer full REDIS_URL if provided (supports redis:// and rediss://)
      redisClient = new Redis(url, {
        lazyConnect: true,
        maxRetriesPerRequest: 3,
      });
      logger.info('Initializing Redis using REDIS_URL');
    } else if (appConfig.redis || process.env.REDIS_HOST) {
      // Fallback to discrete host/port configuration
      redisClient = new Redis({
        host,
        port,
        password,
        lazyConnect: true,
        maxRetriesPerRequest: 3,
      });
      logger.info(`Initializing Redis using host/port (${host}:${port})`);
    } else {
      logger.warn('Redis configuration not found, running without cache');
      return null;
    }

    redisClient.on('connect', () => {
      logger.info('Redis connected successfully');
    });

    redisClient.on('error', (err: Error) => {
      logger.error('Redis connection error:', err);
    });
  } catch (error) {
    logger.error('Failed to initialize Redis client:', error);
    redisClient = null;
  }

  return redisClient;
};

export const closeRedisConnection = async (): Promise<void> => {
  if (redisClient) {
    await redisClient.quit();
    redisClient = null;
    logger.info('Redis connection closed');
  }
};

export default { getRedisClient, closeRedisConnection };
