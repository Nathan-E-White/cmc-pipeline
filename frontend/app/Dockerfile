FROM oven/bun:1.4.0-alpine AS build
WORKDIR /app
COPY package.json bun.lock ./
COPY app/package.json app/package.json
RUN bun install --frozen-lockfile
COPY . .
RUN bun run --cwd app build
RUN script=$(find app/dist/client/assets -name 'index-*.js' -exec basename {} \;) && style=$(find app/dist/client/assets -name 'styles-*.css' -exec basename {} \;) && printf '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/assets/%s"></head><body><div id="root"></div><script type="module" src="/assets/%s"></script></body></html>' "$style" "$script" > app/dist/client/index.html
FROM nginx:1.27-alpine
COPY app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/app/dist/client /usr/share/nginx/html
EXPOSE 80
