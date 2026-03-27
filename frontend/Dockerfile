# Для фронтенда на Node.js/React/Vue
FROM node:18-alpine as build

WORKDIR /app

# Копируем package.json и устанавливаем зависимости
COPY package*.json ./
RUN npm ci --only=production

# Копируем исходный код и собираем
COPY . .
RUN npm run build

# Второй этап: nginx для раздачи статики
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Если используете React/Vue, обычно сборка в папке dist
# Для разных фреймворков путь может отличаться: /build, /public и т.д.

EXPOSE 80