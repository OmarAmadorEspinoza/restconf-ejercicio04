import pytest
import requests
import yaml

import deploy
import verify
from payloads import build_items

CFG = {
    "host": "192.0.2.1",
    "port": 443,
    "loopback": {"id": 201, "description": "MGMT-LOOPBACK-DEVOPS",
                 "ip": "10.201.201.1", "mask": "255.255.255.255"},
    "snmp": {"community": "DEVOPS-RO", "location": "Lab-DevNet",
             "contact": "equipo@ejemplo.com"},
}


def http_error(codigo, cuerpo):
    resp = requests.Response()
    resp.status_code = codigo
    resp.encoding = "utf-8"
    resp._content = cuerpo.encode()
    return requests.HTTPError(f"{codigo} Client Error", response=resp)


class FakeClient:
    """Switch simulado: estado en memoria; rechaza las rutas de `rechaza`."""

    def __init__(self, rechaza=()):
        self.state = {}
        self.puts = []
        self.rechaza = rechaza

    def get(self, path):
        return self.state.get(path)

    def put(self, path, payload):
        if any(r in path for r in self.rechaza):
            raise http_error(400, '{"error-message": "Device refused"}')
        self.puts.append(path)
        self.state[path] = payload
        return 201


@pytest.fixture
def cfg_file(tmp_path):
    ruta = tmp_path / "vars.yml"
    ruta.write_text(yaml.safe_dump(CFG), encoding="utf-8")
    return str(ruta)


def usar(monkeypatch, cliente):
    monkeypatch.setattr(deploy, "RestconfClient", lambda host, port=443: cliente)
    monkeypatch.setattr(verify, "RestconfClient", lambda host, port=443: cliente)
    return cliente


@pytest.fixture
def fake(monkeypatch):
    return usar(monkeypatch, FakeClient())


def test_check_no_modifica_el_equipo(fake, cfg_file, capsys):
    assert deploy.main(["--config", cfg_file, "--check"]) == 0
    out = capsys.readouterr().out
    assert fake.puts == []
    assert out.count("[CAMBIO]") == 4
    assert "4 cambio(s) pendiente(s)" in out


def test_deploy_aplica_los_cuatro_recursos(fake, cfg_file, capsys):
    assert deploy.main(["--config", cfg_file]) == 0
    out = capsys.readouterr().out
    assert len(fake.puts) == 4
    assert out.count("[APLICADO] HTTP 201") == 4
    assert "4 cambio(s) aplicado(s)" in out


def test_segunda_ejecucion_es_idempotente(fake, cfg_file, capsys):
    deploy.main(["--config", cfg_file])
    capsys.readouterr()
    deploy.main(["--config", cfg_file])
    out = capsys.readouterr().out
    assert len(fake.puts) == 4  # no hubo PUT nuevos
    assert out.count("[OK] sin cambios") == 4
    assert "0 cambio(s) aplicado(s)" in out


def test_corrige_una_desviacion(fake, cfg_file):
    deploy.main(["--config", cfg_file])
    ruta, _ = build_items(CFG)[2]  # location
    fake.state[ruta] = {"Cisco-IOS-XE-snmp:location": "Alguien-lo-cambio"}
    fake.puts.clear()
    deploy.main(["--config", cfg_file])
    assert fake.puts == [ruta]


def test_corrige_desviacion_del_loopback(fake, cfg_file):
    deploy.main(["--config", cfg_file])
    ruta, _ = build_items(CFG)[0]
    fake.state[ruta] = {"Cisco-IOS-XE-native:Loopback": [{"name": 201,
                                                          "description": "CAMBIADA"}]}
    fake.puts.clear()
    deploy.main(["--config", cfg_file])
    assert fake.puts == [ruta]


def test_check_detecta_desviacion_sin_corregirla(fake, cfg_file, capsys):
    deploy.main(["--config", cfg_file])
    ruta, _ = build_items(CFG)[3]  # contact
    fake.state[ruta] = {"Cisco-IOS-XE-snmp:contact": "otro@correo.com"}
    fake.puts.clear()
    capsys.readouterr()
    deploy.main(["--config", cfg_file, "--check"])
    out = capsys.readouterr().out
    assert fake.puts == []
    assert out.count("[CAMBIO]") == 1
    assert "1 cambio(s) pendiente(s)" in out


def test_config_extra_en_el_switch_no_cuenta_como_cambio(fake, cfg_file, capsys):
    for ruta, payload in build_items(CFG):
        fake.state[ruta] = {**payload, "campo-extra": "x"}
    deploy.main(["--config", cfg_file, "--check"])
    assert capsys.readouterr().out.count("[OK]") == 4


def test_un_recurso_rechazado_no_detiene_a_los_demas(monkeypatch, cfg_file, capsys):
    cliente = usar(monkeypatch, FakeClient(rechaza=["community-config"]))
    assert deploy.main(["--config", cfg_file]) == 1
    out = capsys.readouterr().out
    assert out.count("[ERROR]") == 1
    assert "Device refused" in out
    assert out.count("[APLICADO]") == 3  # loopback, location y contact sí
    assert len(cliente.puts) == 3
    assert "Errores: 1" in out


def test_config_inexistente_falla(fake):
    with pytest.raises(FileNotFoundError):
        deploy.main(["--config", "no_existe.yml"])


def test_verify_pass_cuando_todo_coincide(fake, cfg_file, capsys):
    for ruta, payload in build_items(CFG):
        fake.state[ruta] = payload
    assert verify.main(["--config", cfg_file]) == 0
    assert capsys.readouterr().out.count("[PASS]") == 4


def test_verify_fail_si_el_switch_esta_vacio(fake, cfg_file, capsys):
    assert verify.main(["--config", cfg_file]) == 1
    assert capsys.readouterr().out.count("[FAIL]") == 4


def test_verify_detecta_una_desviacion(fake, cfg_file, capsys):
    for ruta, payload in build_items(CFG):
        fake.state[ruta] = payload
    ruta, _ = build_items(CFG)[0]
    fake.state[ruta] = {"Cisco-IOS-XE-native:Loopback": {"name": 201,
                                                         "description": "CAMBIADA"}}
    assert verify.main(["--config", cfg_file]) == 1
    out = capsys.readouterr().out
    assert out.count("[FAIL]") == 1
    assert out.count("[PASS]") == 3
