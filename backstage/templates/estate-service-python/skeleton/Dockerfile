FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd -u 10001 -r app
USER 10001
EXPOSE 8000
CMD ["uvicorn", "${{ values.pkg }}.app:app", "--host", "0.0.0.0", "--port", "8000"]
