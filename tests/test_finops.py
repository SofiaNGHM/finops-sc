"""Pruebas locales: nunca llaman a AWS ni modifican recursos."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src import finops


def instancia(identificador, entorno="dev", horario="office-hours", estado="running", tipo="t3.small"):
    return {
        "InstanceId": identificador,
        "InstanceType": tipo,
        "State": {"Name": estado},
        "Tags": [{"Key": "Project", "Value": "finops-demo"},
                 {"Key": "Environment", "Value": entorno},
                 {"Key": "Schedule", "Value": horario}],
    }


class FinopsTests(unittest.TestCase):
    def test_huerfanos_distingue_recursos_en_uso(self):
        antiguo = datetime.now(timezone.utc) - timedelta(days=40)
        datos = {
            "instances": [],
            "volumes": [
                {"VolumeId": "vol-libre", "State": "available", "Attachments": [], "Size": 8},
                {"VolumeId": "vol-uso", "State": "in-use", "Attachments": [{}], "Size": 8},
            ],
            "snapshots": [{"SnapshotId": "snap-antiguo", "StartTime": antiguo}],
            "public_ips": [
                {"AllocationId": "eip-libre"},
                {"AllocationId": "eip-uso", "AssociationId": "eipassoc-1"},
            ],
        }
        ids = {item["id"] for item in finops.huerfanos(datos)["findings"]}
        self.assertEqual(ids, {"vol-libre", "snap-antiguo", "eip-libre"})

    def test_programacion_excluye_produccion_y_solo_simula(self):
        lunes_22_utc = datetime(2026, 10, 19, 22, tzinfo=timezone.utc)
        datos = {"instances": [
            instancia("i-dev"),
            instancia("i-prod", entorno="prod"),
            instancia("i-always", horario="always-on"),
        ]}
        resultado = finops.programacion(datos, lunes_22_utc)
        self.assertEqual(resultado["mode"], "simulation")
        self.assertEqual(resultado["actions"], [{"id": "i-dev", "would": "stop"}])

    @patch("src.finops.cpu_promedio", return_value=None)
    def test_rightsizing_sin_metricas_no_inventa_recomendacion(self, cpu_mock):
        resultado = finops.recomendaciones({"instances": [instancia("i-dev")]})
        self.assertEqual(resultado["recommendations"], [])
        cpu_mock.assert_called_once_with("i-dev")


if __name__ == "__main__":
    unittest.main()
