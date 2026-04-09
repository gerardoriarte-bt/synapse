from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from services.cortex_analyst import process_with_cortex_analyst, validate_cortex_analyst_config
from database.database import get_db
from database.models import Conversation, init_db
from dotenv import load_dotenv
import uuid
import os
import json
from typing import Optional

from database.repositories.cortex_session_repository import CortexSessionRepository
from services.cortex_threads import create_cortex_thread

load_dotenv()


def _query_mode() -> str:
    m = os.getenv("SYNAPSE_QUERY_MODE", "cortex_analyst").strip().lower()
    if m not in ("cortex_analyst", "legacy"):
        return "cortex_analyst"
    return m


def _legacy_allowed() -> bool:
    return os.getenv("SYNAPSE_ALLOW_LEGACY", "false").strip().lower() in (
        "1",
        "true",
        "yes",
    )


app = FastAPI(title="Synapse API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar DB al arrancar
@app.on_event("startup")
def on_startup():
    init_db()

class QueryRequest(BaseModel):
    query: str
    tenant_id: str
    user_id: str = "default_user"
    conversation_id: Optional[str] = Field(
        None,
        description="Reenviar desde la respuesta anterior para continuar el hilo Cortex Agent.",
    )


def to_json_compatible(value):
    """Convierte objetos no serializables (date/datetime/Decimal) a JSON seguro."""
    if value is None:
        return None
    return json.loads(json.dumps(value, default=str))

@app.get("/")
async def health_check():
    return {"status": "Synapse Online", "database": "Postgres Connected"}


@app.get("/api/health/snowflake")
async def snowflake_health():
    """Endpoint de diagnóstico para validar la conexión con Snowflake paso a paso."""
    import snowflake.connector
    results = {
        "step_1_env_vars": {},
        "step_2_connection": None,
        "step_3_cortex": None,
        "step_4_table": None,
    }
    
    # Step 1: Verificar variables de entorno
    required_vars = ["SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_DATABASE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_TOKEN"]
    for var in required_vars:
        val = os.getenv(var)
        if val:
            # Mostramos diagnóstico del valor (longitud y pista de caracteres)
            pista = f"{val[0]}...{val[-1]}" if len(val) > 2 else val
            results["step_1_env_vars"][var] = f"✅ Set (len: {len(val)}, hint: {pista})"
        else:
            results["step_1_env_vars"][var] = "❌ MISSING"
    
    # Step 2: Intentar conexión
    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            database=os.getenv("SNOWFLAKE_DATABASE", "DB_BT_UA"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            schema="BT_UA_MART_ANALYTICS",
        )
        results["step_2_connection"] = "✅ Connected successfully"
        
        cursor = conn.cursor()
        
        # Step 3: Probar Cortex AI
        try:
            cursor.execute("SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large', $$Responde solo: OK$$)")
            row = cursor.fetchone()
            results["step_3_cortex"] = f"✅ Cortex responding: {str(row[0])[:80]}"
        except Exception as e:
            results["step_3_cortex"] = f"❌ Cortex error: {str(e)}"
        
        # Step 4: Listar tablas disponibles en la DB
        try:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [t[1] for t in tables] if tables else []
            results["step_4_table"] = f"✅ Tables found: {table_names}"
        except Exception as e:
            results["step_4_table"] = f"❌ Table list error: {str(e)}"
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        results["step_2_connection"] = f"❌ Connection failed: {str(e)}"
    
    return results


@app.get("/api/health/cortex-analyst")
async def cortex_analyst_health():
    """Valida configuración de Cortex Analyst (sin consumir la API de inferencia)."""
    mode = _query_mode()
    if mode != "cortex_analyst":
        return {"mode": mode, "cortex_analyst_configured": False}
    v = validate_cortex_analyst_config()
    return {"mode": mode, "cortex_analyst_configured": v["ok"], **v}


@app.post("/api/synapse/ask")
async def ask_synapse(request: QueryRequest, db: Session = Depends(get_db)):
    try:
        # 1. Recuperar historial (últimos 5 para mayor contexto en storytelling)
        past_interactions = db.query(Conversation).filter(
            Conversation.user_id == request.user_id
        ).order_by(Conversation.created_at.desc()).limit(5).all()

        history = [{"q": c.query, "a": c.narrative} for c in reversed(past_interactions)]

        mode = _query_mode()
        if mode == "legacy" and not _legacy_allowed():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Este despliegue está configurado para usar solo Snowflake Cortex (API REST). "
                    "No está habilitado el motor legacy en Python (SQL + narrativa generados en código). "
                    "Mantén SYNAPSE_QUERY_MODE=cortex_analyst. "
                    "Solo en entornos de desarrollo explícitos: SYNAPSE_ALLOW_LEGACY=true."
                ),
            )
        if mode == "cortex_analyst":
            api_mode = os.getenv("CORTEX_API_MODE", "analyst").strip().lower()
            use_threads = (
                os.getenv("CORTEX_USE_AGENT_THREADS", "true").strip().lower()
                in ("1", "true", "yes")
                and api_mode == "agent_run"
            )
            if use_threads:
                repo = CortexSessionRepository(db)
                out_conversation_id: Optional[str] = None
                agent_thread_id: Optional[int] = None
                agent_parent_message_id: Optional[int] = None
                if request.conversation_id:
                    out_conversation_id = request.conversation_id
                    sess = repo.get(request.conversation_id)
                    if not sess or sess.user_id != request.user_id:
                        raise HTTPException(
                            status_code=400,
                            detail="conversation_id inválido o expirado.",
                        )
                    agent_thread_id = int(sess.cortex_thread_id)
                    if sess.last_assistant_message_id is None:
                        agent_parent_message_id = 0
                    else:
                        agent_parent_message_id = int(sess.last_assistant_message_id)
                else:
                    out_conversation_id = str(uuid.uuid4())
                    tid = create_cortex_thread()
                    repo.create(
                        session_id=out_conversation_id,
                        user_id=request.user_id,
                        tenant_id=request.tenant_id,
                        cortex_thread_id=tid,
                    )
                    agent_thread_id = tid
                    agent_parent_message_id = 0
                response = process_with_cortex_analyst(
                    request.query,
                    history,
                    agent_thread_id=agent_thread_id,
                    agent_parent_message_id=agent_parent_message_id,
                    conversation_id=out_conversation_id,
                )
                last_mid = None
                if response.cortex_analyst and isinstance(
                    response.cortex_analyst, dict
                ):
                    last_mid = response.cortex_analyst.get("last_assistant_message_id")
                if isinstance(last_mid, int) and out_conversation_id:
                    repo.update_last_assistant(out_conversation_id, last_mid)
            else:
                response = process_with_cortex_analyst(request.query, history)
        else:
            from services.snowflake import SnowflakeService

            agent = SnowflakeService(tenant_id=request.tenant_id)
            response = agent.process_query(request.query, history=history)

        # 3. Persistir en Postgres
        new_conv = Conversation(
            id=response.response_id,
            user_id=request.user_id,
            query=request.query,
            narrative=response.narrative,
            render_type=response.render_type,
            chart_config=to_json_compatible(response.chart_config.dict()) if response.chart_config else None,
            raw_data=to_json_compatible(response.raw_data),
        )
        db.add(new_conv)
        db.commit()

        return response
    except Exception as e:
        db.rollback()
        print(f"Error in Synapse Backend: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
