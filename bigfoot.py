#!/usr/bin/env python3


import sys
import os
from pathlib import Path
import time

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from bigfoot_classes import LoginWidget
 

if __name__ == '__main__':
    
    style_file = "bigfoot_style.stylesheet"
    app = QApplication(sys.argv)
    with open(style_file,'r') as style_sh:
        app.setStyleSheet(style_sh.read())
    
    login = LoginWidget()
    login.show()

    try:
        sys.exit(app.exec())
    except SystemExit:
        print('Closing Window...')  
    
