# Built with `network: none`: node_modules comes from the sandbox restore step (npm ci).
FROM node:22-bookworm AS build
WORKDIR /work/mobile-web
COPY . .
RUN npm run build

FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /work/mobile-web/dist/mobile-web/browser /usr/share/nginx/html
EXPOSE 80
