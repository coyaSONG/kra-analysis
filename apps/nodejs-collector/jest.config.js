/** @type {import('jest').Config} */
export default {
  // Test environment
  preset: 'ts-jest/presets/default-esm',
  testEnvironment: 'node',

  // TypeScript configuration
  extensionsToTreatAsEsm: ['.ts'],

  // Module resolution
  moduleNameMapper: {
    '^(\\.{1,2}/.*)\\.js$': '$1',
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],

  // Test file patterns
  testMatch: [
    '<rootDir>/tests/api-simple.test.ts',
    '<rootDir>/tests/middleware/validation.test.ts',
    // Integration and E2E tests require real API, use pnpm test:real-api
    // '<rootDir>/tests/integration/kra-api-integration.test.ts',
    // '<rootDir>/tests/e2e/api-e2e.test.ts',
  ],

  // Test categories
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/cache/',
    '/logs/',
  ],

  // Coverage configuration
  collectCoverage: false,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html', 'json'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/index.ts',
    '!src/server.ts',
    '!src/**/__tests__/**',
    '!src/**/*.test.ts',
    '!src/**/*.spec.ts',
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],

  // Test timeout (10 seconds)
  testTimeout: 10000,

  // Reporter configuration
  reporters: [
    'default'
  ],

  // Transform configuration
  transform: {
    '^.+\\.(ts|tsx)$': [
      'ts-jest',
      {
        useESM: true,
        tsconfig: {
          module: 'esnext',
          moduleResolution: 'node',
          allowSyntheticDefaultImports: true,
          esModuleInterop: true,
        },
      },
    ],
  },

  // Mock configuration
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true,

  // Verbose output
  verbose: false,

  // Parallel test execution
  maxWorkers: '50%',

  // Error handling
  bail: false,
  errorOnDeprecated: true,

  // Watch mode configuration
  watchman: true,
  watchPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/cache/',
    '/logs/',
    '/coverage/',
  ],

  // Additional Jest configuration
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testResultsProcessor: undefined,

  // Global variables available in tests
  globals: {
    'ts-jest': {
      useESM: true,
    },
    // Test environment variables
    TEST_ENV: true,
    NODE_ENV: 'test',
  },

  // Snapshot configuration
  snapshotSerializers: [],
  updateSnapshot: false,

  // Notification configuration (only for watch mode)
  notify: false,
  notifyMode: 'failure-change',

  // Debugging configuration
  detectLeaks: false,
  forceExit: true,  // Force exit after tests complete
  logHeapUsage: false,

  // Disable projects for now - causing issues with setup file
  // projects: [],
};