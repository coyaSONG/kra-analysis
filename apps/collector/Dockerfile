# =============================================================================
# Multi-stage Dockerfile for KRA Data Collector API
# =============================================================================

# =============================================================================
# Base Stage - Common dependencies and setup
# =============================================================================
FROM node:22-alpine AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    curl \
    dumb-init \
    && rm -rf /var/cache/apk/*

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Set up directory structure
RUN mkdir -p /app/cache /app/logs /app/tmp && \
    chown -R nodejs:nodejs /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production --silent && \
    npm cache clean --force

# Copy application code
COPY --chown=nodejs:nodejs . .

# =============================================================================
# Development Stage - For local development with hot reload
# =============================================================================
FROM base AS development

# Install all dependencies (including dev dependencies)
RUN npm ci --silent && \
    npm cache clean --force

# Install development tools globally
RUN npm install -g tsx nodemon --silent

# Expose application port and debugger port
EXPOSE 3001 9229

# Switch to non-root user
USER nodejs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# Start command for development
CMD ["npm", "run", "dev"]

# =============================================================================
# Build Stage - TypeScript compilation
# =============================================================================
FROM base AS builder

# Install all dependencies for building
RUN npm ci --silent && \
    npm cache clean --force

# Copy source code
COPY --chown=nodejs:nodejs src ./src
COPY --chown=nodejs:nodejs tsconfig.json ./

# Build the application
RUN npm run build && \
    npm run type-check

# Clean up dev dependencies
RUN npm ci --only=production --silent && \
    npm cache clean --force

# =============================================================================
# Production Stage - Optimized for production deployment
# =============================================================================
FROM node:22-alpine AS production

# Install system dependencies and security updates
RUN apk add --no-cache \
    curl \
    dumb-init \
    ca-certificates \
    && apk upgrade \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Set working directory
WORKDIR /app

# Copy production dependencies from base stage
COPY --from=base --chown=nodejs:nodejs /app/node_modules ./node_modules

# Copy built application from builder stage
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/package*.json ./

# Set up directory structure
RUN mkdir -p /app/cache /app/logs /app/tmp && \
    chown -R nodejs:nodejs /app

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3001
ENV HOST=0.0.0.0

# Expose application port
EXPOSE 3001

# Switch to non-root user
USER nodejs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# Add labels for image metadata
LABEL maintainer="KRA Data Collector Team"
LABEL version="1.0.0"
LABEL description="Korean Racing Authority Data Collector API"
LABEL org.opencontainers.image.title="KRA Data Collector API"
LABEL org.opencontainers.image.description="Enterprise-grade Node.js API for collecting Korean Racing Authority data"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="KRA Analysis Team"
LABEL org.opencontainers.image.licenses="ISC"

# Start the application with dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]
CMD ["npm", "start"]

# =============================================================================
# Test Stage - For running tests in CI/CD
# =============================================================================
FROM base AS test

# Install all dependencies including dev dependencies
RUN npm ci --silent && \
    npm cache clean --force

# Install test dependencies
RUN npm install -g jest --silent

# Copy test files and configuration
COPY --chown=nodejs:nodejs tests ./tests
COPY --chown=nodejs:nodejs jest.config.js ./.env.test ./

# Copy source code for testing
COPY --chown=nodejs:nodejs src ./src
COPY --chown=nodejs:nodejs tsconfig.json ./

# Set test environment
ENV NODE_ENV=test

# Switch to non-root user
USER nodejs

# Default command runs tests
CMD ["npm", "test"]

# =============================================================================
# Nginx Stage - Optional reverse proxy (can be used separately)
# =============================================================================
FROM nginx:alpine AS nginx

# Copy custom nginx configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/conf.d/ /etc/nginx/conf.d/

# Create log directory
RUN mkdir -p /var/log/nginx && \
    chown -R nginx:nginx /var/log/nginx

# Expose ports
EXPOSE 80 443

# Health check for nginx
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
