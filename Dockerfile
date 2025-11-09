# Use Python 3.13 base image
FROM python:3.13-slim

# Install system dependencies required for PyAudio
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    gcc \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install pip dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code
COPY . .

# Expose streamlit port
EXPOSE 8501

# Start the app
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
