"""Configuración central del proyecto. Todo valor ajustable vive aquí o en .env."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- AWS ---
AWS_PROFILE = os.getenv("AWS_PROFILE", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
# Vacío = AWS real; con valor apunta a LocalStack/moto
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL") or None

# Tag que marca los recursos del proyecto. Los scripts SOLO actúan sobre recursos con este tag.
PROJECT_TAG_KEY = "Project"
PROJECT_TAG_VALUE = "finops-demo"

# --- PostgreSQL ---
POSTGRES = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "finops"),
    "user": os.getenv("POSTGRES_USER", "finops"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

# --- Horario laboral (hora simulada) ---
OFFICE_START_HOUR = 8    # encendido 08:00
OFFICE_END_HOUR = 20     # apagado 20:00
WORK_DAYS = [0, 1, 2, 3, 4]  # lunes=0 ... viernes=4

# --- Reloj simulado ---
# Segundos reales que equivalen a 1 hora simulada (un stop/start real tarda ~30-60 s, no bajar de 60)
REAL_SECONDS_PER_SIM_HOUR = 60

# --- Recursos de prueba (seed) ---
# AMI Amazon Linux 2023 resuelta por SSM (siempre la última, sin IDs fijos)
AMI_SSM_PARAMETER = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
ORPHAN_VOLUME_SIZE_GB = 1
