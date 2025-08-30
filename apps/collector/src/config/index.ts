import { config } from 'dotenv';
import type { Config } from '../types/index.js';

// Load environment variables
config();

const getConfig = (): Config => {
  return {
    port: parseInt(process.env.PORT || '3001', 10),
    host: process.env.HOST || 'localhost',
    nodeEnv: process.env.NODE_ENV || 'development',
    corsOrigins: process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',') : ['*'],
    redis: process.env.REDIS_URL
      ? {
          host: process.env.REDIS_HOST || 'localhost',
          port: parseInt(process.env.REDIS_PORT || '6379', 10),
          password: process.env.REDIS_PASSWORD,
        }
      : undefined,
    kra: {
      baseUrl: process.env.KRA_API_BASE_URL || 'https://apis.data.go.kr/B551015',
      apiKey: process.env.KRA_SERVICE_KEY || process.env.KRA_API_KEY,
      timeout: parseInt(process.env.KRA_API_TIMEOUT || '30000', 10),
      retry: {
        attempts: parseInt(process.env.KRA_RETRY_ATTEMPTS || '3', 10),
        delay: parseInt(process.env.KRA_RETRY_DELAY || '1000', 10),
        backoffFactor: parseFloat(process.env.KRA_RETRY_BACKOFF || '2'),
      },
      rateLimit: {
        maxRequests: parseInt(process.env.KRA_RATE_LIMIT_MAX || '60', 10),
        windowMs: parseInt(process.env.KRA_RATE_LIMIT_WINDOW || '60000', 10),
      },
    },
  };
};

export const appConfig = getConfig();
export default appConfig;
