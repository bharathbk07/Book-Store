from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2

from app.auth.auth_routes import router as auth_router
from app.users.user_routes import router as user_router
from app.books.view_books import router as books_router

class OAuth2BearerHeader(OAuth2):
    def __init__(self):
        flows = OAuthFlowsModel(password={"tokenUrl": "login"})
        super().__init__(flows=flows)

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
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/users", tags=["User Management"])
app.include_router(books_router, prefix="/books", tags=["Books Management"])

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

