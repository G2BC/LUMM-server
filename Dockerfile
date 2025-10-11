FROM python:3.8.10-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

ARG ENV=production
ENV ENV=${ENV}

CMD ["sh", "-c", "if [ \"$ENV\" = 'development' ]; then python3 -m flask run --host=0.0.0.0 --port=8000; else gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app; fi"]
