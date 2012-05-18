# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'tools/Ui_LP_Objekt.ui'
#
# Created by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_LP_Objekt(object):
    def setupUi(self, LP_Objekt):
        LP_Objekt.setObjectName(_fromUtf8("LP_Objekt"))
        LP_Objekt.resize(400, 271)
        self.verticalLayout = QtGui.QVBoxLayout(LP_Objekt)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(LP_Objekt)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.bereich = QtGui.QListWidget(LP_Objekt)
        self.bereich.setObjectName(_fromUtf8("bereich"))
        self.verticalLayout.addWidget(self.bereich)
        self.buttonBox = QtGui.QDialogButtonBox(LP_Objekt)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Save)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(LP_Objekt)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), LP_Objekt.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), LP_Objekt.reject)
        QtCore.QMetaObject.connectSlotsByName(LP_Objekt)

    def retranslateUi(self, LP_Objekt):
        LP_Objekt.setWindowTitle(QtGui.QApplication.translate("LP_Objekt", "LP_Objekt", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("LP_Objekt", "gehoertZuLP_Bereich", None, QtGui.QApplication.UnicodeUTF8))

