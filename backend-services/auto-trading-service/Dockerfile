FROM python:3.11-slim  
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# SỬA DÒNG NÀY:
# Copy nội dung của thư mục 'app' (tức là main.py) vào '.'
COPY ./app/ .

# Cổng 8000
EXPOSE 8000

# ĐẢM BẢO DÒNG NÀY ĐÚNG:
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]