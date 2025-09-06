###########
# Builder #
###########
FROM node:20-alpine AS builder
WORKDIR /app

# Install dependencies (full) first for layer caching
COPY package*.json ./
RUN npm ci

# Copy only what is needed to build
COPY tsconfig.json ./
COPY src ./src

# Build and then prune to production deps
RUN npm run build && npm prune --production

############
# Runtime  #
############
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production

# Copy production node_modules and built dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY package*.json ./

# Create non-root user for security
RUN addgroup -S app && adduser -S app -G app && chown -R app:app /app
USER app

# No port exposed yet (MCP stdio). Expose later if adding HTTP/WS transport

ENTRYPOINT ["node", "dist/index.js"]