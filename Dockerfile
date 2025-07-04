FROM python:3.10

WORKDIR /app

COPY requirements-base.txt .
COPY requirements-tf.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-base.txt

RUN pip install --no-cache-dir -r requirements-tf.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . .

# Descargar recursos NLTK
RUN mkdir -p /usr/share/nltk_data && \
    python -m nltk.downloader -d /usr/share/nltk_data punkt stopwords snowball_data wordnet omw-1.4

ENV NLTK_DATA=/usr/share/nltk_data

EXPOSE 54321

CMD ["python", "-m", "HeiderDB.server"]
