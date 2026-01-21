FROM node:20-alpine AS builder

WORKDIR /app

# Force cache bust - v2
ARG CACHEBUST=2

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source files
COPY . .

# Set memory limit for build
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Build Next.js application
RUN npm run build

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
