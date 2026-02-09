# Multi-stage build for production-ready frontend

# ── Development Stage ──
FROM node:22-alpine AS development

WORKDIR /app

# Copy package files
COPY frontend/package*.json /app/

# Install all dependencies (including devDependencies for Vite)
RUN npm ci

# Copy source code
COPY frontend /app/

# Expose Vite dev server port
EXPOSE 5173

# Start dev server (overridden by docker-compose)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ── Build Stage ──
FROM node:22-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json /app/

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY frontend /app/

# Build the application
RUN npm run build

# ── Production Stage with Nginx ──
FROM nginx:alpine

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user for nginx
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown appuser:appuser /var/run/nginx.pid

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8080 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
