# -*- coding: utf-8 -*-
"""
/***************************************************************************
XPlan
A QGIS plugin
Fachschale XPlan für XPlanung
                             -------------------
begin                : 2011-03-08
copyright            : (C) 2011 by Bernhard Stroebl, KIJ/DV
email                : bernhard.stroebl@jena.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from PyQt4 import QtCore, QtGui, QtSql
from qgis.core import *
from qgis.gui import *
from Ui_Bereichsauswahl import Ui_Bereichsauswahl

class BereichsauswahlDialog(QtGui.QDialog):
    def __init__(self, iface, db):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_Bereichsauswahl()
        self.ui.setupUi(self)
        #self.ui.bereich.currentItemChanged.connect(self.enableOk)
        self.iface = iface
        self.db = db
        self.okBtn = self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok)
        self.okBtn.setEnabled(False)
        self.initializeValues()

    def initializeValues(self):
        # fülle QGroupBox Bereichsauswahl (planArt)
        planArt = self.ui.planArt
        lyPlanArt = planArt.layout() # Layout der QGroupBox planArt
        firstItem = lyPlanArt.itemAt(0)

        loadPlanArt = True #(not bool(firstItem))

        if not loadPlanArt:
            loadPlanArt = ('planart1' == firstItem.objectName())
            lyPlanArt.removeItem(firstItem)

        if loadPlanArt:
            query = QtSql.QSqlQuery(self.db)
            query.prepare("SELECT DISTINCT \"planart\"  \
                        FROM \"QGIS\".\"XP_Bereiche\" \
                        ORDER BY \"planart\";")
            query.exec_()

            if query.isActive():
                while query.next():
                    aPlanArt = query.value(0).toString()
                    chkPlanArt = QtGui.QCheckBox(aPlanArt,  planArt)
                    chkPlanArt.setObjectName(aPlanArt)
                    lyPlanArt.addWidget(chkPlanArt)

                query.finish()

            else:
                self.showQueryError(query)
                query.finish()

        self.fillBereichTree()
    
    def debug(self,  msg):
        QtGui.QMessageBox.information(None, "Debug",  msg)
    def fillBereichTree(self):
        planArt = self.ui.planArt
        lyPlanArt = planArt.layout() # Layout der QGroupBox planArt
        whereClause = QtCore.QString()

        for i in range(10):
            planArtItem = lyPlanArt.itemAt(i)

            if bool(planArtItem):
                planArtWidget = planArtItem.widget()

                if planArtWiddget.isChecked():

                    if whereClause.isEmpty():
                        whereClause = QtCore.QString(" WHERE \"planArt\"=\'")
                    else:
                        whereClause.append(QtCore.QString(" OR \"planArt\"=\'"))

                    whereClause.append(planArtWidget.objectName() + "\'")
            else:
                break

        sQuery = QtCore.QString("SELECT plangid, planname, gid, bereichsname FROM \"QGIS\".\"XP_Bereiche\"")
        sQuery.append(whereClause)
        sQuery.append(" ORDER BY planname, bereichsname")
        query = QtSql.QSqlQuery(self.db)
        query.prepare(sQuery)
        query.exec_()

        if query.isActive():
            self.ui.bereich.clear()
            lastParentId = -9999

            while query.next():
                parentId = query.value(0).toInt()[0]
                parent = query.value(1).toString()
                childId = query.value(2).toInt()[0]
                child = query.value(3).toString()

                if parentId != lastParentId:
                    parentItem = QtGui.QTreeWidgetItem(QtCore.QStringList(parent))
                    parentItem.parentId = parentId
                    parentItem.childId = None
                    self.ui.bereich.addTopLevelItem(parentItem)
                    lastParentId = parentId

                childItem = QtGui.QTreeWidgetItem(QtCore.QStringList(child))
                childItem.parentId = None
                childItem.childId = childId
                parentItem.addChild(childItem)
            query.finish()
        else:
            self.showQueryError(query)
            query.finish()

    #SLOTS
    @QtCore.pyqtSlot()
    def on_bereich_currentItemChanged(self):
        self.debug("bereich_currentItemChanged")
        
    @QtCore.pyqtSlot()
    def on_bereich_itemSelectionChanged(self):
        self.debug("bereich_itemSelectionChanged")
        
    def accept(self):
        thisBereichId = self.ui.bereich.currentItem().childId
        self.done(thisBereichId)
        
    def reject(self):
        self.done(-1)

    def showQueryError(self, query):
        QtGui.QMessageBox.warning(None, "Database Error", \
            QtCore.QString("%1 \n %2").arg(query.lastError().text()).arg(query.lastQuery()))

