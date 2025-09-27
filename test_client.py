import asyncio
import websockets
import json
import uuid
import random

class TestClient:
    def __init__(self, player_name: str):
        self.player_name = player_name
        self.uuid = str(uuid.uuid4())
        self.websocket = None
    
    async def connect(self):
        """連接到伺服器"""
        try:
            self.websocket = await websockets.connect("ws://localhost:8765")
            print(f"🟢 {self.player_name} 已連接到伺服器")
            return True
        except Exception as e:
            print(f"🔴 {self.player_name} 連接失敗: {e}")
            return False
    
    async def listen_for_messages(self):
        """監聽伺服器訊息"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print(f"🟡 {self.player_name} 與伺服器的連接已關閉")
        except Exception as e:
            print(f"🔴 {self.player_name} 監聽訊息時發生錯誤: {e}")
    
    async def handle_message(self, data: dict):
        """處理伺服器訊息"""
        message_type = data.get("type")
        
        if message_type == "welcome":
            print(f"🎉 {self.player_name} 收到歡迎訊息:")
            print(f"   水杯: {data['water_cup']}/{data['water_cup_limit']}")
            print(f"   在線人數: {data['online_players']}")
            
        elif message_type == "toss_result":
            result = data["coin_result"]
            print(f"🪙 {self.player_name} 拋擲結果:")
            print(f"   最終結果: {'正面(女神)' if result['is_heads'] else '反面(雲朵)'}")
            print(f"   翻轉序列: {[('正面' if h else '反面') for h in result['flip_results']]}")
            print(f"   正面/反面: {result.get('heads_count', 0)}/{result.get('tails_count', 0)}")
            print(f"   水滴數量: +{result['water_drops_added']}")
            print(f"   水杯狀態: {data['water_cup']}/{data['water_cup_limit']}")
            
            # 顯示雲碎片獎勵
            if "fragment_rewards" in data:
                fragments = data["fragment_rewards"]
                print(f"   💎 雲碎片獎勵: {fragments['total']} 個")
                if fragments["after_adversity"] > 0:
                    print(f"      - 否極泰來: {fragments['after_adversity']} 個")
                if fragments["drop_reward"] > 0:
                    print(f"      - 滴水之恩: {fragments['drop_reward']} 個")
            
            # 顯示活躍事件
            if "active_events" in data and data["active_events"]:
                print(f"   🎪 活躍事件:")
                for event in data["active_events"]:
                    print(f"      - {event['name']}: {event['description']} (剩餘 {event['remaining_seconds']}秒)")
            
        elif message_type == "cup_update":
            print(f"💧 {self.player_name} 收到水杯更新: {data['water_cup']}/{data['water_cup_limit']} (在線: {data['online_players']})")
            
        elif message_type == "server_event":
            if data["event"] == "new_event_started":
                print(f"🎆 {self.player_name} 收到新事件:")
                print(f"   事件名稱: {data['event_name']}")
                print(f"   事件描述: {data['event_description']}")
                print(f"   持續時間: {data['duration_minutes']} 分鐘")
                print(f"   優先級: {data['priority']}")
            else:
                print(f"🎆 {self.player_name} 收到全服事件: {data.get('message', '未知事件')}")
                
        elif message_type == "personal_reward":
            print(f"🎁 {self.player_name} 收到個人獎勵:")
            print(f"   {data['message']}")
            
        elif message_type == "error":
            print(f"❌ {self.player_name} 收到錯誤: {data['message']}")
            
        elif message_type == "events_info":
            print(f"📋 {self.player_name} 收到事件資訊:")
            if data.get("active_events"):
                print("   活躍事件:")
                for event in data["active_events"]:
                    print(f"   - {event['name']}: {event['description']} (剩餘 {event['remaining_seconds']}秒)")
            else:
                print("   目前沒有活躍事件")
    
    async def toss_coin(self, hold_duration: float = 0):
        """拋擲硬幣"""
        if not self.websocket:
            print(f"🔴 {self.player_name} 未連接到伺服器")
            return
        
        message = {
            "type": "toss",
            "uuid": self.uuid,
            "hold_duration": hold_duration
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            print(f"🪙 {self.player_name} 拋擲硬幣 (長按: {hold_duration:.1f}秒)")
        except Exception as e:
            print(f"🔴 {self.player_name} 拋擲硬幣失敗: {e}")
    
    async def get_status(self):
        """查詢伺服器狀態"""
        if not self.websocket:
            return
        
        message = {
            "type": "get_status",
            "uuid": self.uuid
        }
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            print(f"🔴 {self.player_name} 查詢狀態失敗: {e}")
    
    async def get_events(self):
        """查詢活躍事件"""
        if not self.websocket:
            return
        
        message = {
            "type": "get_events",
            "uuid": self.uuid
        }
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            print(f"🔴 {self.player_name} 查詢事件失敗: {e}")
    
    async def disconnect(self):
        """斷開連接"""
        if self.websocket:
            await self.websocket.close()
            print(f"🟡 {self.player_name} 已斷開連接")

async def simulate_player(player_name: str, toss_count: int = 5):
    """模擬一個玩家的行為"""
    client = TestClient(player_name)
    
    if not await client.connect():
        return
    
    # 啟動訊息監聽
    listen_task = asyncio.create_task(client.listen_for_messages())
    
    try:
        # 等待接收歡迎訊息
        await asyncio.sleep(1)
        
        # 查詢初始狀態
        await client.get_status()
        await asyncio.sleep(0.5)
        
        # 查詢活躍事件
        await client.get_events()
        await asyncio.sleep(0.5)
        
        # 進行多次拋擲
        for i in range(toss_count):
            # 隨機長按時間 (0-5秒)
            hold_duration = random.uniform(0, 5)
            await client.toss_coin(hold_duration)
            
            # 隨機等待間隔
            await asyncio.sleep(random.uniform(1, 3))
        
        # 最後等待一下接收剩餘訊息
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"🔴 {player_name} 模擬過程中發生錯誤: {e}")
    finally:
        listen_task.cancel()
        await client.disconnect()

async def main():
    print("🎮 硬幣拋擲遊戲 - 測試客戶端")
    print("=" * 50)
    
    # 創建多個玩家進行測試
    players = ["Alice", "Bob", "Charlie", "Diana"]
    
    # 並行模擬多個玩家
    tasks = []
    for player_name in players:
        task = asyncio.create_task(simulate_player(player_name, toss_count=8))
        tasks.append(task)
        # 錯開連接時間
        await asyncio.sleep(0.5)
    
    # 等待所有玩家完成
    await asyncio.gather(*tasks)
    
    print("\n🏁 測試完成")

if __name__ == "__main__":
    asyncio.run(main())