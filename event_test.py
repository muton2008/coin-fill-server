import asyncio
import websockets
import json
import uuid

async def test_events_system():
    """測試全服事件系統"""
    try:
        # 連接到伺服器
        websocket = await websockets.connect("ws://localhost:8765")
        print("✅ 成功連接到伺服器")
        
        player_uuid = str(uuid.uuid4())
        
        # 接收歡迎訊息
        welcome_msg = await websocket.recv()
        welcome_data = json.loads(welcome_msg)
        print(f"📩 歡迎訊息: 水杯 {welcome_data['water_cup']}/{welcome_data['water_cup_limit']}")
        
        # 查詢事件
        await websocket.send(json.dumps({"type": "get_events", "uuid": player_uuid}))
        events_msg = await websocket.recv()
        events_data = json.loads(events_msg)
        print(f"🎪 事件資訊: {len(events_data.get('active_events', []))} 個活躍事件")
        
        # 進行多次拋擲來測試事件觸發
        print("\n開始測試拋擲...")
        for i in range(20):  # 進行20次拋擲
            # 發送拋擲請求
            toss_request = {
                "type": "toss",
                "uuid": player_uuid,
                "hold_duration": 3.0  # 長按3秒增加翻轉機率
            }
            
            await websocket.send(json.dumps(toss_request))
            print(f"\n🪙 第 {i+1} 次拋擲:")
            
            # 接收可能的多個回應
            responses_received = 0
            timeout_count = 0
            
            while responses_received < 3 and timeout_count < 2:  # 最多接收3個回應或2次超時
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    responses_received += 1
                    
                    if data["type"] == "toss_result":
                        result = data["coin_result"]
                        print(f"   結果: {'正面' if result['is_heads'] else '反面'}")
                        print(f"   翻轉: {len(result['flip_results'])} 次")
                        print(f"   水滴: +{result['water_drops_added']}")
                        print(f"   水杯: {data['water_cup']}/{data['water_cup_limit']}")
                        
                        if "active_events" in data:
                            active_events = data["active_events"]
                            if active_events:
                                print(f"   🎪 活躍事件: {len(active_events)} 個")
                                for event in active_events:
                                    print(f"      - {event['name']}: {event['remaining_seconds']}秒剩餘")
                        
                        if "fragment_rewards" in data:
                            fragments = data["fragment_rewards"]
                            print(f"   💎 獲得雲碎片: {fragments['total']} 個")
                    
                    elif data["type"] == "server_event":
                        if data["event"] == "new_event_started":
                            print(f"   🎆 新事件開始: {data['event_name']}")
                            print(f"      描述: {data['event_description']}")
                    
                    elif data["type"] == "personal_reward":
                        print(f"   🎁 個人獎勵: {data['message']}")
                    
                    elif data["type"] == "cup_update":
                        pass  # 水杯更新訊息不用特別顯示
                    
                except asyncio.TimeoutError:
                    timeout_count += 1
                    break
            
            # 每10次拋擲後查詢一次狀態
            if (i + 1) % 10 == 0:
                await websocket.send(json.dumps({"type": "get_status", "uuid": player_uuid}))
                try:
                    status_msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    status_data = json.loads(status_msg)
                    if status_data["type"] == "status":
                        print(f"\n📊 狀態更新:")
                        print(f"   水杯: {status_data['water_cup']}/{status_data['water_cup_limit']}")
                        print(f"   在線人數: {status_data['online_players']}")
                        if status_data.get("active_events"):
                            print(f"   活躍事件: {len(status_data['active_events'])} 個")
                except asyncio.TimeoutError:
                    pass
            
            await asyncio.sleep(0.5)  # 短暫延遲
        
        await websocket.close()
        print("\n✅ 測試完成")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

if __name__ == "__main__":
    print("🧪 全服事件系統測試")
    print("=" * 50)
    asyncio.run(test_events_system())