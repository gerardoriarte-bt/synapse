# Producción en EC2 (solo EC2)

Arquitectura: **nginx (80)** → **Next.js (127.0.0.1:3000)** y **`/api` → FastAPI (127.0.0.1:8000)**.

## Requisitos en AWS

- Instancia Ubuntu 24.04 (o similar).
- **Security Group**: entrada TCP **22** (SSH), **80** (HTTP). Opcional **443** si añades TLS después.
- Clave SSH para el usuario `ubuntu`.

## Snowflake (resumen)

- **Network policy** con la IP pública de salida de la instancia (o la IP elástica si aplica).
- Usuario técnico + **PAT**; `ALTER USER ... SET DEFAULT_ROLE = SYNAPSE_APP_ROLE`.
- `GRANT USAGE` (y si aplica `OPERATE`) sobre un **warehouse que exista** (ej. `WH_BT_UA_TRANSFORM`).
- `GRANT` de lectura sobre DB/schemas/tablas que usa el backend.

## 1) Variables del backend

En `~/Synapse/backend/.env` (no commitear):

- Ver `backend/.env.example`.
- `SNOWFLAKE_WAREHOUSE` = nombre real de `SHOW WAREHOUSES;`.
- `DATABASE_URL` = Postgres (RDS) o, solo para pruebas, SQLite local.

## 2) Instalación automática

En la instancia:

```bash
chmod +x ~/Synapse/deploy/ec2/bootstrap.sh
~/Synapse/deploy/ec2/bootstrap.sh
```

Si el repo aún no está clonado:

```bash
git clone https://github.com/gerardoriarte-bt/synapse.git ~/Synapse
```

El script instala dependencias, construye el frontend, configura **nginx** y **systemd** (`synapse-api`, `synapse-frontend`).

## 3) Frontend y mismo origen

`frontend/.env.production` debe incluir:

```env
NEXT_PUBLIC_API_URL=
```

(vacío = el navegador llama a `/api/...` en el mismo dominio/IP que sirve nginx).

Tras cambiar variables del frontend, reconstruir:

```bash
cd ~/Synapse/frontend && npm run build && sudo systemctl restart synapse-frontend
```

## 4) Comandos útiles

```bash
sudo systemctl status synapse-api synapse-frontend nginx
journalctl -u synapse-api -f
```

## 5) Comprobación

- `curl -s http://127.0.0.1:8000/` → JSON del API.
- Navegador: `http://TU_IP/` → UI; una consulta debe llegar a `/api/synapse/ask`.
