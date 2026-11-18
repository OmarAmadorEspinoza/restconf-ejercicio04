import ipaddress
from pathlib import Path

import pytest
import yaml

from payloads import NATIVE, build_items, is_subset

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg():
    return {
        "host": "192.0.2.1",
        "port": 443,
        "loopback": {"id": 201, "description": "MGMT-LOOPBACK-DEVOPS",
                     "ip": "10.201.201.1", "mask": "255.255.255.255"},
        "snmp": {"community": "DEVOPS-RO", "location": "Lab-DevNet",
                 "contact": "equipo@ejemplo.com"},
    }


def test_cuatro_recursos(cfg):
    assert len(build_items(cfg)) == 4


def test_todas_las_rutas_usan_modulo_native(cfg):
    assert all(path.startswith(NATIVE) for path, _ in build_items(cfg))


def test_loopback_payload(cfg):
    path, body = build_items(cfg)[0]
    assert path.endswith("/interface/Loopback=201")
    lb = body["Cisco-IOS-XE-native:Loopback"]
    assert lb["name"] == 201
    assert lb["description"] == "MGMT-LOOPBACK-DEVOPS"
    prim = lb["ip"]["address"]["primary"]
    assert prim == {"address": "10.201.201.1", "mask": "255.255.255.255"}


def test_snmp_community_payload(cfg):
    path, body = build_items(cfg)[1]
    assert path.endswith("community-config=DEVOPS-RO")
    com = body["Cisco-IOS-XE-snmp:community-config"]
    assert com["name"] == "DEVOPS-RO"
    assert "RO" not in com  # permission usa el default del YANG: ro


def test_snmp_location_y_contact(cfg):
    items = dict(build_items(cfg))
    loc = items[f"{NATIVE}/snmp-server/Cisco-IOS-XE-snmp:location"]
    con = items[f"{NATIVE}/snmp-server/Cisco-IOS-XE-snmp:contact"]
    assert loc == {"Cisco-IOS-XE-snmp:location": "Lab-DevNet"}
    assert con == {"Cisco-IOS-XE-snmp:contact": "equipo@ejemplo.com"}


def test_payload_sigue_a_la_configuracion(cfg):
    cfg["loopback"]["id"] = 305
    cfg["snmp"]["community"] = "OTRA-RO"
    paths = [p for p, _ in build_items(cfg)]
    assert any("Loopback=305" in p for p in paths)
    assert any("community-config=OTRA-RO" in p for p in paths)


def test_is_subset_basico():
    assert is_subset({"a": 1}, {"a": 1, "b": 2})
    assert not is_subset({"a": 1}, {"a": 2})


def test_is_subset_anidado():
    desired = {"x": {"y": {"z": 1}}}
    assert is_subset(desired, {"x": {"y": {"z": 1, "w": 2}, "k": 3}})
    assert not is_subset(desired, {"x": {"y": {"z": 9}}})


def test_is_subset_clave_faltante():
    assert not is_subset({"a": 1}, {"b": 1})


def test_is_subset_tipos_distintos():
    assert not is_subset({"a": 1}, "texto")
    assert not is_subset({"a": 1}, None)


def test_is_subset_listas():
    assert is_subset([None], [None])
    assert not is_subset([None], [])
    assert not is_subset([None], None)


def test_is_subset_compara_como_texto():
    # RESTCONF devuelve el id como número; el YAML puede traerlo como texto
    assert is_subset({"name": "201"}, {"name": 201})


def test_vars_yml_real_es_valido():
    with open(ROOT / "config" / "vars.yml", encoding="utf-8") as f:
        real = yaml.safe_load(f)
    assert real["host"]
    assert isinstance(real["loopback"]["id"], int)
    assert 0 <= real["loopback"]["id"] <= 2147483647
    iface = ipaddress.ip_interface(f"{real['loopback']['ip']}/{real['loopback']['mask']}")
    assert iface.ip.is_private
    assert real["snmp"]["community"].lower() not in ("public", "private")
    assert "@" in real["snmp"]["contact"]


def test_is_subset_lista_yang_del_switch():
    # El switch devuelve Loopback como lista de un elemento
    deseado = {"Loopback": {"name": 201, "ip": {"a": 1}}}
    actual = {"Loopback": [{"name": 201, "description": "x", "ip": {"a": 1, "b": 2}}]}
    assert is_subset(deseado, actual)
    assert not is_subset(deseado, {"Loopback": [{"name": 202, "ip": {"a": 1}}]})
    assert not is_subset(deseado, {"Loopback": []})
