# Use the official Python image as the base
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy files into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the Flask app environment variable
ENV FLASK_APP=fantasy.py

# Expose the Flask port
EXPOSE 5000

# Start Flask
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

