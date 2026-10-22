# Plataforma FinOps y Scheduling Automatizado (Tema 13)

> **Arquitectura vigente:** dos EC2 privadas (APP y DATA), con NAT temporal solo tras autorización. Ver [RUNBOOK.md](docs/RUNBOOK.md) y [STATUS.md](docs/STATUS.md). El contenido histórico que sigue describe otro prototipo: crear ocho EC2, usuarios IAM o recursos de prueba y ejecutar `src/teardown.py` no forma parte del laboratorio actual. No ejecutar `terraform apply` ni `terraform destroy` sin autorización explícita.

## Contexto del proyecto

Proyecto final universitario del curso **Servicios Cloud (UTP, 2026-2)**. Es un **prototipo demostrativo**, no un sistema de producción.

**Problema:** una empresa de software gasta de más porque sus entornos de desarrollo y pruebas quedan encendidos fuera del horario laboral.

**Objetivo:** un sistema que apaga, enciende y redimensiona recursos automáticamente, detecta recursos huérfanos y muestra en un dashboard el costo antes vs. después.

**Restricciones:**
- **Costo controlado:** se usa una **cuenta real de AWS con $100 de créditos gratuitos**. Meta: gastar **menos de $20** en todo el proyecto. Los recursos en AWS solo existen mientras se prueba o se hace la demo; se destruyen al terminar cada sesión.
- **Lo local sigue siendo local:** PostgreSQL y Grafana corren en Docker en la máquina del alumno (costo cero).
- **Plazo:** 3 semanas.
- **Código simple y legible:** se prioriza que funcione y se entienda en una sustentación, no la robustez de producción.

## Alineación con el sílabo (no perder de vista)

| Eje de la matriz | Qué lo cubre |
|---|---|
| U1 – Limitaciones y Eficiencia | Virtualización en EC2 real (Nitro), límites de la cuenta (cuotas de vCPU, free plan) |
| U2 – Planificación (Scheduling) y Asignación | Scheduler por tiempo, por reglas y por uso + algoritmo FFD de consolidación |
| U2 – Monitoreo (series temporales, métricas) | CPU real de CloudWatch → PostgreSQL + Grafana |
| U3 – Centro de datos y eficiencia en costos | KPI de energía (kWh, PUE) y CO₂, comparativa física vs. nube |

## Stack

- **AWS real** (región `us-east-2` Ohio — la SCP de la organización de la cuenta bloquea las demás regiones; mismo precio que us-east-1): EC2, EBS, snapshots, Elastic IPs, CloudWatch (métricas básicas, gratis).
- **Docker + docker-compose** solo para PostgreSQL y Grafana.
- **Python 3.11+** con `boto3`, `psycopg2-binary`, `APScheduler`.
- **PostgreSQL** como almacén de métricas (datasource nativo de Grafana).
- **Grafana OSS** con provisioning (datasource y dashboard como código).
- **Respaldo:** `aws_client.py` acepta `AWS_ENDPOINT_URL` opcional. Vacío = AWS real; si se define (p. ej. `http://localhost:4566`) apunta a LocalStack/moto. Sirve para desarrollar sin gastar y como plan B si la cuenta falla.

## Guardarraíles de costo y seguridad (OBLIGATORIOS)

Estos puntos aplican a **todas** las fases. Claude debe respetarlos sin excepción:

1. **Credenciales:** usar un usuario IAM dedicado (no la cuenta root) con un perfil del AWS CLI (`AWS_PROFILE=finops-demo`). **Nunca** escribir access keys en el código, en `.env.example` ni en commits. `.env` va en `.gitignore`.
2. **Tag de proyecto:** todo recurso creado lleva `Project=finops-demo`. Los scripts **solo** listan y actúan sobre recursos con ese tag (filtro en cada llamada `describe_*`). Así nunca se toca nada ajeno al proyecto.
3. **Instancias pequeñas:** solo `t3.nano`, `t3.micro` y `t3.small`. Volúmenes `gp3` de 8 GB. AMI Amazon Linux 2023 obtenida por parámetro SSM (no AMI fija).
4. **Sin IPv4 públicas:** las instancias se lanzan sin IP pública (AWS cobra ~$0.005/h por cada IPv4 pública). No se necesita SSH.
5. **Pocos recursos:** 8 instancias en total (no 20). Los huérfanos se limitan a 3 volúmenes, 2 snapshots y 1–2 Elastic IPs.
6. **Teardown siempre disponible:** `src/teardown.py` borra todo lo que tenga `Project=finops-demo`. Se ejecuta al terminar cada sesión de trabajo.
7. **Presupuesto con alerta:** crear un AWS Budget de $10 con aviso por email al 50 % y 100 % (se hace a mano en la consola en la Fase 0; Claude da los pasos).
8. **Confirmación antes de gastar:** cualquier script que cree recursos en AWS muestra un resumen (cantidad, tipo, costo estimado/hora) y pide confirmación, salvo con `--yes`.

**Costo estimado de referencia (aproximado):** 8 × t3.micro ≈ $0.08/h encendidas. Una sesión de 3 h ≈ $0.25. Olvidarlas encendidas un mes ≈ $60 → por eso el teardown y el budget son obligatorios.

## Estructura objetivo del repositorio

```
finops-scheduler/
├── CLAUDE.md
├── README.md
├── docker-compose.yml     # solo PostgreSQL + Grafana
├── .env.example           # AWS_PROFILE, AWS_REGION, AWS_ENDPOINT_URL (opcional), datos de Postgres
├── .gitignore
├── requirements.txt
├── config/
│   ├── settings.py        # región, perfil, tag de proyecto, horario laboral, aceleración del reloj
│   └── pricing.py         # tabla fija de precios USD/hora por tipo de instancia (us-east-2)
├── db/
│   └── schema.sql         # tablas de métricas
├── src/
│   ├── aws_client.py      # clientes boto3 (AWS real o endpoint opcional)
│   ├── seed.py            # crea instancias con tags y recursos huérfanos
│   ├── teardown.py        # borra todo lo que tenga Project=finops-demo
│   ├── clock.py           # reloj simulado (1 min real = 1 h simulada)
│   ├── scheduler.py       # políticas de stop/start
│   ├── rightsizing.py     # redimensionamiento por CPU (CloudWatch)
│   ├── orphans.py         # detección de huérfanos
│   ├── consolidation.py   # algoritmo First Fit Decreasing
│   ├── energy.py          # kWh y CO2 ahorrados
│   └── synthetic.py       # histórico sintético antes/después
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       └── dashboards/
└── docs/
    └── demo.md            # guion de la demo
```

## Convenciones

- Código y comentarios en **español** (nombres de variables pueden ir en inglés si es más natural con boto3).
- Funciones cortas, sin abstracciones innecesarias. Nada de clases si una función basta.
- Toda configuración en `config/settings.py` o `.env`, nunca valores sueltos en el código.
- **Regla de seguridad del scheduler:** nunca tocar recursos con `Environment=prod` ni `Schedule=always-on`, y nunca recursos sin `Project=finops-demo`.
- Todo script que ejecute acciones sobre recursos tiene modo `--dry-run`.
- Tags usados: `Project` (finops-demo), `Environment` (dev | test | prod), `Schedule` (office-hours | always-on | weekend-off), `Owner`, `CostCenter`.
- Precios y factores de energía son **valores de referencia**: dejarlos comentados como aproximados.
- Las llamadas a AWS manejan errores comunes (`UnauthorizedOperation`, `IncorrectInstanceState`, límites de cuota) con un mensaje claro, sin trazas largas.

## Forma de trabajo: POR FASES

**Instrucciones obligatorias para Claude:**

1. Trabaja **una sola fase a la vez**. No crees archivos de fases futuras.
2. Al iniciar una fase, explica en 3–5 líneas qué vas a hacer.
3. Al terminarla, indica **cómo probarla** (comandos exactos y resultado esperado) y **cuánto cuesta aproximadamente** la prueba en AWS.
4. **Detente y espera** a que el usuario confirme con "continúa" o similar antes de pasar a la siguiente.
5. Marca la fase como completada en la sección "Progreso" de este archivo.
6. Sugiere un mensaje de commit al cerrar cada fase.
7. **Claude no ejecuta comandos que creen o modifiquen recursos en AWS** sin que el usuario lo pida explícitamente; solo `--dry-run` o lecturas (`describe_*`).
8. Si una API de AWS falla por permisos, cuota o restricción del free plan, avisa y propone la alternativa más simple (p. ej. simular ese dato en PostgreSQL); no la implementes sin confirmar.

---

### Fase 0 — Entorno base y cuenta AWS
- Pasos manuales (Claude los explica, el usuario los hace en la consola): usuario IAM con permisos sobre EC2, CloudWatch (lectura) y SSM `GetParameter`; `aws configure --profile finops-demo`; AWS Budget de $10 con alertas.
- `docker-compose.yml` con PostgreSQL y Grafana.
- `requirements.txt`, `.env.example`, `.gitignore`, `config/settings.py`, `src/aws_client.py`.
- **Prueba:** `aws sts get-caller-identity --profile finops-demo` muestra el usuario IAM; `docker compose up -d` levanta los contenedores; un script mínimo lista instancias EC2 con `Project=finops-demo` (lista vacía) sin errores. Costo: $0.

### Fase 1 — Recursos de prueba (`seed.py` + `teardown.py`)
- `seed.py`: 8 instancias con tags variados — 4 dev/test `office-hours`, 2 `weekend-off`, 2 prod `always-on`. Mezcla de `t3.small` (candidatas a right-sizing) y `t3.micro`.
- Huérfanos: 3 volúmenes EBS sin adjuntar (1 GB, gp3), 2 snapshots, 1–2 Elastic IPs sin asociar.
- Como AWS no permite "envejecer" un snapshot, se agrega el tag `SimulatedAgeDays` para la demo.
- `teardown.py`: termina instancias, borra volúmenes y snapshots, libera Elastic IPs (todo filtrado por `Project=finops-demo`), con `--dry-run`.
- **Prueba:** `seed.py --dry-run`, luego `seed.py`; verificar en consola/CLI los tags; `teardown.py` deja la cuenta limpia. Costo: centavos.

### Fase 2 — Base de datos de métricas
- `db/schema.sql`: tablas para estado de instancias por tick, acciones del scheduler, huérfanos detectados, cambios de right-sizing.
- Carga automática del esquema al levantar PostgreSQL.
- **Prueba:** conectarse y ver las tablas vacías. Costo: $0.

### Fase 3 — Reloj simulado + scheduler (estrategias por tiempo y por reglas)
- `clock.py`: reloj acelerado configurable (por defecto 1 min real = 1 h simulada; un ciclo stop/start real tarda ~30–60 s, así que no bajar de eso).
- `scheduler.py`: encendido 08:00, apagado 20:00, lunes a viernes; fin de semana apagado para `weekend-off`; respeta las reglas de tags.
- Llamadas reales `stop_instances` / `start_instances`; cada tick registra el estado y las acciones en PostgreSQL.
- **Prueba:** correr unos minutos y ver en la consola de AWS y en PostgreSQL instancias pasar de `running` a `stopped`. Costo: centavos.

### Fase 4 — Right-sizing (estrategia por uso)
- CPU desde **CloudWatch** (`CPUUtilization`, promedio). Instancias ociosas darán ~0–2 %; si no hay datos aún, usar un valor simulado guardado en un tag `SimulatedCpu`.
- Si el promedio es < 10 %, bajar un tipo (`t3.small` → `t3.micro` → `t3.nano`). En AWS real esto exige: stop → `modify_instance_attribute` → start.
- Registrar el cambio y el ahorro estimado.
- **Prueba:** ver instancias con nuevo tipo en la consola y el registro en la base de datos. Costo: centavos.

### Fase 5 — Detección de huérfanos
- `orphans.py`: volúmenes `available`, snapshots con antigüedad > N días (real o `SimulatedAgeDays`), Elastic IPs sin `AssociationId`.
- Costo mensual estimado por hallazgo; opción `--cleanup` con confirmación.
- **Prueba:** reporte en consola + registros en PostgreSQL. Costo: $0 (solo lecturas).

### Fase 6 — Algoritmo de consolidación (FFD)
- `consolidation.py`: First Fit Decreasing sobre las cargas (CPU/RAM) para minimizar servidores. Es un cálculo local, **no** mueve instancias reales.
- Puede usar las 8 instancias reales más una flota simulada más grande (p. ej. 40 VMs) para que el resultado sea vistoso.
- Comparar con Round Robin o Best Fit (tabla de resultados).
- **Prueba:** salida tipo "de 40 VMs a 12 hosts, ahorro X USD/mes". Costo: $0.

### Fase 7 — Energía e histórico sintético
- `energy.py`: kWh ahorrados = horas apagadas × potencia por servidor × PUE (~1.5); CO₂ con un factor de emisión de referencia.
- `synthetic.py`: 30 días "antes" (24/7) y 30 días "después" (con políticas) para que el dashboard tenga datos, ya que no se mantendrán instancias reales encendidas un mes.
- **Prueba:** consultas SQL que devuelvan costo antes vs. después. Costo: $0.

### Fase 8 — Dashboard en Grafana (provisioning)
- Datasource PostgreSQL y dashboard JSON provisionados.
- Paneles: KPIs (costo antes, después, % ahorro, kWh, CO₂), costo diario con annotation de activación, costo por entorno/equipo, tabla de huérfanos, state timeline de instancias (datos reales de AWS), resultado de consolidación.
- Variable de dashboard para elegir horario laboral (escenarios precalculados).
- Auto-refresh de 5 s.
- **Prueba:** abrir `http://localhost:3000` y ver el dashboard sin configurar nada a mano. Costo: $0.

### Fase 9 — Documentación y demo
- `README.md`: requisitos (cuenta AWS, perfil CLI), cómo levantar el proyecto en 3 comandos y cómo destruir todo.
- `docs/demo.md`: guion de 5 minutos para la sustentación, incluyendo `seed.py` al inicio y `teardown.py` al final, y mostrar la consola de AWS en vivo.
- Nota de cómo se llevaría a producción sin una PC encendida: EventBridge Scheduler + Lambda ejecutando el mismo código boto3 (opcional implementarlo si sobra tiempo y crédito; Lambda y EventBridge entran en la capa gratuita).

---

## Progreso

- [x] Fase 0 — Entorno base y cuenta AWS
- [ ] Fase 1 — Recursos de prueba
- [ ] Fase 2 — Base de datos de métricas
- [ ] Fase 3 — Reloj simulado + scheduler
- [ ] Fase 4 — Right-sizing
- [ ] Fase 5 — Detección de huérfanos
- [ ] Fase 6 — Algoritmo de consolidación (FFD)
- [ ] Fase 7 — Energía e histórico sintético
- [ ] Fase 8 — Dashboard en Grafana
- [ ] Fase 9 — Documentación y demo
