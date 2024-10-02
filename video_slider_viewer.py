import sys
import cv2
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QPushButton,
    QWidget, QFileDialog, QFormLayout, QSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap


class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Frame Viewer with CSV Data")
        self.setGeometry(200, 200, 800, 600)

        self.video_loaded = False
        self.csv_data = pd.DataFrame()
        self.coordinates = {}
        self.video_cap = None
        self.current_frame = 0
        self.min_frame = 0
        self.max_frame = 0
        self.total_frames = 0

        # Define colors for the dots (RGB format)
        self.colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 165, 0),  # Orange
            (0, 255, 255),  # Cyan
            (255, 0, 255),  # Magenta
            (128, 0, 128),  # Purple
            (0, 128, 128),  # Teal
            (128, 128, 0)   # Olive
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
        self.slider.sliderMoved.connect(self.slider_changed)
        navigation_layout.addWidget(self.slider)

        # Frame Range Input
        form_layout = QFormLayout()

        # Style sheet for making labels white
        label_style = "QLabel { color : white; }"

        self.min_frame_input = QSpinBox(self)
        self.min_frame_input.setMinimum(0)
        min_frame_label = QLabel("Min Frame:")
        min_frame_label.setStyleSheet(label_style)  # Set label to white
        form_layout.addRow(min_frame_label, self.min_frame_input)

        self.max_frame_input = QSpinBox(self)
        max_frame_label = QLabel("Max Frame:")
        max_frame_label.setStyleSheet(label_style)  # Set label to white
        form_layout.addRow(max_frame_label, self.max_frame_input)

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

    def open_video(self):
        try:
            # Open file dialog to select video
            video_file, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv)")
            if video_file:
                self.video_cap = cv2.VideoCapture(video_file)
                if not self.video_cap.isOpened():
                    raise IOError("Could not open video file.")

                self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.max_frame_input.setMaximum(self.total_frames - 1)
                self.max_frame_input.setValue(self.total_frames - 1)

                self.video_loaded = True
                self.slider.setEnabled(True)
                self.slider.setMinimum(self.min_frame)
                self.slider.setMaximum(self.max_frame)
                self.slider.setValue(self.min_frame)

                # Get video width and height for auto-resize
                self.video_width = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.video_height = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Adjust QLabel size to match video resolution
                self.frame_label.setFixedSize(self.video_width, self.video_height)

                # Set window size to fit the video resolution properly
                self.resize(self.video_width, self.video_height + 150)  # Add some height for the controls

                self.show_frame(self.min_frame)

        except Exception as e:
            self.show_error_message(f"Error loading video: {e}")

    def load_csv(self):
        try:
            # Open file dialog to select CSV file
            csv_file, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
            if csv_file:
                # Load CSV with pandas
                self.csv_data = pd.read_csv(csv_file)

                # Parse columns and identify pairs of x, y coordinates
                self.coordinates = {}
                columns = self.csv_data.columns

                for i in range(1, len(columns), 2):  # Skip 'frame' column (0 index)
                    if 'x' in columns[i].lower() and 'y' in columns[i + 1].lower():
                        label = columns[i].replace('x', '').strip()
                        self.coordinates[label] = (columns[i], columns[i + 1])

                print("Detected Coordinates Pairs:", self.coordinates)
        except Exception as e:
            self.show_error_message(f"Error loading CSV: {e}")

    def set_frame_range(self):
        try:
            # Set minimum and maximum frames based on user input
            self.min_frame = self.min_frame_input.value()
            self.max_frame = self.max_frame_input.value()

            if self.min_frame >= self.max_frame:
                self.max_frame = self.min_frame + 1
                self.max_frame_input.setValue(self.max_frame)

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

                # If CSV data is available, plot the dots and add their labels
                if not self.csv_data.empty and frame_number in self.csv_data['frame'].values:
                    row_data = self.csv_data[self.csv_data['frame'] == frame_number]

                    for index, (label, (x_col, y_col)) in enumerate(self.coordinates.items()):
                        x = int(float(str(row_data[x_col].values[0]).replace(u'\xa0', u'')))
                        y = int(float(str(row_data[y_col].values[0]).replace(u'\xa0', u'')))

                        # Cycle through colors based on the index of the label
                        color = self.colors[index % len(self.colors)]

                        # Draw the dot
                        cv2.circle(frame, (x, y), 5, color, -1)  # Colored dot

                        # Draw the label text next to the dot
                        label_x = x + 10  # Offset the label slightly
                        label_y = y - 10
                        cv2.putText(frame, label, (label_x, label_y), font, 0.7, color, 2)

                # Convert the frame to QImage format and display it
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                qimg = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                self.frame_label.setPixmap(QPixmap.fromImage(qimg))
        except Exception as e:
            self.show_error_message(f"Error showing frame: {e}")

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
    sys.exit(app.exec_())
