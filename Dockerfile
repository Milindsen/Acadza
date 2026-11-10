FROM python:3.12-slim
WORKDIR /app
COPY . .
ENV HOST=0.0.0.0 PORT=8765 ACADZA_DB=/data/review.sqlite3 PYTHONUNBUFFERED=1
EXPOSE 8765
CMD ["python", "server.py"]
