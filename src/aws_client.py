"""Clientes boto3 del proyecto: AWS real por defecto, o LocalStack/moto si hay AWS_ENDPOINT_URL."""
import sys

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from config import settings


def get_session():
    """Sesión con el perfil del CLI (AWS real) o credenciales falsas (emulador local)."""
    if settings.AWS_ENDPOINT_URL:
        return boto3.Session(
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name=settings.AWS_REGION,
        )
    return boto3.Session(region_name=settings.AWS_REGION) if not settings.AWS_PROFILE or settings.AWS_PROFILE == "default" else boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)


def client(servicio):
    """Cliente boto3 para un servicio ('ec2', 'cloudwatch', 'ssm', 'sts')."""
    return get_session().client(servicio, endpoint_url=settings.AWS_ENDPOINT_URL)


def ec2():
    return client("ec2")


def cloudwatch():
    return client("cloudwatch")


def ssm():
    return client("ssm")


def filtro_proyecto():
    """Filtro que limita cualquier describe_* a los recursos del proyecto."""
    return [{"Name": f"tag:{settings.PROJECT_TAG_KEY}", "Values": [settings.PROJECT_TAG_VALUE]}]


def listar_instancias():
    """Devuelve las instancias del proyecto (excepto las ya terminadas)."""
    filtros = filtro_proyecto() + [
        {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}
    ]
    instancias = []
    for pagina in ec2().get_paginator("describe_instances").paginate(Filters=filtros):
        for reserva in pagina["Reservations"]:
            instancias.extend(reserva["Instances"])
    return instancias


def tags_proyecto(**extra):
    """Lista de tags en formato AWS, siempre con Project=finops-demo."""
    tags = {settings.PROJECT_TAG_KEY: settings.PROJECT_TAG_VALUE, **extra}
    return [{"Key": k, "Value": str(v)} for k, v in tags.items()]


def tags_a_dict(recurso):
    """Convierte la lista 'Tags' de un recurso de AWS en un diccionario."""
    return {t["Key"]: t["Value"] for t in recurso.get("Tags", [])}


def probar_permiso(descripcion, funcion, **kwargs):
    """Llama a la API con DryRun=True: AWS valida permisos sin crear nada ni cobrar."""
    try:
        funcion(DryRun=True, **kwargs)
    except ClientError as e:
        codigo = e.response["Error"]["Code"]
        if codigo == "DryRunOperation":
            print(f"  OK     {descripcion}")
            return True
        print(f"  FALLA  {descripcion}: {codigo} - {e.response['Error']['Message'][:120]}")
        return False
    return True


def confirmar(mensaje):
    """Pide confirmación explícita por consola antes de crear o borrar recursos."""
    return input(f"{mensaje} Escribe 'si' para continuar: ").strip().lower() == "si"


def main():
    """Prueba de la Fase 0: identidad de la cuenta y lista de instancias del proyecto."""
    destino = settings.AWS_ENDPOINT_URL or f"AWS real ({settings.AWS_REGION}, perfil {settings.AWS_PROFILE})"
    print(f"Conectando a: {destino}")
    try:
        identidad = client("sts").get_caller_identity()
        print(f"Cuenta: {identidad['Account']}  Usuario: {identidad['Arn']}")
        instancias = listar_instancias()
    except ProfileNotFound:
        sys.exit(f"ERROR: no existe el perfil '{settings.AWS_PROFILE}'. Ejecuta: aws configure --profile {settings.AWS_PROFILE}")
    except NoCredentialsError:
        sys.exit("ERROR: no se encontraron credenciales de AWS.")
    except ClientError as e:
        sys.exit(f"ERROR de AWS: {e.response['Error']['Code']} - {e.response['Error']['Message']}")

    print(f"Instancias con {settings.PROJECT_TAG_KEY}={settings.PROJECT_TAG_VALUE}: {len(instancias)}")
    for i in instancias:
        print(f"  {i['InstanceId']}  {i['InstanceType']}  {i['State']['Name']}")


if __name__ == "__main__":
    main()
