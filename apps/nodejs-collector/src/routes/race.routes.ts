/**
 * Race Routes
 *
 * Handles all race-related API endpoints with comprehensive middleware
 */

import { Router, type Router as ExpressRouter } from 'express';
import { raceController } from '../controllers/index.js';
import {
  // Rate limiting
  generalRateLimit,
  apiCollectionRateLimit,

  // Validation
  validateDate,
  validateMeet,
  validateRaceNo,
  validateRaceParams,
  validateCollectionRequest,
  validateEnrichmentRequest,
  handleValidationErrors,

  // Auth
  optionalAuth,
  requireAuth,

  // Logging
  performanceLogger,
} from '../middleware/index.js';

const router: ExpressRouter = Router();

/**
 * GET /races/:date
 * Get all races for a specific date
 */
router.get(
  '/:date',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateDate(),
  validateRaceParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  raceController.getRacesByDate
);

/**
 * GET /races/:date/:meet/:raceNo
 * Get specific race details
 */
router.get(
  '/:date/:meet/:raceNo',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateDate(),
  validateMeet(),
  validateRaceNo(),
  validateRaceParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  raceController.getRaceDetails
);

/**
 * POST /races/collect
 * Trigger race data collection
 * Requires authentication
 */
router.post(
  '/collect',
  // Middleware stack
  apiCollectionRateLimit,
  requireAuth,
  validateCollectionRequest,
  handleValidationErrors,
  performanceLogger,

  // Controller
  raceController.collectRaceData
);

/**
 * POST /races/enrich
 * Trigger race data enrichment
 * Requires authentication
 */
router.post(
  '/enrich',
  // Middleware stack
  apiCollectionRateLimit,
  requireAuth,
  validateEnrichmentRequest,
  handleValidationErrors,
  performanceLogger,

  // Controller
  raceController.enrichRaceData
);

/**
 * GET /races/:date/:meet/:raceNo/result
 * Get race result (if available)
 */
router.get(
  '/:date/:meet/:raceNo/result',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  validateDate(),
  validateMeet(),
  validateRaceNo(),
  validateRaceParams,
  handleValidationErrors,
  performanceLogger,

  // Controller
  raceController.getRaceResult
);

/**
 * GET /races/stats
 * Get race statistics and metrics
 */
router.get(
  '/stats',
  // Middleware stack
  generalRateLimit,
  optionalAuth,
  performanceLogger,

  // Controller
  raceController.getRaceStats
);

export default router;
