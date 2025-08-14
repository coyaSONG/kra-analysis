/**
 * Horse Controller
 *
 * Handles horse-related API endpoints including horse details and race history
 */

import type { Request, Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';
import { services } from '../services/index.js';
import type { ApiResponse, HorseQueryParams } from '../types/api.types.js';
import type { Api8_2Item } from '../types/kra-api.types.js';
import { ValidationError, AppError } from '../types/index.js';
import logger from '../utils/logger.js';

/**
 * Enhanced horse data with additional metadata
 */
interface HorseDetails extends Api8_2Item {
  /** Additional metadata */
  metadata?: {
    lastUpdated: string;
    dataSource: 'api' | 'cache';
    cacheExpiresAt?: string;
  };
}

/**
 * Horse race history entry
 */
interface HorseRaceHistory {
  /** Race date */
  raceDate: string;
  /** Track/meet name */
  meet: string;
  /** Race number */
  raceNo: number;
  /** Race name */
  raceName: string;
  /** Finishing position */
  ord: number;
  /** Total horses in race */
  totalHorses: number;
  /** Win odds */
  winOdds: number;
  /** Prize money */
  prizeMoney: number;
  /** Jockey name */
  jkName: string;
  /** Trainer name */
  trName: string;
  /** Weight carried */
  wgBudam: number;
  /** Race distance */
  rcDist: number;
  /** Track condition */
  trackCond: string;
  /** Weather */
  weather: string;
}

export class HorseController {
  /**
   * Get horse details by horse number
   * GET /api/horses/:hrNo
   */
  getHorseDetails = async (
    req: Request<{ hrNo: string }, ApiResponse<HorseDetails>, Record<string, never>, HorseQueryParams>,
    res: Response<ApiResponse<HorseDetails>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      // Validate request parameters
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        throw new ValidationError(
          `Validation failed: ${errors
            .array()
            .map((err) => err.msg)
            .join(', ')}`
        );
      }

      const { hrNo } = req.params;
      const { meet } = req.query;

      logger.info('Getting horse details', { hrNo, meet });

      // Check cache first
      const cacheKeyParams = { hrNo, meet: meet || 'all' };
      let horseData = await services.cacheService.get('horse_detail', cacheKeyParams);

      if (!horseData) {
        // Fetch from KRA API if not in cache
        logger.info('Horse data not in cache, fetching from API', { hrNo, meet });

        try {
          // Get horse detail from KRA API
          horseData = await services.kraApiService.getHorseDetail(hrNo);

          if (!horseData) {
            throw new AppError('Horse not found', 404, true, { hrNo, meet });
          }

          // Cache the result for 4 hours (horse data doesn't change frequently)
          await services.cacheService.set('horse_detail', cacheKeyParams, horseData, { ttl: 14400 });

          // Add metadata
          (horseData as HorseDetails).metadata = {
            lastUpdated: new Date().toISOString(),
            dataSource: 'api',
          };
        } catch (error) {
          logger.error('Failed to fetch horse data from API', { hrNo, meet, error });
          throw error;
        }
      } else {
        // Add cache metadata
        (horseData as HorseDetails).metadata = {
          lastUpdated: new Date().toISOString(),
          dataSource: 'cache',
          cacheExpiresAt: new Date(Date.now() + 14400 * 1000).toISOString(),
        };
      }

      res.json({
        success: true,
        data: horseData as HorseDetails,
        message: 'Horse details retrieved successfully',
        meta: {
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now()),
        },
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get horse race history
   * GET /api/horses/:hrNo/history
   */
  getHorseHistory = async (
    req: Request<{ hrNo: string }, ApiResponse<HorseRaceHistory[]>, Record<string, never>, HorseQueryParams>,
    res: Response<ApiResponse<HorseRaceHistory[]>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        throw new ValidationError(
          `Validation failed: ${errors
            .array()
            .map((err) => err.msg)
            .join(', ')}`
        );
      }

      const { hrNo } = req.params;
      const { meet, page = 1, pageSize = 20, sortBy = 'raceDate', sortOrder = 'desc' } = req.query;

      logger.info('Getting horse race history', {
        hrNo,
        meet,
        page,
        pageSize,
        sortBy,
        sortOrder,
      });

      // Check cache first
      const historyCacheParams = {
        type: 'history',
        hrNo,
        meet: meet || 'all',
        page: page?.toString() || '1',
        pageSize: pageSize?.toString() || '20',
        sort: `${sortBy}_${sortOrder}`,
      };
      let historyData = await services.cacheService.get('horse_detail', historyCacheParams);

      if (!historyData) {
        // In a real implementation, you would:
        // 1. Query your database for race results where this horse participated
        // 2. Parse and format the data
        // 3. Apply pagination and sorting

        // For now, we'll return an empty array as this requires database integration
        logger.info('Horse history data not in cache and database integration pending', { hrNo });

        historyData = [];

        // Cache for 2 hours (race history data changes less frequently than current races)
        await services.cacheService.set('horse_detail', historyCacheParams, historyData, { ttl: 7200 });
      }

      const totalCount = Array.isArray(historyData) ? historyData.length : 0;
      const totalPages = Math.ceil(totalCount / (pageSize || 20));

      res.json({
        success: true,
        data: historyData as HorseRaceHistory[],
        message: 'Horse race history retrieved successfully',
        meta: {
          totalCount,
          page: page || 1,
          pageSize: pageSize || 20,
          totalPages,
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now()),
        },
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Search horses by name or other criteria
   * GET /api/horses (with query parameters)
   */
  searchHorses = async (
    req: Request<Record<string, never>, ApiResponse<HorseDetails[]>, Record<string, never>, HorseQueryParams>,
    res: Response<ApiResponse<HorseDetails[]>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        throw new ValidationError(
          `Validation failed: ${errors
            .array()
            .map((err) => err.msg)
            .join(', ')}`
        );
      }

      const { hrName, meet, rank, page = 1, pageSize = 20, sortBy = 'hrName', sortOrder = 'asc' } = req.query;

      logger.info('Searching horses', {
        hrName,
        meet,
        rank,
        page,
        pageSize,
        sortBy,
        sortOrder,
      });

      // Check cache first
      const searchCacheParams = {
        type: 'search',
        hrName: hrName || 'all',
        meet: meet || 'all',
        rank: rank || 'all',
        page: page?.toString() || '1',
        pageSize: pageSize?.toString() || '20',
        sort: `${sortBy}_${sortOrder}`,
      };
      let searchResults = await services.cacheService.get('horse_detail', searchCacheParams);

      if (!searchResults) {
        // In a real implementation, you would:
        // 1. Query your database with the search criteria
        // 2. Apply filters, pagination, and sorting
        // 3. Return formatted results

        logger.info('Horse search results not in cache and database integration pending');

        searchResults = [];

        // Cache search results for 1 hour
        await services.cacheService.set('horse_detail', searchCacheParams, searchResults, { ttl: 3600 });
      }

      const totalCount = Array.isArray(searchResults) ? searchResults.length : 0;
      const totalPages = Math.ceil(totalCount / (pageSize || 20));

      res.json({
        success: true,
        data: searchResults as HorseDetails[],
        message: 'Horse search completed successfully',
        meta: {
          totalCount,
          page: page || 1,
          pageSize: pageSize || 20,
          totalPages,
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now()),
        },
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get horse performance analytics
   * GET /api/horses/:hrNo/performance
   */
  getHorsePerformance = async (
    req: Request<{ hrNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      const { hrNo } = req.params;

      logger.info('Getting horse performance', { hrNo });

      // TODO: Implement actual horse performance analytics
      res.json({
        success: true,
        data: {
          hrNo,
          message: 'Horse performance endpoint - to be implemented',
        },
        message: 'Horse performance retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get top performing horses
   * GET /api/horses/top/performers
   */
  getTopPerformers = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      logger.info('Getting top performing horses');

      // TODO: Implement actual top performers retrieval
      res.json({
        success: true,
        data: {
          message: 'Top performers endpoint - to be implemented',
        },
        message: 'Top performing horses retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get horse statistics
   * GET /api/horses/stats
   */
  getHorseStats = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      logger.info('Getting horse statistics');

      // TODO: Implement actual horse statistics
      res.json({
        success: true,
        data: {
          message: 'Horse statistics endpoint - to be implemented',
        },
        message: 'Horse statistics retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };
}

// Export singleton instance
export const horseController = new HorseController();
