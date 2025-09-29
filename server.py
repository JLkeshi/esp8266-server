import os
import asyncio
import websockets
import json

connected_ws = set()  # Store connected ESP clients

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

# ===== HTTP POST handler (for PHP commands) =====
async def http_handler(reader, writer):
    # Read HTTP request
    data = await reader.read(1024)
    request = data.decode()
    
    # Extract command from POST body
    try:
        body = request.split("\r\n\r\n")[1]
        cmd_data = json.loads(body)
        command = cmd_data.get("command", "")
        print(f"📩 Command from PHP: {command}")

        # Forward to all connected ESP clients
        if connected_ws:
            await asyncio.gather(*[ws.send(command) for ws in connected_ws])
            print(f"➡️ Sent to ESP: {command}")
        else:
            print("⚠️ No ESP connected")
    except Exception as e:
        print("❌ Error parsing request:", e)

    # Respond to PHP
    response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK"
    writer.write(response.encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def main():
    # Use Render's assigned port
    port = int(os.environ.get("PORT", 8765))
    print(f"Using Render port: {port}")

    # Start WebSocket server
    ws_server = await websockets.serve(ws_handler, "0.0.0.0", port)
    print(f"✅ WebSocket running on 0.0.0.0:{port}")

    # Start lightweight TCP server for PHP POST commands
    tcp_server = await asyncio.start_server(http_handler, "0.0.0.0", port)
    print(f"✅ HTTP command endpoint running on 0.0.0.0:{port}")

    async with ws_server, tcp_server:
        await asyncio.gather(ws_server.wait_closed(), tcp_server.serve_forever())

if __name__ == "__main__":
    asyncio.run(main())
