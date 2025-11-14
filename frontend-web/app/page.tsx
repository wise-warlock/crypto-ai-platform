// frontend-web/app/page.tsx

"use client"; 

import { useState, useEffect } from "react";
import io, { Socket } from "socket.io-client";

// --- URL (Không đổi) ---
const SOCKET_URL = "http://localhost:8002";
const AI_SERVICE_URL = "http://localhost:8001";
const TRADE_SERVICE_URL = "http://localhost:8000";

// ... (Interface PriceData không đổi) ...
interface PriceData {
  symbol: string;
  price: string;
}

export default function Home() {
  // --- States (Không đổi) ---
  const [price, setPrice] = useState<PriceData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [aiResponse, setAiResponse] = useState(""); 
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [tradeResult, setTradeResult] = useState(""); 
  const [isTrading, setIsTrading] = useState(false); 
  const [priceResult, setPriceResult] = useState("");
  const [isPriceLoading, setIsPriceLoading] = useState(false);

  // --- 1. WebSocket (Không đổi) ---
  useEffect(() => {
    // ... (Giữ nguyên code)
    const socket: Socket = io(SOCKET_URL);
    socket.on("connect", () => setIsConnected(true));
    socket.on("disconnect", () => setIsConnected(false));
    socket.on("price-update", (data: PriceData) => {
      setPrice(data); 
    });
    return () => {
      socket.disconnect();
    };
  }, []); 

  // --- 2. AI Chat (Không đổi) ---
  const handleChatSubmit = async (e: React.FormEvent) => {
    // ... (Giữ nguyên code)
    e.preventDefault(); 
    if (!prompt) return; 
    setIsAiLoading(true);
    setAiResponse("");
    try {
      const response = await fetch(`${AI_SERVICE_URL}/api/v1/agent/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "user_001", prompt: prompt }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setAiResponse(data.response); 
    } catch (error) {
      console.error("Lỗi khi gọi AI service:", error);
      setAiResponse("Lỗi: Không thể kết nối hoặc xử lý yêu cầu đến AI service.");
    } finally {
      setIsAiLoading(false); 
    }
  };

  // --- 3. HÀM NÂNG CẤP: GỌI AUTO-TRADING THẬT ---
  const handleExecuteTrade = async () => {
    setIsTrading(true);
    setTradeResult("Đang gửi lệnh SWAP (5 USDC -> SOL)...");
    try {
      // --- THAY ĐỔI PAYLOAD ---
      // Định nghĩa một lệnh swap thật (Đổi 5 USDC lấy SOL)
      const order = {
        input_symbol: "USDC",
        output_symbol: "SOL",
        amount: 5.0, // Swap 5 USDC
        slippage_bps: 50
      };

      const response = await fetch(`${TRADE_SERVICE_URL}/api/v1/trade/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(order),
      });

      const data = await response.json(); // Lấy data kể cả khi lỗi

      if (!response.ok) {
        // Nếu lỗi, hiển thị lỗi từ server
        throw new Error(data.detail || `HTTP error! status: ${response.status}`);
      }

      // Nếu thành công, hiển thị kết quả
      setTradeResult(
        `Trạng thái: ${data.status}\nMessage: ${data.message}\n` +
        `Input: ${data.input_amount} ${data.input_token}\n` +
        `Output (Dự kiến): ${data.output_amount_prediction} ${data.output_token}\n` +
        `TX ID: ${data.tx_id}`
      );
      
    } catch (error: any) {
      console.error("Lỗi khi gọi Trading service:", error);
      setTradeResult(`Lỗi: ${error.message || "Không thể kết nối Trading service."}`);
    } finally {
      setIsTrading(false); // Luôn tắt loading
    }
  };

  // --- 4. Lấy giá (Không đổi) ---
  const handleGetPrice = async () => {
    // ... (Giữ nguyên code)
    setIsPriceLoading(true);
    setPriceResult("Đang lấy giá...");
    const startTime = Date.now(); 
    try {
      const response = await fetch(`${TRADE_SERVICE_URL}/api/v1/price/SOL-USDT`, { method: "GET" });
      const endTime = Date.now();
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Lỗi không xác định từ API");
      }
      setPriceResult(
        `Giá: $${data.price}\nNguồn: ${data.source}\nThời gian: ${endTime - startTime} ms`
      );
    } catch (error: any) { 
      console.error("Lỗi khi gọi Price service:", error);
      setPriceResult(`Lỗi: ${error.message || "Không thể kết nối đến Price service."}`);
    }
    setIsPriceLoading(false);
  };

  // --- PHẦN RENDER GIAO DIỆN (THAY ĐỔI) ---
  return (
    <>
      <h1>Bảng điều khiển Crypto AI</h1>

      {/* --- Khu vực 1 (Không đổi) --- */}
      <section className="section">
        {/* ... (Giữ nguyên code) ... */}
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

      {/* --- Khu vực 2 (Không đổi) --- */}
      <section className="section">
        {/* ... (Giữ nguyên code) ... */}
        <h2>Hỏi AI Agent (FastAPI - Port 8001)</h2>
        <form onSubmit={handleChatSubmit} className="input-group">
          <input
            type="text"
            className="input-text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Hỏi về thị trường (vd: swap 0.1 SOL lấy USDC)"
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

      {/* --- Khu vực 3 (THAY ĐỔI TEXT NÚT BẤM) --- */}
      <section className="section">
        <h2>Thực thi Giao dịch (FastAPI - Port 8000)</h2>
        <button onClick={handleExecuteTrade} disabled={isTrading} className="button">
          {isTrading ? "Đang xử lý..." : "Thực hiện lệnh SWAP 5 USDC lấy SOL (Thật)"}
        </button>
        {tradeResult && (
          <div className="result-box">
            <strong>Kết quả giao dịch:</strong>
            <pre>{tradeResult}</pre>
          </div>
        )}
      </section>

      {/* --- Khu vực 4 (Không đổi) --- */}
      <section className="section">
        {/* ... (Giữ nguyên code) ... */}
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