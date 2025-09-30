import asyncio
import websockets
import logging

# ===== Logging setup =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

connected_ws = set()  # Store connected WebSocket clients (ESP)

# ===== WebSocket handler (ESP8266) =====
async def ws_handler(websocket):
    connected_ws.add(websocket)
    logging.info("✅ ESP connected via WebSocket")
    try:
        async for message in websocket:
            logging.info(f"📩 From ESP: {message}")
    except websockets.exceptions.ConnectionClosed:
        logging.warning("⚠️ ESP connection closed unexpectedly")
    finally:
        connected_ws.discard(websocket)
        logging.info("❌ ESP disconnected")

# ===== TCP handler (PHP) =====
async def tcp_handler(reader, writer):
    data = await reader.read(1024)
    message = data.decode().strip()
    addr = writer.get_extra_info('peername')
    logging.info(f"📩 From PHP {addr}: {message}")

    # Forward message to all connected WebSocket clients (ESP)
    if connected_ws:
        disconnected = set()
        for ws in connected_ws:
            try:
                await ws.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(ws)
        # Remove disconnected clients
        connected_ws.difference_update(disconnected)
        logging.info(f"➡️ Sent to ESP: {message}")
    else:
        logging.warning("⚠️ No ESP connected, message not forwarded")

    writer.close()
    await writer.wait_closed()

# ===== Main server setup =====
async def main():
    # Start WebSocket server
    ws_server = await websockets.serve(ws_handler, "0.0.0.0", 8765)
    logging.info("✅ WebSocket server running on ws://0.0.0.0:8765")

    # Start TCP server
    tcp_server = await asyncio.start_server(tcp_handler, "0.0.0.0", 8766)
    logging.info("✅ TCP server running on 0.0.0.0:8766")

    async with ws_server, tcp_server:
        await asyncio.gather(ws_server.wait_closed(), tcp_server.serve_forever())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Server stopped manually")
