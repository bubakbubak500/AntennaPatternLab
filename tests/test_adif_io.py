from antenna_pattern_lab.adif_io import import_adif, parse_adif_records


def _field(name: str, value: str) -> str:
    return f"<{name}:{len(value)}>{value}"


def test_wsjt_x_adif_qso_maps_received_report_to_remote_receiver(tmp_path):
    record = "".join(
        (
            _field("CALL", "DL1ABC"),
            _field("GRIDSQUARE", "JO62QM"),
            _field("STATION_CALLSIGN", "OK7PS"),
            _field("MY_GRIDSQUARE", "JN79AA"),
            _field("MODE", "MFSK"),
            _field("SUBMODE", "FT8"),
            _field("RST_RCVD", "-07"),
            _field("FREQ", "14.074"),
            _field("BAND", "20M"),
            _field("QSO_DATE", "20260723"),
            _field("TIME_ON", "201530"),
            "<EOR>",
        )
    )
    path = tmp_path / "wsjtx_log.adi"
    path.write_text(
        _field("ADIF_VER", "3.1.4") + "<EOH>" + record,
        encoding="utf-8",
    )

    result = import_adif(path)

    assert result.record_count == 1
    assert result.skipped_count == 0
    assert len(result.spots) == 1
    spot = result.spots[0]
    assert spot.tx_call == "OK7PS"
    assert spot.tx_grid == "JN79AA"
    assert spot.rx_call == "DL1ABC"
    assert spot.rx_grid == "JO62QM"
    assert spot.snr_db == -7
    assert spot.frequency_hz == 14_074_000
    assert spot.band == "20m"
    assert spot.mode == "FT8"
    assert spot.source == "adif"
    assert spot.observed_at.isoformat() == "2026-07-23T20:15:30+00:00"


def test_adif_without_header_uses_fallback_station_and_skips_unusable_qso(tmp_path):
    valid = "".join(
        (
            _field("CALL", "G4AAA"),
            _field("GRIDSQUARE", "IO91AA"),
            _field("MODE", "FT8"),
            _field("RST_RCVD", "+03"),
            _field("BAND", "20M"),
            _field("QSO_DATE", "20260723"),
            _field("TIME_ON", "2015"),
            "<EOR>",
        )
    )
    unusable = _field("CALL", "N0GRID") + _field("MODE", "FT8") + "<EOR>"
    path = tmp_path / "mixed.adif"
    path.write_text(valid + unusable, encoding="utf-8")

    result = import_adif(
        path,
        fallback_tx_call="ok7ps",
        fallback_tx_grid="jn79aa",
    )

    assert result.record_count == 2
    assert result.skipped_count == 1
    assert result.spots[0].frequency_hz == 14_074_000
    assert result.spots[0].observed_at.second == 0


def test_adif_parser_honors_field_length_even_when_value_contains_angle_bracket():
    records = parse_adif_records(_field("COMMENT", "a<b") + "<EOR>")
    assert records == [{"COMMENT": "a<b"}]
