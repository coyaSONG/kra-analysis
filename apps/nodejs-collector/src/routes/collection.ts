import { Router, type Router as ExpressRouter } from 'express';
import { body, query } from 'express-validator';
import { CollectionController } from '../controllers/collectionController.js';

const router: ExpressRouter = Router();
const controller = new CollectionController();

// Validation rules
const collectionValidation = [
  body('date').optional().isISO8601({ strict: true }).withMessage('Date must be in YYYY-MM-DD format'),
  query('date').optional().isISO8601({ strict: true }).withMessage('Date must be in YYYY-MM-DD format'),
  body('raceNo').optional().isInt({ min: 1, max: 12 }).withMessage('Race number must be between 1 and 12'),
  query('raceNo').optional().isInt({ min: 1, max: 12 }).withMessage('Race number must be between 1 and 12'),
  body('track').optional().isIn(['SEOUL', 'BUSAN', 'JEJU']).withMessage('Track must be one of: SEOUL, BUSAN, JEJU'),
  query('track').optional().isIn(['SEOUL', 'BUSAN', 'JEJU']).withMessage('Track must be one of: SEOUL, BUSAN, JEJU'),
];

// Routes
router.post('/collect', collectionValidation, controller.collectRaceData);
router.get('/collect', collectionValidation, controller.collectRaceData);
router.get('/health', controller.healthCheck);

export default router;
