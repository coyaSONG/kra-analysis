/**
 * Jockey Controller
 *
 * Handles jockey-related API endpoints including jockey details and statistics
 */

import type { Request, Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';
import { services } from '../services/index.js';
import type { ApiResponse, JockeyQueryParams } from '../types/api.types.js';
import type { Api12_1Item } from '../types/kra-api.types.js';
import { ValidationError, AppError } from '../types/index.js';
import logger from '../utils/logger.js';

/**
 * Enhanced jockey data with additional metadata
 */
interface JockeyDetails extends Api12_1Item {
  /** Additional metadata */
  metadata?: {
    lastUpdated: string;
    dataSource: 'api' | 'cache';
    cacheExpiresAt?: string;
  };
}

/**
 * Jockey performance statistics
 */
interface JockeyStats {
  /** Basic information */
  jkNo: string;
  jkName: string;

  /** Performance metrics */
  totalRaces: number;
  wins: number;
  places: number;
  shows: number;

  /** Calculated rates */
  winRate: number;
  placeRate: number;
  showRate: number;

  /** Financial metrics */
  totalPrizeMoney: number;
  avgPrizeMoney: number;

  /** Recent form (last 10 races) */
  recentForm: {
    races: number;
    wins: number;
    places: number;
    shows: number;
    winRate: number;
  };

  /** Track-specific performance */
  trackStats?: {
    meet: string;
    races: number;
    wins: number;
    winRate: number;
  }[];

  /** Period information */
  period: {
    startDate: string;
    endDate: string;
    totalDays: number;
  };

  /** Last updated timestamp */
  lastUpdated: string;
}

export class JockeyController {
  /**
   * Get jockey details by jockey number
   * GET /api/jockeys/:jkNo
   */
  getJockeyDetails = async (
    req: Request<{ jkNo: string }, ApiResponse<JockeyDetails>, Record<string, never>, JockeyQueryParams>,
    res: Response<ApiResponse<JockeyDetails>>,
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

      const { jkNo } = req.params;
      const { meet } = req.query;

      logger.info('Getting jockey details', { jkNo, meet });

      // Check cache first
      const cacheKeyParams = { jkNo, meet: meet || 'all' };
      let jockeyData = await services.cacheService.get('jockey_detail', cacheKeyParams);

      if (!jockeyData) {
        // Fetch from KRA API if not in cache
        logger.info('Jockey data not in cache, fetching from API', { jkNo, meet });

        try {
          jockeyData = await services.kraApiService.getJockeyDetail(jkNo);

          if (!jockeyData) {
            throw new AppError('Jockey not found', 404, true, { jkNo, meet });
          }

          // Cache the result for 6 hours (jockey data doesn't change frequently)
          await services.cacheService.set('jockey_detail', cacheKeyParams, jockeyData, { ttl: 21600 });

          // Add metadata
          (jockeyData as JockeyDetails).metadata = {
            lastUpdated: new Date().toISOString(),
            dataSource: 'api',
          };
        } catch (error) {
          logger.error('Failed to fetch jockey data from API', { jkNo, meet, error });
          throw error;
        }
      } else {
        // Add cache metadata
        (jockeyData as JockeyDetails).metadata = {
          lastUpdated: new Date().toISOString(),
          dataSource: 'cache',
          cacheExpiresAt: new Date(Date.now() + 21600 * 1000).toISOString(),
        };
      }

      res.json({
        success: true,
        data: jockeyData as JockeyDetails,
        message: 'Jockey details retrieved successfully',
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
   * Get jockey performance statistics
   * GET /api/jockeys/:jkNo/stats
   */
  getJockeyStats = async (
    req: Request<{ jkNo: string }, ApiResponse<JockeyStats>, Record<string, never>, JockeyQueryParams>,
    res: Response<ApiResponse<JockeyStats>>,
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

      const { jkNo } = req.params;
      const { meet, sortBy = 'winRate', sortOrder = 'desc' } = req.query;

      logger.info('Getting jockey statistics', {
        jkNo,
        meet,
        sortBy,
        sortOrder,
      });

      // Check cache first
      const statsCacheParams = {
        type: 'stats',
        jkNo,
        meet: meet || 'all',
        sort: `${sortBy}_${sortOrder}`,
      };
      let statsData = await services.cacheService.get('jockey_detail', statsCacheParams);

      if (!statsData) {
        // In a real implementation, you would:
        // 1. Query your database for all race results with this jockey
        // 2. Calculate win/place/show rates, prize money, etc.
        // 3. Generate recent form analysis
        // 4. Calculate track-specific performance

        logger.info('Jockey stats not in cache, calculating from race history', { jkNo, meet });

        // For now, we'll create a mock stats object
        const mockStats: JockeyStats = {
          jkNo: jkNo || '',
          jkName: jkNo ? `기수-${jkNo}` : '알 수 없음', // This would come from the database
          totalRaces: 0,
          wins: 0,
          places: 0,
          shows: 0,
          winRate: 0,
          placeRate: 0,
          showRate: 0,
          totalPrizeMoney: 0,
          avgPrizeMoney: 0,
          recentForm: {
            races: 0,
            wins: 0,
            places: 0,
            shows: 0,
            winRate: 0,
          },
          trackStats: meet
            ? [
                {
                  meet,
                  races: 0,
                  wins: 0,
                  winRate: 0,
                },
              ]
            : undefined,
          period: {
            startDate: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] as string,
            endDate: new Date().toISOString().split('T')[0] as string,
            totalDays: 365,
          },
          lastUpdated: new Date().toISOString(),
        };

        statsData = mockStats;

        // Cache for 2 hours (stats should be refreshed more frequently)
        await services.cacheService.set('jockey_detail', statsCacheParams, statsData, { ttl: 7200 });
      }

      res.json({
        success: true,
        data: statsData as JockeyStats,
        message: 'Jockey statistics retrieved successfully',
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
   * Search jockeys by name or other criteria
   * GET /api/jockeys (with query parameters)
   */
  searchJockeys = async (
    req: Request<Record<string, never>, ApiResponse<JockeyDetails[]>, Record<string, never>, JockeyQueryParams>,
    res: Response<ApiResponse<JockeyDetails[]>>,
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

      const { jkName, meet, part, page = 1, pageSize = 20, sortBy = 'jkName', sortOrder = 'asc' } = req.query;

      logger.info('Searching jockeys', {
        jkName,
        meet,
        part,
        page,
        pageSize,
        sortBy,
        sortOrder,
      });

      // Check cache first
      const searchCacheParams = {
        type: 'search',
        jkName: jkName || 'all',
        meet: meet || 'all',
        part: part || 'all',
        page: page?.toString() || '1',
        pageSize: pageSize?.toString() || '20',
        sort: `${sortBy}_${sortOrder}`,
      };
      let searchResults = await services.cacheService.get('jockey_detail', searchCacheParams);

      if (!searchResults) {
        // In a real implementation, you would:
        // 1. Query your database with the search criteria
        // 2. Apply filters for name, meet, part (프리기수/전속기수)
        // 3. Apply pagination and sorting
        // 4. Include performance statistics if requested

        logger.info('Jockey search results not in cache and database integration pending');

        searchResults = [];

        // Cache search results for 1 hour
        await services.cacheService.set('jockey_detail', searchCacheParams, searchResults, { ttl: 3600 });
      }

      const totalCount = Array.isArray(searchResults) ? searchResults.length : 0;
      const totalPages = Math.ceil(totalCount / (pageSize || 20));

      res.json({
        success: true,
        data: searchResults as JockeyDetails[],
        message: 'Jockey search completed successfully',
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
   * Get top performing jockeys
   * GET /api/jockeys/top (with query parameters for criteria)
   */
  getTopJockeys = async (
    req: Request<
      Record<string, never>,
      ApiResponse<(JockeyDetails & { stats: Partial<JockeyStats> })[]>,
      Record<string, never>,
      JockeyQueryParams
    >,
    res: Response<ApiResponse<(JockeyDetails & { stats: Partial<JockeyStats> })[]>>,
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

      const { meet, page = 1, pageSize = 10, sortBy = 'winRate', sortOrder = 'desc' } = req.query;

      logger.info('Getting top jockeys', {
        meet,
        page,
        pageSize,
        sortBy,
        sortOrder,
      });

      // Check cache first
      const topCacheParams = {
        type: 'top',
        meet: meet || 'all',
        page: page?.toString() || '1',
        pageSize: pageSize?.toString() || '10',
        sort: `${sortBy}_${sortOrder}`,
      };
      let topJockeys = await services.cacheService.get('jockey_detail', topCacheParams);

      if (!topJockeys) {
        // In a real implementation, you would:
        // 1. Query database for all jockeys
        // 2. Calculate performance statistics
        // 3. Rank by specified criteria (win rate, prize money, etc.)
        // 4. Apply pagination

        logger.info('Top jockeys data not in cache and database integration pending');

        topJockeys = [];

        // Cache for 4 hours (rankings don't change very frequently)
        await services.cacheService.set('jockey_detail', topCacheParams, topJockeys, { ttl: 14400 });
      }

      const totalCount = Array.isArray(topJockeys) ? topJockeys.length : 0;
      const totalPages = Math.ceil(totalCount / (pageSize || 10));

      res.json({
        success: true,
        data: topJockeys as (JockeyDetails & { stats: Partial<JockeyStats> })[],
        message: 'Top jockeys retrieved successfully',
        meta: {
          totalCount,
          page: page || 1,
          pageSize: pageSize || 10,
          totalPages,
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now()),
        },
      });
    } catch (error) {
      next(error);
    }
  };

  // (removed duplicate lighter stub of getJockeyStats)

  /**
   * Get jockey performance
   * GET /api/jockeys/:jkNo/performance
   */
  getJockeyPerformance = async (
    req: Request<{ jkNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      const { jkNo } = req.params;

      logger.info('Getting jockey performance', { jkNo });

      // TODO: Implement actual jockey performance
      res.json({
        success: true,
        data: {
          jkNo,
          message: 'Jockey performance endpoint - to be implemented',
        },
        message: 'Jockey performance retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get jockey races
   * GET /api/jockeys/:jkNo/races
   */
  getJockeyRaces = async (
    req: Request<{ jkNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      const { jkNo } = req.params;

      logger.info('Getting jockey races', { jkNo });

      // TODO: Implement actual jockey races
      res.json({
        success: true,
        data: {
          jkNo,
          message: 'Jockey races endpoint - to be implemented',
        },
        message: 'Jockey races retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  // (removed duplicate lighter stub of searchJockeys)

  // (removed duplicate lighter stub of getTopJockeys)

  /**
   * Get jockey rankings
   * GET /api/jockeys/rankings
   */
  getJockeyRankings = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      logger.info('Getting jockey rankings');

      // TODO: Implement actual jockey rankings
      res.json({
        success: true,
        data: {
          message: 'Jockey rankings endpoint - to be implemented',
        },
        message: 'Jockey rankings retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get jockey stats summary
   * GET /api/jockeys/stats/summary
   */
  getJockeyStatsSummary = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      logger.info('Getting jockey stats summary');

      // TODO: Implement actual jockey stats summary
      res.json({
        success: true,
        data: {
          message: 'Jockey stats summary endpoint - to be implemented',
        },
        message: 'Jockey stats summary retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };
}

// Export singleton instance
export const jockeyController = new JockeyController();
