# Configuración RBAC y accesos — Synapse + Cortex (para administrador Snowflake)

Documento orientado al **administrador de RBAC / seguridad** de Snowflake. Ajustar nombres de usuario, rol, warehouse, base de datos y esquema a los estándares de la organización.

## Contexto

La aplicación **Synapse** (backend) usa un **usuario técnico de servicio** y un **Programmatic Access Token (PAT)** para:

1. **Modo legacy:** SQL ejecutado desde la aplicación + `SNOWFLAKE.CORTEX.COMPLETE` para generar narrativa.
2. **Modo Cortex Analyst (REST):** `POST /api/v2/cortex/analyst/message` con **vista semántica** o **modelo YAML en stage**.

Se requiere alinear **rol por defecto**, **privilegios sobre datos**, **roles de sistema Cortex**, **objetos semánticos**, **stage** (si aplica), **network policy** y **PAT**.

---

## 1. Usuario de servicio

- Crear o confirmar el usuario técnico (ej. `SYNAPSE_SERVICE_USER`) dedicado a la integración.
- Autenticación recomendada: **PAT** (según política de seguridad).
- Fijar el **rol por defecto** al rol de aplicación acordado (ej. `SYNAPSE_APP_ROLE`).

```sql
ALTER USER SYNAPSE_SERVICE_USER SET DEFAULT_ROLE = SYNAPSE_APP_ROLE;
```

---

## 2. Rol de aplicación y Cortex (database roles)

Otorgar al rol de aplicación el **database role** de Snowflake necesario para Cortex Analyst y modelos cubiertos. **Confirmar el nombre exacto** en la documentación vigente de la cuenta (puede variar por edición/región).

```sql
-- Ejemplo habitual; validar en documentación Snowflake / AI / legal notices de la cuenta:
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_ANALYST_USER TO ROLE SYNAPSE_APP_ROLE;
```

Si en la cuenta aplica otro rol (p. ej. `SNOWFLAKE.CORTEX_USER`), usar el que corresponda según política interna.

---

## 3. Warehouse

```sql
GRANT USAGE ON WAREHOUSE <WH_SYNAPSE> TO ROLE SYNAPSE_APP_ROLE;
```

Sustituir `<WH_SYNAPSE>` por el warehouse configurado en la variable de entorno `SNOWFLAKE_WAREHOUSE` del backend.

---

## 4. Base de datos y esquema (mart / Gold)

Sustituir `DB_BT_UA` y `BT_UA_MART_ANALYTICS` por los nombres reales del proyecto.

```sql
GRANT USAGE ON DATABASE DB_BT_UA TO ROLE SYNAPSE_APP_ROLE;
GRANT USAGE ON SCHEMA DB_BT_UA.BT_UA_MART_ANALYTICS TO ROLE SYNAPSE_APP_ROLE;
```

---

## 5. Tablas y vistas (datos + modelo semántico)

Conceder **`SELECT`** sobre todas las tablas y vistas que:

- exponga el **semantic model** / **semantic view** usado por Cortex Analyst, y
- use el modo legacy de Synapse (ej. `FCT_PERFORMANCE`, `VENTAS_PRODUCTOS_FUENTE`, vistas `GLD_*`, etc., según diseño).

**La lista definitiva la define el dueño del modelo semántico / analytics.**

Ejemplo ilustrativo sobre un esquema:

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA DB_BT_UA.BT_UA_MART_ANALYTICS TO ROLE SYNAPSE_APP_ROLE;
GRANT SELECT ON ALL VIEWS  IN SCHEMA DB_BT_UA.BT_UA_MART_ANALYTICS TO ROLE SYNAPSE_APP_ROLE;
```

Objetos futuros (opcional, según gobernanza):

```sql
GRANT SELECT ON FUTURE TABLES IN SCHEMA DB_BT_UA.BT_UA_MART_ANALYTICS TO ROLE SYNAPSE_APP_ROLE;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA DB_BT_UA.BT_UA_MART_ANALYTICS TO ROLE SYNAPSE_APP_ROLE;
```

---

## 6. Vista semántica (modo `semantic_view`)

- Crear o identificar la **semantic view** (ej. `DB_BT_UA.BT_UA_MART_ANALYTICS.<NOMBRE_VISTA_SEMANTICA>`).
- Asegurar privilegios de uso/lectura según el tipo de objeto y la versión de Snowflake (validar en [Semantic views](https://docs.snowflake.com/en/user-guide/views-semantic/overview)).

---

## 7. Stage y YAML (modo `semantic_model_file`)

Si la aplicación referencia `@DB_BT_UA.BT_UA_MART_ANALYTICS.<STAGE>/modelo.yaml`:

```sql
GRANT USAGE ON STAGE DB_BT_UA.BT_UA_MART_ANALYTICS.<STAGE> TO ROLE SYNAPSE_APP_ROLE;
GRANT READ ON STAGE DB_BT_UA.BT_UA_MART_ANALYTICS.<STAGE> TO ROLE SYNAPSE_APP_ROLE;
```

Ajustar `READ` / `USAGE` según política del equipo y tipo de stage.

---

## 8. Cortex Search (si el modelo lo referencia)

Otorgar al rol `SYNAPSE_APP_ROLE` los privilegios requeridos sobre el **Cortex Search service** indicado en el modelo semántico, según documentación de Cortex Search.

---

## 9. Network policy

Incluir las **IPs de salida** del backend (EC2, NAT Gateway, otros proveedores) en la lista permitida de la **network policy** aplicada al usuario de servicio o a la cuenta, de forma coherente con el resto de integraciones.

---

## 10. Programmatic Access Token (PAT)

- Emitir o rotar el PAT para `SYNAPSE_SERVICE_USER` según política de seguridad.
- Entregar el secreto por **canal aprobado** (vault, gestor de secretos); no por correo en claro.
- Confirmar que el PAT está permitido para **Snowflake REST APIs** según configuración de la cuenta.

---

## 11. URL base REST (para el equipo de plataforma)

Facilitar la URL base de la cuenta para llamadas REST (misma familia que Snowsight), por ejemplo:

`https://<account_locator>.<region>.<cloud>.snowflakecomputing.com`

Configuración en backend: variable `SNOWFLAKE_REST_BASE_URL` (ver `backend/.env.example`).

---

## 12. Verificación opcional

Con sesión usando `ROLE SYNAPSE_APP_ROLE` y warehouse activo:

```sql
SELECT CURRENT_ROLE(), CURRENT_USER();

SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', $$Responde solo: OK$$);
```

La prueba end-to-end de Cortex Analyst es una llamada exitosa a `POST /api/v2/cortex/analyst/message` desde el entorno de la aplicación o un cliente REST autorizado.

---

## Resumen

| Área | Acción |
|------|--------|
| Usuario | Usuario técnico + `DEFAULT_ROLE` = rol de app |
| Rol app | `SYNAPSE_APP_ROLE` + database role Cortex según doc (`CORTEX_ANALYST_USER` / equivalente) |
| Compute | `USAGE` sobre warehouse |
| Datos | `USAGE` DB/schema + `SELECT` sobre tablas/vistas del mart y del semantic model |
| Analyst | Semantic view **o** YAML en stage con privilegios de stage |
| Red | Network policy con IPs del backend |
| Secreto | PAT para REST y conector Python |

## Referencias útiles

- [Cortex Analyst](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-analyst)
- [Cortex Analyst REST API](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-analyst/rest-api)
- [Autenticación REST / PAT](https://docs.snowflake.com/en/developer-guide/sql-api/authenticating)
- Script AWS (red / rol ejemplo): `docs/aws/snowflake_setup_aws.sql`
