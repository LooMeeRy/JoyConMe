import importlib
import json
import math
import os
import time

import pygame

try:
    from ui.overlay_ui import RadialMenuOverlay
except ImportError:
    RadialMenuOverlay = None

from menus.utils import format_button_name, get_emoji

ACTION_INFO = {
    "id": "radial_setup",
    "name": "ระบบตั้งค่าเมนูวงกลม",
    "actions": [{"key": "open_menu", "type": "button", "desc": "เปิด/ปิด เมนูวงกลม"}],
}

# --- State Variables ---
overlay_window = None
is_active = False
last_btn_state = False
current_menu_id = "main"
wait_for_neutral = False
listen_mode = None
last_detected_inputs = []
reference_inputs = []
last_input_time = 0
has_started_sequence = False
GRACE_PERIOD = 0.5
TIMEOUT_SECONDS = 5.0

try:
    from menus import button_menu, cheat_menu, main_menu, mouse_menu
except ImportError:
    main_menu = None
    mouse_menu = None
    button_menu = None
    cheat_menu = None


def is_combo_pressed(joystick, mapping_value):
    if mapping_value is None:
        return False
    if isinstance(mapping_value, int):
        return joystick.get_button(mapping_value)
    if isinstance(mapping_value, list):
        return all(joystick.get_button(btn) for btn in mapping_value)
    if isinstance(mapping_value, dict):
        if "hat" in mapping_value:
            h_id = mapping_value["hat"]
            target_dir = mapping_value["dir"]
            try:
                current_val = joystick.get_hat(h_id)
            except:
                return False
            if target_dir[0] != 0 and current_val[0] == target_dir[0]:
                return True
            if target_dir[1] != 0 and current_val[1] == target_dir[1]:
                return True
    return False


def get_current_physical_inputs(joystick, include_analog=False):
    inputs = []
    # Buttons
    for i in range(joystick.get_numbuttons()):
        if joystick.get_button(i):
            inputs.append(i)
    # Hats
    for h in range(joystick.get_numhats()):
        val = joystick.get_hat(h)
        if val != (0, 0):
            inputs.append({"hat": h, "dir": list(val)})

    # ✨ Analog (ตรวจจับเมื่อเปิดใช้งาน)
    if include_analog:
        for a in range(joystick.get_numaxes()):
            val = joystick.get_axis(a)
            if abs(val) > 0.85:  # กำหนด Threshold ว่าต้องกดแรงพอสมควร
                inputs.append(a)
    return inputs


# --- Main Run Function ---
def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    global \
        overlay_window, \
        is_active, \
        last_btn_state, \
        current_menu_id, \
        wait_for_neutral, \
        listen_mode
    global last_detected_inputs, reference_inputs, last_input_time, has_started_sequence

    # 1. Trigger Mode
    if trigger_key == "open_menu":
        print("[Radial] Trigger: Open Menu")
        try:
            is_active = True
            current_menu_id = "main"
            wait_for_neutral = True
            if RadialMenuOverlay:
                items = main_menu.MENU_ITEMS if main_menu else ["Error"]
                overlay_window = RadialMenuOverlay(menu_items=items)
                overlay_window.show()
        except Exception as ex:
            print(f"Error forcing menu: {ex}")
        return

    # 2. Normal Mode

    # --- ตรวจจับการเปิดเมนู ---
    trigger_config = mod_mapping.get("buttons", {}).get("open_menu")
    btn_pressed = is_combo_pressed(joystick, trigger_config)

    is_just_pressed = btn_pressed and not last_btn_state
    last_btn_state = btn_pressed

    if is_just_pressed:
        is_active = not is_active
        if is_active and RadialMenuOverlay:
            current_menu_id = "main"
            listen_mode = None
            wait_for_neutral = True
            last_detected_inputs = []
            items = main_menu.MENU_ITEMS if main_menu else ["Error"]
            overlay_window = RadialMenuOverlay(menu_items=items)
            overlay_window.show()
        elif overlay_window:
            overlay_window.close()
            overlay_window = None
            return "RELOAD"

    if is_active and overlay_window:
        # --- Logic โหมด Input/Sequence ---
        if listen_mode is not None:
            # ✨ แก้ไขตรงนี้: เปิดการตรวจจับ Analog เฉพาะโหมด Input (ตั้งค่าปุ่ม)
            # โหมด Sequence (สูตร) ไม่ควรใช้ Analog เพราะมักจะใช้ D-Pad/Button
            detect_analog = listen_mode == "input"
            current_inputs = get_current_physical_inputs(
                joystick, include_analog=detect_analog
            )

            if wait_for_neutral:
                if 0 in current_inputs:
                    overlay_window.center_msg = "รอปล่อยปุ่ม A..."
                    overlay_window.timeout_progress = 0.0
                else:
                    wait_for_neutral = False
                    reference_inputs = current_inputs
                    last_detected_inputs = []
                    last_input_time = time.time()
                    has_started_sequence = False
                    overlay_window.center_msg = "พร้อมรับสัญญาณ\n(กดปุ่มใหม่ได้เลย)"

            else:
                if listen_mode == "sequence":
                    if 0 in current_inputs and 2 in current_inputs:
                        if cheat_menu:
                            cheat_menu.toggle_recording({"overlay": overlay_window})
                            reference_inputs = current_inputs
                            last_detected_inputs = []
                            wait_for_neutral = True
                            overlay_window.timeout_progress = 0.0
                            overlay_window.update()
                            return True

                is_recording = True
                if listen_mode == "sequence" and cheat_menu:
                    is_recording = cheat_menu.is_recording

                if is_recording:
                    new_inputs = [
                        x for x in current_inputs if x not in reference_inputs
                    ]

                    if new_inputs:
                        last_input_time = time.time()
                        overlay_window.timeout_progress = 0.0
                        has_started_sequence = True

                        parts = []
                        for inp in new_inputs:
                            if isinstance(inp, int):
                                parts.append(f"{inp}️⃣")
                            elif isinstance(inp, dict):
                                parts.append(get_emoji(inp))
                        overlay_window.center_msg = f"กดอยู่:\n{' + '.join(parts)}"
                        last_detected_inputs = new_inputs
                    else:
                        if last_detected_inputs:
                            final_val = (
                                last_detected_inputs[0]
                                if len(last_detected_inputs) == 1
                                else last_detected_inputs
                            )

                            if listen_mode == "input":
                                if button_menu:
                                    button_menu.set_detected_input(final_val)
                                    res = button_menu.proceed_after_input(
                                        {"overlay": overlay_window}
                                    )
                                    if res == "UPDATE_UI":
                                        listen_mode = None
                                        last_detected_inputs = []
                                        overlay_window.update()
                                        return True

                            elif listen_mode == "sequence":
                                if cheat_menu and cheat_menu.is_recording:
                                    cheat_menu.add_sequence_input(
                                        final_val, {"overlay": overlay_window}
                                    )

                            last_detected_inputs = []

                        else:
                            elapsed = time.time() - last_input_time
                            if has_started_sequence and elapsed > GRACE_PERIOD:
                                progress = (elapsed - GRACE_PERIOD) / TIMEOUT_SECONDS
                                overlay_window.timeout_progress = progress
                                secs_left = int(
                                    TIMEOUT_SECONDS - (elapsed - GRACE_PERIOD)
                                )
                                overlay_window.center_msg = (
                                    f"หยุดบันทึกใน\n{secs_left} วินาที..."
                                )
                                if progress >= 1.0:
                                    cheat_menu.is_recording = False
                                    has_started_sequence = False
                                    overlay_window.timeout_progress = 0.0
                                    overlay_window.center_msg = (
                                        "หยุดบันทึกแล้ว\nเลือกเมนูด้านล่าง"
                                    )
                                    wait_for_neutral = True

                else:
                    overlay_window.timeout_progress = 0.0
                    axis_x, axis_y = joystick.get_axis(0), joystick.get_axis(1)
                    if math.sqrt(axis_x**2 + axis_y**2) > 0.4:
                        angle = (math.degrees(math.atan2(axis_y, axis_x)) + 90) % 360
                        overlay_window.update_selection(angle)

                    if 0 in current_inputs and 0 not in reference_inputs:
                        selected_item = overlay_window.menu_items[
                            overlay_window.current_selection
                        ]
                        if cheat_menu:
                            result = cheat_menu.run(
                                selected_item,
                                {
                                    "overlay": overlay_window,
                                    "joystick": joystick,
                                    "app_config": app_config,
                                },
                            )
                            if result:
                                if result == "STOP_SEQUENCE_LISTEN":
                                    listen_mode = None
                                    wait_for_neutral = True
                                    reference_inputs = current_inputs
                                elif result == "UPDATE_UI":
                                    wait_for_neutral = True
                                    reference_inputs = current_inputs
                            overlay_window.update()
                            pygame.time.wait(250)

            overlay_window.update()
            return True

        # --- Logic เมนูปกติ ---
        if wait_for_neutral:
            all_released = True
            if joystick.get_button(0):
                all_released = False
            if all_released:
                wait_for_neutral = False
            else:
                return True

        axis_x, axis_y = joystick.get_axis(0), joystick.get_axis(1)
        if math.sqrt(axis_x**2 + axis_y**2) > 0.4:
            angle = (math.degrees(math.atan2(axis_y, axis_x)) + 90) % 360
            overlay_window.update_selection(angle)

        if joystick.get_button(0):
            selected_item = overlay_window.menu_items[overlay_window.current_selection]
            result = None
            context = {
                "overlay": overlay_window,
                "joystick": joystick,
                "app_config": app_config,
            }

            if current_menu_id == "main" and main_menu:
                result = main_menu.run(selected_item, context)
            elif current_menu_id.startswith("mouse") and mouse_menu:
                result = mouse_menu.run(selected_item, context)
            elif current_menu_id.startswith("button") and button_menu:
                result = button_menu.run(selected_item, context)
            elif current_menu_id.startswith("cheat") and cheat_menu:
                result = cheat_menu.run(selected_item, context)

            if result:
                if result == "CLOSE_MENU":
                    is_active = False
                    overlay_window.close()
                    overlay_window = None
                    return "RELOAD"
                elif isinstance(result, str) and result.startswith("SWITCH:"):
                    target = result.split(":")[1]
                    current_menu_id = target
                    wait_for_neutral = True
                    if target == "main" and main_menu:
                        overlay_window.menu_items = main_menu.MENU_ITEMS
                    elif target == "mouse_main" and mouse_menu:
                        overlay_window.menu_items = mouse_menu.MENU_ITEMS
                    elif target == "button_main" and button_menu:
                        button_menu.reset()
                        overlay_window.menu_items = button_menu.MENU_MAIN
                    elif target == "cheat_main" and cheat_menu:
                        cheat_menu.reset()
                        overlay_window.menu_items = cheat_menu.MENU_MAIN
                    overlay_window.center_msg = ""

                elif result == "LISTEN_INPUT":
                    listen_mode = "input"
                    wait_for_neutral = True
                    # ✨ แก้ไข: ต้องเปิด include_analog ตอนเก็บ Reference ด้วย
                    reference_inputs = get_current_physical_inputs(
                        joystick, include_analog=True
                    )
                    last_detected_inputs = []
                    overlay_window.menu_items = ["(รอสัญญาณ)"]
                    overlay_window.center_msg = "รอปล่อยปุ่ม A..."

                elif result == "START_SEQUENCE_LISTEN":
                    listen_mode = "sequence"
                    wait_for_neutral = True
                    reference_inputs = get_current_physical_inputs(
                        joystick
                    )  # Sequence ไม่ต้องการ Analog
                    last_detected_inputs = []
                    last_input_time = time.time()
                    has_started_sequence = False

                elif result == "STOP_SEQUENCE_LISTEN":
                    listen_mode = None
                    wait_for_neutral = True
                elif result == "UPDATE_UI":
                    wait_for_neutral = True

                if overlay_window:
                    overlay_window.update()
                pygame.time.wait(250)

        return True
    return False
