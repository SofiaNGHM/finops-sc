"""Crea los recursos de prueba en AWS: 8 instancias con tags y recursos huérfanos.

Uso:
    python -m src.seed --dry-run   # valida permisos con DryRun de AWS, no crea nada
    python -m src.seed             # muestra resumen y costo, pide confirmación
    python -m src.seed --yes       # sin confirmación
"""
import argparse
import sys

from botocore.exceptions import ClientError

from config import pricing, settings
from src import aws_client

# Flota de prueba. SimulatedCpu (%) se usa en la Fase 4 si CloudWatch aún no tiene datos.
INSTANCIAS = [
    {"Name": "web-dev-01",   "Type": "t3.small", "Environment": "dev",  "Schedule": "office-hours", "Owner": "equipo-web",   "CostCenter": "CC-100", "SimulatedCpu": 4},
    {"Name": "api-dev-01",   "Type": "t3.small", "Environment": "dev",  "Schedule": "office-hours", "Owner": "equipo-api",   "CostCenter": "CC-200", "SimulatedCpu": 6},
    {"Name": "qa-test-01",   "Type": "t3.micro", "Environment": "test", "Schedule": "office-hours", "Owner": "equipo-qa",    "CostCenter": "CC-300", "SimulatedCpu": 25},
    {"Name": "qa-test-02",   "Type": "t3.small", "Environment": "test", "Schedule": "office-hours", "Owner": "equipo-qa",    "CostCenter": "CC-300", "SimulatedCpu": 8},
    {"Name": "batch-dev-01", "Type": "t3.micro", "Environment": "dev",  "Schedule": "weekend-off",  "Owner": "equipo-datos", "CostCenter": "CC-400", "SimulatedCpu": 35},
    {"Name": "etl-test-01",  "Type": "t3.micro", "Environment": "test", "Schedule": "weekend-off",  "Owner": "equipo-datos", "CostCenter": "CC-400", "SimulatedCpu": 15},
    {"Name": "web-prod-01",  "Type": "t3.micro", "Environment": "prod", "Schedule": "always-on",    "Owner": "equipo-web",   "CostCenter": "CC-100", "SimulatedCpu": 45},
    # CPU baja a propósito: el right-sizing NO debe tocarla por ser prod (regla de seguridad)
    {"Name": "api-prod-01",  "Type": "t3.small", "Environment": "prod", "Schedule": "always-on",    "Owner": "equipo-api",   "CostCenter": "CC-200", "SimulatedCpu": 5},
]

# Huérfanos: volúmenes sin adjuntar; los 2 primeros además generan un snapshot "antiguo"
VOLUMENES_HUERFANOS = [
    {"Name": "vol-huerfano-web",   "Owner": "equipo-web",   "CostCenter": "CC-100", "SnapshotAgeDays": 120},
    {"Name": "vol-huerfano-qa",    "Owner": "equipo-qa",    "CostCenter": "CC-300", "SnapshotAgeDays": 45},
    {"Name": "vol-huerfano-datos", "Owner": "equipo-datos", "CostCenter": "CC-400", "SnapshotAgeDays": None},
]

ELASTIC_IPS = [
    {"Name": "eip-huerfana-api", "Owner": "equipo-api", "CostCenter": "CC-200"},
    {"Name": "eip-huerfana-web", "Owner": "equipo-web", "CostCenter": "CC-100"},
]


def obtener_ami():
    respuesta = aws_client.ssm().get_parameter(Name=settings.AMI_SSM_PARAMETER)
    return respuesta["Parameter"]["Value"]


def obtener_subnet():
    """Primera subred por defecto (ordenada por zona) de la VPC por defecto."""
    subnets = aws_client.ec2().describe_subnets(
        Filters=[{"Name": "default-for-az", "Values": ["true"]}]
    )["Subnets"]
    if not subnets:
        sys.exit("ERROR: la región no tiene VPC/subred por defecto.")
    return sorted(subnets, key=lambda s: s["AvailabilityZone"])[0]


def mostrar_resumen():
    costo_hora = 0.0
    print("\nInstancias a crear (sin IP pública):")
    for i in INSTANCIAS:
        precio = pricing.costo_hora_instancia(i["Type"])
        costo_hora += precio
        print(f"  {i['Name']:<13} {i['Type']:<9} {i['Environment']:<5} {i['Schedule']:<13} ${precio:.4f}/h")

    gb_huerfanos = len(VOLUMENES_HUERFANOS) * settings.ORPHAN_VOLUME_SIZE_GB
    costo_hora += pricing.costo_mes_volumen(gb_huerfanos) / pricing.HOURS_PER_MONTH
    costo_hora += len(ELASTIC_IPS) * pricing.ELASTIC_IP_HOURLY
    snapshots = sum(1 for v in VOLUMENES_HUERFANOS if v["SnapshotAgeDays"])
    print(f"\nHuérfanos: {len(VOLUMENES_HUERFANOS)} volúmenes de {settings.ORPHAN_VOLUME_SIZE_GB} GB, "
          f"{snapshots} snapshots, {len(ELASTIC_IPS)} Elastic IPs sin asociar")
    print(f"\nCosto estimado mientras exista todo: ~${costo_hora:.3f}/hora "
          f"(~${costo_hora * 3:.2f} por una sesión de 3 h). Valores aproximados.\n")


def validar_permisos(ami, subnet):
    """Modo --dry-run: AWS valida cada operación sin crear recursos."""
    print("Validando permisos con DryRun de AWS (no crea nada, costo $0):")
    ec2 = aws_client.ec2()
    ok = True
    for tipo in sorted({i["Type"] for i in INSTANCIAS}):
        ok &= aws_client.probar_permiso(f"run_instances {tipo}", ec2.run_instances,
                                        ImageId=ami, InstanceType=tipo, MinCount=1, MaxCount=1,
                                        SubnetId=subnet["SubnetId"])
    ok &= aws_client.probar_permiso("create_volume gp3", ec2.create_volume,
                                    AvailabilityZone=subnet["AvailabilityZone"],
                                    Size=settings.ORPHAN_VOLUME_SIZE_GB, VolumeType="gp3")
    ok &= aws_client.probar_permiso("allocate_address", ec2.allocate_address, Domain="vpc")
    print("\nTodo listo para crear." if ok else "\nHay operaciones bloqueadas: revisar antes de crear.")


def crear_instancias(ami, subnet):
    ec2 = aws_client.ec2()
    ids = []
    for i in INSTANCIAS:
        tags = aws_client.tags_proyecto(**{k: v for k, v in i.items() if k != "Type"})
        respuesta = ec2.run_instances(
            ImageId=ami,
            InstanceType=i["Type"],
            MinCount=1,
            MaxCount=1,
            # Sin IPv4 pública: AWS la cobra aparte y no necesitamos SSH
            NetworkInterfaces=[{"DeviceIndex": 0, "SubnetId": subnet["SubnetId"],
                                "AssociatePublicIpAddress": False}],
            TagSpecifications=[
                {"ResourceType": "instance", "Tags": tags},
                {"ResourceType": "volume", "Tags": tags},
            ],
        )
        instancia_id = respuesta["Instances"][0]["InstanceId"]
        ids.append(instancia_id)
        print(f"  instancia {i['Name']:<13} {instancia_id}")
    return ids


def crear_huerfanos(subnet):
    ec2 = aws_client.ec2()
    volumenes = []
    for v in VOLUMENES_HUERFANOS:
        tags = aws_client.tags_proyecto(Name=v["Name"], Owner=v["Owner"], CostCenter=v["CostCenter"])
        vol = ec2.create_volume(
            AvailabilityZone=subnet["AvailabilityZone"],
            Size=settings.ORPHAN_VOLUME_SIZE_GB,
            VolumeType="gp3",
            TagSpecifications=[{"ResourceType": "volume", "Tags": tags}],
        )
        volumenes.append((vol["VolumeId"], v))
        print(f"  volumen   {v['Name']:<20} {vol['VolumeId']}")

    print("  esperando que los volúmenes estén disponibles para crear snapshots...")
    ec2.get_waiter("volume_available").wait(VolumeIds=[vid for vid, _ in volumenes])

    for vid, v in volumenes:
        if not v["SnapshotAgeDays"]:
            continue
        # AWS no permite fechar un snapshot en el pasado: la antigüedad se simula con un tag
        tags = aws_client.tags_proyecto(Name=f"snap-{v['Name']}", Owner=v["Owner"],
                                        CostCenter=v["CostCenter"], SimulatedAgeDays=v["SnapshotAgeDays"])
        snap = ec2.create_snapshot(VolumeId=vid, Description=f"Snapshot de prueba de {v['Name']}",
                                   TagSpecifications=[{"ResourceType": "snapshot", "Tags": tags}])
        print(f"  snapshot  snap-{v['Name']:<15} {snap['SnapshotId']} ({v['SnapshotAgeDays']} días simulados)")

    for e in ELASTIC_IPS:
        tags = aws_client.tags_proyecto(**e)
        eip = ec2.allocate_address(Domain="vpc",
                                   TagSpecifications=[{"ResourceType": "elastic-ip", "Tags": tags}])
        print(f"  elastic-ip {e['Name']:<19} {eip['PublicIp']}")


def main():
    parser = argparse.ArgumentParser(description="Crea los recursos de prueba del proyecto en AWS.")
    parser.add_argument("--dry-run", action="store_true", help="valida permisos sin crear nada")
    parser.add_argument("--yes", action="store_true", help="no pedir confirmación")
    args = parser.parse_args()

    try:
        existentes = aws_client.listar_instancias()
        if existentes:
            sys.exit(f"Ya existen {len(existentes)} instancias del proyecto. "
                     "Ejecuta 'python -m src.teardown' antes de volver a sembrar.")

        ami = obtener_ami()
        subnet = obtener_subnet()
        print(f"Región {settings.AWS_REGION} | AMI {ami} | subred {subnet['SubnetId']} ({subnet['AvailabilityZone']})")
        mostrar_resumen()

        if args.dry_run:
            validar_permisos(ami, subnet)
            return
        if not args.yes and not aws_client.confirmar("Se crearán estos recursos en AWS (consume créditos)."):
            print("Cancelado. No se creó nada.")
            return

        print("Creando recursos...")
        crear_instancias(ami, subnet)
        crear_huerfanos(subnet)
        print("\nListo. Recuerda ejecutar 'python -m src.teardown' al terminar la sesión.")
    except ClientError as e:
        sys.exit(f"ERROR de AWS: {e.response['Error']['Code']} - {e.response['Error']['Message']}\n"
                 "Si se creó algo a medias, límpialo con 'python -m src.teardown'.")


if __name__ == "__main__":
    main()
