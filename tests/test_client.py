#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `hpio` package."""

import pytest
from click.testing import CliRunner
import os
from hpio import Client


@pytest.fixture
def client():
    return Client()

class TestClientCreation():

    def test_initial_state(self):
        assert self.model = None
        assert self.sensors = None

    def test_set_port(self):
        client = Client(port='/dev/test')
        assert client.port == '/dev/test'

    def test_autoport_unix(self):
        client = Client()
        assert client.port == '/dev/ttyAMA0'

    def test_autoport_win(self, monkeypatch):
        monkeypatch.setattr(os, 'name', 'nt')
        client = Client()
        assert client.port == 'COM1'

class TestConnect():

    def test_
