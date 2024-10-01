import sys
import cv2
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QSlider, QVBoxLayout, QPushButton,
    QWidget, QFileDialog, QFormLayout, QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap


class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Frame Viewer")
        self.setGeometry(200, 200, 800, 600)

        self.video_loaded = False
        self.video_cap = None
        self.current_frame = 0
        self.min_frame = 0
        self.max_frame = 0
        self.total_frames = 0

        self.init_ui()

    def init_ui(self):
        # Layouts
        main_layout = QVBoxLayout()

        # Frame Display Label
        self.frame_label = QLabel(self)
        main_layout.addWidget(self.frame_label)

        # Open Video Button
        open_button = QPushButton("Open Video")
        open_button.clicked.connect(self.open_video)
        main_layout.addWidget(open_button)

        # Slider for frame navigation
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)
        self.slider.sliderMoved.connect(self.slider_changed)
        main_layout.addWidget(self.slider)

        # Frame Range Input
        form_layout = QFormLayout()

        self.min_frame_input = QSpinBox(self)
        self.min_frame_input.setMinimum(0)
        form_layout.addRow("Min Frame:", self.min_frame_input)

        self.max_frame_input = QSpinBox(self)
        form_layout.addRow("Max Frame:", self.max_frame_input)

        set_range_button = QPushButton("Set Frame Range")
        set_range_button.clicked.connect(self.set_frame_range)
        form_layout.addWidget(set_range_button)

        main_layout.addLayout(form_layout)

        # Container widget
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def open_video(self):
        # Open file dialog to select video
        video_file, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv)")
        if video_file:
            self.video_cap = cv2.VideoCapture(video_file)
            if self.video_cap.isOpened():
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

    def set_frame_range(self):
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

    def slider_changed(self, position):
        # Display the frame corresponding to the slider's position
        if self.video_loaded:
            self.show_frame(position)

    def show_frame(self, frame_number):
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

            # Convert the frame to QImage format and display it
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            qimg = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.frame_label.setPixmap(QPixmap.fromImage(qimg))

    def closeEvent(self, event):
        if self.video_cap:
            self.video_cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec_())
