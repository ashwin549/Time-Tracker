import sys
import time
import psutil
import datetime
from collections import defaultdict
import json
import os
from win32gui import GetWindowText, GetForegroundWindow
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QSystemTrayIcon,
                            QMenu, QTableWidget, QTableWidgetItem, QStyle,
                            QHeaderView)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction

class TimeTracker:
    def __init__(self, parent=None):
        self.usage_data = defaultdict(int)
        self.current_app = "None"
        self.start_time = None
        self.today_date = datetime.date.today().strftime("%Y-%m-%d")
        self.data_file = "time_tracker_data.json"
        self.is_tracking = True
        self.parent = parent
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    if self.today_date in data:
                        self.usage_data = defaultdict(int, data[self.today_date])
            except json.JSONDecodeError:
                pass

    def save_data(self):
        data = {}
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                pass
        
        data[self.today_date] = dict(self.usage_data)
        
        with open(self.data_file, 'w') as f:
            json.dump(data, f)

    def get_active_window_title(self):
        return GetWindowText(GetForegroundWindow())

    def pause_tracking(self):
        self.is_tracking = False
        if self.current_app and self.start_time:
            time_spent = int(time.time() - self.start_time)
            self.usage_data[self.current_app] += time_spent
        self.save_data()

    def resume_tracking(self):
        self.is_tracking = True
        self.start_time = time.time()
        self.current_app = self.get_active_window_title()

    def track(self):
        while True:
            if self.is_tracking:
                new_app = self.get_active_window_title()
                current_time = time.time()

                if new_app != self.current_app:
                    if self.current_app and self.start_time:
                        time_spent = int(current_time - self.start_time)
                        self.usage_data[self.current_app] += time_spent

                    self.current_app = new_app
                    self.start_time = current_time

                if int(current_time) % 60 == 0:
                    self.save_data()

            time.sleep(1)

class TimeTrackerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Time Tracker")
        self.setMinimumSize(800, 600)
        
        # Initialize tracker
        self.tracker = TimeTracker(self)
        
        # Setup UI
        self.setup_ui()
        
        # Setup system tray
        self.setup_system_tray()
        
        # Start tracking
        self.tracking_thread = threading.Thread(target=self.tracker.track, daemon=True)
        self.tracking_thread.start()
        
        # Setup timer for UI updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(1000)  # Update every second

    def setup_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Status bar at top
        status_bar = QWidget()
        status_layout = QHBoxLayout(status_bar)
        
        self.status_label = QLabel("Currently tracking: None")
        status_layout.addWidget(self.status_label)
        
        self.toggle_button = QPushButton("Pause")
        self.toggle_button.clicked.connect(self.toggle_tracking)
        status_layout.addWidget(self.toggle_button)
        
        layout.addWidget(status_bar)
        
        # Statistics table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Application", "Time Spent"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)
        
        # Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 4px;
                color: #000000;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1984D8;
            }
            QLabel {
                font-size: 14px;
                color: black;
            }
        """)

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        # Create tray menu
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def toggle_tracking(self):
        if self.tracker.is_tracking:
            self.tracker.pause_tracking()
            self.toggle_button.setText("Resume")
            self.toggle_button.setStyleSheet("background-color: #28a745;")
        else:
            self.tracker.resume_tracking()
            self.toggle_button.setText("Pause")
            self.toggle_button.setStyleSheet("background-color: #0078D7;")

    def update_ui(self):
        self.status_label.setText(f"Currently tracking: {self.tracker.current_app}")
        
        # Update table
        sorted_usage = sorted(self.tracker.usage_data.items(), key=lambda x: x[1], reverse=True)
        self.table.setRowCount(len(sorted_usage))
        
        for row, (app, seconds) in enumerate(sorted_usage):
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            
            app_item = QTableWidgetItem(app)
            time_item = QTableWidgetItem(time_str)
            
            self.table.setItem(row, 0, app_item)
            self.table.setItem(row, 1, time_item)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Time Tracker",
            "Application minimized to system tray",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def quit_app(self):
        self.tracker.save_data()
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion') 
    
    window = TimeTrackerWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
