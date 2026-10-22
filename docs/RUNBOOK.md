# Guía de laboratorio temporal (arquitectura B)

**Estado:** preparación local. No existe evidencia de que esta infraestructura se haya desplegado. No ejecutar `apply`, `destroy` ni `src/seed.py` como parte de estas verificaciones.

## Validaciones locales

En PowerShell, desde la raíz del proyecto:

```powershell
cd infra
terraform fmt -recursive
terraform init -backend=false
terraform validate
```

En AWS CloudShell (Bash), después de instalar Terraform si no está disponible:

```bash
cd infra
terraform fmt -recursive
terraform init -backend=false
terraform validate
```

`terraform plan` no calcula precios. Antes de habilitar cualquier interruptor, verificar identidad y cuenta con `aws sts get-caller-identity`, región `us-east-2`, cuotas, créditos, precio vigente y estado Terraform. Los valores predeterminados deben permanecer `enable_network=false`, `enable_nat=false`, `enable_compute=false`.

## Red privada y acceso administrativo

APP y DATA no tienen IPv4 pública. La ruta seleccionada para un laboratorio corto es un **NAT Gateway temporal**, aún desactivado. Permite SSM y descargas de paquetes e imágenes; exige aprobación de su costo horario y del tráfico procesado antes de habilitarlo. Una alternativa son endpoints privados para SSM, pero también pueden facturarse por hora y no proporcionan por sí solos acceso a repositorios de paquetes o registros públicos de contenedores. Una AMI preparada reduce descargas en el arranque, pero requiere preparar y mantener esa imagen y todavía resolver conectividad SSM. Ninguna alternativa está desplegada.

Antes de instalar o iniciar contenedores en EC2, comprobar que ambas instancias aparezcan como nodos administrados en Systems Manager y que exista conectividad. Amazon Linux 2023 suele traer SSM Agent; verificar el estado real del agente. El acceso a la API y Grafana debe hacerse por túnel de Session Manager hacia los puertos 8000 y 3000 ligados a `127.0.0.1` en APP. El SG de DATA solo acepta TCP 5432 desde el SG de APP.

## Datos y secretos

### Preparación de Amazon Linux 2023 tras un despliegue autorizado

Antes de la demo, publicar en Git **solo** código y ejemplos sin secretos; verificar que no se incluyan `.env`, `*.tfstate`, `*.tfvars`, llaves ni archivos de `.terraform`. Anotar el SHA completo del commit publicado. Un repositorio público se puede clonar por HTTPS sin credenciales de Git; no hace falta subir otro ZIP a CloudShell.

Después de un despliegue autorizado, comprobar que ambas EC2 estén administradas por SSM y que exista salida temporal por NAT. En **cada** instancia, dentro de una sesión SSM, sustituir los dos marcadores por la URL pública y el SHA del mismo commit:

```bash
sudo dnf install -y git
sudo git clone https://HOST/ORGANIZACION/REPOSITORIO.git /opt/finops
sudo git -C /opt/finops checkout --detach SHA_COMPLETO_DEL_COMMIT
sudo git -C /opt/finops rev-parse HEAD
cd /opt/finops
sudo bash deploy/install-docker-al2023.sh
sudo docker version
sudo docker compose version
```

Confirmar que `rev-parse HEAD` coincide con el SHA esperado en APP y DATA antes de iniciar contenedores. El script instala Docker desde Amazon Linux 2023 y Docker Compose v5.6.0 según la [instalación oficial](https://docs.docker.com/compose/install/linux/); no inicia contenedores ni formatea discos. Este procedimiento no se ha ejecutado en AWS.

En DATA, antes de iniciar PostgreSQL, identificar el EBS adicional por ID y verificar con `lsblk -f` y `sudo blkid` si contiene un sistema de archivos. El formateo de un volumen existente destruye datos; hacerlo solo si se confirma que el volumen correcto está vacío. Montar en `/srv/finops/postgres` usando UUID en `/etc/fstab`, según la [guía de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-using-volumes.html), y verificar el montaje tras reiniciar.

El volumen gp3 cifrado adicional se adjunta a DATA, pero **Terraform no lo formatea ni monta**. No usar el nombre NVMe como identificador persistente.

Crear `deploy/.env` solo en la instancia correspondiente, con permisos `0600`, a partir del ejemplo de APP o DATA. Configurar una contraseña PostgreSQL fuerte y la misma en ambas instancias; sustituir la IP de DATA en APP por el output real. No subir `.env`, `*.tfstate`, `*.tfvars` ni credenciales. Las variables de entorno de Docker son visibles para operadores con acceso al daemon; limitar ese acceso.

## Demo y límites actuales

- La API expone inventario, posibles huérfanos, vista previa de horario y recomendaciones de tamaño, todos de solo lectura.
- La vista previa del scheduler no ejecuta cambios. Las recomendaciones no redimensionan EC2.
- El panel Grafana lee tablas inicialmente vacías. No muestra ahorros reales ni simulados hasta registrar datos identificados por origen.
- CPU procede de CloudWatch cuando existe; memoria requiere un agente o fuente adicional. No se inventan métricas.
- APP y DATA no instalan Docker ni clonan el repositorio automáticamente. El procedimiento por Git público está documentado, pero no probado en EC2. No se considera listo para ejecutar en AWS sin verificar SSM, montaje, secretos y contenedores.

## Limpieza de una demo futura

Tras autorización explícita, usar únicamente el mismo directorio y estado Terraform que creó los recursos para revisar un `terraform plan -destroy` y ejecutar `terraform destroy`. `src/teardown.py` pertenece al prototipo anterior y no reemplaza Terraform. Verificar después, mediante lecturas de AWS en `us-east-2`, que no queden EC2, NAT Gateway, Elastic IP, EBS o snapshots del proyecto; revisar además Billing. No borrar recursos ajenos al tag del proyecto ni confiar en que detener EC2 elimine cargos por NAT o EBS.

## Referencias técnicas

- [Conectividad privada de Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html)
- [SSM Agent en AMI de Amazon Linux](https://docs.aws.amazon.com/systems-manager/latest/userguide/ami-preinstalled-agent.html)
- [Identificación de EBS NVMe](https://docs.aws.amazon.com/ebs/latest/userguide/identify-nvme-ebs-device.html)
- [Montaje persistente de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-using-volumes.html)
- [Precios de NAT y endpoints de VPC](https://aws.amazon.com/vpc/pricing/)
