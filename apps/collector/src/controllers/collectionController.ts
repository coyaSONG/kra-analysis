import type { Request, Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';
import { KraApiService } from '../services/kraApiService.js';
import { ValidationError } from '../types/index.js';
import type { ApiResponse } from '../types/index.js';
import logger from '../utils/logger.js';
import { meetToApiParam, meetCodeToName } from '../utils/meet-converter.js';

export class CollectionController {
  private kraApiService: KraApiService;

  constructor() {
    this.kraApiService = new KraApiService();
  }

  /**
   * Collect race data
   */
  collectRaceData = async (req: Request, res: Response<ApiResponse>, next: NextFunction): Promise<void> => {
    try {
      // Check for validation errors
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        throw new ValidationError(
          `Validation failed: ${errors
            .array()
            .map((err) => err.msg)
            .join(', ')}`
        );
      }

      const dateInput = (req.body.date || req.query.date) as string;
      const meetInput = req.body.meet || (req.query.meet as string | undefined);
      const raceNoInput = req.body.raceNo ?? (req.query.raceNo as number | string | undefined);

      const normalizedDate = dateInput.replace(/-/g, '');

      let meetCode: string;
      try {
        meetCode = meetToApiParam(meetInput ?? '');
      } catch (error) {
        throw new ValidationError('Validation failed for meet parameter', [
          { field: 'meet', message: (error as Error).message, value: meetInput },
        ]);
      }
      const raceNo =
        typeof raceNoInput === 'number'
          ? raceNoInput
          : raceNoInput
          ? parseInt(String(raceNoInput), 10)
          : undefined;

      const logContext = {
        date: normalizedDate,
        meetCode,
        meetName: meetCodeToName(parseInt(meetCode, 10)),
        raceNo: raceNo ?? 1,
      };

      logger.info('Processing collection request', logContext);

      const data = await this.kraApiService.getRaceResult(
        normalizedDate,
        meetCode,
        raceNo ?? 1
      );

      res.json({
        success: true,
        data,
        message: 'Race data collected successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Health check endpoint
   */
  healthCheck = async (req: Request, res: Response<ApiResponse>, next: NextFunction): Promise<void> => {
    try {
      const isHealthy = await this.kraApiService.healthCheck();

      res.json({
        success: isHealthy,
        message: isHealthy ? 'Service is healthy' : 'Service is unhealthy',
      });
    } catch (error) {
      next(error);
    }
  };
}
