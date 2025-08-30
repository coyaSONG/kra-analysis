# TypeScript Type Definitions for KRA APIs

This document describes the comprehensive TypeScript type definitions created for the Korea Racing Authority (KRA) public APIs in the collector application.

## Overview

The type system provides:
- **Complete KRA API coverage**: Types for API214_1, API8_2, API12_1, and API19_1
- **Type safety**: Fully typed request/response structures with proper validation
- **Documentation**: JSDoc comments for all interfaces and properties
- **Backwards compatibility**: Legacy types maintained for existing code

## File Structure

```
src/types/
├── index.ts              # Central type exports and application types
├── kra-api.types.ts      # KRA API specific type definitions
└── api.types.ts          # REST API and response wrapper types
```

## KRA API Types (kra-api.types.ts)

### Core API Response Structure

All KRA APIs follow a consistent wrapper pattern:

```typescript
interface KraApiResponse<T> {
  response: {
    header: KraApiHeader;     // Result code and message
    body: KraApiBody<T>;      // Paginated data structure
  };
}
```

### API Coverage

#### 1. API214_1 - Race Result (경주 결과 조회)
**Type**: `Api214Response`, `Api214Item`

Complete race result data including:
- Basic race information (date, race number, track conditions)
- Horse details (name, number, age, sex, equipment)
- Performance data (finish position, times, odds)
- Section times for all tracks (Busan, Seoul, Jeju)
- Prize money distribution
- Weather and track conditions

**Key Fields**:
```typescript
interface Api214Item {
  hrNo: string;           // Horse number
  hrName: string;         // Horse name
  jkNo: string;          // Jockey number  
  jkName: string;        // Jockey name
  trNo: string;          // Trainer number
  trName: string;        // Trainer name
  ord: number;           // Finish position
  winOdds: number;       // Win odds
  plcOdds: number;       // Place odds
  rcTime: number;        // Race time
  // + 50+ additional timing and performance fields
}
```

#### 2. API8_2 - Horse Information (경주마 정보 조회)
**Type**: `Api8_2Response`, `Api8_2Item`

Detailed horse profile including:
- Bloodline information (sire, dam)
- Career statistics (races, wins, earnings)
- Physical characteristics
- Ownership details

```typescript
interface Api8_2Item {
  hrNo: string;          // Horse number
  hrName: string;        // Horse name
  faHrName: string;      // Father horse name
  moHrName: string;      // Mother horse name
  rcCntT: number;        // Total race count
  ord1CntT: number;      // Total wins
  chaksunT: number;      // Total earnings
  // + performance statistics
}
```

#### 3. API12_1 - Jockey Information (기수 정보 조회)
**Type**: `Api12_1Response`, `Api12_1Item`

Comprehensive jockey data:
- Personal details (age, debut date)
- Career statistics (wins, races, percentages)
- Professional classification
- Performance metrics

```typescript
interface Api12_1Item {
  jkNo: string;          // Jockey number
  jkName: string;        // Jockey name
  age: number;           // Age
  debut: number;         // Debut date (YYYYMMDD)
  rcCntT: number;        // Total races
  ord1CntT: number;      // Total wins
  part: string;          // Classification (프리기수, 전속기수)
  // + detailed statistics
}
```

#### 4. API19_1 - Trainer Information (조교사 정보 조회)
**Type**: `Api19_1Response`, `Api19_1Item`

Complete trainer profiles:
- Career performance rates (win, place, show)
- Training statistics by period
- Professional details
- Success metrics

```typescript
interface Api19_1Item {
  trNo: string;          // Trainer number
  trName: string;        // Trainer name
  winRateT: number;      // Total win rate
  plcRateT: number;      // Total place rate
  rcCntT: number;        // Total races trained
  ord1CntT: number;      // Total wins
  stDate: number;        // Start date (YYYYMMDD)
  // + performance metrics
}
```

### Enriched Data Types

For comprehensive analysis, enriched types combine multiple API responses:

```typescript
interface EnrichedHorseEntry extends Api214Item {
  horseDetail?: Api8_2Item;      // Detailed horse info
  jockeyDetail?: Api12_1Item;    // Detailed jockey info  
  trainerDetail?: Api19_1Item;   // Detailed trainer info
  performanceMetrics?: {         // Computed metrics
    horseWinRate: number;
    jockeyWinRate: number;
    trainerWinRate: number;
    combinedScore: number;
  };
}
```

### Type Guards

Runtime type validation functions for API response identification:

```typescript
// Check if response is race result data
isApi214Response(response: KraApiResponseUnion): response is Api214Response

// Check if response is horse information  
isApi8_2Response(response: KraApiResponseUnion): response is Api8_2Response

// Check if response is jockey information
isApi12_1Response(response: KraApiResponseUnion): response is Api12_1Response

// Check if response is trainer information
isApi19_1Response(response: KraApiResponseUnion): response is Api19_1Response
```

## REST API Types (api.types.ts)

### Standard Response Wrapper

All internal API responses use a consistent structure:

```typescript
interface ApiResponse<T> {
  success: boolean;              // Operation success flag
  data?: T;                     // Response payload
  message?: string;             // Success message
  error?: string;               // Error message
  meta?: ResponseMetadata;      // Pagination and metadata
}
```

### Collection Operations

#### Data Collection Request/Response
```typescript
interface CollectionRequest {
  date: string;                 // YYYY-MM-DD format
  raceNo?: number;             // Optional race number
  meet?: string;               // Track identifier
  enrichData?: boolean;        // Include detailed information
  forceRefresh?: boolean;      // Force API refresh
}

interface CollectionResponse extends ApiResponse<CollectedRaceData> {}
```

#### Batch Collection
```typescript
interface BatchCollectionRequest {
  startDate: string;           // Collection period start
  endDate: string;             // Collection period end
  meets?: string[];            // Specific tracks
  enrichData?: boolean;        // Include enrichment
  concurrency?: number;        // Parallel API calls
}
```

### Query Parameters

Type-safe query parameters for different endpoints:

```typescript
interface RaceQueryParams extends PaginationParams {
  date?: string;               // Filter by date
  dateFrom?: string;           // Date range start
  dateTo?: string;             // Date range end
  raceNo?: number;             // Specific race
  meet?: string;               // Track filter
  includeEnriched?: boolean;   // Include detailed data
}

interface HorseQueryParams extends PaginationParams {
  hrNo?: string;               // Horse number filter
  hrName?: string;             // Horse name search
  meet?: string;               // Track filter
  rank?: string;               // Grade filter
}
```

### Error Handling

Comprehensive error type system:

```typescript
interface ErrorResponse extends ApiResponse<never> {
  success: false;
  error: string;
  statusCode?: number;
  errorCode?: string;          // Programmatic error identification
  details?: Record<string, any>;
}

interface ValidationErrorResponse extends ErrorResponse {
  errorCode: 'VALIDATION_ERROR';
  validationErrors: ValidationError[];
}
```

## Application Types (index.ts)

### Configuration

Complete application configuration structure:

```typescript
interface Config {
  port: number;
  nodeEnv: string;
  redis?: {
    host: string;
    port: number;
    password?: string;
    connectTimeout?: number;
    // + additional Redis options
  };
  kra: {
    baseUrl: string;
    apiKey?: string;
    timeout?: number;
    rateLimit?: {
      maxRequests: number;
      windowMs: number;
    };
    // + retry configuration
  };
  // + database, logging configuration
}
```

### Error Classes

Extended error classes with context and debugging information:

```typescript
class AppError extends Error {
  constructor(
    message: string,
    statusCode: number = 500,
    isOperational: boolean = true,
    context?: Record<string, any>
  );
}

class ValidationError extends AppError {
  validationErrors: Array<{
    field: string;
    message: string;
    value?: any;
  }>;
}

class ExternalApiError extends AppError {
  apiName: string;
  endpoint?: string;
  apiResponseCode?: string;
  apiResponseMessage?: string;
}
```

## Usage Examples

### Basic KRA API Response Handling

```typescript
import { Api214Response, isApi214Response } from './types';

function processRaceResult(response: unknown) {
  if (isApi214Response(response)) {
    // TypeScript now knows this is Api214Response
    const items = Array.isArray(response.response.body.items.item) 
      ? response.response.body.items.item 
      : [response.response.body.items.item];
    
    items.forEach(horse => {
      console.log(`${horse.hrName} finished ${horse.ord} with odds ${horse.winOdds}`);
    });
  }
}
```

### Collection Service Implementation

```typescript
import { CollectionRequest, CollectionResponse } from './types';

class RaceCollectionService {
  async collectRace(request: CollectionRequest): Promise<CollectionResponse> {
    try {
      // Type-safe request handling
      const raceData = await this.kraApi.getRaceResult({
        date: request.date,
        raceNo: request.raceNo,
        meet: request.meet
      });

      return {
        success: true,
        data: {
          raceInfo: {
            date: request.date,
            meet: request.meet || 'SEOUL',
            raceNo: request.raceNo || 1,
            // ... other fields
          },
          raceResult: raceData,
          collectionMeta: {
            collectedAt: new Date().toISOString(),
            isEnriched: request.enrichData || false,
            dataSource: 'kra_api'
          }
        }
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
}
```

### Error Handling with Type Safety

```typescript
import { AppError, ValidationError, ExternalApiError } from './types';

function handleApiError(error: unknown) {
  if (error instanceof ValidationError) {
    // Handle validation errors
    error.validationErrors.forEach(validationError => {
      console.log(`Field ${validationError.field}: ${validationError.message}`);
    });
  } else if (error instanceof ExternalApiError) {
    // Handle KRA API errors
    console.log(`KRA API Error: ${error.apiName} - ${error.apiResponseMessage}`);
  } else if (error instanceof AppError) {
    // Handle general application errors
    console.log(`App Error: ${error.message} (${error.statusCode})`);
  }
}
```

## Type Safety Benefits

1. **Compile-time Validation**: Catch type mismatches before runtime
2. **IntelliSense Support**: Full autocomplete for all API fields
3. **Refactoring Safety**: IDE can safely rename and update references
4. **Documentation**: Self-documenting code with JSDoc comments
5. **Runtime Type Guards**: Safe type narrowing with validation functions

## Migration from Legacy Types

The type system includes deprecated legacy types for backward compatibility:

```typescript
// Legacy (deprecated)
interface RaceData {
  date: string;
  raceNo: number;
  track: string;  // deprecated
  horses: HorseData[];
}

// New (recommended)
interface CollectedRaceData {
  raceInfo: {
    date: string;
    meet: string;   // replaces track
    raceNo: number;
  };
  raceResult: Api214Item[];
  collectionMeta: {
    collectedAt: string;
    isEnriched: boolean;
  };
}
```

## Development Guidelines

1. **Use specific types**: Prefer `Api214Item` over generic `any`
2. **Leverage type guards**: Use `isApi214Response()` for runtime validation  
3. **Document with JSDoc**: Add descriptions for custom interfaces
4. **Handle errors properly**: Use typed error classes with context
5. **Validate at boundaries**: Check types at API entry points

## Build and Type Checking

The type definitions are built as part of the standard TypeScript compilation:

```bash
# Type check without emitting files
npm run type-check

# Build with type declaration generation  
npm run build

# Generated files in dist/types/
# - index.d.ts (main type exports)
# - kra-api.types.d.ts (KRA API types)
# - api.types.d.ts (REST API types)
```

This comprehensive type system ensures type safety, improves developer experience, and provides a solid foundation for the KRA data analysis application.