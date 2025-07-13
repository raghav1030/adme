FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Initialize database and run FastAPI app with hot-reloading
CMD ["bash", "-c", "python app/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]