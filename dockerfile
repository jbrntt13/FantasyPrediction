FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so code changes don't bust the pip cache layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Credentials and season come from the environment, e.g.
#   docker run --env-file .env -p 8000:8000 fantasy-prediction
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
