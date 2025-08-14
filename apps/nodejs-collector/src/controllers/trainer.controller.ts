/**
 * Trainer Controller
 *
 * Handles trainer-related API endpoints including trainer details and statistics
 */

import type { Request, Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';
import { services } from '../services/index.js';
import type { ApiResponse, TrainerQueryParams } from '../types/api.types.js';
import type { Api19_1Item } from '../types/kra-api.types.js';
import { ValidationError, AppError } from '../types/index.js';
import logger from '../utils/logger.js';

/**
 * Enhanced trainer data with additional metadata
 */
interface TrainerDetails extends Api19_1Item {
  /** Additional metadata */
  metadata?: {
    lastUpdated: string;
    dataSource: 'api' | 'cache';
    cacheExpiresAt?: string;
  };
}

/**
 * Trainer performance statistics
 */
interface TrainerStats {
  /** Basic information */
  trNo: string;
  trName: string;

  /** Performance metrics */
  totalRaces: number;
  totalHorses: number;
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

  /** Horse development metrics */
  avgHorseCareerLength: number;
  horsesImproved: number;
  improvementRate: number;

  /** Recent form (last 30 days) */
  recentForm: {
    races: number;
    wins: number;
    places: number;
    shows: number;
    winRate: number;
    period: string;
  };

  /** Track-specific performance */
  trackStats?: {
    meet: string;
    races: number;
    wins: number;
    winRate: number;
    specialization: string;
  }[];

  /** Horse grade specialization */
  gradeStats?: {
    grade: string;
    races: number;
    wins: number;
    winRate: number;
  }[];

  /** Distance specialization */
  distanceStats?: {
    distance: string;
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

export class TrainerController {
  /**
   * Get trainer details by trainer number
   * GET /api/trainers/:trNo
   */
  getTrainerDetails = async (
    req: Request<{ trNo: string }, ApiResponse<TrainerDetails>, Record<string, never>, TrainerQueryParams>,
    res: Response<ApiResponse<TrainerDetails>>,
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

      const { trNo } = req.params;
      const { meet } = req.query;

      logger.info('Getting trainer details', { trNo, meet });

      // Check cache first
      const cacheKeyParams = { trNo, meet: meet || 'all' };
      let trainerData = await services.cacheService.get('trainer_detail', cacheKeyParams);

      if (!trainerData) {
        // Fetch from KRA API if not in cache
        logger.info('Trainer data not in cache, fetching from API', { trNo, meet });

        try {
          trainerData = await services.kraApiService.getTrainerDetail(trNo);

          if (!trainerData) {
            throw new AppError('Trainer not found', 404, true, { trNo, meet });
          }

          // Cache the result for 8 hours (trainer data changes infrequently)
          await services.cacheService.set('trainer_detail', cacheKeyParams, trainerData, { ttl: 28800 });

          // Add metadata
          (trainerData as TrainerDetails).metadata = {
            lastUpdated: new Date().toISOString(),
            dataSource: 'api',
          };
        } catch (error) {
          logger.error('Failed to fetch trainer data from API', { trNo, meet, error });
          throw error;
        }
      } else {
        // Add cache metadata
        (trainerData as TrainerDetails).metadata = {
          lastUpdated: new Date().toISOString(),
          dataSource: 'cache',
          cacheExpiresAt: new Date(Date.now() + 28800 * 1000).toISOString(),
        };
      }

      res.json({
        success: true,
        data: trainerData as TrainerDetails,
        message: 'Trainer details retrieved successfully',
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
   * Get trainer performance statistics
   * GET /api/trainers/:trNo/stats
   */
  getTrainerStats = async (
    req: Request<{ trNo: string }, ApiResponse<TrainerStats>, Record<string, never>, TrainerQueryParams>,
    res: Response<ApiResponse<TrainerStats>>,
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

      const { trNo } = req.params;
      const { meet, minWinRate, sortBy = 'winRate', sortOrder = 'desc' } = req.query;

      logger.info('Getting trainer statistics', {
        trNo,
        meet,
        minWinRate,
        sortBy,
        sortOrder,
      });

      // Check cache first
      const statsCacheParams = {
        type: 'stats',
        trNo,
        meet: meet || 'all',
        minWinRate: minWinRate?.toString() || 'all',
        sort: `${sortBy}_${sortOrder}`,
      };
      let statsData = await services.cacheService.get('trainer_detail', statsCacheParams);

      if (!statsData) {
        // In a real implementation, you would:
        // 1. Query your database for all race results with this trainer's horses
        // 2. Calculate win/place/show rates, prize money, horse development metrics
        // 3. Analyze specialization patterns (distance, grade, track)
        // 4. Generate recent form analysis
        // 5. Calculate horse career progression under this trainer

        logger.info('Trainer stats not in cache, calculating from race history', { trNo, meet });

        // For now, we'll create a mock stats object
        const mockStats: TrainerStats = {
          trNo: trNo || '',
          trName: trNo ? `조교사-${trNo}` : '알 수 없음', // This would come from the database
          totalRaces: 0,
          totalHorses: 0,
          wins: 0,
          places: 0,
          shows: 0,
          winRate: 0,
          placeRate: 0,
          showRate: 0,
          totalPrizeMoney: 0,
          avgPrizeMoney: 0,
          avgHorseCareerLength: 0,
          horsesImproved: 0,
          improvementRate: 0,
          recentForm: {
            races: 0,
            wins: 0,
            places: 0,
            shows: 0,
            winRate: 0,
            period: '지난 30일',
          },
          trackStats: meet
            ? [
                {
                  meet,
                  races: 0,
                  wins: 0,
                  winRate: 0,
                  specialization: '미확인',
                },
              ]
            : undefined,
          gradeStats: [
            { grade: '특급', races: 0, wins: 0, winRate: 0 },
            { grade: '1급', races: 0, wins: 0, winRate: 0 },
            { grade: '2급', races: 0, wins: 0, winRate: 0 },
            { grade: '3급', races: 0, wins: 0, winRate: 0 },
          ],
          distanceStats: [
            { distance: '1000-1200m', races: 0, wins: 0, winRate: 0 },
            { distance: '1300-1600m', races: 0, wins: 0, winRate: 0 },
            { distance: '1700-2000m', races: 0, wins: 0, winRate: 0 },
            { distance: '2000m+', races: 0, wins: 0, winRate: 0 },
          ],
          period: {
            startDate: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] as string,
            endDate: new Date().toISOString().split('T')[0] as string,
            totalDays: 365,
          },
          lastUpdated: new Date().toISOString(),
        };

        // Apply minWinRate filter if specified
        if (minWinRate && mockStats.winRate < minWinRate) {
          statsData = null; // Would filter out this trainer
        } else {
          statsData = mockStats;
        }

        // Cache for 3 hours (stats should be refreshed regularly)
        await services.cacheService.set('trainer_detail', statsCacheParams, statsData, { ttl: 10800 });
      }

      res.json({
        success: true,
        data: statsData as TrainerStats,
        message: 'Trainer statistics retrieved successfully',
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
   * Search trainers by name or other criteria
   * GET /api/trainers (with query parameters)
   */
  searchTrainers = async (
    req: Request<Record<string, never>, ApiResponse<TrainerDetails[]>, Record<string, never>, TrainerQueryParams>,
    res: Response<ApiResponse<TrainerDetails[]>>,
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

      const { trName, meet, minWinRate, page = 1, pageSize = 20, sortBy = 'trName', sortOrder = 'asc' } = req.query;

      logger.info('Searching trainers', {
        trName,
        meet,
        minWinRate,
        page,
        pageSize,
        sortBy,
        sortOrder,
      });

      // Check cache first
      const searchCacheParams = {
        type: 'search',
        trName: trName || 'all',
        meet: meet || 'all',
        minWinRate: minWinRate?.toString() || 'all',
        page: page?.toString() || '1',
        pageSize: pageSize?.toString() || '20',
        sort: `${sortBy}_${sortOrder}`,
      };
      let searchResults = await services.cacheService.get('trainer_detail', searchCacheParams);

      if (!searchResults) {
        // In a real implementation, you would:
        // 1. Query your database with the search criteria
        // 2. Apply filters for name, meet, minimum win rate
        // 3. Apply pagination and sorting
        // 4. Include performance statistics if requested

        logger.info('Trainer search results not in cache and database integration pending');

        searchResults = [];

        // Cache search results for 1 hour
        await services.cacheService.set('trainer_detail', searchCacheParams, searchResults, { ttl: 3600 });
      }

      const totalCount = Array.isArray(searchResults) ? searchResults.length : 0;
      const totalPages = Math.ceil(totalCount / (pageSize || 20));

      res.json({
        success: true,
        data: searchResults as TrainerDetails[],
        message: 'Trainer search completed successfully',
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
   * Get top performing trainers
   * GET /api/trainers/top (with query parameters for criteria)
   */
  getTopTrainers = async (
    req: Request<
      Record<string, never>,
      ApiResponse<(TrainerDetails & { stats: Partial<TrainerStats> })[]>,
      Record<string, never>,
      TrainerQueryParams
    >,
    res: Response<ApiResponse<(TrainerDetails & { stats: Partial<TrainerStats> })[]>>,
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

      const { meet, minWinRate, page = 1, pageSize = 10, sortBy = 'winRate', sortOrder = 'desc' } = req.query;

      logger.info('Getting top trainers', {
        meet,
        minWinRate,
        page,
        pageSize,
        sortBy,
        sortOrder,
      });

      // Check cache first
      const topCacheParams = {
        type: 'top',
        meet: meet || 'all',
        minWinRate: minWinRate?.toString() || 'all',
        page: page?.toString() || '1',
        pageSize: pageSize?.toString() || '10',
        sort: `${sortBy}_${sortOrder}`,
      };
      let topTrainers = await services.cacheService.get('trainer_detail', topCacheParams);

      if (!topTrainers) {
        // In a real implementation, you would:
        // 1. Query database for all trainers
        // 2. Calculate performance statistics
        // 3. Filter by minimum win rate if specified
        // 4. Rank by specified criteria (win rate, prize money, improvement rate, etc.)
        // 5. Apply pagination

        logger.info('Top trainers data not in cache and database integration pending');

        topTrainers = [];

        // Cache for 4 hours (rankings don't change very frequently)
        await services.cacheService.set('trainer_detail', topCacheParams, topTrainers, { ttl: 14400 });
      }

      const totalCount = Array.isArray(topTrainers) ? topTrainers.length : 0;
      const totalPages = Math.ceil(totalCount / (pageSize || 10));

      res.json({
        success: true,
        data: topTrainers as (TrainerDetails & { stats: Partial<TrainerStats> })[],
        message: 'Top trainers retrieved successfully',
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

  /**
   * Get trainer specialization analysis
   * GET /api/trainers/:trNo/specialization
   */
  getTrainerSpecialization = async (
    req: Request<
      { trNo: string },
      ApiResponse<{
        distanceSpecialization: { distance: string; winRate: number; confidence: number }[];
        gradeSpecialization: { grade: string; winRate: number; confidence: number }[];
        trackSpecialization: { meet: string; winRate: number; confidence: number }[];
        seasonalPerformance: { season: string; winRate: number; races: number }[];
        recommendations: string[];
      }>,
      Record<string, never>,
      TrainerQueryParams
    >,
    res: Response<
      ApiResponse<{
        distanceSpecialization: { distance: string; winRate: number; confidence: number }[];
        gradeSpecialization: { grade: string; winRate: number; confidence: number }[];
        trackSpecialization: { meet: string; winRate: number; confidence: number }[];
        seasonalPerformance: { season: string; winRate: number; races: number }[];
        recommendations: string[];
      }>
    >,
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

      const { trNo } = req.params;

      logger.info('Getting trainer specialization analysis', { trNo });

      // Check cache first
      const specializationCacheParams = {
        type: 'specialization',
        trNo,
      };
      let specializationData = await services.cacheService.get('trainer_detail', specializationCacheParams);

      if (!specializationData) {
        // In a real implementation, this would analyze race history to identify:
        // 1. Distance preferences and success rates
        // 2. Grade level specializations
        // 3. Track-specific performance patterns
        // 4. Seasonal variations
        // 5. Generate AI-powered recommendations

        logger.info('Trainer specialization data not in cache and analysis integration pending');

        const mockSpecializationData = {
          distanceSpecialization: [],
          gradeSpecialization: [],
          trackSpecialization: [],
          seasonalPerformance: [],
          recommendations: ['데이터 분석 시스템을 완성한 후 개인 맞춤 추천을 제공합니다.'],
        };
        specializationData = mockSpecializationData;

        // Cache for 6 hours (specialization patterns change slowly)
        await services.cacheService.set('trainer_detail', specializationCacheParams, specializationData, {
          ttl: 21600,
        });
      }

      res.json({
        success: true,
        data: specializationData as {
          distanceSpecialization: { distance: string; winRate: number; confidence: number }[];
          gradeSpecialization: { grade: string; winRate: number; confidence: number }[];
          trackSpecialization: { meet: string; winRate: number; confidence: number }[];
          seasonalPerformance: { season: string; winRate: number; races: number }[];
          recommendations: string[];
        },
        message: 'Trainer specialization analysis retrieved successfully',
        meta: {
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now()),
        },
      });
    } catch (error) {
      next(error);
    }
  };
  // (removed duplicate lighter stub of getTrainerStats)

  // (removed duplicate lighter stub of getTrainerSpecialization)

  /**
   * Get trainer performance
   * GET /api/trainers/:trNo/performance
   */
  getTrainerPerformance = async (
    req: Request<{ trNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      const { trNo } = req.params;

      logger.info('Getting trainer performance', { trNo });

      // TODO: Implement actual trainer performance
      res.json({
        success: true,
        data: {
          trNo,
          message: 'Trainer performance endpoint - to be implemented',
        },
        message: 'Trainer performance retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get trainer horses
   * GET /api/trainers/:trNo/horses
   */
  getTrainerHorses = async (
    req: Request<{ trNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      const { trNo } = req.params;

      logger.info('Getting trainer horses', { trNo });

      // TODO: Implement actual trainer horses
      res.json({
        success: true,
        data: {
          trNo,
          message: 'Trainer horses endpoint - to be implemented',
        },
        message: 'Trainer horses retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  // (removed duplicate lighter stub of searchTrainers)

  // (removed duplicate lighter stub of getTopTrainers)

  /**
   * Get trainer rankings
   * GET /api/trainers/rankings
   */
  getTrainerRankings = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      logger.info('Getting trainer rankings');

      // TODO: Implement actual trainer rankings
      res.json({
        success: true,
        data: {
          message: 'Trainer rankings endpoint - to be implemented',
        },
        message: 'Trainer rankings retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get trainer stats summary
   * GET /api/trainers/stats/summary
   */
  getTrainerStatsSummary = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      logger.info('Getting trainer stats summary');

      // TODO: Implement actual trainer stats summary
      res.json({
        success: true,
        data: {
          message: 'Trainer stats summary endpoint - to be implemented',
        },
        message: 'Trainer stats summary retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get specializations
   * GET /api/trainers/specializations
   */
  getSpecializations = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      logger.info('Getting specializations');

      // TODO: Implement actual specializations
      res.json({
        success: true,
        data: {
          message: 'Specializations endpoint - to be implemented',
        },
        message: 'Specializations retrieved successfully',
      });
    } catch (error) {
      next(error);
    }
  };
}

// Export singleton instance
export const trainerController = new TrainerController();
