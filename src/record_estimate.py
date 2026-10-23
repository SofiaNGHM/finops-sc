"""Registra una comparación hipotética de costo EC2; nunca consulta ni modifica AWS."""

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def positive_decimal(value: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("Se requiere un número decimal") from exc
    if not number.is_finite() or number < 0:
        raise argparse.ArgumentTypeError("Se requiere un número finito no negativo")
    return number


def calculate(hourly_usd: Decimal, hours_before: Decimal, hours_after: Decimal) -> dict:
    if hourly_usd > Decimal("999999.999999") or any(
        hours > Decimal("9999999999.99") for hours in (hours_before, hours_after)
    ):
        raise ValueError("Valor fuera del rango de almacenamiento")
    if hourly_usd.as_tuple().exponent < -6 or any(
        hours.as_tuple().exponent < -2 for hours in (hours_before, hours_after)
    ):
        raise ValueError("Use máximo 6 decimales para tarifa y 2 para horas")
    before = hourly_usd * hours_before
    after = hourly_usd * hours_after
    return {
        "before_usd": str(before),
        "after_usd": str(after),
        "difference_usd": str(before - after),
        "source": "estimate",
        "aws_actual": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-id", required=True, help="Etiqueta del escenario hipotético")
    parser.add_argument("--hourly-usd", required=True, type=positive_decimal)
    parser.add_argument("--hours-before", required=True, type=positive_decimal)
    parser.add_argument("--hours-after", required=True, type=positive_decimal)
    parser.add_argument("--rate-source", required=True, help="Fuente y fecha de la tarifa supuesta")
    parser.add_argument("--write", action="store_true", help="Inserta en PostgreSQL; sin esta opción solo muestra cálculo")
    args = parser.parse_args()
    if not args.resource_id.startswith("hypothetical-"):
        parser.error("--resource-id debe comenzar por hypothetical-")
    try:
        result = calculate(args.hourly_usd, args.hours_before, args.hours_after)
    except ValueError as exc:
        parser.error(str(exc))
    result.update({
        "resource_id": args.resource_id,
        "hourly_usd": str(args.hourly_usd),
        "hours_before": str(args.hours_before),
        "hours_after": str(args.hours_after),
        "rate_source": args.rate_source,
        "persisted": False,
    })
    if args.write:
        import psycopg2
        from config.settings import POSTGRES

        recorded_at = datetime.now(timezone.utc)
        with psycopg2.connect(**POSTGRES) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO cost_scenarios
                       (recorded_at, scenario, resource_id, hourly_usd, hours, source)
                       VALUES (%s, %s, %s, %s, %s, 'estimate')""",
                    [
                        (recorded_at, "antes", args.resource_id, args.hourly_usd, args.hours_before),
                        (recorded_at, "después", args.resource_id, args.hourly_usd, args.hours_after),
                    ],
                )
                cursor.execute(
                    """INSERT INTO audit_events
                       (action, resource_id, mode, result, details)
                       VALUES (%s, %s, %s, %s, %s::jsonb)""",
                    ("record_cost_estimate", args.resource_id, "simulation", "recorded", json.dumps(result)),
                )
        result["persisted"] = True
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
