# Graph Report - .  (2026-05-04)

## Corpus Check
- Corpus is ~11,412 words - fits in a single context window. You may not need a graph.

## Summary
- 232 nodes · 344 edges · 20 communities detected
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 31 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Menu Systems|Menu Systems]]
- [[_COMMUNITY_Virtual Keyboard|Virtual Keyboard]]
- [[_COMMUNITY_Radial Menu Controller|Radial Menu Controller]]
- [[_COMMUNITY_Mapper UI (Textual)|Mapper UI (Textual)]]
- [[_COMMUNITY_Core Engine|Core Engine]]
- [[_COMMUNITY_Keyboard Overlay UI|Keyboard Overlay UI]]
- [[_COMMUNITY_Sequence Engine (Cheat Codes)|Sequence Engine (Cheat Codes)]]
- [[_COMMUNITY_App Bootstrap|App Bootstrap]]
- [[_COMMUNITY_Virtual Input Layer|Virtual Input Layer]]
- [[_COMMUNITY_System Architecture Concepts|System Architecture Concepts]]
- [[_COMMUNITY_Macro Keyboard|Macro Keyboard]]
- [[_COMMUNITY_Button Configuration Menu|Button Configuration Menu]]
- [[_COMMUNITY_Macro Library Menu|Macro Library Menu]]
- [[_COMMUNITY_Main Menu Router|Main Menu Router]]
- [[_COMMUNITY_Profile Switcher|Profile Switcher]]
- [[_COMMUNITY_Profile Manager Menu|Profile Manager Menu]]
- [[_COMMUNITY_Exit Handler|Exit Handler]]
- [[_COMMUNITY_Action Shield|Action Shield]]
- [[_COMMUNITY_System Controls|System Controls]]
- [[_COMMUNITY_Config & Macro Systems|Config & Macro Systems]]

## God Nodes (most connected - your core abstractions)
1. `KeyboardOverlay` - 19 edges
2. `MapperApp` - 19 edges
3. `JoyConEngine` - 16 edges
4. `KeyboardController` - 13 edges
5. `get_config_path()` - 11 edges
6. `SequenceEngine` - 11 edges
7. `RadialMenuController` - 11 edges
8. `JoyConApp` - 9 edges
9. `VirtualInput` - 9 edges
10. `RadialMenuOverlay` - 9 edges

## Surprising Connections (you probably didn't know these)
- `Macro Recording & Playback` --semantically_similar_to--> `Config-Driven Button Mapping`  [INFERRED] [semantically similar]
  actions/macro_keyboard.py → config/mapping.json
- `e` --uses--> `KeyboardOverlay`  [INFERRED]
  actions/keyboard.py → ui/keyboard_ui.py
- `Virtual Keyboard Character Input` --semantically_similar_to--> `UInput Virtual Device Bridge`  [INFERRED] [semantically similar]
  actions/keyboard.py → engine.py
- `Cross-Platform Input Abstraction` --semantically_similar_to--> `UInput Virtual Device Bridge`  [INFERRED] [semantically similar]
  virtual_input.py → engine.py
- `JoyConApp` --uses--> `JoyConEngine`  [INFERRED]
  main.py → engine.py

## Hyperedges (group relationships)
- **Main Tick Loop: Shield → Priority Sort → Run → Break** — action_shield, action_priority_system, event_loop_architecture, virtual_keyboard_input [EXTRACTED 1.00]
- **Keyboard Input Flow: Open → Navigate → Select → Type** — virtual_keyboard_input, uinput_bridge, keyboard_bug_fix, radial_menu_system [INFERRED 0.80]

## Communities (23 total, 6 thin omitted)

### Community 0 - "Menu Systems"
Cohesion: 0.1
Nodes (29): get_recipe_items(), reset(), run(), run(), format_button_name(), get_all_available_actions(), get_config_path(), get_emoji() (+21 more)

### Community 1 - "Virtual Keyboard"
Cohesion: 0.14
Nodes (8): _analog_to_cell(), e, KeyboardController, _type_char(), load_json(), โหลดข้อมูลจากไฟล์ JSON เท่านั้น, create_if_not_exists(), initialize_configs()

### Community 2 - "Radial Menu Controller"
Cohesion: 0.15
Nodes (6): get_emoji(), RadialMenuController, RadialState, run(), QMainWindow, RadialMenuOverlay

### Community 4 - "Core Engine"
Cohesion: 0.21
Nodes (3): JoyConEngine, load_mapping(), ✨ โหลด Mapping ใหม่จากไฟล์และ Update แรมทันที

### Community 6 - "Sequence Engine (Cheat Codes)"
Cohesion: 0.24
Nodes (4): จัดการแกะก้ามปู [[...]] และแปลงเป็น String เพื่อเปรียบเทียบสูตร, run(), SequenceEngine, SequenceState

### Community 7 - "App Bootstrap"
Cohesion: 0.26
Nodes (5): JoyConApp, main(), คืนค่าทรัพยากรทั้งหมดก่อนปิดแอป, เริ่มการทำงานของแอปพลิเคชัน พร้อมแสดง Boot Logs, รันรอบการทำงานของ Engine และเช็คสัญญาณพิเศษ

### Community 8 - "Virtual Input Layer"
Cohesion: 0.17
Nodes (4): สำหรับพิมพ์ตัวอักษรปกติ, Hybrid Abstraction Layer สำหรับเมาส์และคีย์บอร์ด     Linux -> evdev (UInput), สำหรับปุ่มพิเศษ เช่น backspace, enter, space, VirtualInput

### Community 9 - "System Architecture Concepts"
Cohesion: 0.24
Nodes (11): Action Priority & Blocking System, Action Shield (Lock All Non-System Actions), Cheat Code / Sequence Input System, Cross-Platform Input Abstraction, Event Loop Architecture, JoyConMe System, Keyboard UInput Bug (type_char/tap_special), Plug & Play Menu System (+3 more)

### Community 10 - "Macro Keyboard"
Cohesion: 0.48
Nodes (6): execute_step(), is_input_active(), load_macro_library(), ฟังก์ชันเช็คสถานะปุ่ม/แกน/D-Pad แบบรองรับการกด Combo ทุกรูปแบบ, run(), _trigger_macro()

### Community 11 - "Button Configuration Menu"
Cohesion: 0.47
Nodes (3): get_edit_items(), reset(), run()

### Community 12 - "Macro Library Menu"
Cohesion: 0.53
Nodes (5): get_keys_menu(), get_sequence_preview(), ✨ ฟังก์ชันช่วยสร้างรายการคีย์แบบแบ่งหน้า, reset(), run()

### Community 13 - "Main Menu Router"
Cohesion: 0.33
Nodes (4): get_menu_module(), ฟังก์ชันสำหรับสแกนหาไฟล์เมนูใหม่ๆ แบบอัตโนมัติ (Plug & Play), ส่งคืน Module ของเมนูตาม target ที่ร้องขอ, reload_menus()

### Community 14 - "Profile Switcher"
Cohesion: 0.53
Nodes (5): hide_osd(), is_triggered(), ฟังก์ชันแสดงแจ้งเตือนแบบ Compact (เล็กและไม่ดึงสายตา), run(), show_osd()

### Community 19 - "Config & Macro Systems"
Cohesion: 0.67
Nodes (3): Config-Driven Button Mapping, Macro Recording & Playback, Profile System

## Ambiguous Edges - Review These
- `Virtual Keyboard Character Input` → `Cross-Platform Input Abstraction`  [AMBIGUOUS]
  actions/keyboard.py · relation: references

## Knowledge Gaps
- **28 isolated node(s):** `เริ่มการทำงานของแอปพลิเคชัน พร้อมแสดง Boot Logs`, `รันรอบการทำงานของ Engine และเช็คสัญญาณพิเศษ`, `คืนค่าทรัพยากรทั้งหมดก่อนปิดแอป`, `Hybrid Abstraction Layer สำหรับเมาส์และคีย์บอร์ด     Linux -> evdev (UInput)`, `สำหรับปุ่มพิเศษ เช่น backspace, enter, space` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Virtual Keyboard Character Input` and `Cross-Platform Input Abstraction`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `KeyboardOverlay` connect `Keyboard Overlay UI` to `Virtual Keyboard`, `Radial Menu Controller`?**
  _High betweenness centrality (0.231) - this node is a cross-community bridge._
- **Why does `KeyboardController` connect `Virtual Keyboard` to `Virtual Input Layer`, `Keyboard Overlay UI`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `KeyboardOverlay` (e.g. with `e` and `KeyboardController`) actually correct?**
  _`KeyboardOverlay` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `JoyConEngine` (e.g. with `JoyConApp` and `.__init__()`) actually correct?**
  _`JoyConEngine` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `KeyboardController` (e.g. with `KeyboardOverlay` and `.__init__()`) actually correct?**
  _`KeyboardController` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `เริ่มการทำงานของแอปพลิเคชัน พร้อมแสดง Boot Logs`, `รันรอบการทำงานของ Engine และเช็คสัญญาณพิเศษ`, `คืนค่าทรัพยากรทั้งหมดก่อนปิดแอป` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._