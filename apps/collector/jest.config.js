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
  // Run unit + integration tests under tests/** (exclude e2e by ignore pattern below)
  testMatch: [
    '<rootDir>/tests/**/*.test.ts'
  ],

  // Test categories
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/cache/',
    '/logs/',
    '/tests/e2e/'
  ],

  // Coverage configuration
  collectCoverage: process.env.CI === 'true',
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
      branches: 5,
      functions: 10,
      lines: 20,
      statements: 20,
    },
  },

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],

  // Test timeout (5 seconds for faster execution)
  testTimeout: 5000,

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

  // Parallel test execution (reduced for stability)
  maxWorkers: 1,

  // Error handling
  bail: false,
  errorOnDeprecated: true,
  forceExit: true, // Force exit to prevent hanging processes

  // Watch mode configuration
  watchman: false,
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
  // Note: ts-jest config moved to transform options above.
  globals: {
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
  logHeapUsage: false,

  // Disable projects for now - causing issues with setup file
  // projects: [],
};
