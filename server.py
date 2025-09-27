import asyncio
import websockets
from websockets.legacy.server import WebSocketServerProtocol
import json
import random
import time
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import os

flip_time = {} #test

connected_clients: Set[WebSocketServerProtocol] = set()
water_cup: int = 0
water_cup_limit: int = 200
cloud_fragments_reward: int = 45

class EventPriority(Enum):
    """事件優先級"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

@dataclass
class ServerEvent:
    """全服事件資料結構"""
    name: str
    description: str
    duration_minutes: int
    priority: EventPriority
    start_time: float
    active: bool = True
    
    def is_expired(self) -> bool:
        """檢查事件是否過期"""
        return time.time() - self.start_time > self.duration_minutes * 60
    
    def remaining_time(self) -> int:
        """獲取剩餘時間（秒）"""
        elapsed = time.time() - self.start_time
        remaining = (self.duration_minutes * 60) - elapsed
        return max(0, int(remaining))

# 事件管理
active_events: Dict[str, ServerEvent] = {}

# 定義所有可能的全服事件
SERVER_EVENTS = {
    "speak_do": {
        "name": "說到做到",
        "description": "第一次落地後必定翻轉一次",
        "duration": 3,
        "priority": EventPriority.HIGH
    },
    "unfair": {
        "name": "這不公平",
        "description": "正面機率提升至70%",
        "duration": 3,
        "priority": EventPriority.HIGH
    },
    "water_source": {
        "name": "飲水思源",
        "description": "每次滴入水時，每3滴水多滴入1滴",
        "duration": 3,
        "priority": EventPriority.HIGH
    },
    "lottery": {
        "name": "大樂透",
        "description": "下次滿水獎勵翻倍",
        "duration": None,  # 持續到下次滿水
        "priority": EventPriority.MEDIUM
    },
    "overcome": {
        "name": "克服阻力",
        "description": "翻轉機率衰減率變為原本的60%",
        "duration": 5,
        "priority": EventPriority.HIGH
    },
    "dragon_gate": {
        "name": "魚躍龍門",
        "description": "翻轉機率固定為76%",
        "duration": 2,
        "priority": EventPriority.MEDIUM
    },
    "double_work": {
        "name": "事半功倍",
        "description": "硬幣正面可滴入的水滴量翻倍",
        "duration": 1,
        "priority": EventPriority.MEDIUM
    },
    "crow_water": {
        "name": "烏鴉喝水",
        "description": "水杯容量減少100",
        "duration": None,  # 永久性
        "priority": EventPriority.MEDIUM
    },
    "while_true": {
        "name": "while(true)",
        "description": "拋擲時每次硬幣為正面，翻轉機率提升3%，但不會超過90%",
        "duration": 2,
        "priority": EventPriority.LOW
    },
    "after_adversity": {
        "name": "否極泰來",
        "description": "一次拋擲事件中，若反面數 > 總數的70% 且 反面數 > 10，獲得 floor(反面數/10) 個雲碎片",
        "duration": 3,
        "priority": EventPriority.MEDIUM
    },
    "sunshine": {
        "name": "陽光普照",
        "description": "每次拋擲事件結束，水杯原有的水減少3",
        "duration": 1,
        "priority": EventPriority.LOW
    },
    "drop_reward": {
        "name": "滴水之恩",
        "description": "每滴入一滴水，獲得 1 個雲碎片，一次拋擲事件可獲得上限為 5 個",
        "duration": 1,
        "priority": EventPriority.LOW
    }
}
@dataclass
class Player:
    """玩家資料結構"""
    uuid: str
    websocket: WebSocketServerProtocol
    last_toss_time: float = 0
    last_toss_time: float = 0

@dataclass
class CoinToss:
    """硬幣拋擲結果"""
    is_heads: bool  # True = 正面(女神), False = 反面(雲朵)
    flip_probability: float  # 翻轉機率
    water_drops_added: int  # 添加的水滴數
    flip_results: List[bool]  # 連續翻轉結果
    after_adversity_fragments: int = 0  # 否極泰來獲得的雲碎片
    heads_count: int = 0  # 正面次數
    tails_count: int = 0  # 反面次數
    drop_reward_fragments: int = 0  # 滴水之恩獲得的雲碎片

# 玩家管理
players: Dict[str, Player] = {}

def clean_expired_events():
    """清理過期的事件"""
    global active_events
    expired_keys = [key for key, event in active_events.items() if event.is_expired()]
    for key in expired_keys:
        print(f"🕐 事件 '{active_events[key].name}' 已過期")
        del active_events[key]

def is_event_active(event_key: str) -> bool:
    """檢查事件是否活躍"""
    if event_key not in active_events:
        return False
    event = active_events[event_key]
    if event.is_expired():
        del active_events[event_key]
        return False
    return True

def start_server_event(event_key: str) -> bool:
    """啟動全服事件"""
    if event_key not in SERVER_EVENTS:
        return False
    
    event_info = SERVER_EVENTS[event_key]
    duration = event_info["duration"]
    
    # 對於永久性事件（如烏鴉喝水），設定一個很長的持續時間
    if duration is None:
        duration = 999999999
    
    active_events[event_key] = ServerEvent(
        name=event_info["name"],
        description=event_info["description"],
        duration_minutes=duration,
        priority=event_info["priority"],
        start_time=time.time()
    )
    
    print(f"🎪 全服事件啟動: {event_info['name']} - {event_info['description']}")
    return True

def get_random_server_event() -> str:
    """根據優先級權重隨機選擇一個事件"""
    # 權重：高=5, 中=3, 低=1
    weighted_events = []
    for key, info in SERVER_EVENTS.items():
        priority = info["priority"]
        weight = 5 if priority == EventPriority.HIGH else (3 if priority == EventPriority.MEDIUM else 1)
        weighted_events.extend([key] * weight)
    
    return random.choice(weighted_events)

def apply_water_source_bonus(water_drops: int) -> int:
    """飲水思源事件：每3滴水多滴入1滴"""
    if is_event_active("water_source"):
        bonus = water_drops // 3
        return water_drops + bonus
    return water_drops

def apply_double_work_bonus(water_drops: int) -> int:
    """事半功倍事件：硬幣正面可滴入的水滴量翻倍"""
    if is_event_active("double_work"):
        return water_drops * 2
    return water_drops

def get_current_heads_probability() -> float:
    """獲取當前正面機率（受事件影響）"""
    if is_event_active("unfair"):
        return 0.7  # 這不公平：正面機率提升至70%
    return 0.5  # 正常50%

def get_flip_decay_rate() -> float:
    """獲取翻轉機率衰減率（受事件影響）"""
    if is_event_active("overcome"):
        return 0.08 * 0.6  # 克服阻力：衰減率變為原本的60%
    return 0.08  # 正常8%

def get_fixed_flip_probability() -> Optional[float]:
    """獲取固定的翻轉機率（如果有相關事件）"""
    if is_event_active("dragon_gate"):
        return 0.76  # 魚躍龍門：翻轉機率固定為76%
    return None

def calculate_while_true_bonus(heads_count: int) -> float:
    """while(true)事件：每次正面提升3%翻轉機率"""
    if is_event_active("while_true"):
        bonus = heads_count * 0.03
        return min(bonus, 0.4)  # 最多提升40%（到90%）
    return 0.0

def get_online_player_count() -> int:
    """獲取在線玩家數量"""
    return len(connected_clients)

def calculate_water_cup_limit() -> int:
    """根據在線人數計算水杯上限"""
    online_count = get_online_player_count()
    if online_count > 10:
        # random(online_member × 4 + 180 ~ online_member × 5 + 180)
        min_limit = online_count * 4 + 180
        max_limit = online_count * 5 + 180
        base_limit = random.randint(min_limit, max_limit)
    else:
        base_limit = 200
    
    # 烏鴉喝水事件：水杯容量減少100
    if is_event_active("crow_water"):
        base_limit = max(water_cup + 50, base_limit - 100)  # 最少保持剩餘50的容量
    
    return base_limit

def calculate_flip_probability(hold_duration: float) -> float:
    """
    根據長按時間計算翻轉機率
    最多長按5秒（100%），線性增長
    """
    if hold_duration <= 0:
        return 0.5  # 基礎50%
    elif hold_duration >= 5:
        return 0.97  # 最多97%
    else:
        # 線性插值：0秒=50%, 5秒=97%
        return 0.5 + (hold_duration / 5.0) * 0.47

def perform_coin_flip(initial_flip_prob: float, player_uuid: str) -> CoinToss:
    """
    執行硬幣拋擲，包含連續翻轉邏輯和事件效果
    """
    clean_expired_events()  # 清理過期事件
    
    flip_results = []
    water_drops = 0
    heads_count = 0
    tails_count = 0
    
    # 獲取當前正面機率（受事件影響）
    heads_prob = get_current_heads_probability()
    
    # 初次拋擲
    is_heads = random.random() < heads_prob
    flip_results.append(is_heads)
    
    if is_heads:
        heads_count += 1
        water_drops += 1
    else:
        tails_count += 1
    
    # 說到做到事件：第一次落地後必定翻轉一次
    force_first_flip = is_event_active("speak_do")
    
    # 連續翻轉邏輯
    flip_chance = initial_flip_prob
    fixed_prob = get_fixed_flip_probability()  # 檢查是否有固定機率
    
    flip_count = 0
    while True:
        time.sleep(0.0005)
        
        # 計算當前翻轉機率
        if fixed_prob is not None:
            # 魚躍龍門：使用固定翻轉機率
            current_flip_chance = fixed_prob
        else:
            current_flip_chance = flip_chance
            
        # while(true) 事件加成
        while_true_bonus = calculate_while_true_bonus(heads_count)
        current_flip_chance = min(current_flip_chance + while_true_bonus, 0.9)
        
        # 判斷是否要翻轉
        should_flip = (force_first_flip and flip_count == 0) or random.random() < current_flip_chance
        
        if not should_flip:
            break
            
        # 進行翻轉
        is_heads = random.random() < heads_prob
        flip_results.append(is_heads)
        flip_count += 1
        
        if is_heads:
            heads_count += 1
            water_drops += 1
        else:
            tails_count += 1
        
        # 混合衰減系統（只在非固定機率時生效）
        if fixed_prob is None:
            if flip_count <= 10:
                # 前10次：線性衰減，每次減少0.5%
                decay_amount = 0.005
                if is_event_active("overcome"):
                    decay_amount *= 0.6  # 克服阻力事件：衰減率變為60%
                flip_chance = max(0.1, flip_chance - decay_amount)
                print(f"玩家: {player_uuid} 線性衰減第{flip_count}次，機率: {flip_chance:.4f} (-{decay_amount:.2%})")
            else:
                # 第10次之後：指數衰減，每次×0.92
                exponential_factor = 0.92
                if is_event_active("overcome"):
                    exponential_factor = 0.86 + (1 - 0.86) * 0.4  # 克服阻力：緩和指數衰減
                flip_chance = max(0.1, flip_chance * exponential_factor)
                print(f"玩家: {player_uuid} 指數衰減第{flip_count}次，機率: {flip_chance:.4f} (×{exponential_factor:.3f})")
        
        force_first_flip = False  # 強制翻轉只生效一次
    
    # 應用事件加成
    water_drops = apply_double_work_bonus(water_drops)  # 事半功倍
    water_drops = apply_water_source_bonus(water_drops)  # 飲水思源
    
    # 否極泰來事件檢查
    total_flips = len(flip_results)
    after_adversity_fragments = 0
    if is_event_active("after_adversity"):
        if tails_count >= total_flips * 0.7 and tails_count > 10:
            after_adversity_fragments = tails_count // 10
    
    # 滴水之恩事件檢查
    drop_reward_fragments = 0
    if is_event_active("drop_reward"):
        drop_reward_fragments = min(water_drops, 5)  # 最多5個雲碎片
    
    return CoinToss(
        is_heads=flip_results[-1],  # 最後一次的結果
        flip_probability=initial_flip_prob,
        water_drops_added=water_drops,
        flip_results=flip_results,
        after_adversity_fragments=after_adversity_fragments,
        heads_count=heads_count,
        tails_count=tails_count,
        drop_reward_fragments=drop_reward_fragments
    )

async def broadcast_to_all(message: dict):
    """向所有連接的客戶端廣播訊息"""
    if connected_clients:
        message_str = json.dumps(message)
        disconnected = set()
        for websocket in connected_clients:
            try:
                await websocket.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
        
        # 清理斷線的連接
        connected_clients.difference_update(disconnected)
        for ws in disconnected:
            # 找到對應的玩家並移除
            player_to_remove = None
            for uuid, player in players.items():
                if player.websocket == ws:
                    player_to_remove = uuid
                    break
            if player_to_remove:
                del players[player_to_remove]

async def handle_water_cup_full(websocket, uuid):
    """處理水杯裝滿事件"""
    global water_cup, cloud_fragments_reward
    print(f"🎉 水杯已滿！觸發全服事件")
    
    # 計算獎勵（大樂透事件可能翻倍）
    reward = cloud_fragments_reward
    if is_event_active("lottery"):
        reward *= 2
        # 大樂透事件只生效一次，使用後移除
        if "lottery" in active_events:
            del active_events["lottery"]
            print("🎰 大樂透事件已消耗，獎勵翻倍！")
    # 烏鴉喝水事件
    if "crow_water" in active_events:
        del active_events["crow_water"]
        print("烏鴉喝水事件已消耗，水杯容量恢復！")
    
    # 向裝滿水杯的玩家發放雲碎片
    await websocket.send(json.dumps({
        "type": "personal_reward",
        "uuid": uuid,
        "reward": reward,
        "message": f"水杯已滿，你獲得 {reward} 個雲碎片",
        "timestamp": datetime.now().isoformat()
    }))
    
    # 隨機選擇一個新的全服事件
    new_event_key = get_random_server_event()
    event_started = start_server_event(new_event_key)
    
    if event_started:
        event_info = active_events[new_event_key]
        # 向所有玩家廣播新的全服事件
        await broadcast_to_all({
            "type": "server_event",
            "event": "new_event_started",
            "event_key": new_event_key,
            "event_name": event_info.name,
            "event_description": event_info.description,
            "duration_minutes": event_info.duration_minutes,
            "priority": event_info.priority.value,
            "reward": reward,
            "message": f"🎪 新的全服事件開始：{event_info.name} - {event_info.description}",
            "timestamp": datetime.now().isoformat()
        })
    
    # 重置水杯和上限
    water_cup = 0
    global water_cup_limit
    water_cup_limit = calculate_water_cup_limit()
    print(f"水杯已重置，新的上限：{water_cup_limit}")

async def handle_coin_toss(websocket, data: dict):
    """處理硬幣拋擲請求"""
    global water_cup, water_cup_limit
    
    try:
        uuid = data.get("uuid")
        hold_duration = data.get("hold_duration", 0)  # 長按時間（秒）
        
        if not uuid:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "缺少玩家 UUID"
            }))
            return
        
        # 更新玩家資訊
        if uuid not in players:
            players[uuid] = Player(uuid=uuid, websocket=websocket)
        else:
            players[uuid].websocket = websocket
        
        current_time = time.time()
        players[uuid].last_toss_time = current_time
        
        # 計算翻轉機率
        flip_prob = calculate_flip_probability(hold_duration)
        
        # 執行硬幣拋擲
        toss_result = perform_coin_flip(flip_prob, uuid)
        
        # 更新水杯
        old_water_cup = water_cup
        water_cup += toss_result.water_drops_added
        
        # 陽光普照事件：每次拋擲事件結束，水杯原有的水減少3
        if is_event_active("sunshine"):
            water_reduction = min(3, old_water_cup)  # 不能減少超過現有的水
            water_cup -= water_reduction
            print(f"☀️ 陽光普照事件：水杯減少 {water_reduction} 滴水")
        
        print(f"玩家 {uuid} 拋擲硬幣:")
        print(f"  - 長按時間: {hold_duration:.2f}秒")
        print(f"  - 翻轉機率: {flip_prob:.2%}")
        print(f"  - 翻轉序列: {['正面' if h else '反面' for h in toss_result.flip_results]}")
        print(f"  - 正面/反面: {toss_result.heads_count}/{toss_result.tails_count}")
        print(f"  - 水滴數量: {toss_result.water_drops_added}")
        print(f"  - 水杯: {old_water_cup} → {water_cup}")
        
        # 計算總獲得的雲碎片
        total_fragments = toss_result.after_adversity_fragments + toss_result.drop_reward_fragments
        
        # 向拋擲者發送結果
        result_message = {
            "type": "toss_result",
            "uuid": uuid,
            "coin_result": {
                "is_heads": toss_result.is_heads,
                "flip_probability": flip_prob,
                "flip_results": toss_result.flip_results,
                "water_drops_added": toss_result.water_drops_added,
                "heads_count": toss_result.heads_count,
                "tails_count": toss_result.tails_count
            },
            "water_cup": water_cup,
            "water_cup_limit": water_cup_limit,
            "active_events": [{
                "key": key,
                "name": event.name,
                "description": event.description,
                "remaining_seconds": event.remaining_time()
            } for key, event in active_events.items()],
            "timestamp": datetime.now().isoformat()
        }
        if flip_time.get(toss_result.heads_count + toss_result.tails_count):
            flip_time[toss_result.heads_count + toss_result.tails_count] += 1
        else:
            flip_time[toss_result.heads_count + toss_result.tails_count] = 1
        print(f"flip_time: {flip_time}")

        # 添加雲碎片獎勵資訊
        if total_fragments > 0:
            result_message["fragment_rewards"] = {
                "after_adversity": toss_result.after_adversity_fragments,
                "drop_reward": toss_result.drop_reward_fragments,
                "total": total_fragments
            }
        
        await websocket.send(json.dumps(result_message))
        
        # 向所有玩家廣播水杯更新
        await broadcast_to_all({
            "type": "cup_update",
            "water_cup": water_cup,
            "water_cup_limit": water_cup_limit,
            "online_players": get_online_player_count()
        })
        
        # 檢查是否裝滿水杯
        if water_cup >= water_cup_limit:
            await handle_water_cup_full(websocket, uuid)
            
            # 重新廣播新的水杯狀態
            await broadcast_to_all({
                "type": "cup_update",
                "water_cup": water_cup,
                "water_cup_limit": water_cup_limit,
                "online_players": get_online_player_count()
            })
        
    except Exception as e:
        print(f"處理硬幣拋擲時發生錯誤: {e}")
        await websocket.send(json.dumps({
            "type": "error",
            "message": f"處理拋擲請求時發生錯誤: {str(e)}"
        }))

async def handle_get_status(websocket, data: dict):
    """處理狀態查詢請求"""
    clean_expired_events()
    await websocket.send(json.dumps({
        "type": "status",
        "water_cup": water_cup,
        "water_cup_limit": water_cup_limit,
        "online_players": get_online_player_count(),
        "active_events": [{
            "key": key,
            "name": event.name,
            "description": event.description,
            "remaining_seconds": event.remaining_time(),
            "priority": event.priority.value
        } for key, event in active_events.items()],
        "timestamp": datetime.now().isoformat()
    }))

async def handle_get_events(websocket, data: dict):
    """處理事件查詢請求"""
    clean_expired_events()
    await websocket.send(json.dumps({
        "type": "events_info",
        "active_events": [{
            "key": key,
            "name": event.name,
            "description": event.description,
            "remaining_seconds": event.remaining_time(),
            "priority": event.priority.value
        } for key, event in active_events.items()],
        "all_possible_events": [{
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "duration": info["duration"],
            "priority": info["priority"].value
        } for key, info in SERVER_EVENTS.items()],
        "timestamp": datetime.now().isoformat()
    }))

async def handler(websocket):
    """WebSocket 連接處理器"""
    global water_cup_limit
    
    connected_clients.add(websocket)
    print(f"新玩家連接，當前在線人數: {get_online_player_count()}")
    
    # 重新計算水杯上限
    water_cup_limit = calculate_water_cup_limit()
    
    try:
        # 向新連接的客戶端發送當前狀態
        await websocket.send(json.dumps({
            "type": "welcome",
            "water_cup": water_cup,
            "water_cup_limit": water_cup_limit,
            "online_players": get_online_player_count(),
            "message": "歡迎來到硬幣拋擲遊戲！"
        }))
        
        # 向其他玩家廣播在線人數更新
        await broadcast_to_all({
            "type": "cup_update",
            "water_cup": water_cup,
            "water_cup_limit": water_cup_limit,
            "online_players": get_online_player_count()
        })
        
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == "toss":
                    await handle_coin_toss(websocket, data)
                elif message_type == "get_status":
                    await handle_get_status(websocket, data)
                elif message_type == "get_events":
                    await handle_get_events(websocket, data)
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": f"未知的訊息類型: {message_type}"
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "無效的 JSON 格式"
                }))
            except Exception as e:
                print(f"處理訊息時發生錯誤: {e}")
                await websocket.send(json.dumps({
                    "type": "error", 
                    "message": "伺服器內部錯誤"
                }))
                
    except websockets.exceptions.ConnectionClosed:
        print("客戶端連接已關閉")
    except Exception as e:
        print(f"WebSocket 連接錯誤: {e}")
    finally:
        connected_clients.discard(websocket)
        
        # 找到並移除對應的玩家
        player_to_remove = None
        for uuid, player in players.items():
            if player.websocket == websocket:
                player_to_remove = uuid
                break
        if player_to_remove:
            del players[player_to_remove]
            
        print(f"玩家離開，當前在線人數: {get_online_player_count()}")
        
        # 重新計算水杯上限
        water_cup_limit = calculate_water_cup_limit()
        
        # 向剩餘玩家廣播更新
        await broadcast_to_all({
            "type": "cup_update",
            "water_cup": water_cup,
            "water_cup_limit": water_cup_limit,
            "online_players": get_online_player_count()
        })

async def main():
    global water_cup_limit
    water_cup_limit = calculate_water_cup_limit()
    
    print("🎮 硬幣拋擲遊戲伺服器")
    print("=" * 50)
    print("遊戲設定:")
    print("• 正面機率: 50% (女神捧著水壺)")
    print("• 反面機率: 50% (雲朵)")  
    print("• 翻轉機率: 50% 起始，混合衰減系統")
    print("  - 前10次：每次 -2% (線性衰減)")
    print("  - 10次後：每次 ×0.86 (指數衰減)")
    print("• 長按效果: 最多 5 秒提升翻轉機率至 97%")
    print("• 雲碎片獎勵: 水杯滿時獲得 45 個")
    print("=" * 50)
    
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("🚀 伺服器已啟動，等待玩家連線 ws://localhost:8765")
        await asyncio.Future()  # 永遠不結束

if __name__ == "__main__":
    asyncio.run(main())
