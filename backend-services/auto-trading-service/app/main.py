from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import redis # <-- 1. Import redis
import os
import time
import random

# --- 1. Đọc biến môi trường ---
# Dùng "redis" làm host vì đó là tên service trong docker-compose
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

# --- 2. Biến toàn cục cho Redis ---
redis_client = None

# --- 3. Sự kiện Startup: Kết nối Redis ---
app = FastAPI(title="Auto Trading Service")

@app.on_event("startup")
def startup_redis_client():
    global redis_client
    try:
        # Tạo kết nối đến Redis
        redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
        # Kiểm tra kết nối
        redis_client.ping()
        print("Đã kết nối thành công đến Redis!")
    except Exception as e:
        print(f"Lỗi khi kết nối Redis: {e}")

# --- 4. Cấu hình CORS (như cũ) ---
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mô hình Pydantic (như cũ) ---
class TradeOrder(BaseModel):
    user_id: str
    action: str
    symbol: str
    amount_usd: float

# --- 5. HÀM MỚI: Lấy giá (với logic cache) ---

def get_price_from_jupiter_api(symbol: str):
    # GIẢ LẬP việc gọi API sàn (mất 2 giây)
    print(f"ĐANG GỌI API JUPITER CHẬM... cho {symbol}")
    time.sleep(2) # Giả lập độ trễ
    price = round(random.uniform(150.0, 160.0), 4)
    return price

@app.get("/api/v1/price/{symbol}")
async def get_cached_price(symbol: str):
    """
    Endpoint mới để lấy giá, có áp dụng cache.
    """
    if redis_client is None:
        return {"error": "Redis chưa kết nối"}

    # 1. Tạo một "key" (khóa) cho cache
    cache_key = f"price:{symbol}"

    # 2. KIỂM TRA CACHE TRƯỚC
    cached_price = redis_client.get(cache_key)
    
    if cached_price:
        print(f"HIT CACHE: Lấy giá {symbol} từ Redis.")
        return {"symbol": symbol, "price": cached_price, "source": "Cache (Redis)"}

    # 3. NẾU KHÔNG CÓ CACHE (Cache miss)
    print(f"MISS CACHE: Lấy giá {symbol} từ API...")
    # Gọi API thật (giả lập)
    price = get_price_from_jupiter_api(symbol)
    
    # 4. LƯU VÀO CACHE
    # Lưu giá vào Redis và tự động xóa sau 10 giây (EX=10)
    redis_client.set(cache_key, price, ex=10)
    
    return {"symbol": symbol, "price": price, "source": "API (Jupiter)"}


# --- 6. Endpoint execute_trade (như cũ) ---
@app.post("/api/v1/trade/execute")
async def execute_trade(order: TradeOrder):
    """
    GIẢ LẬP thực hiện giao dịch.
    """
    print(f"Executing order: {order.dict()}")
    
    return {
        "status": "success",
        "tx_id": f"mock_tx_12345_{order.symbol}",
        "message": "Lệnh giao dịch giả lập đã được thực thi thành công."
    }