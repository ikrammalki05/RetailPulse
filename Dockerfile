FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-dashboard.txt ./requirements-dashboard.txt
RUN python -m pip install -r requirements-dashboard.txt

RUN useradd --system --create-home --shell /usr/sbin/nologin streamlit

COPY --chown=streamlit:streamlit app.py dashboard_data.py ./
COPY --chown=streamlit:streamlit app_pages ./app_pages
COPY --chown=streamlit:streamlit assets ./assets
COPY --chown=streamlit:streamlit .streamlit/ .streamlit/

USER streamlit
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
