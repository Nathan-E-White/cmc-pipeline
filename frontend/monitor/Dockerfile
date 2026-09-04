FROM oven/bun:1.4.0-alpine AS build
WORKDIR /app
COPY package.json bun.lock ./
COPY monitor/package.json monitor/package.json
RUN bun install --frozen-lockfile
COPY . .
ARG VITE_PHYSICS_APP_ORIGIN
ENV VITE_PHYSICS_APP_ORIGIN=$VITE_PHYSICS_APP_ORIGIN
RUN bun run --cwd monitor build

FROM oven/bun:1.4.0-alpine
WORKDIR /app
COPY --from=build /app/monitor/dist ./dist
COPY monitor/runtime.mjs ./runtime.mjs
ENV PORT=3000
ENV NODE_ENV=production
EXPOSE 3000
CMD ["bun", "runtime.mjs"]
