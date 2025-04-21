FROM python:3.13-slim

WORKDIR /app

# Install system dependencies 
RUN apt-get update && apt-get install -y \
    curl \
    openssl \
    bash \
    ca-certificates \
    git \
    jq \
    wget \
    tar \
    unzip \
    apt-transport-https \
    gnupg \
    lsb-release \
    krb5-user \
    libkrb5-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Azure CLI directly using Microsoft script (more reliable)
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Verify Azure CLI was installed and is on PATH
RUN which az && az --version

# Install Innovation Engine during build
RUN curl -Lks https://raw.githubusercontent.com/Azure/InnovationEngine/v0.2.3/scripts/install_from_release.sh | bash -s -- v0.2.3

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables (these will be overridden at runtime)
ENV AZURE_OPENAI_API_KEY="your_api_key_here"
ENV AZURE_OPENAI_ENDPOINT="your_endpoint_here"
ENV PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH}"

# Set the entrypoint
ENTRYPOINT ["python", "ada.py"]