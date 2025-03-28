# Usar uma imagem base do Python
FROM python:3.9-slim

# Instalar FFmpeg e dependências
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get install -y libsndfile1 && \
    apt-get clean

# Definir o diretório de trabalho dentro do container
WORKDIR /app

# Copiar os arquivos do projeto para o diretório de trabalho
COPY . .

# Instalar as dependências do Python do requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expôr a porta (não necessário para um bot, mas pode ser útil dependendo de como você roda)
EXPOSE 8080

# Comando para rodar o bot (ajustado para o seu main.py)
CMD ["python", "main.py"]
