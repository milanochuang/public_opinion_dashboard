FROM python:3.11-slim

# �w�˻ݭn���M��
RUN apt-get update && apt-get install -y build-essential

# �]�w�u�@�ؿ�
WORKDIR /app

# �ƻs�ɮ�
COPY . .

# �w�� Python �̿�
RUN pip install --no-cache-dir fastapi uvicorn beautifulsoup4 requests six

# �Ұ� API ���A��
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
