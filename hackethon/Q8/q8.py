"""
8. Local "Web-Hook" Trigger
A small Python web server that stays idle until it receives a specific "GET" request from another machine on the local network. Upon receiving it, it executes a pre-defined local maintenance script (like clearing logs).
"""
from fastapi import FastAPI

app = FastAPI()

def run_script():
    print("Running a maintanance script...")

@app.get("/")
def get_request():
    run_script()
    return {"status": "done"}

"""
pip install fastapi
pip install uvicorn
uvicorn q8:app --reload
"""
