/**
 * Jockey Routes
 *
 * Handles all jockey-related API endpoints with comprehensive middleware
 */

import { Router, type Router as ExpressRouter } from 'express';
import { jockeyController } from '../controllers/index.js';
import {
  // Rate limiting
  generalRateLimit,

  // Validation
  validateJockeyId,
  validateJockeyParams,
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
 * GET /jockeys/:jkNo
 * Get detailed jockey information
 */
router.get(
  '/:jkNo',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateJockeyId(),
  validateJockeyParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  jockeyController.getJockeyDetails
);

/**
 * GET /jockeys/:jkNo/stats
 * Get comprehensive jockey statistics
 */
router.get(
  '/:jkNo/stats',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateJockeyId(),
  validateJockeyParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  jockeyController.getJockeyStats
);

/**
 * GET /jockeys/:jkNo/performance
 * Get jockey performance analytics over time
 */
router.get(
  '/:jkNo/performance',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateJockeyId(),
  validateJockeyParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  jockeyController.getJockeyPerformance
);

/**
 * GET /jockeys/:jkNo/races
 * Get jockey's recent races with optional date filtering
 */
router.get(
  '/:jkNo/races',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateJockeyId(),
  validateJockeyParams,
  validatePagination,
  ...validateSort(['jkName', 'winRate', 'total', 'average']),
  handleValidationErrors,
  performanceLogger,

  // Controller
  jockeyController.getJockeyRaces
);

/**
 * GET /jockeys
 * Search jockeys with filters
 */
router.get(
  '/',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validatePagination,
  ...validateSort(['jkName', 'winRate', 'ord1CntT', 'rcCntT']),
  validateJockeyParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  jockeyController.searchJockeys
);

/**
 * GET /jockeys/top/performers
 * Get top performing jockeys
 */
router.get(
  '/top/performers',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validatePagination,
  validateJockeyParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  jockeyController.getTopJockeys
);

/**
 * GET /jockeys/rankings
 * Get current jockey rankings
 */
router.get(
  '/rankings',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validatePagination,
  validateJockeyParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  jockeyController.getJockeyRankings
);

/**
 * GET /jockeys/stats/summary
 * Get overall jockey statistics summary
 */
router.get(
  '/stats/summary',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  performanceLogger,

  // Controller
  jockeyController.getJockeyStatsSummary
);

export default router;
