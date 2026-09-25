FROM python:3.12-slim

WORKDIR /app

# hatchling needs pyproject.toml + README.md alongside src/ to build the wheel
COPY pyproject.toml README.md ./
COPY src/ src/
COPY data/ data/
COPY tests/fixtures/certs.jsonl tests/fixtures/certs.jsonl

RUN pip install --no-cache-dir . \
    && mkdir -p /data/output

ENTRYPOINT ["vigil"]
CMD ["watch", "--source", "fixtures", "--detection", "--output", "/data/output/results.jsonl"]
