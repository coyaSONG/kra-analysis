import type { NextFunction, Request, Response } from 'express';
import { validationResult } from 'express-validator';
import { ValidationError } from '../../types/index.js';
import logger from '../../utils/logger.js';
import { sendNotImplemented } from './notImplemented.js';

type ControllerRequest = Request<any, any, any, any>;

export interface NotImplementedHandlerOptions {
  logMessage: string;
  logContext?: unknown;
  clientMessage: string;
  details: string;
  validate?: boolean;
}

export const validateRequest = (req: ControllerRequest): void => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    throw new ValidationError(
      `Validation failed: ${errors
        .array()
        .map((err) => err.msg)
        .join(', ')}`
    );
  }
};

export const handleNotImplemented = (
  req: ControllerRequest,
  res: Response,
  next: NextFunction,
  options: NotImplementedHandlerOptions
): void => {
  try {
    if (options.validate ?? true) {
      validateRequest(req);
    }
    logger.info(options.logMessage, options.logContext);
    sendNotImplemented(res, options.clientMessage, options.details);
  } catch (error) {
    next(error);
  }
};
