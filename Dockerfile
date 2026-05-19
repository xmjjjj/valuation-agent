FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    MYSQL_HOST=mysql \
    MYSQL_PORT=3306 \
    MYSQL_USER=patent \
    MYSQL_PASSWORD=patent_dev \
    MYSQL_DATABASE=patent_valuation

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
