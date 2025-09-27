import asyncio
import websockets
import json
import uuid

async def simple_test():
    """簡單的伺服器測試"""
    try:
        # 連接到伺服器
        websocket = await websockets.connect("ws://localhost:8765")
        print("✅ 成功連接到伺服器")
        
        # 等待歡迎訊息
        welcome_msg = await websocket.recv()
        welcome_data = json.loads(welcome_msg)
        print(f"📩 收到歡迎訊息: {welcome_data}")
        
        # 發送拋擲請求
        player_uuid = str(uuid.uuid4())
        toss_request = {
            "type": "toss",
            "uuid": player_uuid,
            "hold_duration": 2.5
        }
        
        await websocket.send(json.dumps(toss_request))
        print(f"🪙 發送拋擲請求: {toss_request}")
        
        # 等待結果
        for i in range(3):  # 等待最多3個訊息
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"📨 收到訊息 {i+1}: {data}")
            except asyncio.TimeoutError:
                print("⏰ 等待訊息逾時")
                break
        
        await websocket.close()
        print("✅ 測試完成")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

if __name__ == "__main__":
    print("🧪 簡單伺服器測試")
    print("=" * 30)
    asyncio.run(simple_test())