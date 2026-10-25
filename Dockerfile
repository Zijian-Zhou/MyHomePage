FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system django \
    && useradd --system --gid django --create-home django

COPY requirements.txt requirements-docker.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements-docker.txt

COPY . .

RUN mkdir -p /data /app/media \
    && chown -R django:django /app /data

USER django

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
