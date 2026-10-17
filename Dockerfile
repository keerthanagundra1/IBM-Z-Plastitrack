# PlastiTrack container for IBM LinuxONE (s390x).
#
# Base: the LinuxONE Community Cloud lab image. It already ships s390x builds of
# Python 3.12, scikit-learn, XGBoost, llama-cpp-python and the big-endian IBM Granite
# GGUF model, so nothing has to be compiled here.
FROM registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest

# Run as the image's non-root user (uid 1000)
USER 1000
WORKDIR /app

# Web dependencies (pure-Python wheels, verified to install on s390x)
COPY requirements-app.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements-app.txt

# Application code, trained models, demo data
COPY --chown=1000:1000 src/ src/
COPY --chown=1000:1000 app/ app/
COPY --chown=1000:1000 models/ models/
COPY --chown=1000:1000 demo_emails/ demo_emails/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/mpl \
    PLASTITRACK_MODELS=/app/models \
    PLASTITRACK_LLM=/app/models/llm/granite-4.0-h-350m-Q8_0-be.gguf

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python app/healthcheck.py

# One worker process (sessions live in memory), several threads.
# HTTPS: mount a cert at /certs and set GUNICORN_CMD_ARGS (see scripts/container.sh).
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", "--chdir", "app", "--workers", "1", "--threads", "4", "--timeout", "300", \
     "--bind", "0.0.0.0:8501", "--worker-tmp-dir", "/tmp", "web:app"]
