from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.snowflake import SnowflakeService
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Synapse API - Snowflake Architecture")

# Configuración de CORS para el Frontend en Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción restringe a tu URL de Railway
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    tenant_id: str

@app.get("/")
async def health_check():
    return {"status": "Synapse Online", "engine": "Cortex AI"}

@app.post("/api/synapse/ask")
async def ask_synapse(request: QueryRequest):
    try:
        agent = SnowflakeService(tenant_id=request.tenant_id)
        response = agent.process_query(request.query)
        return response
    except Exception as e:
        print(f"Error in Synapse Backend: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
