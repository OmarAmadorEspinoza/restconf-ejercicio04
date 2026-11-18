"""Aplica la configuración por RESTCONF. --check = prueba en seco."""
import argparse
import sys

import requests
import yaml

from payloads import build_items, is_subset
from restconf_client import RestconfClient


def aplicar(client, cfg, check):
    """Recorre los recursos; un error en uno no detiene a los demás."""
    changes = errores = 0
    for path, payload in build_items(cfg):
        try:
            current = client.get(path)
            if current is not None and is_subset(payload, current):
                print(f"[OK] sin cambios -> {path}")
                continue
            if check:
                changes += 1
                print(f"[CAMBIO] se aplicaría -> {path}")
                continue
            code = client.put(path, payload)
        except requests.HTTPError as err:
            errores += 1
            print(f"[ERROR] {path}\n        {err}")
            if err.response is not None and err.response.text:
                print(err.response.text)
            continue
        changes += 1
        print(f"[APLICADO] HTTP {code} -> {path}")
    return changes, errores


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/vars.yml")
    ap.add_argument("--check", action="store_true", help="no modifica el equipo")
    args = ap.parse_args(argv)

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    client = RestconfClient(cfg["host"], cfg.get("port", 443))
    changes, errores = aplicar(client, cfg, args.check)

    estado = "pendiente(s)" if args.check else "aplicado(s)"
    print(f"\nResumen: {changes} cambio(s) {estado}")
    if errores:
        print(f"Errores: {errores} recurso(s) rechazado(s) por el equipo")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
