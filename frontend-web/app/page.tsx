// frontend-web/app/page.tsx

"use client"; // Đánh dấu đây là Client Component

import { useState, useEffect } from "react";
// Import thư viện socket.io-client
import io, { Socket } from "socket.io-client";

// --- Định nghĩa các URL của Backend ---
const SOCKET_URL = "http://localhost:8002";
const AI_SERVICE_URL = "http://localhost:8001";
const TRADE_SERVICE_URL = "http://localhost:8000";

// Định nghĩa kiểu dữ liệu cho giá
interface PriceData {
  symbol: string;
  price: string;
}

// Đây là component chính của trang chủ
export default function Home() {
  // --- STATE CHO WEBSOCKET ---
  const [price, setPrice] = useState<PriceData | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // --- STATE CHO AI CHAT ---
  const [prompt, setPrompt] = useState(""); // Nội dung gõ vào input
  const [aiResponse, setAiResponse] = useState(""); // Nội dung AI trả về
  const [isAiLoading, setIsAiLoading] = useState(false); // Trạng thái chờ

  // --- STATE CHO TRADING ---
  const [tradeResult, setTradeResult] = useState(""); // Kết quả giao dịch
  const [isTrading, setIsTrading] = useState(false); // Trạng thái chờ

  // --- STATE CHO PRICE CACHE (REDIS) ---
  const [priceResult, setPriceResult] = useState("");
  const [isPriceLoading, setIsPriceLoading] = useState(false);

  // --- 1. HIỆU ỨNG: KẾT NỐI WEBSOCKET ---
  useEffect(() => {
    // Khởi tạo kết nối socket
    const socket: Socket = io(SOCKET_URL);

    // Lắng nghe sự kiện 'connect'
    socket.on("connect", () => setIsConnected(true));

    // Lắng nghe sự kiện 'disconnect'
    socket.on("disconnect", () => setIsConnected(false));

    // Lắng nghe sự kiện 'price-update' từ server
    socket.on("price-update", (data: PriceData) => {
      setPrice(data); // Cập nhật state khi có giá mới
    });

    // Hàm dọn dẹp: Ngắt kết nối khi component bị unmount
    return () => {
      socket.disconnect();
    };
  }, []); // Mảng rỗng [] nghĩa là effect này chỉ chạy 1 lần khi component mount

  // --- 2. HÀM XỬ LÝ: GỌI AI AGENT (MONGO) ---
  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); // Ngăn form reload trang
    if (!prompt) return; // Không làm gì nếu input rỗng

    setIsAiLoading(true);
    setAiResponse("");
    try {
      // Gọi API đến AI Service (FastAPI)
      const response = await fetch(`${AI_SERVICE_URL}/api/v1/agent/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "user_001", prompt: prompt }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setAiResponse(data.response); // Cập nhật kết quả vào state
    } catch (error) {
      console.error("Lỗi khi gọi AI service:", error);
      setAiResponse("Lỗi: Không thể kết nối hoặc xử lý yêu cầu đến AI service.");
    } finally {
      setIsAiLoading(false); // Luôn tắt loading
    }
  };

  // --- 3. HÀM XỬ LÝ: GỌI AUTO-TRADING ---
  const handleExecuteTrade = async () => {
    setIsTrading(true);
    setTradeResult("Đang gửi lệnh giao dịch...");
    try {
      // Định nghĩa một lệnh giao dịch giả lập
      const order = {
        user_id: "user_001",
        action: "BUY",
        symbol: "SOL-USDT",
        amount_usd: 100.0,
      };

      // Gọi API đến Trading Service (FastAPI)
      const response = await fetch(`${TRADE_SERVICE_URL}/api/v1/trade/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(order),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      // Hiển thị kết quả (từ trường 'message' của backend)
      setTradeResult(`Trạng thái: ${data.status}\nMessage: ${data.message}\nTX ID: ${data.tx_id}`);
    } catch (error) {
      console.error("Lỗi khi gọi Trading service:", error);
      setTradeResult("Lỗi: Không thể kết nối hoặc xử lý yêu cầu đến Trading service.");
    } finally {
      setIsTrading(false); // Luôn tắt loading
    }
  };

  // --- 4. HÀM XỬ LÝ: Lấy giá (Kiểm tra Cache Redis) ---
  const handleGetPrice = async () => {
    setIsPriceLoading(true);
    setPriceResult("Đang lấy giá...");

    const startTime = Date.now(); // Bắt đầu bấm giờ
    try {
      const response = await fetch(
        `${TRADE_SERVICE_URL}/api/v1/price/SOL-USDT`,
        { method: "GET" }
      );
      const data = await response.json();
      const endTime = Date.now(); // Dừng bấm giờ

      setPriceResult(
        `Giá: $${data.price}\nNguồn: ${data.source}\nThời gian: ${
          endTime - startTime
        } ms`
      );
    } catch (error) {
      console.error("Lỗi khi gọi Price service:", error);
      setPriceResult("Lỗi, không thể kết nối đến Price service.");
    }
    setIsPriceLoading(false);
  };

  // --- PHẦN RENDER GIAO DIỆN (JSX) ---
  return (
    <>
      <h1>Bảng điều khiển Crypto AI</h1>

      {/* --- Khu vực 1: WebSocket Price --- */}
      <section className="section">
        <h2>Giá Real-time (WebSocket)</h2>
        <p className={`price-status ${isConnected ? 'status-connected' : 'status-disconnected'}`}>
          Trạng thái: {isConnected ? "Đã kết nối" : "Mất kết nối"}
        </p>
        {price ? (
          <div className="price-display">
            {price.symbol}: ${price.price}
          </div>
        ) : (
          <p>Đang chờ dữ liệu...</p>
        )}
      </section>

      {/* --- Khu vực 2: AI Agent Chat (Mongo) --- */}
      <section className="section">
        <h2>Hỏi AI Agent (FastAPI - Port 8001)</h2>
        <form onSubmit={handleChatSubmit} className="input-group">
          <input
            type="text"
            className="input-text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Hỏi về thị trường (vd: phân tích btc)"
            disabled={isAiLoading}
          />
          <button type="submit" className="button" disabled={isAiLoading}>
            {isAiLoading ? "Đang xử lý..." : "Gửi"}
          </button>
        </form>
        {aiResponse && (
          <div className="result-box">
            <strong>AI trả lời:</strong>
            <pre>{aiResponse}</pre>
          </div>
        )}
      </section>

      {/* --- Khu vực 3: Auto Trading --- */}
      <section className="section">
        <h2>Thực thi Giao dịch (FastAPI - Port 8000)</h2>
        <button onClick={handleExecuteTrade} disabled={isTrading} className="button">
          {isTrading ? "Đang xử lý..." : "Thực hiện lệnh MUA 100$ SOL (Giả lập)"}
        </button>
        {tradeResult && (
          <div className="result-box">
            <strong>Kết quả giao dịch:</strong>
            <pre>{tradeResult}</pre>
          </div>
        )}
      </section>

      {/* --- Khu vực 4: Kiểm tra Cache Redis --- */}
      <section className="section">
        <h2>Kiểm tra Cache (Redis - Port 8000)</h2>
        <p style={{ fontSize: "0.9rem", color: "#555", marginBottom: "10px" }}>
          Bấm nút này. Lần đầu sẽ mất ~2 giây (API). Bấm lại ngay sau đó sẽ
          cực nhanh (Cache). Sau 10 giây, cache sẽ hết hạn và lại chậm.
        </p>
        <button onClick={handleGetPrice} disabled={isPriceLoading} className="button">
          {isPriceLoading ? "Đang lấy..." : "Lấy giá SOL-USDT"}
        </button>
        {priceResult && (
          <div className="result-box">
            <strong>Kết quả lấy giá:</strong>
            <pre>{priceResult}</pre>
          </div>
        )}
      </section>
    </>
  );
}