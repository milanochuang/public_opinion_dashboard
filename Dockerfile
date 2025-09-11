FROM python:3.11-slim

# 安裝需要的套件
RUN apt-get update && apt-get install -y build-essential

# 設定工作目錄
WORKDIR /app

# 複製檔案
COPY . .

# 安裝 Python 依賴
RUN pip install --no-cache-dir fastapi uvicorn beautifulsoup4 requests six

# 啟動 API 伺服器
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
