FROM node:20-alpine AS builder

WORKDIR /app

# Force cache bust - increment to force rebuild
ARG CACHEBUST=5

# Delete node_modules to force fresh install
RUN rm -rf node_modules .next

# Copy package files
COPY package*.json ./

# Force fresh npm install (no cache)
RUN npm cache clean --force && npm ci

# Copy source files
COPY . .

# Set memory limit for build
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Build Next.js application with no cache
RUN rm -rf .next && npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0

# Copy only necessary files from standalone build
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

# Start Next.js in production mode using standalone server
CMD ["sh", "-c", "PORT=${PORT:-3000} node server.js"]
