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

load_dotenv()

app = FastAPI(title="Synapse API - Snowflake + Postgres")

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

@app.get("/")
async def health_check():
    return {"status": "Synapse Online", "database": "Postgres Connected"}

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

        # 2. Procesar con Snowflake + Cortex
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
            chart_config=response.chart_config.dict() if response.chart_config else None,
            raw_data=response.raw_data,
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
