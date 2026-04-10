# Serve pre-built dist/ with nginx (build happens on CI)
FROM nginx:1.27-alpine

ARG NGINX_CONF=nginx.conf

COPY dist /usr/share/nginx/html
COPY ${NGINX_CONF} /etc/nginx/conf.d/default.conf

EXPOSE 80 443

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s \
    CMD wget -qO- http://127.0.0.1/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
