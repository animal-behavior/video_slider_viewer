import re
import sys
import cv2
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QSlider,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QFileDialog,
    QFormLayout,
    QSpinBox,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap


class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Frame Viewer")
        self.setGeometry(200, 200, 800, 600)

        self.video_loaded = False
        self.csv_data = pd.DataFrame()
        self.coordinates = {}
        self.frame_set = set()
        self.video_cap = None
        self.current_frame = 0
        self.min_frame = 0
        self.max_frame = 0
        self.total_frames = 0

        # Define colors for the dots (RGB format)
        self.colors = [
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
            (255, 255, 0),  # Yellow
            (255, 165, 0),  # Orange
            (0, 255, 255),  # Cyan
            (255, 0, 255),  # Magenta
            (128, 0, 128),  # Purple
            (0, 128, 128),  # Teal
            (128, 128, 0),  # Olive
        ]

        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()

        # Frame Display Label
        self.frame_label = QLabel(self)
        main_layout.addWidget(self.frame_label)

        # Create a horizontal layout for buttons and slider
        button_layout = QHBoxLayout()

        # Open Video Button
        open_button = QPushButton("Open Video")
        open_button.clicked.connect(self.open_video)
        button_layout.addWidget(open_button)

        # Open CSV Button
        open_csv_button = QPushButton("Load CSV")
        open_csv_button.clicked.connect(self.load_csv)
        button_layout.addWidget(open_csv_button)

        # Add buttons layout below the video
        main_layout.addLayout(button_layout)

        # Create a horizontal layout for slider and frame navigation
        navigation_layout = QHBoxLayout()

        # Slider for frame navigation
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.slider_changed)
        self.slider.setFocusPolicy(
            Qt.StrongFocus
        )  # Ensure the slider can take keyboard focus
        navigation_layout.addWidget(self.slider)

        # Frame Range Input
        form_layout = QFormLayout()

        self.min_frame_input = QSpinBox(self)
        self.min_frame_input.setMinimum(0)
        self.min_frame_input.setMaximum(1000000)
        form_layout.addRow(QLabel("Min Frame:"), self.min_frame_input)

        self.max_frame_input = QSpinBox(self)
        form_layout.addRow(QLabel("Max Frame:"), self.max_frame_input)

        set_range_button = QPushButton("Set Frame Range")
        set_range_button.clicked.connect(self.set_frame_range)
        form_layout.addWidget(set_range_button)

        navigation_layout.addLayout(form_layout)

        # Add navigation layout below the video
        main_layout.addLayout(navigation_layout)

        # Container widget
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Set focus to the main window for keyboard events
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    def open_video(self):
        try:
            # Open file dialog to select video
            video_file, _ = QFileDialog.getOpenFileName(
                self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv)"
            )
            if video_file:
                if self.video_cap is not None:
                    self.video_cap.release()

                self.video_cap = cv2.VideoCapture(video_file)
                if not self.video_cap.isOpened():
                    raise IOError("Could not open video file.")

                self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.min_frame = 0
                self.max_frame = self.total_frames - 1

                self.min_frame_input.setValue(self.min_frame)
                self.max_frame_input.setMaximum(self.max_frame)
                self.max_frame_input.setValue(self.max_frame)

                self.video_loaded = True
                self.slider.setEnabled(True)
                self.slider.setMinimum(self.min_frame)
                self.slider.setMaximum(self.max_frame)
                self.slider.setValue(self.min_frame)

                self.video_width = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.video_height = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Cap window size to the available screen so 4K videos don't overflow.
                screen = QApplication.primaryScreen().availableGeometry()
                max_w = max(1, screen.width() - 80)
                max_h = max(1, screen.height() - 200)
                scale = min(max_w / self.video_width, max_h / self.video_height, 1.0)
                target_w = int(self.video_width * scale)
                target_h = int(self.video_height * scale)
                self.frame_label.setMinimumSize(1, 1)
                self.frame_label.setMaximumSize(target_w, target_h)
                self.resize(target_w, target_h + 150)

                self.show_frame(self.min_frame)

        except Exception as e:
            self.show_error_message(f"Error loading video: {e}")

    def load_csv(self):
        try:
            # Open file dialog to select CSV file
            csv_file, _ = QFileDialog.getOpenFileName(
                self, "Open CSV File", "", "CSV Files (*.csv)"
            )
            if csv_file:
                data = pd.read_csv(csv_file)

                if 'frame' not in data.columns:
                    raise ValueError("CSV must contain a 'frame' column as the frame index.")

                coordinates = {}
                columns = list(data.columns)

                for i in range(1, len(columns) - 1, 2):
                    if "x" in columns[i].lower() and "y" in columns[i + 1].lower():
                        label = re.sub(r'[_ ]*x\s*$', '', columns[i].strip().lower()).strip()
                        coordinates[label] = (columns[i], columns[i + 1])

                self.csv_data = data
                self.coordinates = coordinates
                self.frame_set = set(data['frame'].tolist())

                print("Detected Coordinates Pairs:", self.coordinates)
        except Exception as e:
            self.show_error_message(f"Error loading CSV: {e}")

    def set_frame_range(self):
        try:
            # Set minimum and maximum frames based on user input
            self.min_frame = self.min_frame_input.value()
            self.max_frame = self.max_frame_input.value()

            # Ensure valid range: min_frame should be less than or equal to max_frame
            if self.min_frame > self.max_frame:
                QMessageBox.warning(self, "Invalid Range", "Minimum Frame must be less than or equal to Maximum Frame.")
                return

            self.slider.setMinimum(self.min_frame)
            self.slider.setMaximum(self.max_frame)
            self.slider.setValue(self.min_frame)

            if self.video_loaded:
                self.show_frame(self.min_frame)
        except Exception as e:
            self.show_error_message(f"Error setting frame range: {e}")

    def slider_changed(self, position):
        try:
            # Display the frame corresponding to the slider's position
            if self.video_loaded:
                self.show_frame(position)
        except Exception as e:
            self.show_error_message(f"Error displaying frame: {e}")

    def show_frame(self, frame_number):
        try:
            # Set the frame position in the video and read it
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            success, frame = self.video_cap.read()

            if success:
                # Overlay the frame number in the upper right corner
                text = f"Frame: {frame_number}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1
                color = (255, 255, 255)  # White text
                thickness = 2
                text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
                text_x = self.video_width - text_size[0] - 10  # 10 pixels from the right edge
                text_y = 30  # 30 pixels from the top
                cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)

                if self.coordinates and frame_number in self.frame_set:
                    row_data = self.csv_data[self.csv_data['frame'] == frame_number]

                    # Connect joints in this anatomical order regardless of CSV column order.
                    key_points = ['iliac crest', 'hip', 'knee', 'ankle', 'mtp', 'toe']
                    points = []

                    for index, label in enumerate(key_points):
                        if label not in self.coordinates:
                            continue
                        x_col, y_col = self.coordinates[label]
                        x = int(float(str(row_data[x_col].values[0]).replace(u'\xa0', u'')))
                        y = int(float(str(row_data[y_col].values[0]).replace(u'\xa0', u'')))
                        points.append((x, y))

                        color = self.colors[index % len(self.colors)]
                        cv2.circle(frame, (x, y), 10, color, -1)
                        cv2.putText(frame, label, (x + 10, y - 10), font, 0.7, color, 2)

                    for i in range(len(points) - 1):
                        cv2.line(frame, points[i], points[i + 1], (0, 255, 255), 2)

                # Convert the frame to QImage format and display it
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                qimg = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                label_size = self.frame_label.size()
                if label_size.width() > 0 and label_size.height() > 0:
                    pixmap = pixmap.scaled(
                        label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                self.frame_label.setPixmap(pixmap)

        except Exception as e:
            self.show_error_message(f"Error showing frame: {e}")

    def keyPressEvent(self, event):
        """Handle key press events for the slider navigation."""
        if event.key() == Qt.Key_Right:
            new_value = self.slider.value() + 1
            if new_value <= self.max_frame:
                self.slider.setValue(new_value)
        elif event.key() == Qt.Key_Left:
            new_value = self.slider.value() - 1
            if new_value >= self.min_frame:
                self.slider.setValue(new_value)
        else:
            super().keyPressEvent(event)

    def show_error_message(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

    def closeEvent(self, event):
        if self.video_cap:
            self.video_cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
