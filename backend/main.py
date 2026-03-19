from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from services.snowflake import SnowflakeService
from database.database import get_db
from database.models import Conversation, init_db
from dotenv import load_dotenv
import uuid

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
        # 1. Recuperar historial de conversación (últimos 3 mensajes)
        past_interactions = db.query(Conversation).filter(
            Conversation.user_id == request.user_id
        ).order_by(Conversation.created_at.desc()).limit(3).all()

        history = [{"q": c.query, "a": c.narrative} for c in reversed(past_interactions)]

        # 2. Procesar con Snowflake + Cortex (Pasando el historial)
        agent = SnowflakeService(tenant_id=request.tenant_id)
        response = agent.process_query(request.query, history=history)

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
