# Estado de la auditoría (2026-10-22)

## Verificación AWS de solo lectura (2026-10-22)

CloudShell ejecutó Terraform 1.17.0 con AWS provider 5.100.0. El plan con los tres controles en `false` indicó `No changes`. El primer plan exploratorio con `enable_network=true`, `enable_nat=true` y `enable_compute=true` propuso 25 altas. Tras separar el perfil IAM de DATA, el plan actualizado propuso 28 altas, 0 cambios y 0 eliminaciones. No se ejecutó `apply`; ningún recurso del plan fue creado. El plan no verifica cuotas, cobertura de créditos ni arranque de Docker/PostgreSQL.

El usuario ejecutó consultas en AWS CloudShell con el rol asumido `AccountFullAccessRole`. `freetier get-account-plan-state` devolvió plan `FREE`, estado `ACTIVE`, USD 100 de créditos restantes y vencimiento 2027-04-22. En `us-east-2`, `describe-vpcs` mostró únicamente la VPC predeterminada `172.31.0.0/16`; `describe-instances`, `describe-nat-gateways`, `describe-addresses` y `describe-volumes` no devolvieron recursos. Esto no verifica otras regiones, snapshots ni cargos en Billing. No se ejecutó ninguna operación de escritura.

La demostración prevista dura hasta tres horas. Si el NAT Gateway y su única IPv4 pública permanecieran exactamente tres horas, la referencia publicada para Ohio da USD 0,135 de NAT por tiempo (3 × 0,045) y USD 0,015 de IPv4 pública (3 × 0,005): USD 0,150 antes de procesamiento de datos, transferencia, EC2 y EBS. El costo total y la aplicación de créditos siguen sin verificar. La ventana facturable debe incluir preparación y limpieza, no solo la presentación. Referencia: https://aws.amazon.com/vpc/pricing/

La infraestructura está definida, no desplegada. Los tres interruptores de Terraform permanecen en `false` por defecto. No se ejecutó ninguna operación de escritura en AWS. Terraform 1.17.0 ejecutó `fmt -recursive`, `init -backend=false` y `validate` correctamente con el proveedor AWS v5.100.0. El `plan` con los tres interruptores en `false` no pudo completarse: esta PC no tiene credenciales AWS. No se ejecutó `apply`.

| Requisito | Estado | Evidencia y límite |
|---|---|---|
| VPC, cuatro subredes y rutas | PARCIAL | Definición en `infra/network.tf`; `terraform validate` local correcto, sin despliegue. |
| APP y DATA privadas | PARCIAL | Definición de dos EC2 sin IP pública; falta instalación y verificación operativa. |
| EBS cifrado para PostgreSQL | PARCIAL | Volumen y attachment definidos; montaje persistente pendiente. |
| SSM privado | BLOQUEADO | Requiere NAT temporal o endpoints; no hay conectividad desplegada. |
| Docker APP/DATA | PARCIAL | Compose separados y configuración estructural validada. La imagen API se construyó y PostgreSQL, API y Grafana arrancaron localmente. Se añadió un instalador manual de Docker/Compose para Amazon Linux 2023; no se ejecutó en EC2. La transferencia prevista usa el mismo commit de un repositorio Git público en ambas instancias; falta publicarlo y probar el clonado. |
| Inventario EC2/EBS/snapshots/EIP | PARCIAL | API de solo lectura; sin prueba contra AWS. |
| Detección de huérfanos | PARCIAL | Volúmenes libres, snapshots antiguos e IPs sin asociación; sin prueba AWS. |
| Scheduler EC2 | PARCIAL | Vista previa sin ejecución ni proceso periódico. |
| Rightsizing | PARCIAL | Recomendación CPU con CloudWatch, sin cambio de tamaño. |
| Costos antes/después | PENDIENTE | Tabla y panel vacíos; faltan observaciones o escenarios etiquetados. |
| CPU, memoria, red y latencia | PENDIENTE | Solo CPU para rightsizing. Memoria requiere agente; no se inventan datos. |
| Auditoría de operaciones | PARCIAL | Tabla `audit_events` creada en PostgreSQL local; falta insertar eventos desde la API. |
| Seguridad y segmentación | PARCIAL | SG DATA permite 5432 solo desde APP. APP y DATA usan perfiles IAM separados; DATA tiene únicamente la política administrada básica de SSM. Falta verificar los permisos reales tras desplegar. |
| Resiliencia y escalabilidad | PENDIENTE | Se documentará como propuesta; no hay balanceador ni Auto Scaling. |

## Riesgos pendientes

- `src/seed.py` puede crear ocho EC2, volúmenes, snapshots e IPs públicas. No ejecutarlo para esta arquitectura.
- `src/teardown.py` borra recursos por tag y no conoce el estado Terraform; no usarlo con la infraestructura gestionada por Terraform.
- `enable_nat=true` añade NAT Gateway y Elastic IP facturables incluso si las EC2 están detenidas.
- `budget_limit_usd` es informativa: Terraform no crea Budget ni detiene gastos.
