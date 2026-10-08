import json
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
import threading

from jde_suite import mock_jde
from jde_suite.client import OrchestratorClient, OrchestratorError
from jde_suite.config import Config, load_config
from jde_suite.meters import advance, haversine_km
from jde_suite.query_parser import parse_query
from jde_suite.stock import format_reply, normalize_response, parse_number
from stock_bot.__main__ import handle_message
from iot_demo.server import make_handler


def cfg(**kw):
    base = dict(base_url="", user="demo", password="demo", verify_ssl=True,
                stock_orchestrator="Stock_Item_Availability",
                meter_orchestrator="JDE_ORCH_Sample_UpdateMeterReadings", default_branch_plant="550")
    base.update(kw)
    return Config(**base)


class ParserTests(unittest.TestCase):
    def test_item_and_branch(self):
        self.assertEqual(parse_query("LS501 in branch 550")["item"], "LS501")
        self.assertEqual(parse_query("do we have gt41021 at plant 560?")["branch_plant"], "560")

    def test_default_branch_and_missing_item(self):
        r = parse_query("hello there", "550")
        self.assertTrue(r["needs_item"])
        self.assertEqual(r["branch_plant"], "550")


class StockTests(unittest.TestCase):
    def test_parse_number_handles_comma(self):
        self.assertEqual(parse_number("1,5"), 1.5)
        self.assertEqual(parse_number(None), 0.0)
        self.assertEqual(parse_number("abc"), 0.0)

    def test_totals(self):
        s = normalize_response(mock_jde.stock_response("LS501", "550"), "LS501")
        self.assertEqual(s["totals"]["on_hand"], 165)
        self.assertEqual(s["available"], 165 - 20 - 10 - 5 + 60)
        self.assertEqual(s["rows"][0]["location"], "A-01-01")  # highest on hand first

    def test_missing_form_block(self):
        with self.assertRaises(ValueError):
            normalize_response({}, "X")

    def test_unknown_item_reply(self):
        s = normalize_response(mock_jde.stock_response("NOPE1", "550"), "NOPE1")
        self.assertIn("No stock records", format_reply("NOPE1", "550", s))


class MeterTests(unittest.TestCase):
    def test_haversine_zero_and_known(self):
        self.assertAlmostEqual(haversine_km((0, 0), (0, 0)), 0)
        self.assertAlmostEqual(haversine_km((0, 0), (0, 1)), 111.19, places=1)

    def test_advance(self):
        fuel, hours = advance(3.0, 3.0, 28.0)
        self.assertAlmostEqual(fuel, 3.0 + 28 * 0.35)
        self.assertAlmostEqual(hours, 4.0)
        self.assertAlmostEqual(advance(0, 0, 0.0)[1], 0.05)


class ConfigTests(unittest.TestCase):
    def test_defaults_are_safe(self):
        c = load_config({})
        self.assertTrue(c.use_mock)
        self.assertTrue(c.verify_ssl)
        self.assertEqual(c.user, "")


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock, cls.base = mock_jde.start()
        cls.client = OrchestratorClient(cfg(), cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.mock.shutdown()

    def test_bot_end_to_end(self):
        reply = handle_message("tem LS501 na filial 550", self.client, "550")
        self.assertIn("has physical stock", reply)
        self.assertIn("L2026-001", reply)

    def test_bot_asks_for_item(self):
        self.assertIn("Which item", handle_message("hi", self.client, "550"))

    def test_unreachable_server_reports_error(self):
        bad = OrchestratorClient(cfg(), "http://127.0.0.1:9/x")
        self.assertIn("Lookup failed", handle_message("LS501", bad, "550"))

    def test_auth_required(self):
        req = urllib.request.Request(f"{self.base}/Stock_Item_Availability", data=b"{}", method="POST")
        with self.assertRaises(Exception):
            urllib.request.urlopen(req)

    def test_iot_proxy(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.client, cfg(), True))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{srv.server_address[1]}/api/update-meter-readings"
            req = urllib.request.Request(url, data=json.dumps({"fuelReading": 4.126, "hourReading": 3.5}).encode(),
                                         method="POST", headers={"Content-Type": "application/json"})
            body = json.loads(urllib.request.urlopen(req).read())
            self.assertTrue(body["ok"])
            self.assertEqual(body["requestPayload"]["NewFuelMeterReading"], 4.13)
            self.assertEqual(mock_jde.METER_LOG[-1]["EquipmentNumber"], "30")
            bad = urllib.request.Request(url, data=b"{}", method="POST")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(bad)
            self.assertEqual(ctx.exception.code, 400)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
