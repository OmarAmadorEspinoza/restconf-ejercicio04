# Ejercicio 04 - DevOps con RESTCONF (Cisco IOS-XE)

Configura un Loopback y políticas SNMP en un Catalyst 9300 del DevNet Sandbox
sin tocar la consola. Todo cambio pasa por Git -> Pull Request -> pipeline -> API.

## Uso local
    export SANDBOX_USER=... SANDBOX_PASS=...
    python src/deploy.py --check   # prueba en seco
    python src/deploy.py           # aplica
    python src/verify.py           # monitoreo

## Pruebas
    pytest -v && flake8 src tests && yamllint config .github

## Pipeline
- build-test (GitHub): yamllint, flake8, pytest con switch simulado.
- dry-run y deploy (runner self-hosted con VPN): --check, deploy, segunda
  ejecución idempotente y verify. Se activan con la variable SELF_HOSTED=true.
