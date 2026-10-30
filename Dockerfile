FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system django \
    && useradd --system --gid django --create-home django

COPY requirements.txt requirements-docker.txt ./
RUN pip install --upgrade pip -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple \
    && pip install -r requirements-docker.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

COPY . .

COPY docker-entrypoint.py /usr/local/bin/docker-entrypoint.py

RUN mkdir -p /data /app/media /app/staticfiles \
    && chown -R django:django /app /data

USER django

ENTRYPOINT ["python", "/usr/local/bin/docker-entrypoint.py"]

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
