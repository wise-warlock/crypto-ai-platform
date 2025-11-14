from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os
import datetime
import httpx
from typing import Literal

# --- 1. Import (THAY ĐỔI: Thêm AIMessage) ---
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.tools.render import render_text_description
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel as LangchainBaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage # <-- THÊM AIMessage
from langgraph.graph import StateGraph, END 
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

# --- 2. Khởi tạo (Không đổi) ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
db = None
graph_app = None 
TRADING_SERVICE_URL = "http://trading-service:8000"

# --- 3. Định nghĩa CÔNG CỤ (Tools) ---
# (Toàn bộ các Tool 1, 2, 3, 4 đều giữ nguyên)

# --- Tool 1: Get SOL Price ---
@tool
async def get_sol_price() -> str:
    """
    Sử dụng công cụ này khi người dùng hỏi giá của SOL (SOL-USDT).
    Nó sẽ gọi đến service trading để lấy giá, có thể từ cache hoặc API.
    """
    print("AI Agent: Đang kích hoạt công cụ get_sol_price...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TRADING_SERVICE_URL}/api/v1/price/SOL-USDT")
            response.raise_for_status()
            data = response.json()
            return str(data) 
    except Exception as e:
        print(f"Lỗi khi gọi trading service: {e}")
        return "Lỗi: Không thể kết nối đến service trading."

# --- Tool 2: Get Pump.fun Info ---
class PumpFunInfoInput(LangchainBaseModel):
    contract_address: str = Field(description="Địa chỉ contract (mint address) của token trên Pump.fun.")
@tool(args_schema=PumpFunInfoInput)
async def get_pumpfun_coin_info(contract_address: str) -> str:
    """
    Sử dụng công cụ này khi người dùng hỏi thông tin chi tiết về một token
    trên Pump.fun, sử dụng địa chỉ contract của nó.
    """
    print(f"AI Agent: Đang kích hoạt công cụ get_pumpfun_coin_info cho {contract_address}...")
    try:
        async with httpx.AsyncClient() as client:
            url = f"{TRADING_SERVICE_URL}/api/v1/pumpfun/coin/{contract_address}"
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return str(data)
    except Exception as e:
        print(f"Lỗi khi gọi trading service (Pump.fun): {e}")
        return "Lỗi: Không thể lấy dữ liệu từ Pump.fun qua trading service."

# --- Tool 3: Create Token ---
class CreateTokenToolInput(LangchainBaseModel):
    """Input cho công cụ tạo token Pump.fun."""
    name: str = Field(description="Tên đầy đủ của token (ví dụ: 'My Super Token')")
    symbol: str = Field(description="Mã (symbol) của token (ví dụ: 'MST')")
    description: str = Field(description="Mô tả chi tiết về token.")
    twitter_url: str | None = Field(None, description="Đường link Twitter (nếu có).")
    telegram_url: str | None = Field(None, description="Đường link Telegram (nếu có).")
    website_url: str | None = Field(None, description="Đường link website (nếu có).")

@tool(args_schema=CreateTokenToolInput)
async def create_pumpfun_token_tool(
    name: str, 
    symbol: str, 
    description: str, 
    twitter_url: str = None, 
    telegram_url: str = None, 
    website_url: str = None
) -> str:
    """
    Sử dụng công cụ này khi người dùng yêu cầu TẠO MỘT TOKEN MỚI trên Pump.fun.
    Công cụ này yêu cầu đầy đủ: Tên, Mã (Symbol) và Mô tả.
    """
    print(f"AI Agent: Đang kích hoạt công cụ create_pumpfun_token_tool cho: {symbol}")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {"name": name, "symbol": symbol, "description": description, "twitter_url": twitter_url, "telegram_url": telegram_url, "website_url": website_url}
            response = await client.post(f"{TRADING_SERVICE_URL}/api/v1/pumpfun/create_token", json=payload)
            response.raise_for_status()
            data = response.json()
            return f"Tạo token THÀNH CÔNG: {data}"
    except Exception as e:
        print(f"Lỗi khi gọi trading service (Create Token): {e}")
        return f"Lỗi: Không thể thực hiện tạo token. Lỗi: {e}"

# --- Tool 4: Execute Swap ---
class ExecuteSwapToolInput(LangchainBaseModel):
    """Input cho công cụ thực thi swap (giao dịch)."""
    input_symbol: str = Field(description="Mã token bạn muốn BÁN. (Ví dụ: 'SOL', 'USDC')")
    output_symbol: str = Field(description="Mã token bạn muốn MUA. (Ví dụ: 'SOL', 'USDC')")
    amount: float = Field(description="Số lượng token BÁN (input_symbol) (Ví dụ: 10.5)")
    
@tool(args_schema=ExecuteSwapToolInput)
async def execute_swap_tool(input_symbol: str, output_symbol: str, amount: float) -> str:
    """
    Sử dụng công cụ này khi người dùng yêu cầu thực hiện MUA hoặc BÁN (SWAP)
    một token. (Ví dụ: 'Mua SOL bằng 10 USDC', 'Bán 0.5 SOL lấy USDC').
    """
    print(f"AI Agent: Đang kích hoạt execute_swap_tool: {amount} {input_symbol} -> {output_symbol}")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {"input_symbol": input_symbol.upper(), "output_symbol": output_symbol.upper(), "amount": amount}
            response = await client.post(f"{TRADING_SERVICE_URL}/api/v1/trade/execute", json=payload)
            response.raise_for_status() 
            data = response.json()
            return f"Thực thi SWAP THÀNH CÔNG: {data}"
    except Exception as e:
        print(f"Lỗi khi gọi trading service (Execute Swap): {e}")
        return f"Lỗi: Không thể thực hiện swap. Lỗi: {e}"

# --- Tập hợp các công cụ lại (Không đổi) ---
crypto_tools = [
    get_sol_price, 
    get_pumpfun_coin_info, 
    create_pumpfun_token_tool, 
    execute_swap_tool
]

# --- 4. Hàm create_agent (Không đổi) ---
def create_agent(llm, tools: list, system_prompt: str):
    tool_descriptions = render_text_description(tools)
    prompt_str = f"""
    {system_prompt}
    Bạn có các công cụ sau:
    {tool_descriptions}
    Câu hỏi của người dùng:
    {{input}}
    Lịch sử chat (nếu có):
    {{chat_history}}
    Các bước suy nghĩ:
    {{agent_scratchpad}}
    """
    prompt = ChatPromptTemplate.from_template(prompt_str)
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return executor

# --- 5. Các Node (Không đổi) ---
async def crypto_agent_node(state):
    print(">>> ĐANG GỌI CHUYÊN GIA CRYPTO")
    # (Hàm này lấy 'chat_history' từ state, nên không cần sửa)
    last_message = state['messages'][-1]
    response = await crypto_agent_executor.ainvoke({
        "input": last_message.content,
        "chat_history": state['messages'][:-1] 
    })
    return {"messages": [HumanMessage(content=response["output"], name="CryptoAgent")]}

async def general_agent_node(state):
    print(">>> ĐANG GỌI CHUYÊN GIA CHAT CHUNG")
    # (Hàm này lấy 'chat_history' từ state, nên không cần sửa)
    last_message = state['messages'][-1]
    response = await general_agent_executor.ainvoke({
        "input": last_message.content,
        "chat_history": state['messages'][:-1]
    })
    return {"messages": [HumanMessage(content=response["output"], name="GeneralAgent")]}

# --- Node 3: Bộ định tuyến (MANAGER) (Không đổi) ---
class RouterSchema(LangchainBaseModel):
    """Quyết định định tuyến (route) câu hỏi của người dùng đến chuyên gia phù hợp."""
    destination: Literal["crypto_tools", "general_chat"] = Field(
        description=(
            "Chọn 'crypto_tools' nếu câu hỏi liên quan đến: "
            "1. Giá coin (giá SOL). "
            "2. Thông tin token (Pump.fun). "
            "3. Yêu cầu TẠO TOKEN MỚI. "
            "4. Yêu cầu THỰC THI GIAO DỊCH (Mua, Bán, Swap). "
            "Chọn 'general_chat' cho các câu hỏi chào hỏi, hỏi thăm thông thường."
        )
    )

async def router_node(state):
    print(">>> ĐANG GỌI MANAGER (ROUTER)")
    llm_with_tools = llm.with_structured_output(RouterSchema)
    prompt = f"""
    Bạn là một AI quản lý (Manager). Nhiệm vụ của bạn là phân loại câu hỏi của người dùng
    và chuyển nó cho đúng chuyên gia.
    
    Các chuyên gia:
    - crypto_tools: Trả lời câu hỏi về giá, thông tin token, TẠO TOKEN, và THỰC THI SWAP.
    - general_chat: Trả lời câu hỏi chào hỏi, hỏi thăm (ví dụ: 'chào bạn', 'bạn là ai?').
    
    Câu hỏi cuối cùng của người dùng (và lịch sử nếu có):
    {state['messages']}
    """
    route_decision = await llm_with_tools.ainvoke(prompt)
    print(f">>> QUYẾT ĐỊNH CỦA MANAGER: {route_decision.destination}")
    if route_decision.destination == "crypto_tools":
        return "crypto_tools"
    else:
        return "general_chat"

# --- 6. Định nghĩa State và Graph (Không đổi) ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
crypto_agent_executor = create_agent(
    llm, crypto_tools, 
    "Bạn là chuyên gia Crypto, chuyên về Solana, Pump.fun, và có khả năng TẠO TOKEN cũng như THỰC HIỆN SWAP."
)
general_agent_executor = create_agent(
    llm, [], 
    "Bạn là một trợ lý AI thân thiện, trả lời các câu hỏi chung (không phải crypto)."
)
workflow = StateGraph(AgentState)
workflow.add_node("router", router_node) 
workflow.add_node("crypto_tools", crypto_agent_node) 
workflow.add_node("general_chat", general_agent_node) 
workflow.set_entry_point("router")
workflow.add_conditional_edges("router", router_node, {"crypto_tools": "crypto_tools", "general_chat": "general_chat"})
workflow.add_edge("crypto_tools", END)
workflow.add_edge("general_chat", END)
try:
    graph_app = workflow.compile()
    print("Đã biên dịch Graph (Manager-Agent) thành công!")
except Exception as e:
    print(f"Lỗi khi biên dịch Graph: {e}")

# --- 7. FastAPI Startup (Không đổi) ---
app = FastAPI(title="AI Agent Service (Manager-Agent Architecture)")
@app.on_event("startup")
def startup_app():
    global db
    try:
        client = MongoClient(MONGO_URI)
        db = client["crypto_ai_platform"]
        print("Đã kết nối thành công đến MongoDB!")
    except Exception as e:
        print(f"Lỗi khi kết nối MongoDB: {e}")
    if not OPENAI_API_KEY:
        print("LỖI: OPENAI_API_KEY chưa được thiết lập!")
        return
    if graph_app is None:
        print("LỖI: Graph (Bộ não AI) chưa được biên dịch!")
    else:
        print("AI Agent Service (Manager-Agent) đã sẵn sàng!")

# --- 8. CORS (Không đổi) ---
origins = ["http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ChatPrompt(BaseModel):
    user_id: str
    prompt: str

# --- 9. Endpoint (THAY ĐỔI: TẢI LỊCH SỬ CHAT TỪ DB) ---
@app.post("/api/v1/agent/chat")
async def handle_chat(payload: ChatPrompt):
    print(f"Graph nhận prompt: {payload.prompt} từ user: {payload.user_id}")
    
    if graph_app is None or db is None:
        return {"user_id": payload.user_id, "response": "LỖI: AI Graph hoặc CSDL chưa được khởi tạo."}

    # --- ĐÂY LÀ LOGIC THÊM TRÍ NHỚ ---
    chat_history_messages = []
    try:
        # 1. Lấy 10 tin nhắn gần nhất (5 cặp hỏi-đáp)
        history_cursor = db.chat_history.find(
            {"user_id": payload.user_id}
        ).sort("timestamp", -1).limit(10)
        
        # 2. Chuyển đổi DB records -> Langchain Messages
        # (Lưu ý: Phải lặp ngược `reversed` để đưa tin nhắn cũ nhất vào trước)
        db_records = list(history_cursor)
        for doc in reversed(db_records):
            chat_history_messages.append(HumanMessage(content=doc["prompt"]))
            chat_history_messages.append(AIMessage(content=doc["response"]))
        
        print(f" - Đã tải {len(chat_history_messages)} tin nhắn từ lịch sử.")

    except Exception as e:
        print(f"Lỗi khi tải lịch sử chat từ MongoDB: {e}")
        # Không làm gián đoạn, tiếp tục với lịch sử rỗng

    # 3. Thêm tin nhắn MỚI của người dùng vào cuối
    chat_history_messages.append(HumanMessage(content=payload.prompt))
    
    # 4. Tạo input cho Graph
    inputs = {"messages": chat_history_messages}
    # --- KẾT THÚC LOGIC TRÍ NHỚ ---

    try:
        # Gọi Graph với đầy đủ lịch sử
        response = await graph_app.ainvoke(inputs)
        
        # Lấy tin nhắn cuối cùng (là câu trả lời của AI)
        response_text = response["messages"][-1].content

    except Exception as e:
        print(f"Lỗi trong khi Graph thực thi: {e}")
        response_text = "Xin lỗi, đã có lỗi xảy ra trong quá trình suy nghĩ (Graph Error)."

    # --- LƯU VÀO MONGODB (Không đổi) ---
    # (Lưu lại cặp hỏi-đáp MỚI NHẤT này)
    if db is not None:
        try:
            chat_record = {
                "user_id": payload.user_id,
                "prompt": payload.prompt, # Câu hỏi của người dùng
                "response": response_text, # Câu trả lời của AI
                "timestamp": datetime.datetime.now(datetime.timezone.utc)
            }
            db.chat_history.insert_one(chat_record)
            print("Đã lưu chat (từ Agent) vào MongoDB.")
        except Exception as e:
            print(f"Lỗi khi lưu vào MongoDB: {e}")

    return {"user_id": payload.user_id, "response": response_text}

# Endpoint kiểm tra CSDL (Không đổi)
@app.get("/api/v1/agent/history")
async def get_chat_history():
    if db is None:
        return {"error": "CSDL chưa kết nối"}
    history = []
    # (Tăng limit lên 20 để xem được nhiều hơn)
    cursor = db.chat_history.find().sort("timestamp", -1).limit(20)
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        history.append(doc)
    return history