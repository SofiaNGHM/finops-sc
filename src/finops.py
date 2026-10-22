"""Inventario y recomendaciones de solo lectura para la demostración FinOps."""

from datetime import datetime, timedelta, timezone

from config import pricing, settings
from src import aws_client


def _proyecto(recurso):
    return aws_client.tags_a_dict(recurso).get(settings.PROJECT_TAG_KEY) == settings.PROJECT_TAG_VALUE


def inventario():
    """Consulta únicamente recursos marcados con el tag del proyecto."""
    ec2 = aws_client.ec2()
    filtro = aws_client.filtro_proyecto()
    instancias = aws_client.listar_instancias()
    volumenes = []
    for pagina in ec2.get_paginator("describe_volumes").paginate(Filters=filtro):
        volumenes.extend(v for v in pagina["Volumes"] if _proyecto(v))
    snapshots = []
    for pagina in ec2.get_paginator("describe_snapshots").paginate(OwnerIds=["self"], Filters=filtro):
        snapshots.extend(s for s in pagina["Snapshots"] if _proyecto(s))
    ips = [e for e in ec2.describe_addresses(Filters=filtro)["Addresses"] if _proyecto(e)]
    return {"instances": instancias, "volumes": volumenes, "snapshots": snapshots, "public_ips": ips}


def resumen_inventario(datos):
    return {
        "source": "aws_inventory",
        "region": settings.AWS_REGION,
        "instances": [
            {"id": i["InstanceId"], "type": i["InstanceType"], "state": i["State"]["Name"],
             "name": aws_client.tags_a_dict(i).get("Name"), "tags": aws_client.tags_a_dict(i)}
            for i in datos["instances"]
        ],
        "volumes": [{"id": v["VolumeId"], "size_gb": v["Size"], "state": v["State"]} for v in datos["volumes"]],
        "snapshots": [{"id": s["SnapshotId"], "created_at": s["StartTime"].isoformat()} for s in datos["snapshots"]],
        "public_ips": [{"allocation_id": e["AllocationId"], "associated": bool(e.get("AssociationId"))} for e in datos["public_ips"]],
    }


def huerfanos(datos, dias_snapshot=30):
    """Hallazgos potenciales; nunca borra recursos automáticamente."""
    limite = datetime.now(timezone.utc) - timedelta(days=dias_snapshot)
    hallazgos = []
    for v in datos["volumes"]:
        if v["State"] == "available" and not v.get("Attachments"):
            hallazgos.append({"kind": "ebs_volume", "id": v["VolumeId"], "reason": "unattached",
                               "estimated_monthly_usd": round(pricing.costo_mes_volumen(v["Size"]), 2)})
    for s in datos["snapshots"]:
        if s["StartTime"] < limite:
            hallazgos.append({"kind": "snapshot", "id": s["SnapshotId"], "reason": "older_than_threshold",
                               "estimated_monthly_usd": None})
    for e in datos["public_ips"]:
        if not e.get("AssociationId"):
            hallazgos.append({"kind": "public_ip", "id": e["AllocationId"], "reason": "unassociated",
                               "estimated_monthly_usd": round(pricing.ELASTIC_IP_HOURLY * pricing.HOURS_PER_MONTH, 2)})
    return {"source": "estimated_from_inventory", "findings": hallazgos}


def cpu_promedio(instance_id, horas=24):
    """Devuelve None si CloudWatch no tiene puntos recientes; no inventa CPU."""
    fin = datetime.now(timezone.utc)
    puntos = aws_client.cloudwatch().get_metric_statistics(
        Namespace="AWS/EC2", MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=fin - timedelta(hours=horas), EndTime=fin,
        Period=3600, Statistics=["Average"],
    )["Datapoints"]
    return round(sum(p["Average"] for p in puntos) / len(puntos), 2) if puntos else None


def recomendaciones(datos):
    """Solo recomienda; nunca llama ModifyInstanceAttribute."""
    siguiente = {"t3.small": "t3.micro", "t3.micro": "t3.nano"}
    resultado = []
    for i in datos["instances"]:
        tags = aws_client.tags_a_dict(i)
        if tags.get("Environment") == "prod" or tags.get("Schedule") == "always-on":
            continue
        actual = i["InstanceType"]
        if actual not in siguiente or i["State"]["Name"] != "running":
            continue
        cpu = cpu_promedio(i["InstanceId"])
        if cpu is None or cpu >= 10:
            continue
        nuevo = siguiente[actual]
        resultado.append({"id": i["InstanceId"], "from": actual, "to": nuevo,
                          "cpu_average_percent": cpu, "metric_hours": 24,
                          "estimated_savings_usd_per_hour": round(
                              pricing.costo_hora_instancia(actual) - pricing.costo_hora_instancia(nuevo), 4)})
    return {"source": "cloudwatch_cpu_and_reference_prices", "mode": "simulation", "recommendations": resultado}


def programacion(datos, momento=None):
    """Vista previa de horario en UTC. No envía órdenes a EC2."""
    momento = momento or datetime.now(timezone.utc)
    laboral = momento.weekday() in settings.WORK_DAYS and settings.OFFICE_START_HOUR <= momento.hour < settings.OFFICE_END_HOUR
    acciones = []
    for i in datos["instances"]:
        tags = aws_client.tags_a_dict(i)
        if tags.get("Environment") == "prod" or tags.get("Schedule") == "always-on":
            continue
        horario = tags.get("Schedule")
        if horario not in ("office-hours", "weekend-off"):
            continue
        encender = laboral if horario == "office-hours" else momento.weekday() in settings.WORK_DAYS
        estado = i["State"]["Name"]
        if encender and estado == "stopped":
            acciones.append({"id": i["InstanceId"], "would": "start"})
        elif not encender and estado == "running":
            acciones.append({"id": i["InstanceId"], "would": "stop"})
    return {"mode": "simulation", "timezone": "UTC", "at": momento.isoformat(), "actions": acciones}
