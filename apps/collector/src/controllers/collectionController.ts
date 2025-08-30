import type { Request, Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';
import { KraApiService } from '../services/kraApiService.js';
import { ValidationError } from '../types/index.js';
import type { ApiResponse } from '../types/index.js';
import logger from '../utils/logger.js';

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

      const request = {
        date: req.body.date || (req.query.date as string),
        raceNo: req.body.raceNo || (req.query.raceNo ? parseInt(req.query.raceNo as string, 10) : undefined),
        meet: req.body.meet || (req.query.meet as string),
      };

      logger.info('Processing collection request', { request });

      // Fix: Use correct service method
      const data = await this.kraApiService.getRaceResult(
        request.date.replace(/-/g, ''), // Convert YYYY-MM-DD to YYYYMMDD
        request.meet || '서울',
        request.raceNo || 1
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
