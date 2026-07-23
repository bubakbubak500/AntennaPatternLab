from datetime import datetime, timezone

from antenna_pattern_lab.ui_formatting import (
    TechnicalTableItem,
    compact_source,
    format_bearing,
    format_distance_km,
    format_frequency_mhz,
    format_signed_snr,
    format_utc_timestamp,
)


def test_technical_report_formatting_is_consistent():
    stamp = datetime(2026, 7, 23, 12, 34, tzinfo=timezone.utc)
    assert format_utc_timestamp(stamp) == "2026-07-23 12:34"
    assert format_signed_snr(4) == "+4"
    assert format_signed_snr(-7) == "-7"
    assert format_signed_snr(1.25, decimals=1) == "+1.2"
    assert format_distance_km(10133.4) == "10,133"
    assert format_bearing(41.8) == "42°"
    assert format_frequency_mhz(14_074_123) == "14.074123"
    assert compact_source("pskreporter") == "PSKR"
    assert compact_source("adif") == "ADIF"


def test_technical_table_item_retains_numeric_sort_value():
    low = TechnicalTableItem("9", sort_value=9, numeric=True)
    high = TechnicalTableItem("10", sort_value=10, numeric=True)
    assert low < high
    assert low.textAlignment()
