# Reference service image.
#
# Not hardened for production. See SECURITY.md for what a deployment must add
# before this is exposed to anything that matters.
FROM python:3.12-slim AS build

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

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
