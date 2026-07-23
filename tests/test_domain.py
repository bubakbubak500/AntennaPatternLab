from datetime import timezone

from antenna_pattern_lab.domain import Spot


def test_pskr_v2_payload_is_parsed():
    spot = Spot.from_pskr_payload(
        {
            "sq": 30142870791,
            "f": 21074653,
            "md": "FT8",
            "rp": -5,
            "t": 1662407712,
            "t_tx": 1662407697,
            "sc": "ok7ps",
            "sl": "JN79aa",
            "rc": "CU3AT",
            "rl": "HM68jp",
            "b": "15m",
        }
    )
    assert spot.tx_call == "OK7PS"
    assert spot.snr_db == -5
    assert spot.frequency_hz == 21_074_653
    assert spot.observed_at.tzinfo == timezone.utc
    assert spot.source_key.startswith("spot:")
