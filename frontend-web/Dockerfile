FROM node:18-alpine
WORKDIR /app

# Tách riêng cài đặt dependencies để tận dụng cache
COPY package.json ./
RUN npm install

# Copy toàn bộ code
COPY . .

# Build ứng dụng
RUN npm run build

# Cổng 3000 mà Next.js sẽ chạy
EXPOSE 3000

# Chạy ứng dụng
CMD ["npm", "start"]