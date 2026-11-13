# ms-analitica

Semáforo de riesgo académico (reglas R1 promedio, R2 tardías, R3 caída). Se alimenta SOLO de eventos; escribe indicadores propios y avisa de las transiciones a ROJO.

- **Tablas DynamoDB** (PK `tenant_id`, solo `Query`): `sp_indicadores`
- **Publica:** AlumnoEnRiesgo
- **Consume:** NotaPublicada, EntregaRegistrada (cola sp-analitica + DLQ)
- **Seguridad:** Lambda Authorizer de `ms-auth` en todas las rutas; el tenant sale del token, nunca del cliente.

## Endpoints
| Método | Ruta | Acceso | Handler |
|---|---|---|---|
| GET | `/analitica/alumnos/{alumno_id}` | token | `handler.obtener_indicadores` |
| GET | `/analitica/riesgo` | token | `handler.consultar_riesgo` |
| GET | `/analitica/resumen` | token | `handler.resumen` |

## Desplegar
```bash
# con credenciales del Learner Lab vigentes y tras desplegar infra-base
npx --yes serverless@3 deploy --stage dev
```
Orden completo y atajo: `../docs-ops/deploy-all.sh`.

## Probar sin AWS
```bash
python3 ../pruebas-locales/test_e2e.py     # emulador con los serverless.yml reales
```
> `common.py` es **idéntico** en todos los servicios (la prueba lo verifica). Si lo cambias, cópialo a los demás.
