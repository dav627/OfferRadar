FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir openpyxl pyyaml ruamel.yaml

COPY core/ core/
COPY launcher.py start.sh config.yaml.example 公司清单.json ./
COPY scripts/ scripts/

RUN mkdir -p data

EXPOSE 8686

CMD ["python", "launcher.py", "dashboard"]
