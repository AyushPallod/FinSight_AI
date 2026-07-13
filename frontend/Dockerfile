# Stage 1: Build the React Application
FROM node:20-alpine AS build

WORKDIR /app

# Copy package descriptors and resolve dependencies
COPY package*.json ./
RUN npm ci

# Copy frontend source code and compile Vite assets
COPY . .
RUN npm run build

# Stage 2: Serve the compiled static assets using Nginx
FROM nginx:stable-alpine

# Copy built bundle files from the Node environment to Nginx webroot
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx routing rules to support SPA clients
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
