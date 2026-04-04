# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:1.27-alpine

# NGINX_CONF=nginx.conf (dev/default) | nginx.prod.conf (production with HTTPS)
ARG NGINX_CONF=nginx.conf

COPY --from=build /app/dist /usr/share/nginx/html
COPY ${NGINX_CONF} /etc/nginx/conf.d/default.conf

EXPOSE 80 443

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s \
    CMD wget -qO- http://127.0.0.1/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
