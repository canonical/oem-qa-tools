# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

from ops import testing

from charm import BMCServiceCharm


def test_start():
    # Arrange:
    ctx = testing.Context(BMCServiceCharm)
    # Act:
    state_out = ctx.run(ctx.on.start(), testing.State())
    # Assert:
    assert state_out.unit_status == testing.ActiveStatus()
