import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Import separated modules
from telemetry import setup_telemetry
from logger import logger
from middleware import add_custom_telemetry_middleware
from routes import router

app = FastAPI(title="Log Doctor Python Sample API")

# Initialize OpenTelemetry & Application Insights
setup_telemetry(app)

# Attach 5W1H custom middleware
app.middleware("http")(add_custom_telemetry_middleware)

# Include application routes
app.include_router(router)


# Optional: Custom Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception caught: {exc}")
    # SDK captures the exception trace automatically (ASGI layer hook)
    return JSONResponse(
        status_code=500,
        content={
            "message": "An intentional error occurred and was logged to Azure Monitor."
        },
    )


if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000)
