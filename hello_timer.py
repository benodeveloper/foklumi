import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
label = QLabel()
label.resize(300, 100)
label.show()

remaining = 10

def tick():
    global remaining
    label.setText(f"{remaining}s left")
    if remaining == 0:
        app.quit()
    remaining -= 1

timer = QTimer()
timer.timeout.connect(tick)
timer.start(1000)
tick()
sys.exit(app.exec())
