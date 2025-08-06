/**
 * Controllers Export
 * 
 * Central export point for all controller classes with registration utilities
 */

import type { Express, Request, Response, NextFunction } from 'express';
import logger from '../utils/logger.js';

// Controller imports
export { CollectionController } from './collectionController.js';
export { RaceController, raceController } from './race.controller.js';
export { HorseController, horseController } from './horse.controller.js';
export { JockeyController, jockeyController } from './jockey.controller.js';
export { TrainerController, trainerController } from './trainer.controller.js';

// Import instances for registration
import { raceController } from './race.controller.js';
import { horseController } from './horse.controller.js';
import { jockeyController } from './jockey.controller.js';
import { trainerController } from './trainer.controller.js';

/**
 * Controller registry for dependency injection and health monitoring
 */
export class ControllerRegistry {
  private static instance: ControllerRegistry;
  
  public readonly controllers = {
    race: raceController,
    horse: horseController,
    jockey: jockeyController,
    trainer: trainerController
  };

  private constructor() {
    logger.info('Controller registry initialized');
  }

  /**
   * Get singleton instance of controller registry
   */
  public static getInstance(): ControllerRegistry {
    if (!ControllerRegistry.instance) {
      ControllerRegistry.instance = new ControllerRegistry();
    }
    return ControllerRegistry.instance;
  }

  /**
   * Health check for all controllers
   * Tests basic functionality and dependency availability
   */
  async healthCheck(): Promise<Record<string, boolean>> {
    const results: Record<string, boolean> = {};

    // Test each controller's basic functionality
    try {
      // Race controller health
      results.race = typeof this.controllers.race.getRacesByDate === 'function';
      
      // Horse controller health
      results.horse = typeof this.controllers.horse.getHorseDetails === 'function';
      
      // Jockey controller health
      results.jockey = typeof this.controllers.jockey.getJockeyDetails === 'function';
      
      // Trainer controller health
      results.trainer = typeof this.controllers.trainer.getTrainerDetails === 'function';

      logger.info('Controller health check completed', { results });
    } catch (error) {
      logger.error('Controller health check failed', { error });
      // Mark all as unhealthy if there's a systemic issue
      Object.keys(this.controllers).forEach(key => {
        results[key] = false;
      });
    }

    return results;
  }

  /**
   * Get controller statistics
   */
  getStats() {
    return {
      totalControllers: Object.keys(this.controllers).length,
      controllerNames: Object.keys(this.controllers),
      initialized: true,
      timestamp: new Date().toISOString()
    };
  }
}

/**
 * Default controller registry instance
 */
export const controllerRegistry = ControllerRegistry.getInstance();

/**
 * Middleware to add request timing for performance monitoring
 */
export const requestTimer = (req: Request, res: Response, next: NextFunction): void => {
  req.startTime = Date.now();
  next();
};

/**
 * Utility to register common middleware for all controller routes
 */
export const registerCommonMiddleware = (app: Express): void => {
  // Add request timing
  app.use(requestTimer);
  
  logger.info('Common controller middleware registered');
};

/**
 * Controller factory function for creating new controller instances
 * Useful for testing or when you need fresh instances
 */
export const createControllers = async () => {
  return {
    race: new (await import('./race.controller.js')).RaceController(),
    horse: new (await import('./horse.controller.js')).HorseController(),
    jockey: new (await import('./jockey.controller.js')).JockeyController(),
    trainer: new (await import('./trainer.controller.js')).TrainerController()
  };
};

/**
 * Type definitions for controller methods
 */
export interface ControllerMethod {
  (req: Request, res: Response, next: NextFunction): Promise<void>;
}

/**
 * Base interface that all controllers should implement
 */
export interface BaseController {
  [key: string]: ControllerMethod | any;
}

/**
 * Controller metadata interface
 */
export interface ControllerInfo {
  name: string;
  methods: string[];
  routes: {
    method: string;
    path: string;
    handler: string;
  }[];
}

/**
 * Get controller information for API documentation
 */
export const getControllerInfo = (): Record<string, ControllerInfo> => {
  return {
    race: {
      name: 'RaceController',
      methods: ['getRacesByDate', 'getRaceDetails', 'collectRaceData', 'enrichRaceData'],
      routes: [
        { method: 'GET', path: '/api/races/:date', handler: 'getRacesByDate' },
        { method: 'GET', path: '/api/races/:date/:meet/:raceNo', handler: 'getRaceDetails' },
        { method: 'POST', path: '/api/races/collect', handler: 'collectRaceData' },
        { method: 'POST', path: '/api/races/enrich', handler: 'enrichRaceData' }
      ]
    },
    horse: {
      name: 'HorseController',
      methods: ['getHorseDetails', 'getHorseHistory', 'searchHorses'],
      routes: [
        { method: 'GET', path: '/api/horses/:hrNo', handler: 'getHorseDetails' },
        { method: 'GET', path: '/api/horses/:hrNo/history', handler: 'getHorseHistory' },
        { method: 'GET', path: '/api/horses', handler: 'searchHorses' }
      ]
    },
    jockey: {
      name: 'JockeyController',
      methods: ['getJockeyDetails', 'getJockeyStats', 'searchJockeys', 'getTopJockeys'],
      routes: [
        { method: 'GET', path: '/api/jockeys/:jkNo', handler: 'getJockeyDetails' },
        { method: 'GET', path: '/api/jockeys/:jkNo/stats', handler: 'getJockeyStats' },
        { method: 'GET', path: '/api/jockeys', handler: 'searchJockeys' },
        { method: 'GET', path: '/api/jockeys/top', handler: 'getTopJockeys' }
      ]
    },
    trainer: {
      name: 'TrainerController',
      methods: ['getTrainerDetails', 'getTrainerStats', 'searchTrainers', 'getTopTrainers', 'getTrainerSpecialization'],
      routes: [
        { method: 'GET', path: '/api/trainers/:trNo', handler: 'getTrainerDetails' },
        { method: 'GET', path: '/api/trainers/:trNo/stats', handler: 'getTrainerStats' },
        { method: 'GET', path: '/api/trainers', handler: 'searchTrainers' },
        { method: 'GET', path: '/api/trainers/top', handler: 'getTopTrainers' },
        { method: 'GET', path: '/api/trainers/:trNo/specialization', handler: 'getTrainerSpecialization' }
      ]
    }
  };
};

// Extend Express Request interface to include startTime
declare global {
  namespace Express {
    interface Request {
      startTime?: number;
    }
  }
}