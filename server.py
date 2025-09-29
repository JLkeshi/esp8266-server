import asyncio
import websockets

connected_ws = set()  # Store connected WebSocket clients (ESP)

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

# ===== TCP handler (PHP) =====
async def tcp_handler(reader, writer):
    data = await reader.read(1024)
    message = data.decode().strip()
    addr = writer.get_extra_info('peername')
    print(f"📩 From PHP {addr}: {message}")

    # Forward message to all WebSocket clients (ESP)
    if connected_ws:
        await asyncio.gather(*[ws.send(message) for ws in connected_ws])
        print(f"➡️ Sent to ESP: {message}")
    else:
        print("⚠️ No ESP connected, message not forwarded")

    writer.close()
    await writer.wait_closed()

async def main():
    # Start WebSocket server
    ws_server = await websockets.serve(ws_handler, "0.0.0.0", 8765)
    print("✅ WebSocket server running on ws://0.0.0.0:8765")

    # Start TCP server
    tcp_server = await asyncio.start_server(tcp_handler, "0.0.0.0", 8766)
    print("✅ TCP server running on 127.0.0.1:8766")

    async with ws_server, tcp_server:
        await asyncio.gather(ws_server.wait_closed(), tcp_server.serve_forever())

if __name__ == "__main__":
    asyncio.run(main())
