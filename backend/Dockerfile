FROM python:3.12-slim

WORKDIR /app

# WeasyPrint системные зависимости + кириллические шрифты
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 libffi-dev libcairo2 \
    fonts-freefont-ttf fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system lawdocs && adduser --system --ingroup lawdocs lawdocs \
    && chown -R lawdocs:lawdocs /app
USER lawdocs

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
