from random import choice
from pathlib import Path
import shutil
import sys
import subprocess
from tinytag import TinyTag

from PyQt6.QtWidgets import (
    QApplication, QDialog, QStyle, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSizePolicy, QFileDialog, QLineEdit, QSlider
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QIcon

# ----------------------------
# Variables
# ----------------------------
looping = False

# ----------------------------
# App setup
# ----------------------------
app = QApplication([])
window = QWidget()
window.setWindowTitle("Suga's Emotional Music Player")
window.setGeometry(100, 100, 800, 600)

layout = QVBoxLayout()
window.setLayout(layout)

videoWidget = QVideoWidget()
videoWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
layout.addWidget(videoWidget)

mediaPlayer = QMediaPlayer()
audio_output = QAudioOutput()
mediaPlayer.setAudioOutput(audio_output)
mediaPlayer.setVideoOutput(videoWidget)
audio_output.setVolume(0.5)

songtitle = QLabel("Select an emotion to start 🎵")
songtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
layout.addWidget(songtitle)

# ----------------------------
# Controls
# ----------------------------
button_layout = QHBoxLayout()
layout.addLayout(button_layout)

pauseplaybutton = QPushButton()
pauseplaybutton.setIcon(app.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

nextbutton = QPushButton("Next")
repeatbutton = QPushButton("Repeat")
loopbutton = QPushButton("Looping: Off")
settingsbutton = QPushButton("⚙")

button_layout.addWidget(pauseplaybutton)
button_layout.addWidget(nextbutton)
button_layout.addWidget(repeatbutton)
button_layout.addWidget(loopbutton)
button_layout.addWidget(settingsbutton)

# ----------------------------
# Seek bar + time
# ----------------------------
seek_layout = QHBoxLayout()
layout.addLayout(seek_layout)

current_time_label = QLabel("00:00")
total_time_label = QLabel("00:00")
seek_slider = QSlider(Qt.Orientation.Horizontal)
seek_slider.setRange(0, 0)

seek_layout.addWidget(current_time_label)
seek_layout.addWidget(seek_slider)
seek_layout.addWidget(total_time_label)

# ----------------------------
# Volume
# ----------------------------
volume_layout = QHBoxLayout()
layout.addLayout(volume_layout)

volume_label = QLabel("Volume")
volume_slider = QSlider(Qt.Orientation.Horizontal)
volume_slider.setRange(0, 100)
volume_slider.setValue(50)

volume_layout.addWidget(volume_label)
volume_layout.addWidget(volume_slider)

# ----------------------------
# Folder setup
# ----------------------------
main_folder = Path("songs")
main_folder.mkdir(exist_ok=True)

subfolders = []
currentSong = {}

# ----------------------------
# Helpers
# ----------------------------
def formatTime(ms):
    seconds = int(ms / 1000)
    minutes = seconds // 60
    seconds %= 60
    return f"{minutes:02}:{seconds:02}"

def clearLayout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

def refreshEmotionButtons():
    subfolders[:] = [x for x in main_folder.iterdir() if x.is_dir()]
    clearLayout(emotion_layout)

    for folder in subfolders:
        btn = QPushButton(folder.name)
        emotion_layout.addWidget(btn)

        def make_handler(folder_name, button):
            return lambda: loadVideo(folder_name, button)

        btn.clicked.connect(make_handler(folder.name, btn))

# ----------------------------
# Video logic
# ----------------------------
def selectVideo(emotion):
    folder = main_folder / emotion
    if not folder.exists():
        return []

    return [
        str(f) for f in folder.rglob("*")
        if f.suffix.lower() in [".mp4", ".mp3", ".wav", ".mkv"]
    ]

def loadVideo(emotion, button=None):
    video_list = selectVideo(emotion)

    if not video_list:
        songtitle.setText(f"No media found for: {emotion}")
        return

    if len(video_list) > 1:
        video_list = [v for v in video_list if v != currentSong.get("file_path")]

    file_path = choice(video_list)

    try:
        tag = TinyTag.get(file_path)
        title = tag.title
    except:
        title = None

    currentSong.update({
        "title": title or Path(file_path).stem,
        "file_path": file_path,
        "emotion": emotion
    })

    songtitle.setText(currentSong["title"])
    mediaPlayer.setSource(QUrl.fromLocalFile(file_path))
    mediaPlayer.play()

    pauseplaybutton.setIcon(
        app.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
    )

def nextVideo():
    if "emotion" in currentSong:
        loadVideo(currentSong["emotion"], None)

def repeatVideo():
    if "file_path" in currentSong:
        mediaPlayer.setPosition(0)
        mediaPlayer.play()

def pausePlayVideo():
    if mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
        mediaPlayer.pause()
        pauseplaybutton.setIcon(
            app.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
    else:
        mediaPlayer.play()
        pauseplaybutton.setIcon(
            app.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        )

# ----------------------------
# Seek + time updates
# ----------------------------
def updatePosition(position):
    seek_slider.setValue(position)
    current_time_label.setText(formatTime(position))

def updateDuration(duration):
    seek_slider.setRange(0, duration)
    total_time_label.setText(formatTime(duration))

def setPosition(position):
    mediaPlayer.setPosition(position)

mediaPlayer.positionChanged.connect(updatePosition)
mediaPlayer.durationChanged.connect(updateDuration)
seek_slider.sliderMoved.connect(setPosition)

# ----------------------------
# Auto-play next / loop
# ----------------------------
def handleMediaStatus(status):
    if status == QMediaPlayer.MediaStatus.EndOfMedia:
        if looping:
            mediaPlayer.setPosition(0)
            mediaPlayer.play()
        else:
            nextVideo()

mediaPlayer.mediaStatusChanged.connect(handleMediaStatus)

# ----------------------------
# Volume
# ----------------------------
def changeVolume(value):
    audio_output.setVolume(value / 100)

volume_slider.valueChanged.connect(changeVolume)

# ----------------------------
# Folder management
# ----------------------------
def createfolder():
    name = createfolderinput.text().strip()
    if not name:
        return

    if name.lower() in [f.name.lower() for f in subfolders]:
        return

    (main_folder / name).mkdir()
    refreshEmotionButtons()

def deletefolder():
    popup = QDialog(window)
    popup.setLayout(QVBoxLayout())

    for folder in subfolders:
        btn = QPushButton(folder.name)
        popup.layout().addWidget(btn)

        def delete_selected(f=folder):
            shutil.rmtree(f)
            popup.close()
            refreshEmotionButtons()

            if currentSong.get("emotion") == f.name:
                mediaPlayer.stop()
                songtitle.setText("No emotion selected")

        btn.clicked.connect(delete_selected)

    popup.exec()

def toggle_looping():
    global looping
    looping = not looping
    loopbutton.setText("Looping: On" if looping else "Looping: Off")

# ----------------------------
# Settings
# ----------------------------
def openFileManager():
    dialog = QFileDialog()
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setDirectory(str(main_folder.resolve()))

    if dialog.exec():
        selected_folder = dialog.selectedFiles()[0]
        QDesktopServices.openUrl(QUrl.fromLocalFile(selected_folder))

def settings():
    dialog = QDialog(window)
    dialog.setLayout(QVBoxLayout())

    global createfolderinput
    createfolderinput = QLineEdit()
    dialog.layout().addWidget(createfolderinput)

    btn1 = QPushButton("Create Folder")
    btn1.clicked.connect(createfolder)

    btn2 = QPushButton("Delete Folder")
    btn2.clicked.connect(deletefolder)

    btn3 = QPushButton("Open Folder")
    btn3.clicked.connect(openFileManager)

    dialog.layout().addWidget(btn1)
    dialog.layout().addWidget(btn2)
    dialog.layout().addWidget(btn3)
    

    dialog.exec()

# ----------------------------
# Connect buttons
# ----------------------------
pauseplaybutton.clicked.connect(pausePlayVideo)
nextbutton.clicked.connect(nextVideo)
repeatbutton.clicked.connect(repeatVideo)
settingsbutton.clicked.connect(settings)
loopbutton.clicked.connect(toggle_looping)

# ----------------------------
# Emotion buttons
# ----------------------------
emotion_layout = QHBoxLayout()
layout.addLayout(emotion_layout)
refreshEmotionButtons()

# ----------------------------
# Start
# ----------------------------
if subfolders:
    loadVideo(subfolders[0].name, None)

window.show()
app.exec()
