"""Unit tests for bmc_manager.utils.execution validators and request checks."""

import pytest

from bmc_manager.utils.errors import ServiceError
from bmc_manager.utils.execution import (
    BMCExecuteRequest,
    BMCValidateRequest,
    validate_cipher_suite,
    validate_ip,
    validate_password,
    validate_protocol,
    validate_username,
)


class TestValidateIp:
    def test_valid_ipv4(self):
        validate_ip("192.168.1.1")

    def test_valid_ipv6(self):
        validate_ip("::1")

    def test_invalid_ip_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            validate_ip("not-an-ip")
        assert exc_info.value.err.code == 4001


class TestValidateUsername:
    def test_non_empty_ok(self):
        validate_username("admin")

    def test_empty_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            validate_username("")
        assert exc_info.value.err.code == 4002

    def test_too_long_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            validate_username("a" * 65)
        assert exc_info.value.err.code == 4002


class TestValidatePassword:
    def test_non_empty_ok(self):
        validate_password("secret")

    def test_empty_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            validate_password("")
        assert exc_info.value.err.code == 4003


class TestValidateProtocol:
    def test_redfish_ok(self):
        validate_protocol("redfish")

    def test_ipmitool_ok(self):
        validate_protocol("ipmitool")

    def test_invalid_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            validate_protocol("http")
        assert exc_info.value.err.code == 4004


class TestValidateCipherSuite:
    def test_none_ok(self):
        validate_cipher_suite(None)

    def test_valid_range_ok(self):
        validate_cipher_suite(0)
        validate_cipher_suite(17)

    def test_out_of_range_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            validate_cipher_suite(18)
        assert exc_info.value.err.code == 4005

    def test_negative_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            validate_cipher_suite(-1)
        assert exc_info.value.err.code == 4005


class TestBMCValidateRequest:
    """Request dataclass runs validators in __post_init__."""

    def test_valid_request_creates(self):
        r = BMCValidateRequest(
            ip="192.168.1.1",
            username="admin",
            password="pwd",
            protocol="redfish",
        )
        assert r.ip == "192.168.1.1"
        assert r.protocol == "redfish"

    def test_invalid_ip_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            BMCValidateRequest(
                ip="invalid",
                username="admin",
                password="pwd",
                protocol="redfish",
            )
        assert exc_info.value.err.code == 4001

    def test_invalid_username_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            BMCValidateRequest(
                ip="192.168.1.1",
                username="",
                password="pwd",
                protocol="redfish",
            )
        assert exc_info.value.err.code == 4002

    def test_invalid_password_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            BMCValidateRequest(
                ip="192.168.1.1",
                username="admin",
                password="",
                protocol="redfish",
            )
        assert exc_info.value.err.code == 4003

    def test_invalid_protocol_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            BMCValidateRequest(
                ip="192.168.1.1",
                username="admin",
                password="pwd",
                protocol="snmp",
            )
        assert exc_info.value.err.code == 4004


class TestBMCExecuteRequest:
    """BMCExecuteRequest extends BMCRequest and adds method."""

    def test_valid_execute_request(self):
        r = BMCExecuteRequest(
            ip="10.0.0.1",
            username="u",
            password="p",
            protocol="ipmitool",
            method="validate_connection",
        )
        assert r.method == "validate_connection"
        assert r.params == {}

    def test_invalid_ip_in_execute_request_raises(self):
        with pytest.raises(ServiceError) as exc_info:
            BMCExecuteRequest(
                ip="999.999.999.999",
                username="u",
                password="p",
                protocol="redfish",
                method="list_users",
            )
        assert exc_info.value.err.code == 4001
