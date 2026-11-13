"""ms-analitica · indicadores y semáforo de riesgo.  CONSUMIDOR de NotaPublicada/EntregaRegistrada
y PRODUCTOR de AlumnoEnRiesgo (el filtro de su cola excluye ese evento: no hay bucle).

Tabla:
  sp_indicadores  PK tenant_id · SK alumno_id · GSI gsi_riesgo (PK tenant_nivel "UTEC#ROJO", SK riesgo_orden)
"""
from boto3.dynamodb.conditions import Key

from common import (ApiError, consulta_paginada, contar, exigir_rol, path_params, procesar_lote,
                    protegido, publicar_evento, query_params, tabla, verificar_tenant)
from riesgo import calcular_riesgo

INDICADORES = tabla("T_INDICADORES")
NIVELES = ("VERDE", "AMBAR", "ROJO")


# ------------------------------------------------- consumidor (cola SQS)
def _procesar(msg):
    evento, tenant, d = msg["evento"], msg["tenant_id"], msg["detalle"]
    if evento not in ("NotaPublicada", "EntregaRegistrada"):
        return  # evento que no es nuestro: se ignora (el filtro de SNS ya lo evita)
    alumno_id = d["alumno_id"]
    previo = INDICADORES.get_item(Key={"tenant_id": tenant, "alumno_id": alumno_id}).get("Item")
    if previo and previo.get("actualizado_en", "") > msg["ts"]:
        return  # evento atrasado: ya hay un cálculo más nuevo
    resumen = d["resumen"]
    puntaje, nivel, motivos = calcular_riesgo(resumen)
    INDICADORES.put_item(Item={
        "tenant_id": tenant, "alumno_id": alumno_id, "alumno_nombre": d.get("alumno_nombre", ""),
        "promedio": resumen.get("promedio"), "n_notas": resumen.get("n_notas", 0),
        "n_tardias": resumen.get("n_tardias", 0), "caida_ultima": resumen.get("caida_ultima", 0),
        "n_entregas": resumen.get("n_entregas", 0), "puntaje": puntaje, "nivel": nivel,
        "motivos": motivos, "tenant_nivel": f"{tenant}#{nivel}",
        "riesgo_orden": f"{puntaje:03d}#{alumno_id}", "actualizado_en": msg["ts"],
        "ultimo_evento": msg["event_id"],
    })
    if nivel == "ROJO" and (not previo or previo.get("nivel") != "ROJO"):
        publicar_evento("AlumnoEnRiesgo", tenant, {
            "alumno_id": alumno_id, "alumno_nombre": d.get("alumno_nombre", ""), "puntaje": puntaje,
            "motivos": motivos, "docente_id": d.get("docente_id"), "curso_id": d.get("curso_id")})


def evaluar_riesgo(event, context):
    return procesar_lote(event, _procesar)


# ---------------------------------------------------------------- API
@protegido
def obtener_indicadores(event, ctx):
    alumno_id = path_params(event)["alumno_id"]
    verificar_tenant(ctx, query_params(event))
    if ctx["rol"] == "alumno" and alumno_id != ctx["user_id"]:
        raise ApiError(403, "SOLO_PROPIOS", "Un alumno solo puede ver sus propios indicadores")
    item = INDICADORES.get_item(Key={"tenant_id": ctx["tenant_id"], "alumno_id": alumno_id}).get("Item")
    if not item:
        raise ApiError(404, "SIN_INDICADORES", "Aún no hay indicadores para este alumno")
    return item


@protegido
def consultar_riesgo(event, ctx):
    exigir_rol(ctx, "docente", "admin")
    qs = query_params(event)
    nivel = (qs.get("nivel") or "ROJO").upper()
    if nivel not in NIVELES:
        raise ApiError(400, "NIVEL_INVALIDO", "nivel debe ser VERDE, AMBAR o ROJO")
    clave = f"{ctx['tenant_id']}#{nivel}"
    kw = {"IndexName": "gsi_riesgo", "KeyConditionExpression": Key("tenant_nivel").eq(clave),
          "ScanIndexForward": False}  # los de mayor puntaje primero
    items, cursor = consulta_paginada(INDICADORES, qs, kw, pk=("tenant_nivel", clave))
    return {"nivel": nivel, "alumnos": items, "cursor": cursor}


@protegido
def resumen(event, ctx):
    exigir_rol(ctx, "docente", "admin")
    conteo = {n: contar(INDICADORES, IndexName="gsi_riesgo",
                        KeyConditionExpression=Key("tenant_nivel").eq(f"{ctx['tenant_id']}#{n}"))
              for n in NIVELES}
    return {"tenant_id": ctx["tenant_id"], "total": sum(conteo.values()), "niveles": conteo}
