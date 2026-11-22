FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --upgrade pip \
    && pip install "poetry>=2,<3"

COPY pyproject.toml ./

RUN poetry install \
    --only main \
    --no-root \
    --no-ansi

COPY ermes_backend ./ermes_backend

RUN useradd --create-home --uid 10001 ermes

USER ermes

EXPOSE 8091

CMD ["uvicorn", "ermes_backend.main:app", "--host", "0.0.0.0", "--port", "8091"]
