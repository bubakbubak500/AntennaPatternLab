from urllib.parse import parse_qs, urlparse

from antenna_pattern_lab.domain import Spot
from antenna_pattern_lab.history import HistoryClient, parse_history_xml


XML = b"""<?xml version="1.0"?>
<receptionReports>
  <lastSequenceNumber value="70979911017"/>
  <receptionReport receiverCallsign="OH8AV" receiverLocator="KP25TB"
    senderCallsign="HS0ZOY" senderLocator="OK14MQ" frequency="14074371"
    flowStartSeconds="1784753127" mode="FT8" sNR="-1" />
  <receptionReport receiverCallsign="N2ZZ" receiverLocator="EM93DN"
    senderCallsign="HS0ZOY" senderLocator="OK14MQ"
    flowStartSeconds="1784753127" mode="FT8" />
</receptionReports>"""


def test_history_xml_parser_skips_incomplete_reports():
    result = parse_history_xml(XML, "20m")
    assert result.report_count == 2
    assert result.skipped_count == 1
    assert result.last_sequence == 70_979_911_017
    assert len(result.spots) == 1
    assert result.spots[0].rx_call == "OH8AV"
    assert result.spots[0].snr_db == -1
    assert result.spots[0].band == "20m"


def test_history_client_builds_bounded_query():
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def read(self):
            return XML

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return Response()

    result = HistoryClient(opener=opener).fetch("hs0zoy", "20m", 6, "OK14MQ")
    query = parse_qs(urlparse(captured["url"]).query)
    assert query["senderCallsign"] == ["HS0ZOY"]
    assert query["flowStartSeconds"] == ["-21600"]
    assert query["frange"] == ["14000000-14350000"]
    assert query["mode"] == ["FT8"]
    assert result.report_count == 2


def test_history_and_mqtt_versions_share_deduplication_key():
    historical = parse_history_xml(XML, "20m").spots[0]
    live = Spot.from_pskr_payload(
        {
            "sq": 123,
            "f": 14074371,
            "md": "FT8",
            "rp": -1,
            "t": 1784753140,
            "t_tx": 1784753127,
            "sc": "HS0ZOY",
            "sl": "OK14MQ",
            "rc": "OH8AV",
            "rl": "KP25TB",
            "b": "20m",
        }
    )
    assert historical.source_key == live.source_key
