from __future__ import annotations

import os

import pytest

import nrn


@pytest.mark.integration
def test_query_reader_information_with_real_hardware():
    port = os.getenv("NRN_SERIAL_PORT")
    if not port:
        pytest.skip("NRN_SERIAL_PORT is not set")

    reader = nrn.create_reader(port)
    reader.open()
    try:
        info = reader.Query_Reader_Information()
        assert isinstance(info, dict)
    finally:
        reader.close()
