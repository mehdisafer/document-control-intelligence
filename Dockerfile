# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
FROM ${PYTHON_IMAGE} AS build
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.6
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-editable
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM ${PYTHON_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng libseccomp2 libgomp1 libcurl4 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 dci && useradd --uid 10001 --gid 10001 --no-create-home dci \
    && mkdir -p /var/lib/dci /models /etc/dci && chown 10001:10001 /var/lib/dci
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 DCI_HOME=/var/lib/dci DCI_AUTH_FILE=/etc/dci/auth.json
USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
ENTRYPOINT ["dci"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000", "--config", "/etc/dci/config.json"]
