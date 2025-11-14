import { Server } from "socket.io";
import axios from "axios"; // <-- 1. Import axios

// Khởi tạo Socket.IO server trên cổng 8002
const io = new Server(8002, {
  cors: {
    origin: "http://localhost:3000", // Chỉ cho phép Next.js kết nối
    methods: ["GET", "POST"],
  },
});

console.log("WebSocket Service đang chạy trên cổng 8002...");

// --- 2. ĐỊNH NGHĨA URL CỦA TRADING SERVICE ---
// (Sử dụng tên service 'trading-service' và cổng 8000
// vì chúng giao tiếp nội bộ trong mạng Docker)
const TRADING_SERVICE_URL = "http://trading-service:8000/api/v1/price/SOL-USDT";

// --- 3. HÀM MỚI: LẤY GIÁ THẬT VÀ PHÁT ĐI ---
const fetchAndEmitPrice = async () => {
  try {
    // console.log("Đang lấy giá thật từ trading-service...");
    
    // Gọi API (GET) đến trading-service
    const response = await axios.get(TRADING_SERVICE_URL, {
      timeout: 2500 // Timeout 2.5 giây
    });

    if (response.data && response.data.price) {
      // Dữ liệu giá thật từ API
      const priceUpdate = {
        symbol: response.data.symbol,
        price: response.data.price,
        source: response.data.source, // Thêm nguồn (Cache / API)
      };
      
      // Gửi sự kiện 'price-update' đến TẤT CẢ client
      io.emit("price-update", priceUpdate);
      // console.log(`Đã phát giá thật: ${priceUpdate.price}`);

    }
  } catch (error) {
    // Nếu trading-service lỗi (ví dụ: API Jupiter lỗi), chúng ta sẽ báo lỗi
    console.error(`Lỗi khi lấy giá từ trading-service: ${error.message}`);
    // Gửi thông báo lỗi (tùy chọn)
    io.emit("price-error", { message: "Không thể lấy giá real-time." });
  }
};

// --- 4. THAY THẾ LOGIC CŨ ---
// Bỏ đoạn `setInterval` với `Math.random()`

// Cứ 3 giây gọi hàm lấy giá thật 1 lần
setInterval(fetchAndEmitPrice, 3000); 

// Cũng gọi 1 lần ngay khi khởi động
fetchAndEmitPrice();

// --- 5. LOGIC KẾT NỐI (Không đổi) ---
io.on("connection", (socket) => {
  console.log(`Một user đã kết nối: ${socket.id}`);
  socket.emit("welcome", { message: "Kết nối thành công đến Price Feed (Real)!" });

  socket.on("disconnect", () => {
    console.log(`User đã ngắt kết nối: ${socket.id}`);
  });
});