FROM apache/airflow:3.3.1

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    cmake \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-fra \
    libreoffice \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt