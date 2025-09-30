# server.py
import os
import asyncio
from aiohttp import web, WSCloseCode

PORT = int(os.environ.get("PORT", 8765))  # Render will set PORT for web services

connected_ws = set()

async def index(request):
    return web.Response(text="OK\n", status=200)

# WebSocket handler for ESP (connect via wss://<your-service>/ws)
async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_ws.add(ws)
    request.app['logger'].info("✅ ESP connected via WebSocket")
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                request.app['logger'].info(f"📩 From ESP: {msg.data}")
            elif msg.type == web.WSMsgType.ERROR:
                request.app['logger'].error(f"WebSocket error: {ws.exception()}")
    finally:
        connected_ws.discard(ws)
        request.app['logger'].info("❌ ESP disconnected")
    return ws

# HTTP POST endpoint for PHP to send messages to ESP
# Example PHP: file_get_contents('https://your-service/send'), or curl POST JSON/form
async def send_handler(request):
    # Accept JSON or form or raw text
    if request.content_type == 'application/json':
        payload = await request.json()
        message = payload.get('message', '')
    else:
        # fallback: read raw text or form
        data = await request.post() if request.can_read_body else {}
        message = data.get('message')
        if message is None:
            body = await request.text()
            message = body.strip()

    if not message:
        return web.json_response({'ok': False, 'error': 'no message provided'}, status=400)

    # forward to all connected WebSocket clients (ESP)
    if connected_ws:
        disconnected = set()
        for ws in list(connected_ws):
            try:
                await ws.send_str(message)
            except Exception as e:
                request.app['logger'].warning(f"Failed to send to ws: {e}")
                disconnected.add(ws)
        connected_ws.difference_update(disconnected)
        request.app['logger'].info(f"➡️ Sent to ESP: {message}")
        return web.json_response({'ok': True, 'sent_to': len(connected_ws)})
    else:
        request.app['logger'].warning("⚠️ No ESP connected, message not forwarded")
        return web.json_response({'ok': False, 'error': 'no connected devices'}, status=503)


async def on_startup(app):
    app['logger'].info(f"Server startup. Listening on 0.0.0.0:{PORT}")

async def on_cleanup(app):
    # close all websockets on shutdown
    for ws in list(connected_ws):
        try:
            await ws.close(code=WSCloseCode.GOING_AWAY, message='Server shutting down')
        except:
            pass
    app['logger'].info("Server cleanup complete.")

def create_app():
    app = web.Application()
    app.add_routes([
        web.get('/', index),
        web.get('/ws', ws_handler),
        web.post('/send', send_handler),
    ])
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=PORT)
