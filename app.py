'''
To test: python3 -m websockets ws://localhost:8081/
Then paste one of the following messages:
    * { "type": "login", "username": "walter" }
    * { "type": "disconnect" }
    * { "type": "chat", "text": "Hello world!", "username": "walter" }
    * { "type": "invalid", "text": "this is an invalid message" }
    
'''

from mmap import ACCESS_COPY
from dotenv import load_dotenv
load_dotenv()

import asyncio
import websockets
import json
import os
import jwt
import requests

logged_in_users = dict()
jwt_secret = os.getenv('JWT_SECRET')
URL = "https://photo-app-demo123.herokuapp.com"
PORT = os.environ.get('PORT') or 8081


async def respond_to_message(websocket, message):
    try:
        data = json.loads(message)
        if data.get("access_token"):
            print("JWT: " + data.get("access_token"))
            access_token = data.get("access_token")
            global decoded_data
            # print("jwt_secret: ", jwt_secret, "type: " , type(jwt_secret))
            decoded_data = jwt.decode(access_token, jwt_secret, algorithms=['HS256'])
            print("id: ", decoded_data)           
        else:
            print("missing access_token")
            return await websocket.send(json.dumps({"type": "error", "text": "missing access_token"}))
        if data.get('type') == 'login':
            username = data.get('username')
            user_id = decoded_data.get('sub')
            if not user_id in logged_in_users:
                logged_in_users[user_id] = websocket
            else:
                del logged_in_users[user_id]
                logged_in_users[user_id] = websocket
            contacts = requests.get(URL + "/api/contacts", headers={'Authorization': 'Bearer ' + data.get("access_token")}).json()
            contacts_id = [contact['id'] for contact in contacts]
            print("contacts: ", contacts_id)
            print("logged_in_users: ", logged_in_users)
            if not user_id in contacts_id:
                await logged_in_users[user_id].send(json.dumps({
                        'type': 'login',
                        "users": list(logged_in_users.keys()),
                        'username': username
                    }))
            for user in logged_in_users:
                if user in contacts_id:
                    print('sending message to ', user)
                    await logged_in_users[user].send(json.dumps({
                        'type': 'login',
                        "users": list(logged_in_users.keys()),
                        'username': username
                    }))
            print(f'{username} logged in')
        if data.get('type') == 'disconnect':
            print("some debug")
            username = data.get("username")
            user_id = decoded_data.get('sub')
            del logged_in_users[user_id]
            for user in logged_in_users:
                await logged_in_users[user].send(json.dumps({
                    'type': 'disconnect',
                    'text': 'Goodbye',
                    'users': list(logged_in_users.keys())
                }))
            print(f'{username} disconnected')
        if data.get('type') == 'chat':
            if not data.get("recipient_id"):
                return await websocket.send(json.dumps({"type": "error", "text": "missing recipient_id"}))
            recipient_id = int(data.get("recipient_id"))
            print("Broadcasting message", data)
            print("logged in: ", logged_in_users)
            if recipient_id in logged_in_users:
                print("found")
                socket = logged_in_users[recipient_id]
                
                await socket.send(json.dumps({
                    'type': 'chat',
                    'text': data.get('text'),
                    'username': data.get('username')
                }))
            
    except Exception as e:
        print(e)
        print("error", message)
        data = { 
            'error': 'error decoding {0}'.format(message),
            'details': 'See instructions for list of valid message formats.'}
        return await websocket.send(json.dumps(data))
  


async def broadcast_messages(websocket, path):
    try:
        async for message in websocket:
            await respond_to_message(websocket, message)
    except websockets.ConnectionClosed as e:
        print('A client just disconnected')
        print(e)
    finally:
        if logged_in_users.get(websocket):
            del logged_in_users[websocket]
    

async def main():
    async with websockets.serve(broadcast_messages, "", PORT, ping_interval=None, ping_timeout=None):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    print('Starting web socket server...')
    print('ws://localhost:{0}'.format(PORT))
    asyncio.run(main())