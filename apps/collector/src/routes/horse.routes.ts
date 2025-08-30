/**
 * Horse Routes
 *
 * Handles all horse-related API endpoints with comprehensive middleware
 */

import { Router, type Router as ExpressRouter } from 'express';
import { horseController } from '../controllers/index.js';
import {
  // Rate limiting
  generalRateLimit,

  // Validation
  validateHorseId,
  validateHorseParams,
  validatePagination,
  validateSort,
  handleValidationErrors,

  // Auth
  optionalAuth,

  // Logging
  performanceLogger,
} from '../middleware/index.js';

const router: ExpressRouter = Router();

/**
 * GET /horses/:hrNo
 * Get detailed horse information
 */
router.get(
  '/:hrNo',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateHorseId(),
  validateHorseParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  horseController.getHorseDetails
);

/**
 * GET /horses/:hrNo/history
 * Get horse racing history
 */
router.get(
  '/:hrNo/history',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateHorseId(),
  validateHorseParams,
  validatePagination,
  ...validateSort(['rcDate', 'ord', 'rcTime']),
  handleValidationErrors,
  performanceLogger,

  // Controller
  horseController.getHorseHistory
);

/**
 * GET /horses/:hrNo/performance
 * Get horse performance analytics
 */
router.get(
  '/:hrNo/performance',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateHorseId(),
  validateHorseParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  horseController.getHorsePerformance
);

/**
 * GET /horses
 * Search horses with filters
 */
router.get(
  '/',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validatePagination,
  ...validateSort(['hrName', 'winRate', 'ord1CntT', 'rcCntT']),
  validateHorseParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  horseController.searchHorses
);

/**
 * GET /horses/top/performers
 * Get top performing horses
 */
router.get(
  '/top/performers',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validatePagination,
  validateHorseParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  horseController.getTopPerformers
);

/**
 * GET /horses/stats
 * Get horse statistics and metrics
 */
router.get(
  '/stats',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  performanceLogger,

  // Controller
  horseController.getHorseStats
);

export default router;
