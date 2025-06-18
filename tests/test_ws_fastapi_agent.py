from whale_sentinel_fastapi_agent import WhaleSentinelFastApiAgent
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
import uvicorn
import os
from werkzeug.utils import secure_filename

app = FastAPI()
ws_agent = WhaleSentinelFastApiAgent()

# Define request body schema
class SearchRequest(BaseModel):
    query: str = None

UPLOAD_FOLDER = "./uploads"  # replace with your path
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

@app.post("/upload", response_class=PlainTextResponse)
@ws_agent.whale_sentinel_agent_protection()
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    filename = secure_filename(file.filename)
    file_location = os.path.join(UPLOAD_FOLDER, filename)

    with open(file_location, "wb") as f:
        contents = await file.read()
        f.write(contents)

    return f"File {filename} uploaded successfully"

if __name__ == "__main__":
    uvicorn.run("test_ws_fastapi_agent:app", host="0.0.0.0", port=3000, reload=True)
