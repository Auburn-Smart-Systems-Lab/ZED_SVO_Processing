# Use NVIDIA CUDA base image for ZED SDK support
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (including zstd for ZED SDK)
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    wget \
    lsb-release \
    less \
    udev \
    sudo \
    build-essential \
    cmake \
    git \
    libopencv-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libusb-1.0-0 \
    redis-server \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Install ZED SDK
RUN wget -q -O ZED_SDK_Linux.run https://download.stereolabs.com/zedsdk/4.1/cu118/ubuntu22 && \
    chmod +x ZED_SDK_Linux.run && \
    ./ZED_SDK_Linux.run -- silent skip_cuda && \
    rm ZED_SDK_Linux.run

# Set environment variables for ZED SDK
ENV PYTHONPATH="${PYTHONPATH}:/usr/local/zed/lib/python3"
ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/zed/lib"

# Upgrade pip
RUN pip3 install --upgrade pip

# Copy requirements file
COPY requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Create media directories
RUN mkdir -p /app/media/svo2_files /app/media/extraction_results

# Collect static files
RUN python3 manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Create entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]