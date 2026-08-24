import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import time
from datetime import datetime, timedelta
import os
import json

class GameReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("游戏活动提醒")
        self.root.geometry("760x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")
        
        # 设置图标（如果有的话）
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 配置文件路径
        self.config_file = "reminder_config.json"
        
        # 创建样式
        self.style = ttk.Style()
        self.style.configure("Title.TLabel", font=("Arial", 16, "bold"), foreground="#2c3e50")
        self.style.configure("Time.TLabel", font=("Arial", 12), foreground="#34495e")
        self.style.configure("Activity.TLabel", font=("Arial", 11), foreground="#2c3e50")
        self.style.configure("ListTitle.TLabelframe", font=("Arial", 12, "bold"))
        # 新增复选框样式
        self.style.configure("Large.TCheckbutton", font=("Arial", 10))
        
        # 活动时间表
        self.activities = {
            "藏经阁":[
                ("10:45", "11:15"),
                ("16:30", "17:00"),
                ("21:30", "22:00"),
                ("23:00", "23:30")
            ],
            "门派BOSS":[
                ("00:00", "丐帮10/少林40/武当70"),
                ("08:00", "丐帮10/少林40/武当70"),
                ("16:00", "丐帮10/少林40/武当70"),
                ("02:30", "峨眉20/星宿50/天山60"),
                ("10:30", "峨眉20/星宿50/天山60"),
                ("18:30", "峨眉20/星宿50/天山60"),
                ("05:00", "明教40/逍遥80/天龙90"),
                ("13:00", "明教40/逍遥80/天龙90"),
                ("21:00", "明教40/逍遥80/天龙90")
            ],
            "珍珑棋局":[
                ("11:30", "14:30"),
                ("20:30", "22:00")
            ],
            "偷袭门派":[
                ("00:00", "00:30"),
                ("04:00", "04:30"),
                ("10:00", "10:30"),
                ("12:00", "12:30"),
                ("16:00", "16:30"),
                ("20:00", "20:30"),
                ("22:00", "22:30")
            ],
            "贼兵入侵":[
                ("02:00", "03:00"),
                ("13:00", "14:00"),
                ("15:00", "16:00"),
                ("17:00", "18:00"),
                ("19:00", "20:00"),
                ("21:00", "22:00")
            ],
            "宝箱争夺":[
                ("03:15", "03:15"),
                ("10:15", "10:15"),
                ("13:15", "13:15"),
                ("18:15", "18:15"),
                ("23:30", "23:30")
            ],
            "千年冰魄":[
                ("00:30", "00:30"),
                ("10:30", "10:30"),
                ("15:30", "15:30"),
                ("19:45", "19:45")
            ],
            "白冥启":[
                ("01:30", "01:30"),
                ("13:30", "13:30"),
                ("18:30", "18:30"),
                ("22:30", "22:30")
            ],
            "玄击金刚":[
                ("02:30", "02:30"),
                ("11:30", "11:30"),
                ("18:00", "18:00"),
                ("23:30", "23:30")
            ],
            "莽牯毒蛤王":[
                ("03:30", "03:30"),
                ("12:30", "12:30"),
                ("19:30", "19:30"),
                ("21:30", "21:30")
            ],
            "野猪暴走":[
                ("14:00", "16:40"),
                ("21:30", "23:59")
            ],
            "珍兽龙龟":[
                ("11:00", "11:00"),
                ("15:45", "15:45"),
                ("19:30", "19:30"),
                ("23:00", "23:00")
            ],
            "天降奇兽":[
                ("13:30", "14:00"),
                ("18:30", "19:00"),
                ("19:00", "19:30"),
                ("21:45", "22:15")
            ],
            "帮派山神":[
                ("19:15", "20:00")
            ],
            "45镜湖小龙":[
                ("00:45", "00:45"),
                ("01:45", "01:45"),
                ("02:45", "02:45"),
                ("10:45", "10:45"),
                ("11:45", "11:45"),
                ("13:45", "13:45"),
                ("14:45", "14:45"),
                ("15:45", "15:45"),
                ("16:45", "16:45"),
                ("17:45", "17:45"),
                ("18:45", "18:45"),
                ("19:45", "19:45"),
                ("20:45", "20:45"),
                ("21:45", "21:45"),
                ("22:45", "22:45"),
                ("23:45", "23:45"),
            ],
            "50镜湖小龙":[
                ("00:50", "00:50"),
                ("01:50", "01:50"),
                ("02:50", "02:50"),
                ("10:50", "10:50"),
                ("11:50", "11:50"),
                ("13:50", "13:50"),
                ("14:50", "14:50"),
                ("15:50", "15:50"),
                ("16:50", "16:50"),
                ("17:50", "17:50"),
                ("18:50", "18:50"),
                ("19:50", "19:50"),
                ("20:50", "20:50"),
                ("21:50", "21:50"),
                ("22:50", "22:50"),
                ("23:50", "23:50"),

            ],
            "55镜湖小龙":[
                ("00:55", "00:55"),
                ("01:55", "01:55"),
                ("02:55", "02:55"),
                ("10:55", "10:55"),
                ("11:55", "11:55"),
                ("13:55", "13:55"),
                ("14:55", "14:55"),
                ("15:55", "15:55"),
                ("16:55", "16:55"),
                ("17:55", "17:55"),
                ("18:55", "18:55"),
                ("19:55", "19:55"),
                ("20:55", "20:55"),
                ("21:55", "21:55"),
                ("22:55", "22:55"),
                ("23:55", "23:55"),
            ],
            

            "25级飞天猫":[
                ("01:00", "01:00"),
                ("04:00", "04:00"),
                ("10:00", "10:00"),
                ("13:00", "13:00"),
                ("16:00", "16:00"),
                ("19:00", "19:00"),
                ("22:00", "22:00")
            ],
            "45级飞天猫":[
                ("02:00", "02:00"),
                ("05:00", "05:00"),
                ("11:00", "11:00"),
                ("14:00", "14:00"),
                ("17:00", "17:00"),
                ("20:00", "20:00"),
                ("23:00", "23:00")
            ],
            "65级飞天猫":[
                ("03:00", "03:00"),
                ("06:00", "06:00"),
                ("12:00", "12:00"),
                ("15:00", "15:00"),
                ("18:00", "18:00"),
                ("21:00", "21:00"),
                ("00:00", "00:00")  # 24:00改为00:00
            ],
            "25级闪电狗":[
                ("02:00", "02:05"),
                ("14:00", "14:05"),
            ],
            "45级闪电狗":[
                ("06:00", "06:05"),
                ("18:00", "18:05"),
            ],
            "65级闪电狗":[
                ("10:00", "10:05"),
                ("22:00", "22:05"),
            ]
            
        }
        
        # 活动详情
        self.activity_details = {
            "珍珑棋局":"活动详情:珍珑棋局\n装备要求:白号\n要求等级:10\n位置:苏州张弈国(174,147)\n洛阳王积薪(269,88)\n大理刘仲甫(274,95)",
            "偷袭门派":"活动详情:偷袭门派\n装备要求:白号\n要求等级:20\n位置:各大门派",
            "贼兵入侵":"活动详情:贼兵入侵\n装备要求:白号\n要求等级:20\n位置:无量山\n剑阁\n镜湖\n敦煌\n太湖\n嵩山",
            "宝箱争夺":"活动详情:宝箱争夺\n装备要求:不建议参加\n要求等级:无\n位置:圣兽山",
            "千年冰魄":"活动详情:千年冰魄\n装备要求:白号不建议参加\n要求等级:无\n位置:武夷\n(153,257)\n(200,243)\n(91,186)\n(50,223)\n(38,191)\n(40,164)\n(99,47)\n(179,133)\n(252,143)\n(275,75)",
            "白冥启":"活动详情:白冥启\n装备要求:白号不建议参加\n要求等级:无\n位置:草原\n169,66(62级)\n204,47(53级)\n278,286(59级)\n43,73(74级)\n57,120(65级)\n62,258(56级)\n73,128(80级)\n99,83(68级)\n99,86(71级)",
            "玄击金刚":"活动详情:玄击金刚\n装备要求:白号不建议参加\n要求等级:无\n位置:苍山\n(131,51)\n(38,52)\n(150,60)\n(201,137)\n(60,217)\n(44,264)\n(108,256)\n(108,278)\n(190,275)\n(262,279)",
            "莽牯毒蛤王":"活动详情:莽牯毒蛤王\n装备要求:白号不建议参加\n要求等级:无\n位置:玄武岛\n73,143(59级)\n42,216(62级)\n132,277(65级)\n133,276(65级)\n134,74 (68级)\n175,50(80级)\n179,47(40级)\n180,37(80级)\n180,66(74级)\n182,63(74级)\n233,47(71级)\n266,52(56级)\n276,87(50级)\n69,141(59级)\n玄武岛有个40级的蛤蟆180,37(40级)，4小时刷新一次",
            "野猪暴走":"活动详情:野猪暴走\n装备要求:白号\n要求等级:40\n位置:圣兽山",
            "珍兽龙龟":"活动详情:珍兽龙龟\n装备要求:白号不建议参加\n要求等级:无\n位置:圣兽山(172,34)",
            "藏经阁":"活动详情:藏经阁\n装备要求:白号可以参加\n要求等级:40\n位置:西湖\n洱海\n雁南",
            "天降奇兽":"活动详情:天降奇兽\n装备要求:白号可以参加\n要求等级:85\n位置:楼兰",
            "帮派山神":"活动详情:帮派山神\n装备要求:白号不建议参加\n要求等级:要求队长要是凤凰霸主\n位置:凤凰霸主的帮地",
            "25级飞天猫":"活动详情:25级飞天猫\n装备要求:白号\n要求等级:无\n位置:玄武岛(212,181)",
            "45级飞天猫":"活动详情:45级飞天猫\n装备要求:白号\n要求等级:无\n位置:玄武岛(113,219)",
            "65级飞天猫":"活动详情:65级飞天猫\n装备要求:白号\n要求等级:无\n位置:玄武岛(271,63)",
            "25级闪电狗":"活动详情:25级闪电狗\n装备要求:白号\n要求等级:无\n位置:圣兽山(221,129)",
            "45级闪电狗":"活动详情:45级闪电狗\n装备要求:白号\n要求等级:无\n位置:圣兽山(158,155)",
            "65级闪电狗":"活动详情:65级闪电狗\n装备要求:白号\n要求等级:无\n位置:圣兽山(35,151)",
            "45镜湖小龙":"活动详情:45镜湖小龙\n装备要求:不建议参加\n要求等级:无\n位置:镜湖(250,98)(141,96)",
            "50镜湖小龙":"活动详情:50镜湖小龙\n装备要求:不建议参加\n要求等级:无\n位置:镜湖(206,253)(100,255)",
            "55镜湖小龙":"活动详情:55镜湖小龙\n装备要求:不建议参加\n要求等级:无\n位置:镜湖(139,133)",
            "门派BOSS":"活动详情:门派BOSS\n装备要求:白号\n要求等级:看门派\n位置:各大门派\n少林 彭侯(45,40)\n丐帮 孙立者(44,39)\n武当 孟昧(88,50)\n逍遥 贾川(140,40)\n天山 白岑(95,45)\n天龙 王君(95,35)\n峨眉 袁公子(45,35)\n明教 金裳(97,58)\n星宿 秋三十娘(140,50)\n\n墓也有boss刷新\n1层:60分钟。2层:90分钟。3层:360/330分钟\n4层:90分钟。5层:120分钟。6层:420/390分钟\n7层:120分钟。8层:150分钟。9层:480/430分钟"
        }
        
        # 每个活动的提醒开关
        self.activity_reminders = {}
        for activity in self.activities.keys():
            self.activity_reminders[activity] = tk.BooleanVar(value=False)  # 默认关闭提醒
        
        # 加载保存的设置
        self.load_settings()
        
        self.setup_ui()
        self.update_time()
        self.start_checking()
        
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题 - 使用样式
        title_label = ttk.Label(main_frame, text="活动提醒", style="Title.TLabel")
        title_label.pack(pady=10)
        
        # 当前时间显示 - 使用样式
        self.time_label = ttk.Label(main_frame, text="", style="Time.TLabel")
        self.time_label.pack(pady=5)
        
        # 下一个活动显示 - 使用样式
        self.next_activity_label = ttk.Label(main_frame, text="", style="Activity.TLabel", 
                                           wraplength=700, justify=tk.LEFT)
        self.next_activity_label.pack(pady=10, padx=10, fill=tk.X)
        
        # 创建分隔线
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=10)
        
        # 创建活动列表框架 - 使用样式
        list_frame = ttk.LabelFrame(main_frame, text="选择需要提醒的活动", padding="10", 
                                  style="ListTitle.TLabelframe")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建滚动条
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建Canvas和内部框架用于滚动
        self.canvas = tk.Canvas(list_frame, yscrollcommand=scrollbar.set, 
                               bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        scrollbar.config(command=self.canvas.yview)
        
        # 创建内部框架
        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        
        # 使用网格布局平铺活动复选框
        self.activity_checkboxes = {}
        activities_list = list(self.activities.keys())
        
        # 计算每行应该放置的列数（根据窗口宽度和活动数量）
        num_columns = 4  # 减少列数以解决右侧平铺问题
        
        # 配置网格权重
        for i in range(num_columns):
            self.inner_frame.columnconfigure(i, weight=1)
        
        # 放置活动复选框
        for i, activity in enumerate(activities_list):
            row = i // num_columns
            col = i % num_columns
            
            var = self.activity_reminders[activity]
            cb = ttk.Checkbutton(self.inner_frame, text=activity, variable=var, 
                                style="Large.TCheckbutton", width=20)  # 增加宽度
            cb.grid(row=row, column=col, sticky="w", padx=5, pady=5)  # 增加间距
            self.activity_checkboxes[activity] = cb
        
        # 更新内部框架大小
        self.inner_frame.update_idletasks()
        
        # 配置Canvas滚动区域
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # 绑定鼠标滚轮事件
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.inner_frame.bind("<MouseWheel>", self.on_mousewheel)
        
        # 绑定Canvas大小变化事件
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        # 保存设置按钮
        save_button = ttk.Button(button_frame, text="保存设置", command=self.save_settings)
        save_button.pack(side=tk.LEFT, padx=5)
        
        # 全选按钮
        select_all_button = ttk.Button(button_frame, text="全选", command=self.select_all)
        select_all_button.pack(side=tk.LEFT, padx=5)
        
        # 取消全选按钮
        deselect_all_button = ttk.Button(button_frame, text="取消全选", command=self.deselect_all)
        deselect_all_button.pack(side=tk.LEFT, padx=5)
        
        # 退出按钮
        quit_button = ttk.Button(button_frame, text="退出程序", command=self.quit_app)
        quit_button.pack(side=tk.LEFT, padx=5)
    
    def on_canvas_configure(self, event):
        # 调整内部框架的宽度以匹配Canvas
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def save_settings(self):
        """保存当前设置到文件"""
        settings = {}
        for activity, var in self.activity_reminders.items():
            settings[activity] = var.get()
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(settings, f)
            messagebox.showinfo("保存成功", "设置已保存，下次启动将自动加载")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存设置时出错: {str(e)}")
    
    def load_settings(self):
        """从文件加载设置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                
                for activity, value in settings.items():
                    if activity in self.activity_reminders:
                        self.activity_reminders[activity].set(value)
            except Exception as e:
                print(f"加载设置时出错: {str(e)}")
    
    def select_all(self):
        """全选所有活动"""
        for var in self.activity_reminders.values():
            var.set(True)
    
    def deselect_all(self):
        """取消全选所有活动"""
        for var in self.activity_reminders.values():
            var.set(False)
    
    def update_time(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"当前时间: {now}")
        self.root.after(1000, self.update_time)
    
    def start_checking(self):
        self.check_activities()
    
    def check_activities(self):
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # 检查所有活动
        for activity_type, times in self.activities.items():
            # 检查是否开启了该活动的提醒
            if not self.activity_reminders[activity_type].get():
                continue
                
            for time_info in times:
                start_time = time_info[0]
                # 提前3分钟提醒
                remind_time = (datetime.strptime(start_time, "%H:%M") - timedelta(minutes=3)).strftime("%H:%M")
                
                if current_time == remind_time:
                    details = self.activity_details.get(activity_type, "")
                    if activity_type == "门派BOSS":
                        self.show_reminder(f"准备刷 {time_info[1]} 门派BOSS了", f"{start_time} 开始\n\n{details}")
                    elif time_info[0] == time_info[1]: # 单个时间点活动
                        self.show_reminder(f"准备{activity_type}了", f"{start_time} 开始\n\n{details}")
                    else: # 时间段活动
                        self.show_reminder(f"准备{activity_type}了", f"{start_time}-{time_info[1]}\n\n{details}")
        
        # 更新下一个活动信息
        self.update_next_activity(now)
        
        # 每分钟检查一次
        self.root.after(60000, self.check_activities)
    
    def update_next_activity(self, now):
        current_time = now.strftime("%H:%M")
        next_activity = None
        min_diff = float('inf')
        next_activity_type = ""
        next_activity_time = ""
        
        for activity_type, times in self.activities.items():
            # 只考虑开启了提醒的活动
            if not self.activity_reminders[activity_type].get():
                continue
                
            for time_info in times:
                start_time = time_info[0]
                # 提前3分钟提醒
                remind_time = (datetime.strptime(start_time, "%H:%M") - timedelta(minutes=3)).strftime("%H:%M")
                
                # 计算时间差
                remind_dt = datetime.strptime(remind_time, "%H:%M")
                now_dt = datetime.strptime(current_time, "%H:%M")
                diff = (remind_dt - now_dt).total_seconds()
                
                if diff > 0 and diff < min_diff:
                    min_diff = diff
                    next_activity_type = activity_type
                    next_activity_time = remind_time
                    if activity_type == "门派BOSS":
                        next_activity = f"{remind_time} - 准备刷 {time_info[1]} 门派BOSS"
                    elif time_info[0] == time_info[1]: # 单个时间点活动
                        next_activity = f"{remind_time} - 准备{activity_type}"
                    else: # 时间段活动
                        next_activity = f"{remind_time} - 准备{activity_type} ({start_time}-{time_info[1]})"
        
        if next_activity:
            # 添加活动详情
            details = self.activity_details.get(next_activity_type, "")
            display_text = f"下个活动: {next_activity}"
            if details:
                # 只显示第一行详情
                first_line = details.split('\n')[0]
                display_text += f"\n{first_line}"
            self.next_activity_label.config(text=display_text)
        else:
            self.next_activity_label.config(text="今天没有更多活动了")
    
    def show_reminder(self, title, message):
        # 创建自定义提醒窗口
        reminder_window = tk.Toplevel(self.root)
        reminder_window.title(title)
        reminder_window.geometry("400x300")
        reminder_window.resizable(False, False)
        reminder_window.configure(bg="white")
        
        # 设置窗口置顶
        reminder_window.attributes('-topmost', True)
        
        # 添加图标
        try:
            reminder_window.iconbitmap("icon.ico")
        except:
            pass
        
        # 添加标题 - 使用标准 tk.Label
        title_label = tk.Label(reminder_window, text=title, font=("Arial", 14, "bold"), 
                               foreground="#e74c3c", background="white")
        title_label.pack(pady=15)
        
        # 添加内容
        message_frame = ttk.Frame(reminder_window)
        message_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        message_text = tk.Text(message_frame, wrap=tk.WORD, font=("Arial", 10), 
                              bg="#f9f9f9", relief=tk.FLAT, padx=10, pady=10)
        message_text.pack(fill=tk.BOTH, expand=True)
        
        message_text.insert(tk.END, message)
        message_text.config(state=tk.DISABLED)
        
        # 添加确定按钮
        button_frame = ttk.Frame(reminder_window)
        button_frame.pack(pady=10)
        
        ok_button = ttk.Button(button_frame, text="确定", command=reminder_window.destroy)
        ok_button.pack(pady=5)
        
        # 30秒后自动关闭
        reminder_window.after(20000, reminder_window.destroy)
        
        # 同时打印到控制台
        print(f"{datetime.now().strftime('%H:%M:%S')} - {title}: {message}")
    
    def quit_app(self):
        self.root.destroy()
        os._exit(0)

def main():
    root = tk.Tk()
    app = GameReminderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()