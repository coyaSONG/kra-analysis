import { body, param, query, ValidationChain, validationResult } from 'express-validator';
import type { Request, Response, NextFunction } from 'express';
import { ValidationError, Meet } from '../types/index.js';
import logger from '../utils/logger.js';

/**
 * Handle validation results and throw ValidationError if validation fails
 */
export const handleValidationErrors = (req: Request, res: Response, next: NextFunction): void => {
  const errors = validationResult(req);

  if (!errors.isEmpty()) {
    const validationErrors = errors.array().map((error) => ({
      field: error.type === 'field' ? error.path : 'unknown',
      message: error.msg,
      value: error.type === 'field' ? error.value : undefined,
    }));

    logger.warn('Validation failed:', {
      url: req.url,
      method: req.method,
      ip: req.ip,
      errors: validationErrors,
    });

    const validationError = new ValidationError('Request validation failed', validationErrors, {
      url: req.url,
      method: req.method,
      ip: req.ip,
    });

    throw validationError;
  }

  next();
};

/**
 * Date validation chain - validates YYYYMMDD format
 */
export const validateDate = (field: 'body' | 'param' | 'query' = 'param', fieldName = 'date'): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return [
    validator(fieldName)
      .notEmpty()
      .withMessage(`${fieldName} is required`)
      .isString()
      .withMessage(`${fieldName} must be a string`)
      .matches(/^\d{8}$/)
      .withMessage(`${fieldName} must be in YYYYMMDD format (e.g., 20241201)`)
      .custom((value: string) => {
        // Validate it's a valid date
        const year = parseInt(value.substring(0, 4), 10);
        const month = parseInt(value.substring(4, 6), 10);
        const day = parseInt(value.substring(6, 8), 10);

        // Basic date validation
        if (year < 2020 || year > 2030) {
          throw new Error(`Year must be between 2020 and 2030`);
        }

        if (month < 1 || month > 12) {
          throw new Error('Month must be between 01 and 12');
        }

        if (day < 1 || day > 31) {
          throw new Error('Day must be between 01 and 31');
        }

        // More precise validation using Date object
        const dateObj = new Date(year, month - 1, day);
        if (dateObj.getFullYear() !== year || dateObj.getMonth() !== month - 1 || dateObj.getDate() !== day) {
          throw new Error('Invalid date');
        }

        return true;
      }),
  ];
};

/**
 * Meet/Track validation chain - validates 1 (Seoul), 2 (Jeju), or 3 (Busan)
 */
export const validateMeet = (field: 'body' | 'param' | 'query' = 'param', fieldName = 'meet'): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  const allowedNames = ['서울', '부산', '부산경남', '제주'];

  return [
    validator(fieldName)
      .notEmpty()
      .withMessage(`${fieldName} is required`)
      .custom((value: any) => {
        // Accept either numeric codes 1-3 or valid Korean names
        if (typeof value === 'number') {
          if (!Object.values(Meet).includes(value)) {
            throw new Error(`Invalid meet value: ${value}. Must be 1 (Seoul), 2 (Jeju), or 3 (Busan)`);
          }
          return true;
        }

        const str = String(value);
        if (/^\d+$/.test(str)) {
          const num = parseInt(str, 10);
          if (!Object.values(Meet).includes(num)) {
            throw new Error(`Invalid meet value: ${str}. Must be 1 (Seoul), 2 (Jeju), or 3 (Busan)`);
          }
          return true;
        }

        if (!allowedNames.includes(str)) {
          throw new Error(`Invalid meet value: ${str}. Must be one of ${allowedNames.join(', ')} or 1/2/3`);
        }
        return true;
      }),
  ];
};

/**
 * Race number validation chain - validates 1-20
 */
export const validateRaceNo = (
  field: 'body' | 'param' | 'query' = 'param',
  fieldName = 'raceNo'
): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return [
    validator(fieldName)
      .notEmpty()
      .withMessage(`${fieldName} is required`)
      .isInt({ min: 1, max: 20 })
      .withMessage(`${fieldName} must be between 1 and 20`)
      .toInt(),
  ];
};

/**
 * Optional race number validation - allows empty values
 */
export const validateOptionalRaceNo = (
  field: 'body' | 'param' | 'query' = 'query',
  fieldName = 'raceNo'
): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return [
    validator(fieldName)
      .optional()
      .isInt({ min: 1, max: 20 })
      .withMessage(`${fieldName} must be between 1 and 20 if provided`)
      .toInt(),
  ];
};

/**
 * Horse ID validation chain - validates format like "0012345"
 */
export const validateHorseId = (field: 'body' | 'param' | 'query' = 'param', fieldName = 'hrNo'): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return [
    validator(fieldName)
      .notEmpty()
      .withMessage(`${fieldName} is required`)
      .isString()
      .withMessage(`${fieldName} must be a string`)
      .matches(/^[0-9]{7}$/)
      .withMessage(`${fieldName} must be a 7-digit number string (e.g., "0012345")`),
  ];
};

/**
 * Jockey ID validation chain - validates format like "01234"
 */
export const validateJockeyId = (
  field: 'body' | 'param' | 'query' = 'param',
  fieldName = 'jkNo'
): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return [
    validator(fieldName)
      .notEmpty()
      .withMessage(`${fieldName} is required`)
      .isString()
      .withMessage(`${fieldName} must be a string`)
      .matches(/^[0-9]{5}$/)
      .withMessage(`${fieldName} must be a 5-digit number string (e.g., "01234")`),
  ];
};

/**
 * Trainer ID validation chain - validates format like "01234"
 */
export const validateTrainerId = (
  field: 'body' | 'param' | 'query' = 'param',
  fieldName = 'trNo'
): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return [
    validator(fieldName)
      .notEmpty()
      .withMessage(`${fieldName} is required`)
      .isString()
      .withMessage(`${fieldName} must be a string`)
      .matches(/^[0-9]{5}$/)
      .withMessage(`${fieldName} must be a 5-digit number string (e.g., "01234")`),
  ];
};

/**
 * Pagination validation chains
 */
export const validatePagination = (_field: 'query' = 'query'): ValidationChain[] => {
  return [
    query('page').optional().isInt({ min: 1 }).withMessage('page must be a positive integer').toInt(),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('limit must be between 1 and 100').toInt(),
  ];
};

/**
 * Sorting validation chains
 */
export const validateSort = (allowedFields: string[]): ValidationChain[] => {
  return [
    query('sortBy')
      .optional()
      .isIn(allowedFields)
      .withMessage(`sortBy must be one of: ${allowedFields.join(', ')}`),
    query('sortOrder').optional().isIn(['asc', 'desc']).withMessage('sortOrder must be either "asc" or "desc"'),
  ];
};

/**
 * Boolean validation chain
 */
export const validateBoolean = (field: 'body' | 'param' | 'query' = 'query', fieldName: string): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return [validator(fieldName).optional().isBoolean().withMessage(`${fieldName} must be a boolean value`).toBoolean()];
};

/**
 * Array validation chain
 */
export const validateArray = (
  field: 'body' | 'param' | 'query' = 'body',
  fieldName: string,
  itemValidator?: (value: any) => boolean,
  options: { min?: number; max?: number } = {}
): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return [
    validator(fieldName)
      .notEmpty()
      .withMessage(`${fieldName} is required`)
      .isArray(options)
      .withMessage(`${fieldName} must be an array`)
      .custom((value: any[]) => {
        if (itemValidator) {
          const isValid = value.every((item) => itemValidator(item));
          if (!isValid) {
            throw new Error(`All items in ${fieldName} must be valid`);
          }
        }
        return true;
      }),
  ];
};

/**
 * Common validation chains for collection endpoints
 */
export const validateCollectionRequest = [
  ...validateDate('body', 'date'),
  ...validateOptionalRaceNo('body', 'raceNo'),
  ...validateMeet('body', 'meet'),
  handleValidationErrors,
];

/**
 * Common validation chains for race endpoints
 */
export const validateRaceParams = [
  ...validateDate('param', 'date'),
  ...validateMeet('param', 'meet'),
  ...validateRaceNo('param', 'raceNo'),
  handleValidationErrors,
];

/**
 * Common validation chains for horse endpoints
 */
export const validateHorseParams = [...validateHorseId('param', 'hrNo'), handleValidationErrors];

/**
 * Common validation chains for jockey endpoints
 */
export const validateJockeyParams = [...validateJockeyId('param', 'jkNo'), handleValidationErrors];

/**
 * Common validation chains for trainer endpoints
 */
export const validateTrainerParams = [...validateTrainerId('param', 'trNo'), handleValidationErrors];

/**
 * Validation for enriched data request
 */
export const validateEnrichmentRequest = [
  ...validateDate('body', 'date'),
  ...validateMeet('body', 'meet'),
  ...validateRaceNo('body', 'raceNo'),
  ...validateBoolean('body', 'forceRefresh'),
  handleValidationErrors,
];

/**
 * Custom validator for specific business logic
 */
export const createCustomValidator = (
  fieldName: string,
  validatorFn: (value: any, req: Request) => boolean | Promise<boolean>,
  errorMessage: string,
  field: 'body' | 'param' | 'query' = 'body'
): ValidationChain => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return validator(fieldName).custom(async (value, { req }) => {
    const isValid = await validatorFn(value, req as Request);
    if (!isValid) {
      throw new Error(errorMessage);
    }
    return true;
  });
};

/**
 * Sanitize and normalize input data
 */
export const sanitizeInput = (field: 'body' | 'param' | 'query' = 'body', fieldName: string): ValidationChain[] => {
  const validator = field === 'body' ? body : field === 'query' ? query : param;

  return [validator(fieldName).trim().escape()];
};

/**
 * Validation middleware factory for dynamic validation chains
 */
export const createValidationMiddleware = (validationChains: ValidationChain[]) => {
  return [...validationChains, handleValidationErrors];
};
