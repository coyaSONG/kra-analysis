import { Redis } from 'ioredis';
import { appConfig } from '../config/index.js';
import logger from './logger.js';

let redisClient: Redis | null = null;

export const getRedisClient = (): Redis | null => {
  if (!appConfig.redis) {
    logger.warn('Redis configuration not found, running without cache');
    return null;
  }

  if (!redisClient) {
    try {
      redisClient = new Redis({
        host: appConfig.redis.host,
        port: appConfig.redis.port,
        password: appConfig.redis.password,
        lazyConnect: true,
        maxRetriesPerRequest: 3,
      });

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
