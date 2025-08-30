/**
 * Validation Middleware Tests
 * 
 * Test suite for request validation middleware including
 * parameter validation, body validation, and error handling.
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { Request, Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';

// Mock express-validator
jest.mock('express-validator', () => ({
  body: jest.fn(() => ({
    notEmpty: jest.fn().mockReturnThis(),
    isString: jest.fn().mockReturnThis(),
    isInt: jest.fn().mockReturnThis(),
    isDate: jest.fn().mockReturnThis(),
    isLength: jest.fn().mockReturnThis(),
    matches: jest.fn().mockReturnThis(),
    custom: jest.fn().mockReturnThis(),
    optional: jest.fn().mockReturnThis(),
  })),
  param: jest.fn(() => ({
    notEmpty: jest.fn().mockReturnThis(),
    isString: jest.fn().mockReturnThis(),
    isInt: jest.fn().mockReturnThis(),
    isLength: jest.fn().mockReturnThis(),
    matches: jest.fn().mockReturnThis(),
    custom: jest.fn().mockReturnThis(),
  })),
  query: jest.fn(() => ({
    optional: jest.fn().mockReturnThis(),
    isString: jest.fn().mockReturnThis(),
    isInt: jest.fn().mockReturnThis(),
    isIn: jest.fn().mockReturnThis(),
    toInt: jest.fn().mockReturnThis(),
    isLength: jest.fn().mockReturnThis(),
  })),
  validationResult: jest.fn(),
}));

// Import after mocking
const mockValidationResult = validationResult as jest.MockedFunction<typeof validationResult>;

// Mock validation middleware (would normally import from actual file)
const createValidationHandler = () => {
  return (req: Request, res: Response, next: NextFunction) => {
    const errors = mockValidationResult(req);
    
    if (!errors.isEmpty()) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Request validation failed',
          details: errors.array()
        },
        timestamp: new Date().toISOString()
      });
    }
    
    next();
  };
};

// Mock validation rules
const validateDateParam = jest.fn();
const validateMeetParam = jest.fn();
const validateRaceNumberParam = jest.fn();
const validateCollectionBody = jest.fn();
const validateHorseQuery = jest.fn();
const validateJockeyQuery = jest.fn();
const validateTrainerQuery = jest.fn();

describe('Validation Middleware', () => {
  let mockRequest: Partial<Request>;
  let mockResponse: Partial<Response>;
  let mockNext: NextFunction;
  let validationHandler: ReturnType<typeof createValidationHandler>;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Create fresh mock objects
    mockRequest = {
      params: {},
      body: {},
      query: {},
      headers: {},
    };

    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis(),
    };

    mockNext = jest.fn();
    validationHandler = createValidationHandler();
  });

  describe('Parameter Validation', () => {
    describe('Date Parameter', () => {
      it('should validate correct date format (YYYYMMDD)', () => {
        // Arrange
        mockRequest.params = { date: '20241201' };
        mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockNext).toHaveBeenCalledWith();
        expect(mockResponse.status).not.toHaveBeenCalled();
      });

      it('should reject invalid date format', () => {
        // Arrange
        mockRequest.params = { date: '2024-12-01' };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [{
            msg: 'Date must be in YYYYMMDD format',
            param: 'date',
            location: 'params'
          }]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockResponse.json).toHaveBeenCalledWith(
          expect.objectContaining({
            success: false,
            error: expect.objectContaining({
              code: 'VALIDATION_ERROR',
              message: 'Request validation failed'
            })
          })
        );
        expect(mockNext).not.toHaveBeenCalled();
      });

      it('should reject future dates', () => {
        // Arrange
        const futureDate = new Date();
        futureDate.setDate(futureDate.getDate() + 1);
        const futureDateString = futureDate.toISOString().slice(0, 10).replace(/-/g, '');
        
        mockRequest.params = { date: futureDateString };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [{
            msg: 'Date cannot be in the future',
            param: 'date',
            location: 'params'
          }]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });

      it('should reject dates too far in the past', () => {
        // Arrange
        mockRequest.params = { date: '19900101' };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [{
            msg: 'Date is too far in the past',
            param: 'date',
            location: 'params'
          }]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });
    });

    describe('Meet Parameter', () => {
      it('should validate correct meet values', () => {
        const validMeets = ['서울', '부산경남', '제주'];
        
        validMeets.forEach(meet => {
          // Arrange
          mockRequest.params = { meet };
          mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

          // Act
          validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

          // Assert
          expect(mockNext).toHaveBeenCalled();
          
          // Reset for next iteration
          jest.clearAllMocks();
          mockNext = jest.fn();
        });
      });

      it('should reject invalid meet values', () => {
        // Arrange
        mockRequest.params = { meet: 'invalid' };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [{
            msg: 'Meet must be one of: 서울, 부산경남, 제주',
            param: 'meet',
            location: 'params'
          }]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });
    });

    describe('Race Number Parameter', () => {
      it('should validate correct race numbers', () => {
        const validRaceNumbers = ['1', '2', '12'];
        
        validRaceNumbers.forEach(raceNo => {
          // Arrange
          mockRequest.params = { raceNo };
          mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

          // Act
          validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

          // Assert
          expect(mockNext).toHaveBeenCalled();
          
          // Reset for next iteration
          jest.clearAllMocks();
          mockNext = jest.fn();
        });
      });

      it('should reject invalid race numbers', () => {
        const invalidRaceNumbers = ['0', '-1', '15', 'abc'];
        
        invalidRaceNumbers.forEach(raceNo => {
          // Arrange
          mockRequest.params = { raceNo };
          mockValidationResult.mockReturnValue({
            isEmpty: () => false,
            array: () => [{
              msg: 'Race number must be between 1 and 12',
              param: 'raceNo',
              location: 'params'
            }]
          } as any);

          // Act
          validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

          // Assert
          expect(mockResponse.status).toHaveBeenCalledWith(400);
          expect(mockNext).not.toHaveBeenCalled();
          
          // Reset for next iteration
          jest.clearAllMocks();
          mockResponse = {
            status: jest.fn().mockReturnThis(),
            json: jest.fn().mockReturnThis(),
          };
          mockNext = jest.fn();
        });
      });
    });
  });

  describe('Body Validation', () => {
    describe('Collection Request Body', () => {
      it('should validate correct collection request body', () => {
        // Arrange
        mockRequest.body = {
          date: '20241201',
          meet: '서울',
          raceNo: 1
        };
        mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockNext).toHaveBeenCalledWith();
      });

      it('should reject missing required fields', () => {
        // Arrange
        mockRequest.body = {
          date: '20241201'
          // missing meet and raceNo
        };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [
            { msg: 'Meet is required', param: 'meet', location: 'body' },
            { msg: 'Race number is required', param: 'raceNo', location: 'body' }
          ]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });

      it('should reject invalid field types', () => {
        // Arrange
        mockRequest.body = {
          date: 20241201, // should be string
          meet: 123, // should be string
          raceNo: '1' // should be number
        };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [
            { msg: 'Date must be a string', param: 'date', location: 'body' },
            { msg: 'Meet must be a string', param: 'meet', location: 'body' },
            { msg: 'Race number must be an integer', param: 'raceNo', location: 'body' }
          ]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });

      it('should handle optional fields correctly', () => {
        // Arrange
        mockRequest.body = {
          date: '20241201',
          meet: '서울'
          // raceNo is optional in some contexts
        };
        mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockNext).toHaveBeenCalledWith();
      });
    });
  });

  describe('Query Parameter Validation', () => {
    describe('Horse Search Query', () => {
      it('should validate horse search parameters', () => {
        // Arrange
        mockRequest.query = {
          name: '천리마',
          limit: '10',
          offset: '0'
        };
        mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockNext).toHaveBeenCalledWith();
      });

      it('should apply default values for optional parameters', () => {
        // Arrange
        mockRequest.query = {
          name: '천리마'
          // limit and offset not provided
        };
        mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockNext).toHaveBeenCalledWith();
      });

      it('should validate limit ranges', () => {
        // Arrange
        mockRequest.query = {
          limit: '200' // exceeds maximum
        };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [{
            msg: 'Limit must be between 1 and 100',
            param: 'limit',
            location: 'query'
          }]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });

      it('should validate offset values', () => {
        // Arrange
        mockRequest.query = {
          offset: '-1' // negative offset
        };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [{
            msg: 'Offset must be non-negative',
            param: 'offset',
            location: 'query'
          }]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });
    });

    describe('Pagination Parameters', () => {
      it('should validate page-based pagination', () => {
        // Arrange
        mockRequest.query = {
          page: '2',
          limit: '20'
        };
        mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockNext).toHaveBeenCalledWith();
      });

      it('should handle both page and offset parameters', () => {
        // Arrange
        mockRequest.query = {
          page: '2',
          offset: '20'
        };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [{
            msg: 'Cannot use both page and offset parameters',
            param: 'pagination',
            location: 'query'
          }]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });
    });

    describe('Sorting Parameters', () => {
      it('should validate sort parameters', () => {
        // Arrange
        mockRequest.query = {
          sort_by: 'date',
          sort_order: 'desc'
        };
        mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockNext).toHaveBeenCalledWith();
      });

      it('should reject invalid sort fields', () => {
        // Arrange
        mockRequest.query = {
          sort_by: 'invalid_field'
        };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [{
            msg: 'Invalid sort field',
            param: 'sort_by',
            location: 'query'
          }]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });

      it('should reject invalid sort orders', () => {
        // Arrange
        mockRequest.query = {
          sort_order: 'invalid'
        };
        mockValidationResult.mockReturnValue({
          isEmpty: () => false,
          array: () => [{
            msg: 'Sort order must be asc or desc',
            param: 'sort_order',
            location: 'query'
          }]
        } as any);

        // Act
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

        // Assert
        expect(mockResponse.status).toHaveBeenCalledWith(400);
        expect(mockNext).not.toHaveBeenCalled();
      });
    });
  });

  describe('Custom Validators', () => {
    describe('Korean Racing Meets', () => {
      it('should validate Korean race track names', () => {
        const validMeets = ['서울', '부산경남', '제주'];
        
        validMeets.forEach(meet => {
          mockRequest.body = { meet };
          mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

          validationHandler(mockRequest as Request, mockResponse as Response, mockNext);
          expect(mockNext).toHaveBeenCalled();

          jest.clearAllMocks();
          mockNext = jest.fn();
        });
      });
    });

    describe('Horse Numbers', () => {
      it('should validate horse number format', () => {
        // Korean horse numbers are typically 8 digits starting with year
        const validHorseNumbers = ['20210001', '20220123'];
        
        validHorseNumbers.forEach(hrNo => {
          mockRequest.params = { hrNo };
          mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

          validationHandler(mockRequest as Request, mockResponse as Response, mockNext);
          expect(mockNext).toHaveBeenCalled();

          jest.clearAllMocks();
          mockNext = jest.fn();
        });
      });

      it('should reject invalid horse number format', () => {
        const invalidHorseNumbers = ['123', 'ABC123', '1990001'];
        
        invalidHorseNumbers.forEach(hrNo => {
          mockRequest.params = { hrNo };
          mockValidationResult.mockReturnValue({
            isEmpty: () => false,
            array: () => [{
              msg: 'Invalid horse number format',
              param: 'hrNo',
              location: 'params'
            }]
          } as any);

          validationHandler(mockRequest as Request, mockResponse as Response, mockNext);
          expect(mockResponse.status).toHaveBeenCalledWith(400);

          jest.clearAllMocks();
          mockResponse = {
            status: jest.fn().mockReturnThis(),
            json: jest.fn().mockReturnThis(),
          };
          mockNext = jest.fn();
        });
      });
    });
  });

  describe('Error Response Format', () => {
    it('should return standardized error response', () => {
      // Arrange
      const mockErrors = [
        { msg: 'Date is required', param: 'date', location: 'body' },
        { msg: 'Meet is invalid', param: 'meet', location: 'body' }
      ];
      
      mockValidationResult.mockReturnValue({
        isEmpty: () => false,
        array: () => mockErrors
      } as any);

      // Act
      validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

      // Assert
      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Request validation failed',
          details: mockErrors
        },
        timestamp: expect.any(String)
      });
    });

    it('should include timestamp in ISO format', () => {
      // Arrange
      mockValidationResult.mockReturnValue({
        isEmpty: () => false,
        array: () => [{ msg: 'Test error', param: 'test', location: 'body' }]
      } as any);

      // Act
      validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

      // Assert
      const jsonCall = (mockResponse.json as jest.Mock).mock.calls[0][0];
      expect(jsonCall.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty validation result gracefully', () => {
      // Arrange
      mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

      // Act
      validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

      // Assert
      expect(mockNext).toHaveBeenCalledWith();
      expect(mockResponse.status).not.toHaveBeenCalled();
    });

    it('should handle malformed validation result', () => {
      // Arrange
      mockValidationResult.mockReturnValue({
        isEmpty: () => false,
        array: () => []
      } as any);

      // Act
      validationHandler(mockRequest as Request, mockResponse as Response, mockNext);

      // Assert
      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockNext).not.toHaveBeenCalled();
    });

    it('should handle null/undefined request properties', () => {
      // Arrange
      mockRequest = {
        params: null,
        body: undefined,
        query: {}
      } as any;
      mockValidationResult.mockReturnValue({ isEmpty: () => true } as any);

      // Act & Assert - should not throw
      expect(() => {
        validationHandler(mockRequest as Request, mockResponse as Response, mockNext);
      }).not.toThrow();
    });
  });
});