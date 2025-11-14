from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import redis
import os
import httpx
import time
import base64 # <-- 1. THÊM IMPORT

# --- Import Solana (Không đổi) ---
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.transaction import VersionedTransaction # <-- 2. THÊM IMPORT
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Confirmed
from spl.token.constants import TOKEN_PROGRAM_ID
import based58 

# --- 3. Đọc Biến môi trường (Không đổi) ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
CREATOR_PRIVATE_KEY_B58 = os.getenv("CREATOR_PRIVATE_KEY") 

# --- 4. Biến toàn cục & Khởi tạo (Không đổi) ---
redis_client = None
http_client = None
solana_client = None 
creator_keypair = None 
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# --- 5. Định nghĩa các địa chỉ (Pump.fun) (Không đổi) ---
PUMP_PROGRAM_ID = Pubkey.from_string("6EF8rrecthR5DkVZW8NMCnwtd39Sjfu9mt33KjkkvM6r")
PUMP_FEE_RECIPIENT = Pubkey.from_string("CebN5WGQ4it1pStoaKjUsS1YrtMQS8SDEhwRVMKwvXCW")
# ... (các địa chỉ khác không đổi)

# --- 6. THÊM HẰNG SỐ CHO JUPITER SWAP ---
# Địa chỉ Mint của các token phổ biến
MINT_ADDRESSES = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xcoVTjcDc1P2VRA",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
}
# Số thập phân của các token
DECIMALS = {
    "SOL": 9,
    "USDC": 6,
    "USDT": 6,
    "BONK": 5,
    "WIF": 6,
}
# API của Jupiter (V6)
JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"

# --- 7. Sự kiện Startup/Shutdown (Không đổi) ---
app = FastAPI(title="Auto Trading Service (Với Pump.fun & Jupiter Swap)")

@app.on_event("startup")
def startup_app():
    # ... (Toàn bộ hàm startup không đổi)
    global redis_client, http_client, solana_client, creator_keypair
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
        redis_client.ping()
        print("Đã kết nối thành công đến Redis!")
    except Exception as e:
        print(f"Lỗi khi kết nối Redis: {e}")
    http_client = httpx.AsyncClient(timeout=10.0)
    print("Đã khởi tạo HTTPX Client.")
    try:
        solana_client = Client(SOLANA_RPC_URL)
        print(f"Đã kết nối Solana RPC: {SOLANA_RPC_URL}")
        if not CREATOR_PRIVATE_KEY_B58:
            raise Exception("CREATOR_PRIVATE_KEY chưa được thiết lập!")
        private_key_bytes = based58.b58decode(CREATOR_PRIVATE_KEY_B58)
        creator_keypair = Keypair.from_bytes(private_key_bytes)
        print(f"Đã tải ví người tạo (Creator): {creator_keypair.pubkey()}")
    except Exception as e:
        print(f"LỖI NGHIÊM TRỌNG khi khởi tạo Solana hoặc Private Key: {e}")

@app.on_event("shutdown")
async def shutdown_app():
    if http_client:
        await http_client.acclose()
        print("Đã đóng HTTPX Client.")

# --- 8. Cấu hình CORS (Không đổi) ---
origins = ["http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- 9. Mô hình Pydantic (THAY ĐỔI) ---

# ĐỊNH NGHĨA LẠI TRADEORDER CHO RÕ RÀNG
class TradeOrder(BaseModel):
    # user_id: str (Bỏ qua, vì chúng ta dùng ví 'creator' chung)
    input_symbol: str   # Ví dụ: "USDC"
    output_symbol: str  # Ví dụ: "SOL"
    amount: float       # Số lượng (ví dụ: 10.5) -> nghĩa là 10.5 USDC
    slippage_bps: int = 50 # 50 bps = 0.5%

class CreateTokenInput(BaseModel): # (Không đổi)
    name: str
    symbol: str
    description: str
    twitter_url: str | None = None
    telegram_url: str | None = None
    website_url: str | None = None

# --- 10. Các Endpoints Get Price/Info (Không đổi) ---
# (Hàm get_price_from_jupiter_api, get_cached_price, get_pumpfun_coin_data không đổi)
# ... (Giữ nguyên 3 hàm này) ...
async def get_price_from_jupiter_api(symbol: str): 
    print(f"ĐANG GỌI API JUPITER... cho {symbol}")
    base, quote = symbol.split('-')
    url = f"https://price.jup.ag/v4/price?ids={base}&vsToken={quote}"
    try:
        if not http_client:
            raise Exception("HTTP Client chưa được khởi tạo")
        response = await http_client.get(url)
        response.raise_for_status() 
        data = response.json()
        price = data.get("data", {}).get(base, {}).get("price")
        if price is None:
            return None 
        return round(price, 6)
    except Exception as e:
        print(f"Lỗi khi gọi API Jupiter: {e}")
        return None

@app.get("/api/v1/price/{symbol}") 
async def get_cached_price(symbol: str):
    if redis_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis chưa kết nối.")
    cache_key = f"price:{symbol}"
    cached_price = redis_client.get(cache_key)
    if cached_price:
        return {"symbol": symbol, "price": cached_price, "source": "Cache (Redis)"}
    price = await get_price_from_jupiter_api(symbol) 
    if price is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Không thể lấy giá từ API Jupiter.")
    redis_client.set(cache_key, price, ex=10) 
    return {"symbol": symbol, "price": price, "source": "API (Jupiter)"}

@app.get("/api/v1/pumpfun/coin/{contract_address}") 
async def get_pumpfun_coin_data(contract_address: str):
    url = f"https://frontend-api.pump.fun/coins/{contract_address}"
    try:
        if not http_client:
            raise Exception("HTTP Client chưa được khởi tạo")
        headers = {"User-Agent": "Mozilla/5.0"}
        response = await http_client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        filtered_data = {
            "name": data.get("name"), "symbol": data.get("symbol"),
            "description": data.get("description"), "market_cap_usd": data.get("market_cap"),
            "contract_address": data.get("mint")
        }
        return filtered_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Không thể lấy dữ liệu từ Pump.fun: {e}")

# --- 11. Endpoint Create Token (Không đổi) ---
@app.post("/api/v1/pumpfun/create_token")
async def create_pumpfun_token(token_input: CreateTokenInput):
    # ... (Toàn bộ hàm create_pumpfun_token không đổi)
    # (Hãy giữ nguyên logic hàm tạo token bạn đã có)
    pass # (Bạn hãy dán code hàm create_token của bạn vào đây)


# --- 12. ENDPOINT NÂNG CẤP: THỰC THI SWAP (JUPITER) ---
@app.post("/api/v1/trade/execute")
async def execute_trade(order: TradeOrder):
    """
    THỰC THI SWAP THẬT (Thay thế hàm mock).
    Sử dụng Jupiter V6 API (Quote -> Swap -> Send).
    """
    global solana_client, http_client, creator_keypair
    
    if solana_client is None or http_client is None or creator_keypair is None:
        raise HTTPException(status_code=503, detail="Service chưa sẵn sàng (Solana/HTTP).")

    try:
        print(f"Nhận lệnh Swap: {order.amount} {order.input_symbol} -> {order.output_symbol}")
        
        # 1. Lấy địa chỉ Mint và Decimals
        input_mint = MINT_ADDRESSES.get(order.input_symbol.upper())
        output_mint = MINT_ADDRESSES.get(order.output_symbol.upper())
        input_decimals = DECIMALS.get(order.input_symbol.upper())
        
        if not input_mint or not output_mint or not input_decimals:
            raise HTTPException(status_code=400, detail="Token symbol không được hỗ trợ.")

        # 2. Chuyển đổi số lượng sang đơn vị nhỏ nhất (Lamports)
        amount_in_smallest_unit = int(order.amount * (10**input_decimals))

        # --- BƯỚC 1: LẤY QUOTE ---
        print(" - (1/3) Đang lấy Quote từ Jupiter...")
        quote_params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount_in_smallest_unit,
            "slippageBps": order.slippage_bps
        }
        quote_response = await http_client.get(JUPITER_QUOTE_API, params=quote_params)
        quote_response.raise_for_status()
        quote_data = quote_response.json()
        print(f" - Quote nhận được: {quote_data.get('outAmount')} {order.output_symbol}")

        # --- BƯỚC 2: LẤY GIAO DỊCH SWAP ---
        print(" - (2/3) Đang lấy Transaction Swap từ Jupiter...")
        swap_payload = {
            "quoteResponse": quote_data,
            "userPublicKey": str(creator_keypair.pubkey()),
            "wrapAndUnwrapSol": True, # Tự động wrap/unwrap SOL
            "computeUnitPriceMicroLamports": 300_000 # Phí ưu tiên
        }
        swap_response = await http_client.post(JUPITER_SWAP_API, json=swap_payload)
        swap_response.raise_for_status()
        
        # Lấy chuỗi base64 của giao dịch
        swap_tx_b64 = swap_response.json()['swapTransaction']

        # --- BƯỚC 3: KÝ VÀ GỬI GIAO DỊCH ---
        print(" - (3/3) Đang ký và gửi Transaction...")
        
        # Decode base64
        raw_tx_bytes = base64.b64decode(swap_tx_b64)
        # Deserialize thành VersionedTransaction
        tx = VersionedTransaction.from_bytes(raw_tx_bytes)
        
        # Ký giao dịch bằng Private Key của bạn
        tx.sign([creator_keypair])
        
        # Gửi giao dịch
        opts = TxOpts(skip_preflight=True, preflight_commitment=Confirmed)
        tx_sig = solana_client.send_transaction(tx, opts=opts).value
        
        print(f" - GIAO DỊCH SWAP THÀNH CÔNG! Signature: {tx_sig}")

        return {
            "status": "success",
            "message": "Swap đã được thực thi thành công!",
            "input_token": order.input_symbol,
            "output_token": order.output_symbol,
            "input_amount": order.amount,
            "output_amount_prediction": int(quote_data.get('outAmount')) / (10**DECIMALS.get(order.output_symbol.upper(), 6)),
            "tx_id": str(tx_sig)
        }

    except Exception as e:
        print(f"LỖI trong quá trình Swap: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi thực thi swap: {e}"
        )