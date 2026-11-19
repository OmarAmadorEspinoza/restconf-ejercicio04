# Ejercicio 04 - DevOps con RESTCONF (Cisco IOS-XE)

Configura un Loopback y políticas SNMP en un Cisco Catalyst 9300 (DevNet Sandbox)
por RESTCONF, sin cambios manuales por consola.
Todo cambio pasa por **Git -> Pull Request -> pipeline -> API**.

## Reporte de evidencias
**[Ver el reporte completo en PDF](docs/Reporte_Ejercicio04.pdf)** con las evidencias de cada fase del ciclo DevOps, problemas encontrados y la limitación de SNMP.

## Configuración deseada (`config/vars.yml`)
| Elemento | Valor |
|---|---|
| Loopback | Loopback201, 10.201.201.1/32, MGMT-LOOPBACK-DEVOPS |
| SNMP community | DEVOPS-RO (solo lectura) |
| SNMP location / contact | Lab-DevNet / equipo@ejemplo.com |

## Ciclo DevOps
| Fase | Qué se hace | Herramienta |
|---|---|---|
| Plan | Requisitos en el Issue #1 | GitHub Issues |
| Code | Configuración como código | Git, YAML, Python |
| Build | Lint | yamllint, flake8 |
| Test | Pruebas unitarias y prueba en seco | pytest, `deploy.py --check` |
| Release | Pull Request, merge a `main`, tag `v1.0` | GitHub |
| Deploy | Aplica los recursos con PUT | `deploy.py` |
| Operate | Re-ejecución idempotente (`[OK]`) | `deploy.py` |
| Monitor | Estado real vs deseado | `verify.py` |

## Estructura
    config/vars.yml            configuración deseada
    src/restconf_client.py     cliente RESTCONF (GET/PUT/PATCH)
    src/payloads.py            payloads YANG y comparación is_subset
    src/deploy.py              aplica la configuración (--check = prueba en seco)
    src/verify.py              verifica el estado (PASS/FAIL)
    tests/                     41 pruebas con switch simulado
    .github/workflows/         pipeline de GitHub Actions

## Uso local (con la VPN del sandbox activa)
    pip install -r requirements.txt
    export SANDBOX_USER=... SANDBOX_PASS=...
    python src/deploy.py --check   # prueba en seco
    python src/deploy.py           # aplica
    python src/verify.py           # monitoreo

## Pruebas y lint
    pytest -v && flake8 src tests && yamllint config .github

## Pipeline (GitHub Actions)
- **build-test** (runners de GitHub): yamllint, flake8 y pytest con switch simulado.
  Corre en cada Pull Request y en `main`. Es un check obligatorio.
- **dry-run y deploy** (runner self-hosted con VPN): solo corren si existe la variable
  `SELF_HOSTED=true`. No se activan porque el repositorio es público y un runner
  propio permitiría ejecutar código de terceros. El despliegue real se ejecutó
  localmente con la VPN.

## Controles contra cambios manuales
- Rama `main` protegida con ruleset: exige Pull Request y el check `build-test`;
  bloquea force push.
- Credenciales solo en GitHub Secrets (`SANDBOX_USER`, `SANDBOX_PASS`).
- Historial de Git como auditoría.

## Limitación conocida: comunidad SNMP
Loopback, `location` y `contact` se aplican por RESTCONF (HTTP 201). El switch del sandbox
rechaza crear cualquier `community-config` con
`inconsistent value: Device refused one or more commands`
(probado con distintos nombres y permisos ro/rw). La causa más probable es una restricción
del sandbox. Por eso `deploy.py` reporta `[ERROR]` en ese recurso, aplica los demás y
termina con código 1, y `verify.py` marca `FAIL` solo en la comunidad.

## Nota sobre rutas YANG
Los nombres varían según la versión de IOS-XE. En este equipo la lista de comunidades es
`community-config` (módulo Cisco-IOS-XE-snmp, revisión 2026-08-01).
