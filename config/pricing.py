"""Precios de referencia en USD (On-Demand, Linux, us-east-2).

Valores APROXIMADOS tomados de la página pública de precios de AWS; sirven para
estimar ahorros en la demo, no para facturar. Si cambian, se actualizan aquí.
"""

# USD por hora por tipo de instancia (aprox.)
INSTANCE_HOURLY = {
    "t3.nano": 0.0052,
    "t3.micro": 0.0104,
    "t3.small": 0.0208,
    "t3.medium": 0.0416,
    "t3.large": 0.0832,
}

EBS_GP3_GB_MONTH = 0.08        # volumen gp3, USD por GB-mes (aprox.)
SNAPSHOT_GB_MONTH = 0.05       # snapshot EBS, USD por GB-mes (aprox.)
ELASTIC_IP_HOURLY = 0.005      # Elastic IP / IPv4 pública, USD por hora (aprox.)

HOURS_PER_MONTH = 730


def costo_hora_instancia(instance_type):
    return INSTANCE_HOURLY[instance_type]


def costo_mes_volumen(size_gb):
    return size_gb * EBS_GP3_GB_MONTH
