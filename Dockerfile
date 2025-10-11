FROM python:3.8.10-slim as base

WORKDIR /app

COPY requirements.txt wsgi.py ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "wsgi.py"]