from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os
import datetime
import httpx  # Cần httpx để gọi service khác

# --- 1. Import các thư viện Langchain ---
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# --- 2. Đọc Biến môi trường ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- 3. Khởi tạo CSDL & LLM ---
db = None
agent_executor = None  # Đây sẽ là "bộ não" AI của chúng ta

# URL của service trading (giao tiếp nội bộ trong Docker)
TRADING_SERVICE_URL = "http://trading-service:8000"

# --- 4. Định nghĩa CÔNG CỤ (Tools) cho Agent ---
# Đây là những "khả năng" mà AI của chúng ta có thể làm

@tool
async def get_sol_price() -> str:
    """
    Sử dụng công cụ này khi người dùng hỏi giá của SOL.
    Nó sẽ gọi đến service trading để lấy giá, có thể từ cache hoặc API.
    """
    print("AI Agent: Đang kích hoạt công cụ get_sol_price...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TRADING_SERVICE_URL}/api/v1/price/SOL-USDT")
            response.raise_for_status()
            data = response.json()
            # Trả về JSON dưới dạng string để AI có thể đọc
            return str(data) 
    except Exception as e:
        print(f"Lỗi khi gọi trading service: {e}")
        return "Lỗi: Không thể kết nối đến service trading."

@tool
async def get_btc_analysis() -> str:
    """
    Sử dụng công cụ này khi người dùng hỏi phân tích về BTC (Bitcoin).
    """
    print("AI Agent: Đang kích hoạt công cụ get_btc_analysis...")
    return "Phân tích giả lập: BTC có vẻ đang ở vùng hỗ trợ mạnh. Cân nhắc quan sát thêm."

# Tập hợp các công cụ lại
tools = [get_sol_price, get_btc_analysis]

# --- 5. Khởi tạo Agent (Hàm Startup) ---
app = FastAPI(title="AI Agent Service")

@app.on_event("startup")
def startup_app():
    global db, agent_executor
    
    # Kết nối Mongo (như cũ)
    try:
        client = MongoClient(MONGO_URI)
        db = client["crypto_ai_platform"]
        print("Đã kết nối thành công đến MongoDB!")
    except Exception as e:
        print(f"Lỗi khi kết nối MongoDB: {e}")

    # Khởi tạo "Bộ não" Agent
    if not OPENAI_API_KEY:
        print("LỖI: OPENAI_API_KEY chưa được thiết lập!")
        return

    try:
        # 1. Định nghĩa LLM (Bạn có thể thay bằng ChatAnthropic nếu dùng Claude)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # 2. Định nghĩa Prompt (câu lệnh cho AI)
        # Đây là "linh hồn" của con AI
        prompt_template = """
        Bạn là một AI Agent trợ lý crypto.
        Bạn có thể trả lời các câu hỏi và thực hiện các tác vụ.
        Bạn có các công cụ sau để sử dụng:

        {tools}

        Hãy suy nghĩ cẩn thận và sử dụng công cụ nếu cần thiết.
        Nếu bạn dùng công cụ, hãy nói cho người dùng biết kết quả từ công cụ đó.
        
        Đây là cuộc trò chuyện (nếu có):
        {chat_history}
        
        Câu hỏi của người dùng:
        {input}
        
        Các bước suy nghĩ và quyết định của bạn:
        {agent_scratchpad}
        """
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # 3. Tạo Agent
        agent = create_tool_calling_agent(llm, tools, prompt)
        
        # 4. Tạo "Người thực thi" (Agent Executor)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        print("Đã khởi tạo AI Agent Executor thành công!")
        
    except Exception as e:
        print(f"Lỗi khi khởi tạo Agent Executor: {e}")


# --- 6. Cấu hình CORS (như cũ) ---
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mô hình Pydantic (như cũ) ---
class ChatPrompt(BaseModel):
    user_id: str
    prompt: str

# --- 7. Cập nhật Endpoint (Đã "thay não") ---
@app.post("/api/v1/agent/chat")
async def handle_chat(payload: ChatPrompt):
    """
    Sử dụng AI Agent (Langchain) để trả lời.
    """
    print(f"Agent nhận prompt: {payload.prompt}")
    
    if agent_executor is None:
        return {"user_id": payload.user_id, "response": "LỖI: AI Agent chưa được khởi tạo. Vui lòng kiểm tra OPENAI_API_KEY."}

    try:
        # --- ĐÂY LÀ LÚC GỌI "BỘ NÃO" ---
        # Chúng ta sẽ thêm lịch sử chat (tạm thời để rỗng)
        response = await agent_executor.ainvoke({
            "input": payload.prompt,
            "chat_history": [] 
        })
        
        response_text = response["output"]

    except Exception as e:
        print(f"Lỗi trong khi Agent thực thi: {e}")
        response_text = "Xin lỗi, đã có lỗi xảy ra trong quá trình suy nghĩ."

    # --- LƯU VÀO MONGODB (như cũ) ---
    if db is not None:
        try:
            chat_record = {
                "user_id": payload.user_id,
                "prompt": payload.prompt,
                "response": response_text,
                "timestamp": datetime.datetime.now(datetime.timezone.utc)
            }
            db.chat_history.insert_one(chat_record)
            print("Đã lưu chat (từ Agent) vào MongoDB.")
        except Exception as e:
            print(f"Lỗi khi lưu vào MongoDB: {e}")

    return {"user_id": payload.user_id, "response": response_text}

# Endpoint kiểm tra CSDL (như cũ, không đổi)
@app.get("/api/v1/agent/history")
async def get_chat_history():
    if db is None:
        return {"error": "CSDL chưa kết nối"}
    history = []
    cursor = db.chat_history.find().sort("timestamp", -1).limit(5)
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        history.append(doc)
    return history