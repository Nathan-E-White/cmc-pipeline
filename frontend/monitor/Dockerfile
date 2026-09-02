FROM oven/bun:1.4.0-alpine AS build
WORKDIR /app
COPY package.json bun.lock ./
COPY monitor/package.json monitor/package.json
RUN bun install --frozen-lockfile
COPY . .
ARG VITE_PHYSICS_APP_ORIGIN
ENV VITE_PHYSICS_APP_ORIGIN=$VITE_PHYSICS_APP_ORIGIN
RUN bun run --cwd monitor build
RUN script=$(find monitor/dist/client/assets -name 'index-*.js' -exec basename {} \;) && style=$(find monitor/dist/client/assets -name 'styles-*.css' -exec basename {} \;) && printf '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/assets/%s"></head><body><div id="root"></div><script type="module" src="/assets/%s"></script></body></html>' "$style" "$script" > monitor/dist/client/index.html
FROM nginx:1.27-alpine
COPY monitor/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/monitor/dist/client /usr/share/nginx/html
EXPOSE 80
