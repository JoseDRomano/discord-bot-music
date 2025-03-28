# Usar a imagem base oficial do Python
FROM python:3.9-slim

# Definir o diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && \
    apt-get install -y ffmpeg libsndfile1 build-essential && \
    apt-get clean

# Copiar os arquivos do seu projeto para o container
COPY . .

# Instalar dependências do Python do requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expôr a porta (não necessário para um bot, mas pode ser útil dependendo de como você roda)
EXPOSE 8080

# Comando para rodar o bot
CMD ["python", "main.py"]
