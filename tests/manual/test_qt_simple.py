"""Simple Qt test to verify PySide6 works."""
import sys
from PySide6.QtWidgets import QApplication, QMessageBox

print("Creating Qt application...")
app = QApplication(sys.argv)

print("Showing message box...")
msg = QMessageBox()
msg.setWindowTitle("Qt Test")
msg.setText("If you see this, PySide6 is working!\n\nClick OK to continue.")
msg.exec()

print("Qt test completed successfully!")
