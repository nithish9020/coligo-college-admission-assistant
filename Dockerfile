FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app"

# Install Nginx and envsubst (gettext-base) for dynamic port binding on Render
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    gettext-base \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY pyproject.toml README.md ./
COPY administration_portal/requirements.txt ./requirements-portal.txt

# Install all backend and frontend dependencies
RUN pip install --no-cache-dir -r requirements-portal.txt && \
    pip install --no-cache-dir -e .

# Copy application directories
COPY api ./api
COPY data ./data
COPY app ./app
COPY administration_portal ./administration_portal
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY start.sh ./start.sh

RUN chmod +x ./start.sh

EXPOSE 8000

CMD ["./start.sh"]
