#!/usr/bin/env python3
import sys
import os
import random
from PyQt5.QtCore import Qt, QTimer, QSettings, QFile, QTextStream
from PyQt5.QtGui import QPixmap, QKeySequence, QKeyEvent, QImageReader, QPalette, QColor, QIcon
from PyQt5.QtWidgets import (QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMainWindow, QCheckBox, QSpinBox, QFileDialog, QProgressBar, QLineEdit, QAction, QDialog, QDialogButtonBox, QGridLayout, QKeySequenceEdit, QWidget)

class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon('icon/KJGICON.ico'))

        self.hide()  # Hide the window during initialization
        self.init_ui()
        self.load_settings()
        self.restore_window_state()  # Move this line here
        self.set_icon()

        QTimer.singleShot(0, self.show)  # Show the window after initialization is complete

    def set_icon(self):
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'icon', 'KJGICON.ico')
        else:
            icon_path = 'icon/KJGICON.ico'

        self.setWindowIcon(QIcon(icon_path))

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.image_label = QLabel(self)
        self.image_label.setScaledContents(False)
        self.image_label.setMinimumSize(1, 1)

        self.image_label.setAlignment(Qt.AlignCenter)
        self.remaining_time_label = QLabel(self)

        self.stay_on_top_cb = QCheckBox("Stay on top", self)
        self.stay_on_top_cb.stateChanged.connect(self.stay_on_top)

        self.random_order_cb = QCheckBox("Randomize", self)
        self.fullscreen_cb = QCheckBox("Fullscreen", self)
        self.fullscreen_cb.stateChanged.connect(self.toggle_fullscreen_cb)
        self.interval_spinbox = QSpinBox(self)
        # self.interval_spinbox.setPrefix("Interval: ")
        self.interval_spinbox.setSuffix(" s")
        self.interval_spinbox.setRange(1, 180)
        self.interval_spinbox.valueChanged.connect(self.update_interval)

        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.browse_directory)

        self.settings_button = QPushButton("Settings", self)
        self.settings_button.clicked.connect(self.show_settings_dialog)

        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.start)
        self.start_button.setShortcut(QKeySequence("Ctrl+S"))

        self.pause_button = QPushButton("Pause", self)
        self.pause_button.clicked.connect(self.pause)
        self.pause_button.setShortcut(QKeySequence("Ctrl+P"))

        self.skip_button = QPushButton("Skip", self)
        self.skip_button.clicked.connect(self.skip)
        self.skip_button.setShortcut(QKeySequence("Ctrl+K"))

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)

        self.folder_path_edit = QLineEdit(self)
        self.folder_path_edit.setReadOnly(True)
        self.folder_path_edit.setDisabled(True)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.stay_on_top_cb)
        top_layout.addWidget(self.random_order_cb)
        top_layout.addWidget(self.fullscreen_cb)
        top_layout.addWidget(self.interval_spinbox)
        top_layout.addWidget(self.browse_button)
        top_layout.addWidget(self.settings_button)

        middle_layout = QHBoxLayout()
        middle_layout.addWidget(self.folder_path_edit)

        bottom_layout = QHBoxLayout()
        self.session_time_label = QLabel(self)
        bottom_layout.addWidget(self.session_time_label)
        bottom_layout.addWidget(self.remaining_time_label)
        bottom_layout.addWidget(self.start_button)
        bottom_layout.addWidget(self.pause_button)
        bottom_layout.addWidget(self.skip_button)

        main_layout = QVBoxLayout(central_widget)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.image_label)
        main_layout.addLayout(middle_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(bottom_layout)

        self.setWindowTitle("JustDraw")
        self.setGeometry(100, 100, 800, 600)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_image)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_remaining_time)
        self.countdown_timer.setInterval(1000)
        self.remaining_time = 0
        self.update_remaining_time()

        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.update_session_time)
        self.session_timer.setInterval(1000)
        self.session_time = 0

        self.fullscreen_action = QAction("Toggle Fullscreen", self)
        self.fullscreen_action.setShortcut(QKeySequence("F11"))
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.addAction(self.fullscreen_action)
        self.set_initial_session_time()

    def browse_directory(self):
        if hasattr(self, 'directory'):
            directory = QFileDialog.getExistingDirectory(self, "Select directory", self.directory)
        else:
            directory = QFileDialog.getExistingDirectory(self, "Select directory")
        if directory:
            self.directory = directory
            self.update_folder_path()
            self.load_images()
            self.pause()

    def show_settings_dialog(self):
        settings_dialog = SettingsDialog(self)
        settings_dialog.set_shortcuts(self.start_button.shortcut(), self.pause_button.shortcut(), self.skip_button.shortcut(), self.fullscreen_action.shortcut())
        if settings_dialog.exec_() == QDialog.Accepted:
            self.start_button.setShortcut(QKeySequence(settings_dialog.start_edit.keySequence()))
            self.pause_button.setShortcut(QKeySequence(settings_dialog.pause_edit.keySequence()))
            self.skip_button.setShortcut(QKeySequence(settings_dialog.skip_edit.keySequence()))
            self.fullscreen_action.setShortcut(QKeySequence(settings_dialog.fullscreen_edit.keySequence()))

    def load_images(self):
        extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif')
        self.images = []
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.lower().endswith(extensions):
                    self.images.append(os.path.join(root, file))
        self.images = sorted(self.images)
        
        if self.random_order_cb.isChecked():
            random.shuffle(self.images)
        
        if not self.images:
            self.pause()
            return
        
        self.current_image_index = 0
        self.update_image()

    def update_image(self):
        if not self.images:
            return

        image_reader = QImageReader(self.images[self.current_image_index])
        if not image_reader.canRead():
            print(f"Warning: {self.images[self.current_image_index]} seems to be a corrupt image file")
            self.current_image_index = (self.current_image_index + 1) % len(self.images)
            return self.update_image()

        pixmap = QPixmap(self.images[self.current_image_index])

        # Check if pixmap is not a null pixmap before scaling
        if not pixmap.isNull():
            pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pixmap)

        self.current_image_index = (self.current_image_index + 1) % len(self.images)
        self.restart_countdown_timer()

    def start(self):
        if not hasattr(self, 'images') or not self.images:
            return

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        if not self.timer.isActive():
            self.timer.start((self.remaining_time + 1) * 1000)
        self.countdown_timer.start()
        self.session_timer.start()

        # Apply the disabled style for the Start button even in dark mode
        self.start_button.setStyleSheet("color: #808080; background-color: #353535; border: none;")
        # Restore the default style for the Pause button when it's enabled
        self.pause_button.setStyleSheet("")

    def pause(self):
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.timer.stop()
        self.countdown_timer.stop()
        self.session_timer.stop()

        # Apply the disabled style for the Pause button even in dark mode
        self.pause_button.setStyleSheet("color: #808080; background-color: #353535; border: none;")
        # Restore the default style for the Start button when it's enabled
        self.start_button.setStyleSheet("")

    def skip(self):
        self.update_image()
        self.restart_countdown_timer()

    def stay_on_top(self, state):
        current_geometry = self.geometry()  # Save current geometry
        if state == Qt.Checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()
        self.setGeometry(current_geometry)  # Restore geometry

    def load_settings(self):
        settings = QSettings('ImageViewer', 'settings')
        self.directory = settings.value('directory')
        self.random_order_cb.setChecked(settings.value('randomOrder', False, bool))
        self.stay_on_top_cb.setChecked(settings.value('stayOnTop', False, bool))
        self.interval_spinbox.setValue(settings.value('interval', 10, int))
        self.stay_on_top(self.stay_on_top_cb.checkState())
        if self.directory:
            self.update_folder_path()
            self.load_images()
            self.pause()
        self.start_button.setShortcut(QKeySequence(settings.value("startShortcut", "Ctrl+S")))
        self.pause_button.setShortcut(QKeySequence(settings.value("pauseShortcut", "Ctrl+P")))
        self.skip_button.setShortcut(QKeySequence(settings.value("skipShortcut", "Ctrl+K")))
        self.fullscreen_action.setShortcut(QKeySequence(settings.value("fullscreenShortcut", "F11")))
        self.restore_window_state()

    def closeEvent(self, event):
        settings = QSettings('ImageViewer', 'settings')
        settings.setValue('directory', self.directory)
        settings.setValue('randomOrder', self.random_order_cb.isChecked())
        settings.setValue('stayOnTop', self.stay_on_top_cb.isChecked())
        settings.setValue('interval', self.interval_spinbox.value())
        settings.setValue("startShortcut", self.start_button.shortcut().toString())
        settings.setValue("pauseShortcut", self.pause_button.shortcut().toString())
        settings.setValue("skipShortcut", self.skip_button.shortcut().toString())
        settings.setValue("fullscreenShortcut", self.fullscreen_action.shortcut().toString())
        self.save_window_state()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'images') and self.images:
            self.update_image_scaled()

    def update_image_scaled(self):
        pixmap = QPixmap(self.images[self.current_image_index - 1])
        pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(pixmap)

    def restart_countdown_timer(self):
        self.timer.stop()
        self.timer.start(self.interval_spinbox.value() * 1000)
        self.remaining_time = self.interval_spinbox.value()
        self.update_remaining_time()

    def update_interval(self):
        if self.timer.isActive():
            self.restart_countdown_timer()
        else:
            self.remaining_time = self.interval_spinbox.value()
            self.update_remaining_time()

    def update_remaining_time(self):
        mins, secs = divmod(self.remaining_time, 60)
        self.remaining_time_label.setText(f"Countdown: {mins:02d}:{secs:02d}")
        self.progress_bar.setValue(int(100 * self.remaining_time / self.interval_spinbox.value()))

        # Update progress bar color
        if self.remaining_time <= 5:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        elif self.remaining_time <= 15:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #2a82da; }")

        self.remaining_time -= 1

    def update_folder_path(self):
        folder_name = os.path.basename(self.directory)
        self.folder_path_edit.setText(folder_name)
        self.folder_path_edit.setDisabled(False)

    def update_fullscreen_checkbox(self):
        if self.isFullScreen():
            self.fullscreen_cb.setChecked(True)
        else:
            self.fullscreen_cb.setChecked(False)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self.update_fullscreen_checkbox()

    def toggle_fullscreen_cb(self, state):
        if state == Qt.Checked:
            self.showFullScreen()
        else:
            self.showNormal()
        self.update_fullscreen_checkbox()

    def set_initial_session_time(self):
        mins, secs = divmod(self.session_time, 60)
        self.session_time_label.setText(f"Session: {mins:02d}:{secs:02d}")

    def update_session_time(self):
        self.session_time += 1
        mins, secs = divmod(self.session_time, 60)
        self.session_time_label.setText(f"Session: {mins:02d}:{secs:02d}")

    def save_window_state(self):
        settings = QSettings('ImageViewer', 'settings')
        settings.beginGroup("MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())
        settings.endGroup()

    def restore_window_state(self):
        settings = QSettings('ImageViewer', 'settings')
        settings.beginGroup("MainWindow")
        result_geometry = settings.value("geometry")
        result_state = settings.value("state")
        if result_geometry:
            self.restoreGeometry(result_geometry)
        if result_state:
            self.restoreState(result_state)
        settings.endGroup()

class CustomQKeySequenceEdit(QKeySequenceEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def focusInEvent(self, event):
        self.prev_key_sequence = self.keySequence()
        self.clear()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if not self.keySequence():
            self.setKeySequence(self.prev_key_sequence)
        super().focusOutEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout(self)

        start_label = QLabel('Start:', self)
        self.start_edit = CustomQKeySequenceEdit(self)
        self.start_edit.setKeySequence("Ctrl+S")

        pause_label = QLabel('Pause:', self)
        self.pause_edit = CustomQKeySequenceEdit(self)
        self.pause_edit.setKeySequence("Ctrl+P")

        skip_label = QLabel('Skip:', self)
        self.skip_edit = CustomQKeySequenceEdit(self)
        self.skip_edit.setKeySequence("Ctrl+K")

        fullscreen_label = QLabel('Toggle Fullscreen:', self)
        self.fullscreen_edit = CustomQKeySequenceEdit(self)
        self.fullscreen_edit.setKeySequence("F11")

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(start_label, 0, 0)
        layout.addWidget(self.start_edit, 0, 1)
        layout.addWidget(pause_label, 1, 0)
        layout.addWidget(self.pause_edit, 1, 1)
        layout.addWidget(skip_label, 2, 0)
        layout.addWidget(self.skip_edit, 2, 1)
        layout.addWidget(fullscreen_label, 3, 0)
        layout.addWidget(self.fullscreen_edit, 3, 1)
        layout.addWidget(button_box, 4, 1)

        self.setWindowTitle("Settings")

        self.setFocus()
        
    def set_shortcuts(self, start_shortcut, pause_shortcut, skip_shortcut, fullscreen_shortcut):
        self.start_edit.setKeySequence(start_shortcut)
        self.pause_edit.setKeySequence(pause_shortcut)
        self.skip_edit.setKeySequence(skip_shortcut)
        self.fullscreen_edit.setKeySequence(fullscreen_shortcut)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(50, 50, 50))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(37, 37, 37))
    dark_palette.setColor(QPalette.AlternateBase, QColor(50, 50, 50))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(50, 50, 50))
    dark_palette.setColor(QPalette.ButtonText, QColor(0, 170, 255))
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)
    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; } QProgressBar { text-align: center; } QProgressBar::chunk { background-color: #2a82da; width: 1px; margin: 0px; }")
    viewer = ImageViewer()
    sys.exit(app.exec_())