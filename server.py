from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Replace these values with your actual GitHub client ID and secret
CLIENT_ID = os.environ.get("CLIENT_ID",'')
CLIENT_SECRET = os.environ.get("CLIENT_SECRET",'')

@app.get("/callback")
async def callback(request: Request, response: Response, code: str):
    try:
        token_response = requests.post(
            'https://github.com/login/oauth/access_token',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            json={
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'code': code
            }
        )
        token_data = token_response.json()

        # Get the user's data using the access token
        user_response = requests.get(
            'https://api.github.com/user',
            headers={
                'Authorization': f"Bearer {token_data['access_token']}"
            }
        )
        user_data = user_response.json()

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
    uvicorn.run(app, host="127.0.0.1", port=3000)