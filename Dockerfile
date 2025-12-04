# FFmpeg bilan pre-installed Ubuntu base
FROM ubuntu:22.04

# Apt ni yangilash va zarur paketlarni o'rnatish (read-only muammosini hal qiladi)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Ish papkasi
WORKDIR /app

# requirements.txt ni nusxalash
COPY requirements.txt .

# Python paketlarini o'rnatish
RUN pip3 install --no-cache-dir -r requirements.txt

# main.py ni nusxalash
COPY main.py .

# Port ochish (Render uchun)
EXPOSE 10000

# Botni ishga tushirish
CMD ["python3", "main.py"]
