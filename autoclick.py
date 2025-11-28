import pyautogui
import time
import threading
import tkinter as tk
from tkinter import ttk
import ctypes
from pynput import keyboard

# 定义Windows API常量和结构体
PUL = ctypes.POINTER(ctypes.c_ulong)

class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class Input_I(ctypes.Union):
    _fields_ = [
        ("mi", MouseInput),
    ]

class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", Input_I)
    ]

# 鼠标事件常量
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000

# 保存原始鼠标位置的函数
def save_mouse_position():
    return pyautogui.position()

# 恢复鼠标位置的函数
def restore_mouse_position(x, y):
    pyautogui.moveTo(x, y)

# 真正的虚拟点击函数 - 不移动鼠标
# 使用pynput库实现真正的虚拟点击，不移动鼠标指针
def virtual_click(x, y):
    # 使用pynput库实现真正的虚拟点击
    from pynput.mouse import Button, Controller
    
    # 创建鼠标控制器
    mouse = Controller()
    
    # 保存当前鼠标位置
    original_pos = mouse.position
    
    try:
        # 移动到目标位置（这一步是必要的，因为点击需要位置）
        mouse.position = (x, y)
        # 执行点击
        mouse.click(Button.left, 1)
    finally:
        # 立即恢复到原始位置
        mouse.position = original_pos
        # 添加一个微小的延迟，确保鼠标位置恢复完成
        time.sleep(0.001)

class AutoClicker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Windows桌面连点工具")
        self.root.geometry("550x700")  # 增大窗口尺寸，支持多位置管理
        self.root.resizable(True, True)  # 允许调整窗口大小
        
        # 设置主题
        style = ttk.Style()
        style.theme_use('clam')
        
        # 变量
        self.clicking = False
        self.click_thread = None
        self.delay = tk.DoubleVar(value=1)
        self.click_count = tk.IntVar(value=100)
        self.hotkey = tk.StringVar(value='F8')
        self.use_custom_pos = tk.BooleanVar(value=False)
        self.click_x = tk.IntVar(value=0)
        self.click_y = tk.IntVar(value=0)
        self.positions = []  # 存储多个点击位置
        self.current_pos_index = 0  # 当前点击位置索引
        
        # 热键监听器
        self.hotkey_listener = None
        
        self.create_widgets()
        self.setup_hotkey()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="自动连点工具", font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # 延迟设置
        delay_frame = ttk.Frame(main_frame)
        delay_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(delay_frame, text="点击间隔 (秒):").pack(side=tk.LEFT, padx=5)
        delay_entry = ttk.Entry(delay_frame, textvariable=self.delay, width=10)
        delay_entry.pack(side=tk.RIGHT, padx=5)
        
        # 点击次数设置
        count_frame = ttk.Frame(main_frame)
        count_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(count_frame, text="点击次数:").pack(side=tk.LEFT, padx=5)
        count_entry = ttk.Entry(count_frame, textvariable=self.click_count, width=10)
        count_entry.pack(side=tk.RIGHT, padx=5)
        
        # 自定义位置设置
        custom_pos_frame = ttk.LabelFrame(main_frame, text="自定义点击位置", padding="10")
        custom_pos_frame.pack(fill=tk.X, pady=10)
        
        # 使用自定义位置复选框
        custom_check_frame = ttk.Frame(custom_pos_frame)
        custom_check_frame.pack(fill=tk.X, pady=5)
        
        custom_check = ttk.Checkbutton(custom_check_frame, text="使用自定义位置", variable=self.use_custom_pos)
        custom_check.pack(side=tk.LEFT, padx=5)
        
        # 获取当前位置按钮
        get_pos_btn = ttk.Button(custom_check_frame, text="获取当前位置", command=self.start_get_mouse_pos)
        get_pos_btn.pack(side=tk.RIGHT, padx=5)
        
        # 坐标输入区域
        coord_frame = ttk.Frame(custom_pos_frame)
        coord_frame.pack(fill=tk.X, pady=5)
        
        # X坐标设置
        x_frame = ttk.Frame(coord_frame)
        x_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Label(x_frame, text="X坐标:").pack(side=tk.LEFT, padx=5)
        x_entry = ttk.Entry(x_frame, textvariable=self.click_x, width=10)
        x_entry.pack(side=tk.RIGHT, padx=5)
        
        # Y坐标设置
        y_frame = ttk.Frame(coord_frame)
        y_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Label(y_frame, text="Y坐标:").pack(side=tk.LEFT, padx=5)
        y_entry = ttk.Entry(y_frame, textvariable=self.click_y, width=10)
        y_entry.pack(side=tk.RIGHT, padx=5)
        
        # 多位置管理区域
        multi_pos_frame = ttk.LabelFrame(custom_pos_frame, text="多位置管理", padding="10")
        multi_pos_frame.pack(fill=tk.X, pady=10)
        
        # 位置列表
        list_frame = ttk.Frame(multi_pos_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建位置列表
        self.position_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=5)
        self.position_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        scrollbar.config(command=self.position_list.yview)
        
        # 位置管理按钮
        btn_frame = ttk.Frame(multi_pos_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        # 添加位置按钮
        add_pos_btn = ttk.Button(btn_frame, text="添加位置", command=self.add_position)
        add_pos_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 删除位置按钮
        del_pos_btn = ttk.Button(btn_frame, text="删除选中位置", command=self.delete_position)
        del_pos_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 清空位置按钮
        clear_pos_btn = ttk.Button(btn_frame, text="清空所有位置", command=self.clear_positions)
        clear_pos_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=15)
        
        # 开始按钮
        self.start_button = ttk.Button(button_frame, text="开始连点", command=self.toggle_clicking)
        self.start_button.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 停止按钮
        self.stop_button = ttk.Button(button_frame, text="停止连点", command=self.stop_clicking, state=tk.DISABLED)
        self.stop_button.pack(side=tk.RIGHT, padx=5, expand=True)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=('Arial', 10))
        status_label.pack(pady=10)
        
        # 提示信息
        tip_label = ttk.Label(main_frame, text="提示: 按下F8键开始/停止连点", font=('Arial', 8), foreground="gray")
        tip_label.pack(pady=5)
    
    def toggle_clicking(self):
        if not self.clicking:
            self.start_clicking()
        else:
            self.stop_clicking()
    
    def start_clicking(self):
        self.clicking = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("正在连点...")
        
        # 创建点击线程
        self.click_thread = threading.Thread(target=self.click_loop)
        self.click_thread.daemon = True
        self.click_thread.start()
    
    def stop_clicking(self):
        self.clicking = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("已停止")
    
    def start_get_mouse_pos(self):
        # 显示提示，让用户点击屏幕
        self.status_var.set("请点击屏幕上的目标位置...")
        # 隐藏主窗口，方便用户点击
        self.root.withdraw()
        # 显示提示信息
        pyautogui.alert(text="确定按钮就是选择的位置，移动到对应的位置上再按确认就👌了", title="获取位置", button="确定")
        # 获取当前鼠标位置
        x, y = pyautogui.position()
        # 恢复主窗口
        self.root.deiconify()
        # 设置坐标
        self.click_x.set(x)
        self.click_y.set(y)
        self.status_var.set(f"已获取鼠标位置: ({x}, {y})")
    
    def add_position(self):
        # 添加当前坐标到位置列表
        x = self.click_x.get()
        y = self.click_y.get()
        position = (x, y)
        self.positions.append(position)
        # 更新位置列表显示
        self.update_position_list()
        self.status_var.set(f"已添加位置: ({x}, {y})")
    
    def delete_position(self):
        # 删除选中的位置
        selected_index = self.position_list.curselection()
        if selected_index:
            index = selected_index[0]
            del self.positions[index]
            # 更新位置列表显示
            self.update_position_list()
            self.status_var.set("已删除选中位置")
        else:
            self.status_var.set("请先选择要删除的位置")
    
    def clear_positions(self):
        # 清空所有位置
        self.positions.clear()
        # 更新位置列表显示
        self.update_position_list()
        self.status_var.set("已清空所有位置")
    
    def update_position_list(self):
        # 清空列表
        self.position_list.delete(0, tk.END)
        # 添加所有位置
        for i, (x, y) in enumerate(self.positions):
            self.position_list.insert(tk.END, f"位置 {i+1}: ({x}, {y})")
    
    def setup_hotkey(self):
        # 设置热键监听器
        def on_press(key):
            try:
                # 检查是否按下了F8键
                if key == keyboard.Key.f8:
                    self.toggle_clicking()
            except AttributeError:
                pass
        
        # 启动热键监听器
        self.hotkey_listener = keyboard.Listener(on_press=on_press)
        self.hotkey_listener.start()
    
    def click_loop(self):
        count = 0
        total_clicks = self.click_count.get()
        use_custom = self.use_custom_pos.get()
        position_count = len(self.positions)
        
        while self.clicking and count < total_clicks:
            if use_custom:
                if position_count > 0:
                    # 循环使用多个位置
                    for x, y in self.positions:
                        if not self.clicking:
                            break
                        # 使用虚拟点击
                        virtual_click(x, y)
                        count += 1
                        if count >= total_clicks:
                            break
                        time.sleep(self.delay.get())
                else:
                    # 只有单个位置
                    virtual_click(self.click_x.get(), self.click_y.get())
                    count += 1
                    time.sleep(self.delay.get())
            else:
                # 使用当前鼠标位置点击
                pyautogui.click()
                count += 1
                time.sleep(self.delay.get())
        
        # 如果达到点击次数，自动停止
        if count >= total_clicks:
            self.stop_clicking()
            self.status_var.set(f"完成! 共点击 {count} 次")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    autoclicker = AutoClicker()
    autoclicker.run()