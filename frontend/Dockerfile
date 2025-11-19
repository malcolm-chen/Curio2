# Frontend Dockerfile

FROM node:20 AS build
WORKDIR /app

# Accept build arguments for Vite environment variables
ARG VITE_VUE_APP_URL
ARG VITE_OPENAI_API_KEY

# Set environment variables for build
ENV VITE_VUE_APP_URL=$VITE_VUE_APP_URL
ENV VITE_OPENAI_API_KEY=$VITE_OPENAI_API_KEY

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]