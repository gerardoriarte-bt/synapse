from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from services.snowflake import SnowflakeService
from database.database import get_db
from database.models import Conversation, init_db
from dotenv import load_dotenv
import uuid
import os
import json

load_dotenv()

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

@app.post("/api/synapse/ask")
async def ask_synapse(request: QueryRequest, db: Session = Depends(get_db)):
    try:
        # Detección de modo Intelligence
        is_intelligence = "REPORT" in request.query.upper() or "INTELLIGENCE" in request.query.upper() or "ESTRATEGIA" in request.query.upper()
        
        # 1. Recuperar historial (últimos 5 para mayor contexto en storytelling)
        past_interactions = db.query(Conversation).filter(
            Conversation.user_id == request.user_id
        ).order_by(Conversation.created_at.desc()).limit(5).all()

        history = [{"q": c.query, "a": c.narrative} for c in reversed(past_interactions)]

        # 2. Procesar consulta (datos + narrativa del modelo)
        agent = SnowflakeService(tenant_id=request.tenant_id)
        
        target_query = request.query
        if is_intelligence:
            # Query forzada para el Dashboard Estratégico
            target_query = "REALIZA UN ANÁLISIS ESTRATÉGICO DEL ROAS Y GASTO DE LAS ÚLTIMAS SEMANAS. DEFINE UN PROBLEMA, UNA EVIDENCIA Y UNA SOLUCIÓN CONCRETA."
            
        response = agent.process_query(target_query, history=history)

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
