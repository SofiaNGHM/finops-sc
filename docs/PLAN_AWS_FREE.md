# FinOps en AWS Free Plan (cuenta personal, NO AWS Academy Learner Lab)

## Validaciones reales reportadas por la usuaria (us-east-2, 2026-10-22)
- CloudShell AWS CLI autenticado con rol asumido AccountFullAccessRole.
- Lecturas exitosas VPC/subnets/AZ/EC2/SSM/Lambda/EventBridge/ALB.
- `DryRunOperation`: CreateVpc, CreateSecurityGroup, CreateVolume, CreateNatGateway, RunInstances (t3.micro).
- IAM simulation `allowed`: CreateRole, CreateInstanceProfile, AddRoleToInstanceProfile, AttachRolePolicy, PassRole.
- `list-instance-profiles` vacío. IAM profile será creado por Terraform cuando compute se habilite.
- Estos resultados NO verifican cuotas, elegibilidad gratuita, créditos restantes ni acceso SSM.

## Arquitectura
- VPC propia 10.20.0.0/16, 2 públicas, APP privada 10.20.11.0/24 y DATA privada 10.20.21.0/24.
- 2 EC2 sin IP pública, SG APP sin inbound y SG DATA solo TCP 5432 desde APP.
- IAM role/profile con AmazonSSMManagedInstanceCore; acceso por SSM requiere red hacia endpoints.
- NAT Gateway (1) y Elastic IP solo si `enable_nat=true`; caro incluso con instancias detenidas.
- EBS cifrado gp3 adicional en DATA, volumen NO formateado ni montado automáticamente.

## Costos y advertencias
- AWS Free Plan/creditos NO implica recursos gratuitos. Consultar Billing > Free Plan y AWS Pricing Calculator.
- NAT Gateway se factura por hora y datos; Elastic IP pública puede facturarse. EBS se factura por almacenamiento.
- EC2, transferencias y CloudWatch pueden generar cargos; no afirmar elegibilidad de t3.micro sin verificar oferta vigente.
- No hay ALB, Auto Scaling, endpoints privados ni scheduler en Terraform: son pendientes, no se debe reportar como implementados.
- Presupuesto `budget_limit_usd` es solo variable informativa: NO crea alarmas ni limita el gasto.
- `terraform plan` NO es una estimación de precios; revisar costos aparte.

## Etapas seguras
1. Instalar Terraform y AWS CLI; validar identidad y cuenta, región, cuotas, Free Plan y créditos.
2. `cd infra; cp terraform.tfvars.example terraform.tfvars; terraform init; terraform fmt -check; terraform validate; terraform plan`.
3. Defaults: no crea recursos. Revisar plan y `terraform state` antes de cada `apply`.
4. Etapa red: habilitar `enable_network=true`, NAT y compute falsos; revisar y aprobar costos, luego `apply` si se decide.
5. Etapa demo: NAT y compute verdaderos solo tras aprobación explícita del costo por hora y presupuesto.
6. Antes de instalar Docker, confirmar SSM conectado, NAT funcional y EBS montado; configuración no automatizada en esta versión.
7. Fin de demo: `terraform destroy` desde el mismo estado; verificar EC2, NAT, EIP, EBS y facturación en la región.

## Limitaciones técnicas pendientes
- Sin NAT no hay salida pública para instalar paquetes ni para SSM (salvo que se agreguen VPC endpoints de pago).
- El APP no tiene entrada HTTP; Grafana/API solo serían accesibles mediante túnel SSM o diseño de exposición controlada pendiente.
- EBS adicional requiere partición/formato/montaje persistente; no automatizado para evitar pérdida accidental de datos.
- Terraform state local contiene información sensible: no subir `.tfstate`, `.tfvars` con secretos ni credenciales.
- Scheduler FinOps, detección de huérfanos, dashboard de costos, monitoreo y autoscaling siguen pendientes de implementación y pruebas.
- `src/seed.py` del repositorio original puede crear 8 instancias en la VPC predeterminada: NO EJECUTAR en AWS Free Plan.
