FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE LICENSE-DOCS LICENSING.md setup.py MANIFEST.in public-release-policy.json ./
COPY tools/verify_public_release.py ./tools/verify_public_release.py
COPY src ./src
COPY spec ./spec
RUN pip install --no-cache-dir .
USER 65532:65532
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "sort4circ_dpp.api:app", "--host", "0.0.0.0", "--port", "8000"]
