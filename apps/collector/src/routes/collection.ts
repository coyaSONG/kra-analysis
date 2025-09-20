import { Router, type Router as ExpressRouter } from 'express';
import { body, query } from 'express-validator';
import { CollectionController } from '../controllers/collectionController.js';
import { getValidMeetNames, isValidMeetName } from '../utils/meet-converter.js';
import { handleValidationErrors } from '../middleware/index.js';

const router: ExpressRouter = Router();
const controller = new CollectionController();

const VALID_MEET_NAMES = getValidMeetNames();
const MEET_VALIDATION_MESSAGE = `Meet must be a valid meet code (1, 2, 3) or Korean name (${VALID_MEET_NAMES.join(', ')})`;

const createCollectionValidation = (source: 'body' | 'query') => {
  const validator = source === 'body' ? body : query;

  return [
    validator('date')
      .notEmpty()
      .withMessage('Date is required')
      .bail()
      .isString()
      .withMessage('Date must be a string')
      .bail()
      .matches(/^\d{8}$/)
      .withMessage('Date must be in YYYYMMDD format (e.g., 20241201)'),
    validator('meet')
      .notEmpty()
      .withMessage('Meet is required')
      .bail()
      .custom((value) => {
        const meetValue = String(value).trim();
        if (!isValidMeetName(meetValue)) {
          throw new Error(MEET_VALIDATION_MESSAGE);
        }
        return true;
      })
      .bail()
      .customSanitizer((value) => String(value).trim()),
    validator('raceNo')
      .optional()
      .isInt({ min: 1, max: 20 })
      .withMessage('Race number must be between 1 and 20')
      .toInt(),
    handleValidationErrors,
  ];
};

const collectionBodyValidation = createCollectionValidation('body');
const collectionQueryValidation = createCollectionValidation('query');

// Routes
router.post('/collect', collectionBodyValidation, controller.collectRaceData);
router.get('/collect', collectionQueryValidation, controller.collectRaceData);
router.get('/health', controller.healthCheck);

export default router;
