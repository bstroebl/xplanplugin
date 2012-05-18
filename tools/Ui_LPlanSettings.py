# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'tools/Ui_LPlanSettings.ui'
#
# Created by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_LPlanSettings(object):
    def setupUi(self, LPlanSettings):
        LPlanSettings.setObjectName(_fromUtf8("LPlanSettings"))
        LPlanSettings.resize(400, 300)
        self.verticalLayout = QtGui.QVBoxLayout(LPlanSettings)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(LPlanSettings)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.bereiche = QtGui.QTreeWidget(LPlanSettings)
        self.bereiche.setObjectName(_fromUtf8("bereiche"))
        self.bereiche.headerItem().setText(0, _fromUtf8("1"))
        self.bereiche.header().setVisible(False)
        self.verticalLayout.addWidget(self.bereiche)
        self.buttonBox = QtGui.QDialogButtonBox(LPlanSettings)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(LPlanSettings)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), LPlanSettings.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), LPlanSettings.reject)
        QtCore.QMetaObject.connectSlotsByName(LPlanSettings)

    def retranslateUi(self, LPlanSettings):
        LPlanSettings.setWindowTitle(QtGui.QApplication.translate("LPlanSettings", "Einstellungen LPlan", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("LPlanSettings", "aktive LP_Bereiche", None, QtGui.QApplication.UnicodeUTF8))

