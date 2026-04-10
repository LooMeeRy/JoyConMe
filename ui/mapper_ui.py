import importlib
import json
import os

import pygame
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Label, Select

# ตั้งค่าสภาพแวดล้อม
os.environ["SDL_VIDEODRIVER"] = "dummy"
MAPPING_FILE = os.path.join(os.path.dirname(__file__), "config", "mapping.json")


class MapperApp(App):
    CSS = """
    #main_layout { padding: 1; }
    DataTable { height: 10; border: tall $accent; margin-bottom: 1; }
    .status-area { background: $boost; padding: 1; border: double white; margin-top: 1; min-height: 12; align: center middle; }
    .control-group { height: 3; align: center middle; margin-bottom: 1; }
    Button { margin-right: 1; }
    #msg { color: yellow; text-align: center; width: 100%; text-style: bold; margin-bottom: 1; }
    .hidden { display: none; }
    .sub-menu { margin-top: 1; align: center middle; }
    #save_btn { margin-top: 1; width: 100%; }
    """

    BINDINGS = [("q", "quit", "ออกโปรแกรม")]

    def __init__(self):
        super().__init__()
        self.mapping_data = self.load_mapping()
        self.actions_list = self.scan_actions()
        self.selected_row_key = None  # เก็บ mod|cat|key
        self.captured_input = None
        self.timer = None

        pygame.init()
        pygame.joystick.init()
        self.joystick = (
            pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
        )
        if self.joystick:
            self.joystick.init()

    def load_mapping(self):
        if os.path.exists(MAPPING_FILE):
            try:
                with open(MAPPING_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def scan_actions(self):
        found = []
        path = os.path.join(os.path.dirname(__file__), "actions")
        if not os.path.exists(path):
            return found

        for f in os.listdir(path):
            if f.endswith(".py") and f != "__init__.py":
                try:
                    # พยายามโหลดโมดูล
                    m = importlib.import_module(f"actions.{f[:-3]}")
                    if hasattr(m, "ACTION_INFO"):
                        found.append(m.ACTION_INFO)
                except Exception as e:
                    # ถ้าโหลดไม่ได้ ให้พิมพ์บอกใน Terminal ว่าติดอะไร
                    print(f"❌ ไม่สามารถโหลด Action '{f}' ได้เพราะ: {e}")
        return found

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main_layout"):
            yield Label("🎮 รายการ Mapping (เลือกแถวในตารางเพื่อจัดการ)")
            yield DataTable(cursor_type="row")

            with Horizontal(classes="control-group"):
                yield Button("➕ เพิ่ม (Add)", id="add_btn", variant="primary")
                yield Button("📝 แก้ไข (Edit)", id="edit_btn", variant="warning")
                yield Button("❌ ลบ (Del)", id="del_btn", variant="error")

            with Vertical(id="setup_area", classes="status-area"):
                yield Label("สถานะ: พร้อมใช้งาน", id="msg")

                # โซนทางเลือกการแก้ไข (จะโชว์เมื่อกด Edit)
                with Horizontal(id="edit_choices", classes="sub-menu hidden"):
                    yield Button(
                        "🔄 เปลี่ยนปุ่มกด (Remap)", id="choice_remap", variant="default"
                    )
                    yield Button(
                        "⚙️ เปลี่ยนหน้าที่ (Change Action)",
                        id="choice_action",
                        variant="default",
                    )

                yield Select(
                    [], prompt="-- เลือกหน้าที่ใหม่ --", id="picker", classes="hidden"
                )
                yield Button(
                    "💾 บันทึกการเปลี่ยนแปลง",
                    id="save_btn",
                    variant="success",
                    classes="hidden",
                )
        yield Footer()

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("ประเภท", "ID จอย", "หน้าที่ (Action)", "โมดูล")
        self.refresh_table()

    def refresh_table(self):
        table = self.query_one(DataTable)
        table.clear()
        for mod_id, cats in self.mapping_data.items():
            for cat, keys in cats.items():
                for k, v in keys.items():
                    label = "แกน" if cat == "analogs" else "ปุ่ม"
                    table.add_row(label, str(v), k, mod_id, key=f"{mod_id}|{cat}|{k}")

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        self.selected_row_key = event.row_key.value
        self.query_one("#msg").update(f"เลือก: {self.selected_row_key.split('|')[2]}")

    def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id

        if btn_id == "add_btn":
            self.reset_ui_states()
            self.start_listen("add")

        elif btn_id == "edit_btn":
            if not self.selected_row_key:
                self.query_one("#msg").update("⚠️ กรุณาเลือกรายการในตารางก่อน!")
                return
            self.show_edit_menu()

        elif btn_id == "choice_remap":
            self.start_listen("edit_remap")

        elif btn_id == "choice_action":
            m, c, k = self.selected_row_key.split("|")
            self.show_action_picker(c[:-1])  # ตัด 's' ออกจาก 'analogs' หรือ 'buttons'

        elif btn_id == "save_btn":
            self.save_logic()

        elif btn_id == "del_btn":
            self.delete_logic()

    def show_edit_menu(self):
        self.reset_ui_states()
        self.query_one("#msg").update("❓ คุณต้องการแก้ไขส่วนไหน?")
        self.query_one("#edit_choices").remove_class("hidden")

    def start_listen(self, mode):
        self.mode = mode
        self.query_one("#edit_choices").add_class("hidden")
        self.query_one("#msg").update("⏳ [ฟังค่า] กรุณากดปุ่มหรือโยกจอย...")
        pygame.event.get()
        if self.timer:
            self.timer.stop()
        self.timer = self.set_interval(0.02, self.poll_joy)

    def poll_joy(self):
        pygame.event.pump()
        events = pygame.event.get()

        # เช็คปุ่มก่อนเสมอ
        for event in events:
            if event.type == pygame.JOYBUTTONDOWN:
                self.input_captured("button", event.button)
                if self.timer:
                    self.timer.stop()
                return

        # เช็ค Analog ทีหลังและเพิ่ม Threshold เพื่อเลี่ยง Drift
        for event in events:
            if event.type == pygame.JOYAXISMOTION:
                if abs(event.value) > 0.85:  # เพิ่มความต้านทาน Drift
                    self.input_captured("analog", event.axis)
                    if self.timer:
                        self.timer.stop()
                    return

        # 3. เช็ค Analog (เอาไว้หลังสุดและเพิ่ม Threshold เพื่อเลี่ยง Drift)
        for event in events:
            if event.type == pygame.JOYAXISMOTION:
                if abs(event.value) > 0.8:  # ปรับเพิ่มจาก 0.5 เป็น 0.8
                    self.input_captured("analog", event.axis)
                    if self.timer:
                        self.timer.stop()
                    return

    def input_captured(self, i_type, i_id):
        if self.timer:
            self.timer.stop()
        self.captured_input = {"type": i_type, "id": i_id}
        in_name = "ปุ่ม" if i_type == "button" else "แกน"
        self.query_one("#msg").update(f"✅ จับได้: {in_name} {i_id}")

        if self.mode == "add":
            self.show_action_picker(i_type)
        else:
            # กรณี Remap ปุ่มใหม่ ในหน้าที่เดิม
            self.query_one("#save_btn").remove_class("hidden")

    def show_action_picker(self, i_type):
        picker = self.query_one("#picker")
        opts = []
        for m in self.actions_list:
            for a in m["actions"]:
                if a["type"] == i_type:
                    opts.append(
                        (
                            f"[{m['name']}] {a['desc']}",
                            f"{m['id']}|{i_type}s|{a['key']}",
                        )
                    )

        if opts:
            picker.set_options(opts)
            picker.remove_class("hidden")
            self.query_one("#save_btn").remove_class("hidden")
            self.query_one("#edit_choices").add_class("hidden")

    def save_logic(self):
        # 1. กรณีเพิ่มใหม่ หรือ เปลี่ยนหน้าที่ (ใช้ค่าจาก Dropdown)
        picker = self.query_one("#picker")

        if not picker.has_class("hidden"):
            if picker.value == Select.BLANK:
                return
            new_mod, new_cat, new_key = str(picker.value).split("|")

            # --- ส่วนที่แก้ไขให้ปลอดภัยขึ้น ---
            # ถ้ายังไม่มีชื่อโมดูลนี้ ให้สร้างรอไว้
            if new_mod not in self.mapping_data:
                self.mapping_data[new_mod] = {}

            # ถ้ายังไม่มีหมวดหมู่ (analogs หรือ buttons) ในโมดูลนี้ ให้สร้างรอไว้
            if new_cat not in self.mapping_data[new_mod]:
                self.mapping_data[new_mod][new_cat] = {}

            # จัดการลบค่าเก่าถ้าเป็นการ Edit
            if self.selected_row_key:
                old_m, old_c, old_k = self.selected_row_key.split("|")
                val = (
                    self.mapping_data[old_m][old_c][old_k]
                    if not self.captured_input
                    else self.captured_input["id"]
                )
                # ลบค่าเก่าทิ้งก่อนบันทึกใหม่
                if old_m in self.mapping_data and old_c in self.mapping_data[old_m]:
                    if old_k in self.mapping_data[old_m][old_c]:
                        del self.mapping_data[old_m][old_c][old_k]
            else:
                val = self.captured_input["id"]

            # บันทึกค่าลงไป
            self.mapping_data[new_mod][new_cat][new_key] = val

        # 2. กรณี Remap (เปลี่ยนแค่ปุ่ม แต่หน้าที่เดิม)
        elif self.selected_row_key and self.captured_input:
            m, c, k = self.selected_row_key.split("|")
            # ตรวจสอบความปลอดภัยของโครงสร้างก่อนบันทึก
            if m not in self.mapping_data:
                self.mapping_data[m] = {}
            if c not in self.mapping_data[m]:
                self.mapping_data[m][c] = {}

            # เช็คว่าประเภทปุ่มใหม่ตรงกับของเดิมไหม
            if (self.captured_input["type"] == "analog" and c == "analogs") or (
                self.captured_input["type"] == "button" and c == "buttons"
            ):
                self.mapping_data[m][c][k] = self.captured_input["id"]
            else:
                self.query_one("#msg").update("❌ ประเภทปุ่มไม่ตรงกับหน้าที่เดิม!")
                return

        self.finalize("🎉 บันทึกสำเร็จ!")

    def delete_logic(self):
        if not self.selected_row_key:
            return
        m, c, k = self.selected_row_key.split("|")
        del self.mapping_data[m][c][k]
        self.finalize("❌ ลบรายการเรียบร้อย")

    def finalize(self, msg):
        os.makedirs(os.path.dirname(MAPPING_FILE), exist_ok=True)
        with open(MAPPING_FILE, "w") as f:
            json.dump(self.mapping_data, f, indent=4)
        self.refresh_table()
        self.reset_ui_states()
        self.query_one("#msg").update(msg)

    def reset_ui_states(self):
        self.query_one("#edit_choices").add_class("hidden")
        self.query_one("#picker").add_class("hidden")
        self.query_one("#save_btn").add_class("hidden")
        self.captured_input = None
        # ไม่ต้องรีเซ็ต selected_row_key เพื่อให้ Edit ต่อได้ถ้าต้องการ


if __name__ == "__main__":
    app = MapperApp()
    app.run()
