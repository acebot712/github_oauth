from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
import sqlite3
from pathlib import Path
from pydantic import BaseModel
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class TokenRequest(BaseModel):
    token: str

# Configure CORS
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Replace these values with your actual GitHub client ID and secret
CLIENT_ID = os.environ.get("CLIENT_ID",'')
CLIENT_SECRET = os.environ.get("CLIENT_SECRET",'')
EXTERNAL_IP = os.environ.get("EXTERNAL_IP", '')

def get_html_from_file(filename: str) -> str:
    file_path = Path(__file__).resolve().parent / filename
    with open(file_path, "r") as file:
        return file.read()

@app.get("/")
async def index():
    html_content = get_html_from_file("index.html")
    modified_html = html_content.replace('"#process.env.CLIENT_ID#"', CLIENT_ID).replace('"#process.env.EXTERNAL_IP#"', EXTERNAL_IP)
    return HTMLResponse(modified_html)

@app.post("/api/check-token")
async def check_token(token_request: TokenRequest):
    # Extract the token from the request
    access_token = token_request.token

    # Connect to the SQLite database
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Execute the query to check the access token
    query = "SELECT * FROM access_tokens WHERE access_token = ?"
    cursor.execute(query, (access_token,))
    result = cursor.fetchone()

    # Close the database connection
    conn.close()

    # pass minimum amount to api.py, use seperate script to populate CSV using the ids from server logs
    if result is not None:
        return {"valid": True, "user_id": result['user_id'], "login_id": result['login_id']}
    else:
        return {"valid": False}

@app.get("/callback")
async def callback(request: Request, response: Response, code: str):
    try:
        print("FINE1")
        token_response = requests.post(
            'https://github.com/login/oauth/access_token',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            json={
                'client_id': str(CLIENT_ID),
                'client_secret': str(CLIENT_SECRET),
                'code': str(code)
            }
        )
        token_data = token_response.json()
        print(token_data)
        print("FINE2")

        # Get the user's data using the access token
        user_response = requests.get(
            'https://api.github.com/user',
            headers={
                'Authorization': f"Bearer {token_data['access_token']}"
            }
        )
        user_data = user_response.json()
        print(user_data)
        print("FINE3")

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Create table
        c.execute('''CREATE TABLE IF NOT EXISTS access_tokens 
                    (user_id INTEGER PRIMARY KEY, login_id, access_token TEXT)''')
        
        # Check if the user_id already exists
        c.execute('SELECT * FROM access_tokens WHERE user_id = ?', (user_data['id'],))
        existing_row = c.fetchone()

        if existing_row:
            # Update the access_token column
            c.execute('UPDATE access_tokens SET access_token = ? WHERE user_id = ?', 
              (token_data['access_token'], user_data['id']))
        else:
            # Insert a new row
            c.execute('INSERT INTO access_tokens (user_id, login_id, access_token) VALUES (?, ?, ?)', 
              (user_data['id'], user_data['login'], token_data['access_token']))

        # Commit changes
        conn.commit()

        # Close connection 
        conn.close()

        return templates.TemplateResponse(
            "success.html",
            {"request": request, "user_data": user_data, "token_data": token_data}
        )
    except Exception as e:
        print(e)
        response.status_code = 500
        return "An error occured."
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)