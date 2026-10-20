# Stage 1: Build production bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies with clean cache
COPY package*.json ./
RUN npm ci || npm install

# Copy application source
COPY . .

# Build production bundle args and environment
ARG VITE_API_BASE_URL=/api
ARG VITE_WS_BASE_URL=
ARG VITE_API_URL=/api
ARG VITE_DEFAULT_TIMEZONE=Asia/Ho_Chi_Minh
ARG VITE_PAGE_SIZE=20

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_BASE_URL=$VITE_WS_BASE_URL
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_DEFAULT_TIMEZONE=$VITE_DEFAULT_TIMEZONE
ENV VITE_PAGE_SIZE=$VITE_PAGE_SIZE

RUN npm run build

# Stage 2: Production Nginx server
FROM nginx:1.27-alpine AS runner

# Remove default nginx configs
RUN rm -rf /etc/nginx/conf.d/*

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
