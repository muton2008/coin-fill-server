# 硬幣拋擲遊戲伺服器 (Coin Fill Server)

一個基於 WebSocket 的多人硬幣拋擲遊戲後端伺服器，專為 Godot 遊戲設計。

## 🎮 遊戲玩法

### 全服事件系統 🎪

當水杯滿時，會隨機觸發一個全服事件。每個事件都有不同的持續時間和效果：

#### 高優先級事件 (權重: 5)
- **說到做到**: 第一次落地後必定翻轉一次 (3分鐘)
- **這不公平**: 正面機率提升至70% (3分鐘)
- **飲水思源**: 每次滴入水時，每3滴水多滴入1滴 (3分鐘)
- **克服阻力**: 翻轉機率衰減率變為原本的60% (5分鐘)

#### 中等優先級事件 (權重: 3)
- **大樂透**: 下次滿水獎勵翻倍 (持續到下次滿水)
- **魚躍龍門**: 翻轉機率固定為76% (2分鐘)
- **事半功倍**: 硬幣正面可滴入的水滴量翻倍 (1分鐘)
- **烏鴉喝水**: 水杯容量減少100 (永久)
- **否極泰來**: 反面數>總數70%且>10時，獲得floor(反面數/10)個雲碎片 (3分鐘)

#### 低優先級事件 (權重: 1)
- **while(true)**: 每次正面翻轉機率+3%，最高90% (2分鐘)
- **陽光普照**: 每次拋擲結束水杯減少3滴 (1分鐘)
- **滴水之恩**: 每滴水獲得1雲碎片，單次最多5個 (1分鐘)

### 基本機制
- **硬幣拋擲**: 玩家點擊拋出硬幣，判定正反面
- **長按效果**: 長按最多5秒可提升翻轉機率至100%
- **連續翻轉**: 硬幣落地後有機率自動再次拋擲
- **共享水杯**: 全服玩家共用一個水杯，正面結果會添加水滴

### 硬幣結果
- **正面 (50%)**: 女神捧著水壺 → 添加一滴水到水杯
- **反面 (50%)**: 雲朵 → 不添加水

### 翻轉機率系統
- 初始翻轉機率：50%
- 每次落地後衰減：9%
- 最低機率限制：10%
- 長按加成：0-5秒線性提升至100%

### 水杯系統
- **水杯上限計算**:
  - 在線人數 > 10: `隨機(在線人數×4+180 ~ 在線人數×5+180)`
  - 在線人數 ≤ 10: `200`
- **滿杯獎勵**: 45個雲碎片
- **全服事件**: 水杯滿時觸發，所有玩家獲得獎勵

## 🚀 快速開始

### 安裝依賴
```bash
# 安裝 uv (Python 套件管理器)
pip install uv

# 安裝專案依賴
uv sync
```

### 啟動伺服器
```bash
# 使用 uv 執行
uv run server.py

# 或使用 Python 直接執行
python server.py
```

伺服器將在 `ws://localhost:8765` 啟動

### 測試伺服器
```bash
# 執行多玩家測試
uv run test_client.py

# 測試事件系統
uv run event_test.py

# 簡單功能測試
uv run simple_test.py
```

## 📡 WebSocket API

### 客戶端 → 伺服器

#### 拋擲硬幣
```json
{
  "type": "toss",
  "uuid": "玩家唯一識別碼",
  "hold_duration": 2.5  // 長按時間(秒)，可選，預設0
}
```

#### 查詢狀態
```json
{
  "type": "get_status",
  "uuid": "玩家唯一識別碼"
}
```

#### 查詢事件
```json
{
  "type": "get_events",
  "uuid": "玩家唯一識別碼"
}
```

### 伺服器 → 客戶端

#### 歡迎訊息 (連接時)
```json
{
  "type": "welcome",
  "water_cup": 42,
  "water_cup_limit": 200,
  "online_players": 5,
  "message": "歡迎來到硬幣拋擲遊戲！"
}
```

#### 拋擲結果
```json
{
  "type": "toss_result",
  "uuid": "玩家UUID",
  "coin_result": {
    "is_heads": true,  // 最終結果
    "flip_probability": 0.75,  // 翻轉機率
    "flip_results": [true, false, true],  // 完整翻轉序列
    "water_drops_added": 2,  // 添加的水滴數
    "heads_count": 2,  // 正面次數
    "tails_count": 1   // 反面次數
  },
  "water_cup": 44,
  "water_cup_limit": 200,
  "active_events": [  // 當前活躍事件
    {
      "key": "speak_do",
      "name": "說到做到",
      "description": "第一次落地後必定翻轉一次",
      "remaining_seconds": 180
    }
  ],
  "fragment_rewards": {  // 雲碎片獎勵 (可選)
    "after_adversity": 2,
    "drop_reward": 1,
    "total": 3
  },
  "timestamp": "2025-09-27T..."
}
```

#### 個人獎勵
```json
{
  "type": "personal_reward",
  "uuid": "玩家UUID",
  "reward": 90,  // 獲得的雲碎片數量 (可能被大樂透翻倍)
  "message": "水杯已滿，你獲得 90 個雲碎片",
  "timestamp": "2025-09-27T..."
}
```

#### 全服事件通知
```json
{
  "type": "server_event",
  "event": "new_event_started",
  "event_key": "speak_do",
  "event_name": "說到做到",
  "event_description": "第一次落地後必定翻轉一次",
  "duration_minutes": 3,
  "priority": "高",
  "message": "🎪 新的全服事件開始：說到做到 - 第一次落地後必定翻轉一次",
  "timestamp": "2025-09-27T..."
}
```

#### 事件資訊查詢回應
```json
{
  "type": "events_info",
  "active_events": [
    {
      "key": "speak_do",
      "name": "說到做到", 
      "description": "第一次落地後必定翻轉一次",
      "remaining_seconds": 180,
      "priority": "高"
    }
  ],
  "all_possible_events": [
    {
      "key": "speak_do",
      "name": "說到做到",
      "description": "第一次落地後必定翻轉一次", 
      "duration": 3,
      "priority": "高"
    }
  ],
  "timestamp": "2025-09-27T..."
}
```

#### 水杯更新 (廣播)
```json
{
  "type": "cup_update",
  "water_cup": 44,
  "water_cup_limit": 200,
  "online_players": 5
}
```

#### 全服事件 (水杯滿時)
```json
{
  "type": "server_event",
  "event": "water_cup_full",
  "reward": 45,
  "message": "水杯已滿！所有玩家獲得 45 個雲碎片！",
  "timestamp": "2025-09-27T..."
}
```

#### 錯誤訊息
```json
{
  "type": "error",
  "message": "錯誤描述"
}
```

## 🏗️ 專案結構

```
coin-fill-server/
├── server.py          # 主要伺服器程式 (含全服事件系統)
├── test_client.py     # 多玩家測試客戶端
├── event_test.py      # 事件系統專用測試
├── simple_test.py     # 簡單功能測試
├── pyproject.toml     # 專案配置
├── uv.lock           # 依賴鎖定檔案
└── README.md         # 專案說明
```

## 🛠️ 技術細節

### 核心功能
- **WebSocket 連接管理**: 自動處理客戶端連接和斷線
- **玩家會話追蹤**: UUID 基礎的玩家識別系統
- **即時廣播**: 水杯狀態和事件即時同步
- **機率計算**: 精確的翻轉機率和衰減系統
- **全服事件系統**: 12種不同效果的隨機事件，優先級權重系統
- **事件生命週期**: 自動過期清理，持續時間管理
- **雲碎片獎勵**: 多重獎勵機制，包含特殊事件加成
- **錯誤處理**: 完整的異常處理和錯誤訊息

### 依賴套件
- `websockets`: WebSocket 伺服器實現
- `typing`: 型別提示支援

## 🎯 Godot 整合

### 在 Godot 中使用
1. 使用 Godot 的 WebSocketClient 連接到 `ws://localhost:8765`
2. 發送 JSON 格式的訊息進行拋擲
3. 監聽伺服器廣播更新 UI

### 建議的 Godot 客戶端結構
```gdscript
# 範例 WebSocket 連接
extends Node

var websocket = WebSocketClient.new()
var player_uuid = UUID.v4()  # 生成唯一玩家ID

func _ready():
    websocket.connect_to_url("ws://localhost:8765")
    websocket.connect("data_received", self, "_on_data_received")

func toss_coin(hold_duration: float = 0):
    var message = {
        "type": "toss",
        "uuid": player_uuid,
        "hold_duration": hold_duration
    }
    websocket.send_text(JSON.print(message))

func _on_data_received():
    var message = JSON.parse(websocket.get_peer(1).get_packet().get_string_from_utf8())
    # 處理伺服器訊息
```

## 📊 遊戲平衡

### 翻轉機率曲線
- 基礎機率：50%
- 長按加成：線性增長至100% (5秒)
- 連續翻轉：每次-9%，最低10%

### 水杯容量設計
- 小型遊戲 (≤10人): 固定200滴
- 大型遊戲 (>10人): 動態調整，平均每人20-25滴貢獻

### 獎勵機制
- 雲碎片：45個/次滿杯事件
- 全服同享：促進合作氛圍

## 🐛 已知問題與限制

1. 伺服器重啟會重置所有狀態
2. 沒有持久化存儲
3. 沒有玩家驗證機制
4. 沒有防作弊措施

## 🔧 開發計劃

- [ ] 添加 Redis 持久化
- [ ] 實現玩家驗證
- [ ] 添加遊戲統計
- [ ] 實現防作弊機制
- [ ] 添加管理員API
- [ ] 實現房間系統

## 📄 授權

此專案為個人開發專案，請在使用前確認授權條款。