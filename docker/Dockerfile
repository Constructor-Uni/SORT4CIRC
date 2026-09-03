# Reference service image.
#
# Not hardened for production. See SECURITY.md for what a deployment must add
# before this is exposed to anything that matters.
# Python 3.12.14-slim for linux/amd64; platform manifest verified against Docker Hub 2026-09-03.
FROM python:3.12.14-slim@sha256:2fe5997d249a808b8eeea52c58a1dbffbba28754dc11699ef5c029f2d818ce79 AS build

WORKDIR /build
COPY pyproject.toml README.md requirements-evidence.txt ./
COPY src/ src/
RUN pip install --no-cache-dir setuptools==84.0.0 wheel==0.48.0 \
 && pip install --no-cache-dir --no-build-isolation --prefix=/install --constraint=requirements-evidence.txt .

FROM python:3.12.14-slim@sha256:2fe5997d249a808b8eeea52c58a1dbffbba28754dc11699ef5c029f2d818ce79

RUN useradd --create-home --uid 10001 dpp
COPY --from=build /install /usr/local
COPY spec/ /app/spec/
WORKDIR /app
USER dpp

ENV S4C_SPEC_DIR=/app/spec \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "sort4circ_dpp.api:app", "--host", "0.0.0.0", "--port", "8000"]
