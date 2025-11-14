FROM node:18-alpine
WORKDIR /app

# Copy cả package.json VÀ package-lock.json (nếu có)
COPY package*.json ./

# --- SỬA LỖI Ở ĐÂY ---
# Quay lại dùng "npm install" thay vì "npm ci"
RUN npm install

# Copy toàn bộ code
COPY . .

# Cổng 8002 mà Node.js sẽ chạy bên trong container
EXPOSE 8002
CMD ["npm", "start"]