
from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(160, 70, 381, 241))
        font = QtGui.QFont()
        font.setFamily("Baghdad")
        font.setPointSize(30)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setMouseTracking(False)
        self.label.setAutoFillBackground(False)
        self.label.setObjectName("label")
        MainWindow.setCentralWidget(self.centralwidget)

        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 36))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuEdit = QtWidgets.QMenu(self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionNew = QtWidgets.QAction(MainWindow)
        self.actionNew.setObjectName("actionNew")
        self.actionSave = QtWidgets.QAction(MainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actioncopy = QtWidgets.QAction(MainWindow)
        self.actioncopy.setObjectName("actioncopy")
        self.actionpaste = QtWidgets.QAction(MainWindow)
        self.actionpaste.setObjectName("actionpaste")
        self.menuFile.addAction(self.actionNew)
        self.menuFile.addAction(self.actionSave)
        self.menuEdit.addAction(self.actioncopy)
        self.menuEdit.addAction(self.actionpaste)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.actionNew.triggered.connect(lambda: self.clicked("New is clicked"))
        self.actionSave.triggered.connect(lambda: self.clicked("Save is clicked"))
        self.actioncopy.triggered.connect(lambda: self.clicked("copy is clicked"))
        self.actionpaste.triggered.connect(lambda: self.clicked("paste is clicked"))

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label.setText(_translate("MainWindow", "TextLabel"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "Edit"))
        self.actionNew.setText(_translate("MainWindow", "New"))
        self.actionNew.setStatusTip(_translate("MainWindow", "Create a new file"))
        self.actionNew.setShortcut(_translate("MainWindow", "Ctrl+N"))
        self.actionSave.setText(_translate("MainWindow", "Save"))
        self.actionSave.setStatusTip(_translate("MainWindow", "save file"))
        self.actionSave.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actioncopy.setText(_translate("MainWindow", "copy"))
        self.actioncopy.setStatusTip(_translate("MainWindow", "copy file"))
        self.actioncopy.setShortcut(_translate("MainWindow", "Ctrl+C"))
        self.actionpaste.setText(_translate("MainWindow", "paste"))
        self.actionpaste.setStatusTip(_translate("MainWindow", "paste file"))
        self.actionpaste.setShortcut(_translate("MainWindow", "Ctrl+V"))


    def clicked(self, text):
        self.label.setText(text)
        self.label.adjustSize()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
