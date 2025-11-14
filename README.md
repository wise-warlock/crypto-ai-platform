# 🤖 Crypto AI Platform

**Xây dựng website ứng dụng AI Agents và LLMs trong Phân tích và Giao dịch Crypto**

-----

## 1\. 🚀 Giới thiệu

**Crypto AI Platform** là một nền tảng web hoàn chỉnh sử dụng kiến trúc microservice để ứng dụng các Mô hình Ngôn ngữ Lớn (LLMs) vào việc phân tích và thực thi giao dịch trên blockchain Solana.

Dự án này vượt qua mô hình AI "chỉ để chat" (if-else), thay vào đó triển khai một **kiến trúc AI Manager-Agent (Langgraph)** tiên tiến. "Agent Quản lý" có khả năng phân tích câu hỏi của người dùng và giao nhiệm vụ cho các "Agent Chuyên gia" (Worker) được trang bị các công cụ (Tools) để tương tác trực tiếp với on-chain (Solana).

Nền tảng này có thể:

  * Phân tích giá và thông tin token (Jupiter, Pump.fun).
  * **Thực thi giao dịch** (Swap) qua Jupiter API.
  * **Tạo token mới** trực tiếp trên Pump.fun.

## 2\. 💡 Ứng dụng & Tính năng chính

Dự án này là một ví dụ điển hình cho thế hệ ứng dụng Web3-AI, nơi AI không chỉ cung cấp thông tin mà còn có thể thay mặt người dùng thực hiện các hành động on-chain một cách thông minh.

### Các tính năng cốt lõi:

  * **Kiến trúc Microservice:** Toàn bộ hệ thống được đóng gói bằng Docker và điều phối bởi `docker-compose.yml`, bao gồm:
      * `frontend-web` (Next.js)
      * `ai-service` (Python - FastAPI, Langgraph)
      * `trading-service` (Python - FastAPI, Solana SDK)
      * `websocket-service` (Node.js - Socket.io)
      * `mongo` (Database)
      * `redis` (Cache)
  * **Giao diện Real-time:** Dashboard (Next.js) hiển thị giá SOL-USDT theo thời gian thực, được phát từ `websocket-service` (dữ liệu được lấy từ `trading-service`).
  * **AI Manager-Agent (Langgraph):**
      * Sử dụng một "Agent Quản lý" (Router) để phân loại ý định của người dùng.
      * Tự động điều hướng câu hỏi đến "Agent Chat chung" (để chào hỏi) hoặc "Agent Crypto" (để thực thi nghiệp vụ).
  * **Trí nhớ (MongoDB):** AI Agent có khả năng ghi nhớ lịch sử hội thoại. Nó sẽ tải 10 tin nhắn gần nhất từ MongoDB để hiểu bối cảnh của câu hỏi tiếp theo (ví dụ: "Mua 0.1 đồng đó" -\> AI hiểu "đồng đó" là SOL từ câu chat trước).
  * **Hệ thống Tools (Công cụ AI):**
    1.  **Get Price:** Lấy giá token (Jupiter API) và lưu cache bằng Redis.
    2.  **Get Token Info:** Lấy thông tin chi tiết token từ Pump.fun.
    3.  **Execute Swap:** **(Tính năng cao cấp)** Thực thi lệnh Mua/Bán (Swap) token thật trên Solana thông qua Jupiter Swap API (V6).
    4.  **Create Token:** **(Tính năng cao cấp)** Tạo một token SPL mới trên Pump.fun (bao gồm tên, mã, mô tả, socials) chỉ bằng một câu lệnh chat.

## 3\. 🛠️ Hướng dẫn Cài đặt & Khởi chạy

Dự án này được thiết kế để chạy hoàn toàn bằng Docker. Bạn không cần cài đặt Python, Node.js hay MongoDB trên máy cá nhân.

### Yêu cầu tiên quyết

  * [Docker](https://www.docker.com/products/docker-desktop/)
  * [Git](https://www.google.com/search?q=https://git-scm.com/downloads)

-----

### Bước 1: Clone dự án

```bash
git clone [URL_REPO_CUA_BAN]
cd crypto-ai-platform
```

-----

### Bước 2: (QUAN TRỌNG NHẤT) Cấu hình Biến môi trường

Các "chìa khóa" bí mật (API key, Private key) được quản lý trong tệp `.env` để đảm bảo an toàn.

1.  Tại thư mục gốc của dự án (ngang hàng với `docker-compose.yml`), hãy tạo một tệp mới tên là `.env`.

2.  Sao chép nội dung dưới đây và dán vào tệp `.env` của bạn:

    ```bash
    # Biến môi trường cho AI Service (Port 8001)
    # Thay bằng API Key của bạn
    OPENAI_API_KEY="sk-..."

    # Biến môi trường cho Trading Service (Port 8000)
    # (Đây là Private Key (Base58) của ví sẽ thực hiện giao dịch)
    CREATOR_PRIVATE_KEY="YOUR_WALLET_PRIVATE_KEY_B58_HERE"
    ```

3.  **Cảnh báo bảo mật:**

      * Tệp `.env` đã được thêm vào `.gitignore` để tránh bị đưa lên Git.
      * **TUYỆT ĐỐI** không sử dụng ví chính của bạn. Hãy tạo một ví Solana **mới (ví "burner")** và nạp vào đó một ít SOL (ví dụ: 0.05 SOL) và một ít USDC (ví dụ: 10 USDC) để thử nghiệm tính năng Swap và Tạo Token.

-----

### Bước 3: Khởi chạy hệ thống

Mở terminal tại thư mục gốc của dự án và chạy lệnh:

```bash
docker-compose up --build
```

  * **`--build`:** Lệnh này yêu cầu Docker xây dựng (build) lại các images (Python/Node.js) dựa trên `Dockerfile`. (Bạn chỉ cần dùng `--build` ở lần chạy đầu tiên hoặc khi có thay đổi code backend/dependencies).
  * Lệnh này sẽ tự động:
    1.  Tải images (Mongo, Redis, Python, Node).
    2.  Cài đặt dependencies (Python/Node.js).
    3.  Khởi chạy 5 container (frontend, 3 backend, 1 CSDL).
    4.  Kết nối chúng vào cùng một mạng nội bộ (theo file `docker-compose.yml`).

-----

### Bước 4: Truy cập ứng dụng

Sau khi tất cả các service đã khởi động (log trong terminal không còn chạy liên tục), hãy mở trình duyệt của bạn và truy cập:

**`http://localhost:3000`**

Bạn sẽ thấy "Bảng điều khiển Crypto AI" và có thể bắt đầu thử nghiệm các tính năng.

### Để dừng hệ thống:

Mở terminal (nơi đang chạy `docker-compose`) và nhấn `Ctrl + C`. Sau đó chạy lệnh:

```bash
docker-compose down
```
