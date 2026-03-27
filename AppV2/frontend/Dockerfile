FROM node:22-alpine AS build

WORKDIR /app

COPY AppV2/frontend/package.json ./
RUN npm install

COPY AppV2/frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY AppV2/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
