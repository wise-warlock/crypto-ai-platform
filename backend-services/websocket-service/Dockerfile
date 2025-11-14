FROM node:18-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY src/ ./src/
# Cổng 8002 mà Node.js sẽ chạy bên trong container
EXPOSE 8002
CMD ["npm", "start"]