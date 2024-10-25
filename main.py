from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2

# Import routers
from app.auth.auth_routes import router as auth_router
from app.users.user_routes import router as user_router
from app.books.bookscontroller import router as books_router
from app.search.searchcontroller import router as search_router

# Set up OAuth2 authentication
class OAuth2BearerHeader(OAuth2):
    def __init__(self):
        flows = OAuthFlowsModel(password={"tokenUrl": "/auth/login"})
        super().__init__(flows=flows)

# Create FastAPI instance
app = FastAPI()

# Middleware: Allow Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust to your needs
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/users", tags=["User Management"])
app.include_router(books_router, prefix="/books", tags=["Books Management"])
app.include_router(search_router, prefix="/api", tags=["Cart Management"])

# Global Exception Handling
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    # Log the exception (optional)
    print(f"An error occurred on {request.url}: {exc}")

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

# Run the app using uvicorn
# Command: uvicorn main:app --reload

