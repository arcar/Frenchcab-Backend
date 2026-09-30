from fastapi import FastAPI, HTTPException, APIRouter

app = FastAPI()
router = APIRouter()

@app.get("/test")
def get_test():

    return {
        "test": "la route fonctionne"
    }