FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Initialize database and run FastAPI app with hot-reloading
CMD ["bash", "-c", "python init_db.py && python main.py"]