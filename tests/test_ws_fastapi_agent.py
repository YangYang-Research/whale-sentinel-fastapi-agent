from whale_sentinel_fastapi_agent import WhaleSentinelFastApiAgent
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()
ws_agent = WhaleSentinelFastApiAgent()

# Define request body schema
class SearchRequest(BaseModel):
    query: str = None

@app.post("/api/v1/search")
@ws_agent.whale_sentinel_agent_protection()
async def search(request: Request, body: SearchRequest):
    """
    Search endpoint (POST)
    """
    search_query = body.query
    if not search_query:
        return JSONResponse({"error": "Query parameter is required"}, status_code=400)

    # Perform the search operation here
    response = {
        "query": search_query,
        "results": [
            {"id": 1, "name": "Result 1"},
            {"id": 2, "name": "Result 2"},
            {"id": 3, "name": "Result 3"},
        ],
    }
    return JSONResponse(response)

if __name__ == "__main__":
    uvicorn.run("test_ws_fastapi_agent:app", host="0.0.0.0", port=3000, reload=True)
