# Squad NK Web — imagem única para os dois serviços.
#
# web e worker rodam o MESMO código: a diferença é só o comando. Uma imagem evita
# que as duas metades saiam de sincronia, e o `web` também precisa do ffprobe para
# validar o upload antes de aceitar o job.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg/ffprobe: motor do Legend IA e validação de upload.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependências antes do código: muda o código, a camada de pip continua em cache.
COPY apps/web/requirements.txt        /tmp/req-web.txt
COPY apps/legend-ia/requirements.txt  /tmp/req-legend.txt
RUN pip install -r /tmp/req-web.txt -r /tmp/req-legend.txt

COPY . /app

# Usuário sem privilégio. /app precisa ser gravável porque o motor do Legend IA
# recusa arquivo fora do próprio projeto — a entrada é estagiada lá e removida
# ao final (ver apps/web/squadnk/runner.py).
RUN useradd --create-home --uid 10001 squad \
    && mkdir -p /data \
    && chown -R squad:squad /data /app
USER squad

ENV SQUAD_REPO_ROOT=/app \
    SQUAD_DATA_HOME=/data \
    PYTHONPATH=/app/apps/web

EXPOSE 8000
CMD ["uvicorn", "squadnk.main:app", "--host", "0.0.0.0", "--port", "8000"]
