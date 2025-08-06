/**
 * Server Bootstrap
 * 
 * Starts the Express server with comprehensive startup checks,
 * health verification, and graceful shutdown handling
 */

import { Server } from 'http';
import { createApp, gracefulShutdown as appShutdown } from './app.js';
import { appConfig } from './config/index.js';
import { controllerRegistry } from './controllers/index.js';
import { services } from './services/index.js';
import logger from './utils/logger.js';
import { getRedisClient, closeRedisConnection } from './utils/redis.js';

/**
 * Startup health check
 */
const performStartupHealthCheck = async (): Promise<boolean> => {
  logger.info('Performing startup health check...');
  
  try {
    // Check Redis connectivity
    const redisClient = getRedisClient();
    if (redisClient) {
      try {
        await redisClient.ping();
        logger.info('✓ Redis connection verified');
      } catch (error) {
        logger.warn('⚠ Redis not available, continuing without cache', { error });
      }
    } else {
      logger.info('ℹ Redis not configured, continuing without cache');
    }
    
    // Check controller initialization
    const controllerHealth = await controllerRegistry.healthCheck();
    const healthyControllers = Object.values(controllerHealth).filter(Boolean).length;
    const totalControllers = Object.keys(controllerHealth).length;
    
    if (healthyControllers === totalControllers) {
      logger.info(`✓ All ${totalControllers} controllers healthy`);
    } else {
      logger.warn(`⚠ ${healthyControllers}/${totalControllers} controllers healthy`, {
        controllerHealth
      });
    }
    
    // Check service availability
    const serviceCount = Object.keys(services).length;
    logger.info(`✓ ${serviceCount} services initialized`);
    
    // Log environment information
    logger.info('Environment information', {
      nodeVersion: process.version,
      platform: process.platform,
      arch: process.arch,
      environment: appConfig.nodeEnv,
      port: appConfig.port,
      memoryUsage: process.memoryUsage(),
      uptime: process.uptime()
    });
    
    logger.info('✅ Startup health check completed successfully');
    return true;
    
  } catch (error) {
    logger.error('❌ Startup health check failed', { error });
    return false;
  }
};

/**
 * Start the server
 */
const startServer = async (): Promise<Server> => {
  try {
    // Create Express application
    const app = createApp();
    
    // Perform startup health check
    const healthCheckPassed = await performStartupHealthCheck();
    if (!healthCheckPassed && appConfig.nodeEnv === 'production') {
      logger.error('Startup health check failed in production, exiting');
      process.exit(1);
    }
    
    // Start HTTP server
    const server = app.listen(appConfig.port, () => {
      logger.info('🚀 KRA Data Collector API Server Started', {
        environment: appConfig.nodeEnv,
        port: appConfig.port,
        host: appConfig.host || 'localhost',
        pid: process.pid,
        version: process.env.npm_package_version || '1.0.0',
        endpoints: {
          health: `http://localhost:${appConfig.port}/health`,
          api: `http://localhost:${appConfig.port}/api`,
          races: `http://localhost:${appConfig.port}/api/v1/races`,
          horses: `http://localhost:${appConfig.port}/api/v1/horses`,
          jockeys: `http://localhost:${appConfig.port}/api/v1/jockeys`,
          trainers: `http://localhost:${appConfig.port}/api/v1/trainers`
        }
      });
    });
    
    // Configure server settings
    server.timeout = 30000; // 30 seconds
    server.keepAliveTimeout = 65000; // 65 seconds
    server.headersTimeout = 66000; // 66 seconds
    
    return server;
    
  } catch (error) {
    logger.error('Failed to start server', { 
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined
    });
    throw error;
  }
};

/**
 * Graceful shutdown handler
 */
const gracefulShutdown = async (server: Server, signal: string): Promise<void> => {
  logger.info(`📡 Received ${signal}. Starting graceful shutdown...`);
  
  // Set a timeout for forceful shutdown
  const shutdownTimeout = setTimeout(() => {
    logger.error('❌ Graceful shutdown timed out, forcing exit');
    process.exit(1);
  }, 15000); // 15 seconds timeout
  
  try {
    // Stop accepting new requests
    server.close(async (error) => {
      if (error) {
        logger.error('Error closing HTTP server', { error });
      } else {
        logger.info('✓ HTTP server closed');
      }
      
      try {
        // Perform application-specific cleanup
        await appShutdown(server as any);
        
        // Close Redis connection
        await closeRedisConnection();
        logger.info('✓ Redis connection closed');
        
        // Clear shutdown timeout
        clearTimeout(shutdownTimeout);
        
        logger.info('✅ Graceful shutdown completed successfully');
        process.exit(0);
        
      } catch (shutdownError) {
        logger.error('❌ Error during graceful shutdown', { error: shutdownError });
        clearTimeout(shutdownTimeout);
        process.exit(1);
      }
    });
    
  } catch (error) {
    logger.error('❌ Error initiating graceful shutdown', { error });
    clearTimeout(shutdownTimeout);
    process.exit(1);
  }
};

/**
 * Error handlers
 */
process.on('uncaughtException', (error) => {
  logger.error('💥 Uncaught Exception - Server will terminate', {
    error: error.message,
    stack: error.stack,
    name: error.name
  });
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('💥 Unhandled Promise Rejection - Server will terminate', {
    reason,
    promise: promise.toString(),
    stack: reason instanceof Error ? reason.stack : undefined
  });
  process.exit(1);
});

/**
 * Main execution
 */
(async () => {
  try {
    const server = await startServer();
    
    // Setup signal handlers for graceful shutdown
    process.on('SIGTERM', () => gracefulShutdown(server, 'SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown(server, 'SIGINT'));
    
    // Log successful startup
    logger.info('🎯 Server initialization complete and ready to accept requests');
    
  } catch (error) {
    logger.error('💥 Failed to start server', { 
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined
    });
    process.exit(1);
  }
})();