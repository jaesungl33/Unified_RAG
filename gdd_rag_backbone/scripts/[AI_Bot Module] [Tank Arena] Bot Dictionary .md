# [AI/Bot Module] [Tank Arena] Bot Dictionary

## 1. Mục đích - Mục tiêu tài liệu

Tài liệu này dùng để thống kê chỉ số/hành vi của các con Bot.

❗ Các chỉ số và hành vi này sẽ được sử dụng để xây dựng các bot

## 2. Bot config

Thiết lập hành vi bot dựa trên bảng sau: [AI/Bot [Module\]](https://fsg14sbxigaq.sg.larksuite.com/sheets/ZU01sBzukhkw8wtIM8SlWeqxgDf?from=from_copylink) [Tank Arena] Bot Config

| N PARAMETERS TỰ ĐỘNG ĐIỀU CHỈNH |         |         |         |
|---------------------------------|---------|---------|---------|
| Parameter                       | Level 1 | Level 3 | Level 5 |
| Fire Rate                       | 40%     | 80%     | 100%    |
| Reaction Time                   | 0.5s    | 0.15s   | 0s      |
| Aim Speed                       | Slow    | Medium  | Instant |
| Retreat HP                      | 50%     | 30%     | 20%     |
| Skill Usage                     | 10%     | 30%     | 50%     |
| Decision Quality                | Poor    | Good    | Perfect |

## 3. Hành vi bot

### 3.1 Khả năng quan sát

❗ Tìm và cập nhật vị trí các kẻ địch

#### Code block

- Max Observation Distance: Phạm vi quan sát kẻ địch 1
- Max enemies observed: Số lượng đối tượng được theo dõi 2
- Raycast Directions: Số lượng tia raycast được sử dụng (Chia đều các tia trên 1 vòng tròn 360°, tâm là tank bot) 3

- Kẻ địch được tìm thấy khi nó đi xuyên qua tia raycast
- Kẻ địch bị theo dõi luôn được cập nhật vị trí
- Kẻ địch bị theo dõi chỉ bị xoá theo dõi khi nó bị phá huỷ
- Khi đã lựa chọn đi tấn công thì sẽ chọn mục tiêu (Nếu có nhiều hơn 1) dựa vào khoảng cách gần nhất.

![](_page_1_Picture_4.jpeg)

8 tia raycasts (Nằm trên mặt phẳng sàn chơi)

❗ THÊM SỐ LƯỢNG THEO DÕI VÀ SỐ LƯỢNG TIA SỬ DỤNG SẼ LÀM CHẬM GAME.

### 3.1 Độ hung hăng

❗ Theo đuổi và tấn công kẻ địch

#### Code block

- Aggressiveness: Xác định tần suất bắn đối tượng 1
- Ability Usage Frequency: Xác định tần suất sử dụng kỹ năng 2

#### Aggresiveness

- Quyết định khả năng tấn công kẻ địch dựa vào chỉ số "hung hăng" (Từ 0 -> 1, hiểu là 0% -> 100%)
- Không chọn hành vi mới tới khi thoả các điều kiện như mục tiêu chết hoặc rút lui.

### Tần suất sử dụng skills

- Quyết định việc sử dụng kỹ năng hay không.
- Được xác định tại bất kì thời điểm nào trong mode chơi.

### 3.2 Độ nhút nhát

❗ Rút lui và bảo tồn mạng sống của bot

#### Code block

Retreat Health Threshold: Bật hành vi rút lui khi HP dưới 1 ngưỡng nhất định 1

- Quyết định rút lui hay không dựa vào số máu hiện tại (Từ 0 -> 1, hiểu là 0% -> 100% HP)
  - ❗ Hành vi này được xét là quan trọng nhất, sẽ override các hành vi khác của bot.