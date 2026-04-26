"""Tests for is_agentscore_test_address + AGENTSCORE_TEST_ADDRESSES."""

from agentscore import AGENTSCORE_TEST_ADDRESSES, is_agentscore_test_address


def test_returns_true_for_each_of_seven_reserved_addresses():
    for i in range(1, 8):
        addr = "0x" + "0" * 39 + str(i)
        assert is_agentscore_test_address(addr) is True


def test_matches_case_insensitively():
    assert is_agentscore_test_address("0x0000000000000000000000000000000000000001".upper()) is True


def test_returns_false_for_addresses_outside_reserved_range():
    assert is_agentscore_test_address("0x0000000000000000000000000000000000000008") is False
    assert is_agentscore_test_address("0xabcabcabcabcabcabcabcabcabcabcabcabcabca") is False


def test_returns_false_for_none_and_empty():
    assert is_agentscore_test_address(None) is False
    assert is_agentscore_test_address("") is False


def test_exports_exactly_seven_addresses():
    assert len(AGENTSCORE_TEST_ADDRESSES) == 7


def test_every_exported_address_passes_recognizer():
    for addr in AGENTSCORE_TEST_ADDRESSES:
        assert is_agentscore_test_address(addr) is True
