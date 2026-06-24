from fastapi import FastAPI
from api.main import router
app = FastAPI(
    title="Northwind Agent API",
    description="An API for the Northwind Agent, which provides various functionalities related to the Northwind database.",
    version="v1",
)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)