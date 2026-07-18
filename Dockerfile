FROM python:3.12-slim

WORKDIR /app

# No system build deps needed: psycopg2-binary ships a self-contained wheel
# (bundled libpq), and every other dependency has a manylinux wheel. Keeping
# the image slim matters on the small shared EC2 host.

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
