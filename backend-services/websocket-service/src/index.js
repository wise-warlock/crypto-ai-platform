import { Server } from "socket.io";

// Khởi tạo Socket.IO server trên cổng 8002
const io = new Server(8002, {
  cors: {
    origin: "http://localhost:3000", // Chỉ cho phép Next.js kết nối
    methods: ["GET", "POST"],
  },
});

console.log("WebSocket Service đang chạy trên cổng 8002...");

// Giả lập nguồn dữ liệu giá
setInterval(() => {
  const priceUpdate = {
    symbol: "SOL-USDT",
    price: (Math.random() * 10 + 150).toFixed(4), // Giá ngẫu nhiên từ 150-160
    timestamp: new Date().getTime(),
  };

  // Gửi sự kiện 'price-update' đến TẤT CẢ client
  io.emit("price-update", priceUpdate);
}, 1000); // Gửi mỗi giây

io.on("connection", (socket) => {
  console.log(`Một user đã kết nối: ${socket.id}`);
  socket.emit("welcome", { message: "Kết nối thành công đến Price Feed!" });

  socket.on("disconnect", () => {
    console.log(`User đã ngắt kết nối: ${socket.id}`);
  });
});