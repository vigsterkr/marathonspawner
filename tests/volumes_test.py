from __future__ import absolute_import, division, print_function

import types
import pytest
from traitlets.config import LoggingConfigurable


def test_default_format_volume_name(monkeypatch):
    from marathonspawner.marathonspawner import MarathonSpawner
    d = MarathonSpawner()
    d.user = types.SimpleNamespace(name='moo')
    d.volumes = [{"containerPath": "/foo/{username}", "hostPath": "/bar/{username}", "mode": "RW"}]
    assert d.get_volumes()[0].containerPath == '/foo/moo'
