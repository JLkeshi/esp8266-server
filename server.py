import os
import asyncio
import websockets

connected_ws = set()

# ===== WebSocket handler (ESP8266) =====
async def ws_handler(websocket):
    connected_ws.add(websocket)
    print("✅ ESP connected via WebSocket")
    try:
        async for message in websocket:
            print(f"📩 From ESP: {message}")
    finally:
        connected_ws.remove(websocket)
        print("❌ ESP disconnected")

# ===== Forward messages from Python (or PHP) =====
# For Render, we can create a simple HTTP endpoint to receive PHP messages
# or use a WebSocket message directly. TCP server on arbitrary port won't work.

async def main():
    port = int(os.environ.get("PORT", 8765))  # Render provides this port
    print(f"Using port: {port}")

    # WebSocket server
    ws_server = await websockets.serve(ws_handler, "0.0.0.0", port)
    print(f"✅ WebSocket server running on ws://0.0.0.0:{port}")

    # Keep the server running
    await ws_server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
