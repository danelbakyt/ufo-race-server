import asyncio
import websockets
import os

CONNECTED_CLIENTS = set()

async def handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"INFO: Client connected. Total: {len(CONNECTED_CLIENTS)}")
    
    try:
        async for message in websocket:
            if CONNECTED_CLIENTS:
                tasks = [
                    asyncio.create_task(client.send(message))
                    for client in CONNECTED_CLIENTS
                    if client != websocket
                ]
                await asyncio.wait(tasks) 
                
    except websockets.exceptions.ConnectionClosedOK:
        pass 
    except Exception as e:
        print(f"ERROR: Error in handler for a client: {e}")
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        print(f"INFO: Client disconnected. Total: {len(CONNECTED_CLIENTS)}")

async def main():
    port = int(os.environ.get("PORT", 8765))
    host = "0.0.0.0"
    
    print(f"Server started on ws://{host}:{port}")

    async with websockets.serve(handler, host, port):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())