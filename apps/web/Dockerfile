# Build context should be the monorepo root:
#   docker build -t ac-web -f apps/web/Dockerfile .

FROM node:24-alpine AS base

# --- Dependencies ---
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy root workspace config and lockfile
COPY package.json package-lock.json ./
COPY packages/types/package.json packages/types/
COPY packages/ui/package.json packages/ui/
COPY apps/web/package.json apps/web/

RUN npm ci --workspaces --include-workspace-root

# --- Builder ---
FROM base AS builder
WORKDIR /app

# npm workspaces hoists everything to root node_modules
COPY --from=deps /app/node_modules ./node_modules

# Copy workspace package sources
COPY package.json ./
COPY packages/types/ packages/types/
COPY packages/ui/ packages/ui/
COPY apps/web/ apps/web/

# Build shared packages first
RUN cd packages/types && npm run build
RUN cd packages/ui && npm run build

ARG NEXT_PUBLIC_CONVEX_URL
ENV NEXT_PUBLIC_CONVEX_URL=$NEXT_PUBLIC_CONVEX_URL

ARG NEXT_PUBLIC_CONVEX_SITE_URL
ENV NEXT_PUBLIC_CONVEX_SITE_URL=$NEXT_PUBLIC_CONVEX_SITE_URL

ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL

ENV NEXT_TELEMETRY_DISABLED=1

RUN cd apps/web && npx next build

# --- Runner ---
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "apps/web/server.js"]
