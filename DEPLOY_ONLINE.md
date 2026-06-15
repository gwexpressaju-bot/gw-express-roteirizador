# Publicar a Plataforma GW Express Online

## Render Free

Use estes comandos:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

O arquivo `render.yaml` já está pronto.

## Railway

O arquivo `Procfile` já está pronto:

```bash
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Docker

```bash
docker build -t gw-express .
docker run -p 8000:8000 gw-express
```

Acesse:

```text
http://localhost:8000
```
