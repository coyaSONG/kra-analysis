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
    redis: process.env.REDIS_URL ? {
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379', 10),
      password: process.env.REDIS_PASSWORD,
    } : undefined,
    kra: {
      baseUrl: process.env.KRA_API_BASE_URL || 'http://data.kra.co.kr',
      apiKey: process.env.KRA_API_KEY,
    },
  };
};

export const appConfig = getConfig();
export default appConfig;