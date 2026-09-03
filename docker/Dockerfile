# Reference service image.
#
# Not hardened for production. See SECURITY.md for what a deployment must add
# before this is exposed to anything that matters.
# Python 3.12.14-slim; multi-platform digest verified against Docker Hub 2026-09-03.
FROM python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS build

WORKDIR /build
COPY pyproject.toml README.md requirements-evidence.txt ./
COPY src/ src/
RUN pip install --no-cache-dir setuptools==84.0.0 wheel==0.48.0 \
 && pip install --no-cache-dir --no-build-isolation --prefix=/install --constraint=requirements-evidence.txt .

FROM python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

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
