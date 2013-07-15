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
    def __init__(self, iface, db,  multiSelect,  title = "Bereichsauswahl"):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_Bereichsauswahl()
        self.ui.setupUi(self)
        self.setWindowTitle(title)
        #self.ui.bereich.currentItemChanged.connect(self.enableOk)
        self.iface = iface
        self.db = db
        self.selected = {} # dict, das id: Name der ausgewählten Bereiche enthält
        self.okBtn = self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok)
        self.okBtn.setEnabled(False)

        if multiSelect:
            self.ui.bereich.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

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
                firstRecord = True
                while query.next():
                    aPlanArt = query.value(0)
                    radPlanArt = QtGui.QRadioButton(aPlanArt,  planArt)
                    radPlanArt.setObjectName(aPlanArt)

                    if firstRecord:
                        radPlanArt.setChecked(True)
                        firstRecord = False

                    radPlanArt.toggled.connect(self.on_anyRadioButton_toggled)
                    lyPlanArt.addWidget(radPlanArt)

                query.finish()

            else:
                self.showQueryError(query)
                query.finish()

        self.fillBereichTree()

    def debug(self,  msg):
        QtGui.QMessageBox.information(None, "Debug",  msg)

    def fillBereichTree(self):
        self.ui.bereich.clear()
        planArt = self.ui.planArt
        lyPlanArt = planArt.layout() # Layout der QGroupBox planArt

        if lyPlanArt.count() > 0:
            whereClause = ""

            for i in range(10): # es gibt nicht mehr als 10 Planarten
                planArtItem = lyPlanArt.itemAt(i)

                if bool(planArtItem):
                    planArtWidget = planArtItem.widget()

                    if planArtWidget.isChecked():

                        if whereClause == "":
                            whereClause = " WHERE \"planart\"=\'"
                        else:
                            whereClause += " OR \"planart\"=\'"

                        whereClause += planArtWidget.objectName() + "\'"
                else:
                    break

            if whereClause != "": # PlanArt ausgewählt
                sQuery = "SELECT plangid, planname, gid, bereichsname FROM \"QGIS\".\"XP_Bereiche\""
                sQuery += whereClause
                sQuery += " ORDER BY planname, bereichsname"
                query = QtSql.QSqlQuery(self.db)
                query.prepare(sQuery)
                query.exec_()

                if query.isActive():
                    lastParentId = -9999

                    while query.next():
                        parentId = query.value(0)
                        parent = query.value(1)
                        childId = query.value(2)
                        child = query.value(3)

                        if parentId != lastParentId:
                            parentItem = QtGui.QTreeWidgetItem([parent])
                            parentItem.parentId = parentId
                            parentItem.childId = None
                            self.ui.bereich.addTopLevelItem(parentItem)
                            lastParentId = parentId

                        childItem = QtGui.QTreeWidgetItem([child])
                        childItem.parentId = None
                        childItem.childId = childId
                        parentItem.addChild(childItem)
                    query.finish()
                else:
                    self.showQueryError(query)
                    query.finish()

    #SLOTS
    #@QtCore.pyqtSlot()
    #def on_bereich_currentItemChanged(self):
    #    self.debug("bereich_currentItemChanged")

    #@QtCore.pyqtSlot()
    #def on_bereich_itemSelectionChanged(self):
    #   self.debug("bereich_itemSelectionChanged")

    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem,  int)
    def on_bereich_itemDoubleClicked(self,  thisItem,  thisColumn):
        if thisItem.childId == None:
            if thisItem.isExpanded():
                self.ui.bereich.collapseItem(thisItem)
            else:
                self.ui.bereich.expandItem(thisItem)
        else:
            self.accept()

    @QtCore.pyqtSlot(   )
    def on_bereich_itemSelectionChanged(self):
        enable = len(self.ui.bereich.selectedItems()) > 0

        for item in self.ui.bereich.selectedItems():
            if item.parentId:
                enable = False
                break

        self.okBtn.setEnabled(enable)

    def on_anyRadioButton_toggled(self,  isChecked):
        self.fillBereichTree()

    def accept(self):
        for item in self.ui.bereich.selectedItems():
            if item.childId:
                self.selected[item.childId] = item.data(0,  0)

        self.done(1)

    def reject(self):
        self.done(0)

    def showQueryError(self, query):
        QtGui.QMessageBox.warning(None, "DBError",  "Database Error: \
            %(error)s \n %(query)s" % {"error": query.lastError().text(),  "query": query.lastQuery()})

