import asyncio
import websockets
import json

connected_clients = set()
water_cup = 0  # 伺服器的「水杯」共享變數

async def handler(websocket):
    global water_cup
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "toss":  # 玩家拋硬幣
                water_cup += 1
                print(f"收到玩家 {data['uuid']} 的拋擲，目前水杯 = {water_cup}")
                
                # 廣播給所有玩家
                update = json.dumps({
                    "type": "cup_update",
                    "water_cup": water_cup
                })
                await asyncio.wait([ws.send(update) for ws in connected_clients])
    finally:
        connected_clients.remove(websocket)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("伺服器已啟動，等待玩家連線 ws://localhost:8765")
        await asyncio.Future()  # 永遠不結束

asyncio.run(main())
