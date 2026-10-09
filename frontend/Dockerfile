# Stage 1: build the static site
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Caddy serves the files (the Caddyfile is mounted by docker-compose)
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
