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
 * Requires authentication (optional in test environment)
 */
router.post(
  '/collect',
  // Middleware stack
  apiCollectionRateLimit,
  process.env.NODE_ENV === 'test' ? optionalAuth : requireAuth,
  validateCollectionRequest,
  handleValidationErrors,
  performanceLogger,

  // Controller
  raceController.collectRaceData
);

/**
 * POST /races/enrich
 * Trigger race data enrichment
 * Requires authentication (optional in test environment)
 */
router.post(
  '/enrich',
  // Middleware stack
  apiCollectionRateLimit,
  process.env.NODE_ENV === 'test' ? optionalAuth : requireAuth,
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

// Handle unsupported methods for specific routes
router.all('/:date', (req, res) => {
  if (req.method !== 'GET') {
    res.status(405).json({
      success: false,
      error: {
        code: 'METHOD_NOT_ALLOWED',
        message: `Method ${req.method} not allowed for this endpoint`,
        details: 'Allowed methods: GET',
      },
      timestamp: new Date().toISOString(),
    });
  }
});

router.all('/:date/:meet/:raceNo', (req, res) => {
  if (req.method !== 'GET') {
    res.status(405).json({
      success: false,
      error: {
        code: 'METHOD_NOT_ALLOWED',
        message: `Method ${req.method} not allowed for this endpoint`,
        details: 'Allowed methods: GET',
      },
      timestamp: new Date().toISOString(),
    });
  }
});

export default router;
