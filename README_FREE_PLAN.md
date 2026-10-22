# Adaptación AWS Free Plan — FinOps

Este paquete parte del repositorio original y agrega `infra/` Terraform, `scripts/` y `docs/PLAN_AWS_FREE.md`.
**Estado:** infraestructura declarativa inicial, sin despliegue ni validación de Terraform en AWS. No es el proyecto final completo.

## Seguridad de costos
- `enable_network=false`, `enable_nat=false`, `enable_compute=false` por defecto.
- Nunca ejecutar `src/seed.py` en AWS real: puede crear 8 EC2.
- NAT y Elastic IP pueden cobrar incluso si se detienen las EC2.
- No crear recursos hasta revisar `terraform plan` y estimar costos de cada fase.

## Validar en una terminal con Terraform y AWS configurados
```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan
```
En Windows PowerShell: `Copy-Item terraform.tfvars.example terraform.tfvars`.
La cuenta usada en CloudShell puede diferir de la cuenta configurada en tu PC; comprobar `aws sts get-caller-identity`.

Consultar `docs/PLAN_AWS_FREE.md` para arquitectura, limitaciones y secuencia de despliegue.
