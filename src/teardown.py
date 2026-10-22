"""Borra TODOS los recursos del proyecto (tag Project=finops-demo) para no consumir créditos.

Es la única herramienta que toca recursos prod: su propósito es dejar la cuenta limpia.
Nunca toca nada sin el tag del proyecto.

Uso:
    python -m src.teardown --dry-run   # solo lista lo que borraría
    python -m src.teardown             # lista y pide confirmación
    python -m src.teardown --yes       # sin confirmación
"""
import argparse
import sys

from botocore.exceptions import ClientError

from config import settings
from src import aws_client


def recolectar():
    """Busca todos los recursos del proyecto, siempre filtrando por el tag."""
    ec2 = aws_client.ec2()
    filtro = aws_client.filtro_proyecto()
    return {
        "instancias": aws_client.listar_instancias(),
        # Solo volúmenes sueltos; los raíz se borran solos al terminar su instancia
        "volumenes": ec2.describe_volumes(
            Filters=filtro + [{"Name": "status", "Values": ["available"]}])["Volumes"],
        "snapshots": ec2.describe_snapshots(OwnerIds=["self"], Filters=filtro)["Snapshots"],
        "elastic_ips": ec2.describe_addresses(Filters=filtro)["Addresses"],
    }


def mostrar(recursos):
    nombre = lambda r: aws_client.tags_a_dict(r).get("Name", "-")
    for i in recursos["instancias"]:
        print(f"  instancia  {i['InstanceId']:<22} {nombre(i):<20} {i['State']['Name']}")
    for v in recursos["volumenes"]:
        print(f"  volumen    {v['VolumeId']:<22} {nombre(v):<20} {v['Size']} GB")
    for s in recursos["snapshots"]:
        print(f"  snapshot   {s['SnapshotId']:<22} {nombre(s):<20} {s['State']}")
    for e in recursos["elastic_ips"]:
        print(f"  elastic-ip {e['AllocationId']:<22} {nombre(e):<20} {e['PublicIp']}")


def borrar(recursos):
    """Borra cada recurso; si uno falla, sigue con el resto y lo reporta."""
    ec2 = aws_client.ec2()
    errores = 0

    def intentar(descripcion, funcion, **kwargs):
        nonlocal errores
        try:
            funcion(**kwargs)
            print(f"  OK     {descripcion}")
        except ClientError as e:
            errores += 1
            print(f"  FALLA  {descripcion}: {e.response['Error']['Code']}")

    for e in recursos["elastic_ips"]:
        if e.get("AssociationId"):
            intentar(f"desasociar {e['PublicIp']}", ec2.disassociate_address, AssociationId=e["AssociationId"])
        intentar(f"liberar elastic-ip {e['PublicIp']}", ec2.release_address, AllocationId=e["AllocationId"])
    for s in recursos["snapshots"]:
        intentar(f"borrar snapshot {s['SnapshotId']}", ec2.delete_snapshot, SnapshotId=s["SnapshotId"])
    for v in recursos["volumenes"]:
        intentar(f"borrar volumen {v['VolumeId']}", ec2.delete_volume, VolumeId=v["VolumeId"])
    if recursos["instancias"]:
        ids = [i["InstanceId"] for i in recursos["instancias"]]
        intentar(f"terminar {len(ids)} instancias", ec2.terminate_instances, InstanceIds=ids)
    return errores


def main():
    parser = argparse.ArgumentParser(description="Borra todos los recursos del proyecto en AWS.")
    parser.add_argument("--dry-run", action="store_true", help="solo listar, no borrar")
    parser.add_argument("--yes", action="store_true", help="no pedir confirmación")
    args = parser.parse_args()

    try:
        recursos = recolectar()
        total = sum(len(lista) for lista in recursos.values())
        print(f"Recursos con {settings.PROJECT_TAG_KEY}={settings.PROJECT_TAG_VALUE} en {settings.AWS_REGION}: {total}")
        if total == 0:
            print("La cuenta está limpia, no hay nada que borrar.")
            return
        mostrar(recursos)

        if args.dry_run:
            print("\n--dry-run: no se borró nada.")
            return
        if not args.yes and not aws_client.confirmar("\nSe BORRARÁN estos recursos de forma permanente."):
            print("Cancelado. No se borró nada.")
            return

        errores = borrar(recursos)
        if errores:
            print(f"\n{errores} operaciones fallaron. Vuelve a ejecutar el teardown en un minuto "
                  "(p. ej. snapshots aún en estado 'pending').")
        else:
            print("\nListo. Las instancias tardan ~1 min en pasar a 'terminated' (sus discos se borran solos).")
    except ClientError as e:
        sys.exit(f"ERROR de AWS: {e.response['Error']['Code']} - {e.response['Error']['Message']}")


if __name__ == "__main__":
    main()
