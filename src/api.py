"""API privada y de solo lectura para inventario y recomendaciones FinOps."""

from fastapi import FastAPI, HTTPException
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from src import finops

app = FastAPI(title="FinOps Lab", version="0.1.0")


def _leer():
    try:
        return finops.inventario()
    except (BotoCoreError, ClientError, NoCredentialsError) as exc:
        raise HTTPException(status_code=503, detail=f"AWS no disponible: {type(exc).__name__}") from exc


@app.get("/health")
def health():
    return {"status": "ok", "aws_checked": False}


@app.get("/inventory")
def inventory():
    return finops.resumen_inventario(_leer())


@app.get("/orphans")
def orphans():
    return finops.huerfanos(_leer())


@app.get("/schedule/preview")
def schedule_preview():
    return finops.programacion(_leer())


@app.get("/rightsizing")
def rightsizing():
    try:
        return finops.recomendaciones(_leer())
    except (BotoCoreError, ClientError, NoCredentialsError) as exc:
        raise HTTPException(status_code=503, detail=f"CloudWatch no disponible: {type(exc).__name__}") from exc
