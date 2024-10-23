from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.CustomerLogin import router as user_router

app = FastAPI()

# Middleware: Allow Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to your needs, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(user_router, prefix="/api", tags=["User Action"])

# Global Exception Handling
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    # Log the exception if needed (you can use logging here)
    print(f"An error occurred: {exc}")

    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

# uvicorn main:app --reload
# Define any additional routes if needed

# If you're using a database connection, make sure to include that setup here too.
