/**
 * Trainer Routes
 *
 * Handles all trainer-related API endpoints with comprehensive middleware
 */

import { Router, type Router as ExpressRouter } from 'express';
import { trainerController } from '../controllers/index.js';
import {
  // Rate limiting
  generalRateLimit,

  // Validation
  validateTrainerId,
  validateTrainerParams,
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
 * GET /trainers/:trNo
 * Get detailed trainer information
 */
router.get(
  '/:trNo',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateTrainerId(),
  validateTrainerParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  trainerController.getTrainerDetails
);

/**
 * GET /trainers/:trNo/stats
 * Get comprehensive trainer statistics
 */
router.get(
  '/:trNo/stats',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateTrainerId(),
  validateTrainerParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  trainerController.getTrainerStats
);

/**
 * GET /trainers/:trNo/specialization
 * Get trainer specialization analysis
 */
router.get(
  '/:trNo/specialization',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateTrainerId(),
  validateTrainerParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  trainerController.getTrainerSpecialization
);

/**
 * GET /trainers/:trNo/performance
 * Get trainer performance analytics over time
 */
router.get(
  '/:trNo/performance',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateTrainerId(),
  validateTrainerParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  trainerController.getTrainerPerformance
);

/**
 * GET /trainers/:trNo/horses
 * Get horses trained by this trainer
 */
router.get(
  '/:trNo/horses',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateTrainerId(),
  validateTrainerParams,
  validatePagination,
  ...validateSort(['trName', 'winRate', 'rcCntT', 'ord1CntT']),
  handleValidationErrors,
  performanceLogger,

  // Controller
  trainerController.getTrainerHorses
);

/**
 * GET /trainers
 * Search trainers with filters
 */
router.get(
  '/',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validatePagination,
  ...validateSort(['trName', 'winRate', 'ord1CntT']),
  validateTrainerParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  trainerController.searchTrainers
);

/**
 * GET /trainers/top/performers
 * Get top performing trainers
 */
router.get(
  '/top/performers',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validatePagination,
  validateTrainerParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  trainerController.getTopTrainers
);

/**
 * GET /trainers/rankings
 * Get current trainer rankings
 */
router.get(
  '/rankings',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validatePagination,
  validateTrainerParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  trainerController.getTrainerRankings
);

/**
 * GET /trainers/stats/summary
 * Get overall trainer statistics summary
 */
router.get(
  '/stats/summary',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  performanceLogger,

  // Controller
  trainerController.getTrainerStatsSummary
);

/**
 * GET /trainers/specializations
 * Get trainer specialization categories and analytics
 */
router.get(
  '/specializations',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validatePagination,
  handleValidationErrors,
  performanceLogger,

  // Controller
  trainerController.getSpecializations
);

export default router;
