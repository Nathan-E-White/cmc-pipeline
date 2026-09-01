FROM oven/bun:1.4.0-alpine AS build

WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build
# The Start build emits client assets but no static HTML entry.  This local
# register is served as an SPA behind nginx, so create its minimal shell from
# the hashed assets produced by the same build.
RUN script=$(find dist/client/assets -name 'index-*.js' -exec basename {} \;) && \
    style=$(find dist/client/assets -name 'styles-*.css' -exec basename {} \;) && \
    printf '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/assets/%s"></head><body><div id="root"></div><script type="module" src="/assets/%s"></script></body></html>' "$style" "$script" > dist/client/index.html

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/client /usr/share/nginx/html

EXPOSE 80
