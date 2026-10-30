import json
import unittest
from pathlib import Path

import dashboard_server as dashboard


class DailyPuVariantTest(unittest.TestCase):
    def test_selecao_preserva_pu_e_fluxos_das_bases_publicadas(self):
        for operation in ("axs01", "axs02", "axs05", "axs06"):
            path = Path(__file__).parent / "data" / "operations" / f"{operation}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            before = json.dumps(payload)
            for option in payload["variant_options"]:
                with self.subTest(operation=operation, variant=option["id"]):
                    selected = dashboard.apply_variant(payload, option["id"])
                    expected = payload["variants"][option["id"]]
                    for field in ("summary", "series", "table_series", "timeline"):
                        self.assertEqual(selected[field], expected[field])
                    if option["id"] == "total":
                        for component in payload["variant_options"]:
                            if component["id"] == "total":
                                continue
                            actual = [row for row in selected["daily_pu_series"] if row["instrument_label"] == component["label"]]
                            original = payload["variants"][component["id"]]["daily_pu_series"]
                            self.assertEqual([(row["date"], row["pu_cheio"]) for row in actual],
                                             [(row["date"], row["pu_cheio"]) for row in original])
                    else:
                        self.assertEqual(selected["daily_pu_series"], expected["daily_pu_series"])
            self.assertEqual(json.dumps(payload), before)


if __name__ == "__main__":
    unittest.main()
