import asyncio
import websockets
import json
import uuid

async def test_decay_system():
    """測試混合衰減系統"""
    try:
        # 連接到伺服器
        websocket = await websockets.connect("ws://localhost:8765")
        print("✅ 成功連接到伺服器")
        
        player_uuid = str(uuid.uuid4())
        
        # 接收歡迎訊息
        welcome_msg = await websocket.recv()
        welcome_data = json.loads(welcome_msg)
        print(f"📩 歡迎訊息: 水杯 {welcome_data['water_cup']}/{welcome_data['water_cup_limit']}")
        
        print(f"\n🧪 測試混合衰減系統")
        print("=" * 50)
        print("📊 衰減規則:")
        print("• 前10次翻轉: 每次減少 2% (線性衰減)")
        print("• 10次之後: 每次 ×0.86 (指數衰減)")
        print("• 最低機率保底: 10%")
        print("=" * 50)
        
        # 進行高翻轉機率測試（長按5秒）
        for test_round in range(3):
            print(f"\n🎲 第 {test_round + 1} 輪測試 (長按5秒，初始機率100%)")
            print("-" * 40)
            
            # 發送拋擲請求
            toss_request = {
                "type": "toss",
                "uuid": player_uuid,
                "hold_duration": 5.0  # 長按5秒獲得100%初始機率
            }
            
            await websocket.send(json.dumps(toss_request))
            
            # 接收結果
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                
                if data["type"] == "toss_result":
                    result = data["coin_result"]
                    flip_count = len(result["flip_results"])
                    heads = result["heads_count"]
                    tails = result["tails_count"]
                    water_drops = result["water_drops_added"]
                    
                    print(f"📈 結果統計:")
                    print(f"• 總翻轉次數: {flip_count} 次")
                    print(f"• 正面/反面: {heads}/{tails}")
                    print(f"• 獲得水滴: +{water_drops}")
                    
                    # 顯示翻轉序列
                    if flip_count > 0:
                        sequence = ''.join(['正' if h else '反' for h in result['flip_results']])
                        print(f"• 翻轉序列: {sequence}")
                        
                        # 分析衰減階段
                        if flip_count <= 10:
                            print(f"• 衰減階段: 線性衰減期 (1-10次)")
                            expected_final = max(0.1, 1.0 - 0.02 * flip_count)
                            print(f"• 預期最終機率: {expected_final:.2%}")
                        else:
                            # 計算預期的指數衰減結果
                            linear_phase = 1.0 - 0.02 * 10  # 前10次線性衰減後的機率
                            exponential_phases = flip_count - 10
                            expected_final = max(0.1, linear_phase * (0.86 ** exponential_phases))
                            print(f"• 衰減階段: 線性期(1-10次) + 指數期(11-{flip_count}次)")
                            print(f"• 預期最終機率: {expected_final:.2%}")
                
                # 處理水杯更新訊息
                try:
                    update_msg = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    # 忽略水杯更新
                except asyncio.TimeoutError:
                    pass
                    
            except asyncio.TimeoutError:
                print(f"⏰ 等待回應逾時")
            
            await asyncio.sleep(1)  # 間隔1秒進行下一輪
        
        # 理論分析
        print(f"\n📊 理論分析:")
        print(f"線性衰減階段 (1-10次):")
        for i in range(1, 11):
            prob = max(0.1, 1.0 - 0.02 * i)
            print(f"  第{i}次後機率: {prob:.2%}")
        
        print(f"\n指數衰減階段 (11次+):")
        base_prob = 0.8  # 第10次後的機率
        for i in range(11, 16):
            phases = i - 10
            prob = max(0.1, base_prob * (0.86 ** phases))
            print(f"  第{i}次後機率: {prob:.2%}")
        
        await websocket.close()
        print("\n✅ 測試完成")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

if __name__ == "__main__":
    print("🎯 混合衰減系統測試")
    print("測試前10次線性衰減(-2%)，之後指數衰減(×0.86)")
    print("=" * 60)
    asyncio.run(test_decay_system())