import json

import pytest
import requests

import restconf_client
from restconf_client import RestconfClient


class FakeResp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body
        self.text = json.dumps(body) if body is not None else ""

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SANDBOX_USER", "usuario")
    monkeypatch.setenv("SANDBOX_PASS", "secreto")
    monkeypatch.delenv("VERIFY_SSL", raising=False)
    return RestconfClient("host.ejemplo", 443)


def test_url_base(client):
    assert client.base == "https://host.ejemplo:443/restconf/data"
    assert client._url("a/b") == "https://host.ejemplo:443/restconf/data/a/b"


def test_credenciales_desde_entorno(client):
    assert client.auth == ("usuario", "secreto")


def test_credenciales_faltantes(monkeypatch):
    monkeypatch.delenv("SANDBOX_USER", raising=False)
    monkeypatch.setenv("SANDBOX_PASS", "x")
    with pytest.raises(KeyError):
        RestconfClient("host.ejemplo")


def test_verify_ssl_false_por_defecto(client):
    assert client.verify is False


def test_verify_ssl_true_por_entorno(monkeypatch):
    monkeypatch.setenv("SANDBOX_USER", "u")
    monkeypatch.setenv("SANDBOX_PASS", "p")
    monkeypatch.setenv("VERIFY_SSL", "TRUE")
    assert RestconfClient("host.ejemplo").verify is True


def test_get_devuelve_json_y_envia_parametros(client, monkeypatch):
    visto = {}

    def fake_get(url, **kwargs):
        visto["url"] = url
        visto.update(kwargs)
        return FakeResp(200, {"clave": "valor"})

    monkeypatch.setattr(restconf_client.requests, "get", fake_get)
    assert client.get("ruta/x") == {"clave": "valor"}
    assert visto["url"].endswith("/restconf/data/ruta/x")
    assert visto["headers"]["Accept"] == "application/yang-data+json"
    assert visto["auth"] == ("usuario", "secreto")
    assert visto["verify"] is False
    assert visto["timeout"] == 30


def test_get_404_devuelve_none(client, monkeypatch):
    monkeypatch.setattr(restconf_client.requests, "get",
                        lambda url, **kw: FakeResp(404))
    assert client.get("no/existe") is None


def test_get_cuerpo_vacio_devuelve_none(client, monkeypatch):
    monkeypatch.setattr(restconf_client.requests, "get",
                        lambda url, **kw: FakeResp(200))
    assert client.get("vacio") is None


def test_get_error_500_lanza_excepcion(client, monkeypatch):
    monkeypatch.setattr(restconf_client.requests, "get",
                        lambda url, **kw: FakeResp(500))
    with pytest.raises(requests.HTTPError):
        client.get("falla")


@pytest.mark.parametrize("codigo", [201, 204])
def test_put_devuelve_codigo_http(client, monkeypatch, codigo):
    visto = {}

    def fake_put(url, **kwargs):
        visto.update(kwargs)
        return FakeResp(codigo)

    monkeypatch.setattr(restconf_client.requests, "put", fake_put)
    assert client.put("ruta", {"a": 1}) == codigo
    assert visto["json"] == {"a": 1}
    assert visto["headers"]["Content-Type"] == "application/yang-data+json"


def test_put_error_400_lanza_excepcion(client, monkeypatch):
    monkeypatch.setattr(restconf_client.requests, "put",
                        lambda url, **kw: FakeResp(400))
    with pytest.raises(requests.HTTPError):
        client.put("ruta", {})


def test_patch_devuelve_204(client, monkeypatch):
    visto = {}

    def fake_patch(url, **kwargs):
        visto["url"] = url
        visto.update(kwargs)
        return FakeResp(204)

    monkeypatch.setattr(restconf_client.requests, "patch", fake_patch)
    assert client.patch("nodo", {"a": 1}) == 204
    assert visto["json"] == {"a": 1}
    assert visto["url"].endswith("/restconf/data/nodo")


def test_patch_error_lanza_excepcion(client, monkeypatch):
    monkeypatch.setattr(restconf_client.requests, "patch",
                        lambda url, **kw: FakeResp(400))
    with pytest.raises(requests.HTTPError):
        client.patch("nodo", {})
