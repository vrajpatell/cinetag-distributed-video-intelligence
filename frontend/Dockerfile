FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .
# Always ensure a public directory exists so the runner stage's COPY does not fail.
RUN mkdir -p public

ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_APP_ENV=gcp
ARG NEXT_PUBLIC_BUILD_VERSION
ARG NEXT_PUBLIC_GCP_REGION=us-central1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_APP_ENV=$NEXT_PUBLIC_APP_ENV \
    NEXT_PUBLIC_BUILD_VERSION=$NEXT_PUBLIC_BUILD_VERSION \
    NEXT_PUBLIC_GCP_REGION=$NEXT_PUBLIC_GCP_REGION \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=8080 \
    HOSTNAME=0.0.0.0

# Run as a non-root user for safer Cloud Run deployments.
RUN addgroup -S app && adduser -S app -G app

COPY --from=builder --chown=app:app /app/.next/standalone ./
COPY --from=builder --chown=app:app /app/.next/static ./.next/static
COPY --from=builder --chown=app:app /app/public ./public

USER app
EXPOSE 8080
CMD ["node", "server.js"]
