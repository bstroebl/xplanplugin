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
#from subprocess import * #Andere Programme aufrufen
from zutils import zqt
from masterplugin.ZMasterPlugin import ZMasterPlugin
from Ui_Bereichsauswahl import Ui_Bereichsauswahl

class BereichsauswahlDialog(QtGui.QDialog):
    def __init__(self, iface, db, slAktiveBereiche):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_Bereichsauswahl()
        self.ui.setupUi(self)
        self.iface = iface
        self.db = db
        self.slAktiveBereiche = slAktiveBereiche
        self.initializeValues()

    def initializeValues(self):
        # fülle QGroupBox Bereichsauswahl (planArt)
        planArt = self.ui.planArt
        lyPlanArt = planArt.layout() # Layout der QGroupBox planArt
        firstItem = lyPlanArt.itemAt(0)

        loadPlanArt = (not bool(firstItem))

        if not loadPlanArt:
            loadPlanArt = ('planart1' == firstItem.objectName())
            lyPlanArt.removeItem(firstItem)

        if loadPlanArt:
            query = QtSql.QSqlQuery(self.db)
            query.prepare("SELECT DISTINCT \"planArt\"  \
                        FROM \"XP_Basisobjekte\".\"XP_Plaene\" \
                        ORDER BY\"planArt\";")
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

        # model für den Bereichsbaum
        self.fillBereichTree()

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

        sQuery = QtCore.QString("SELECT \"planGid\", \"planName\", gid, name FROM \"XP_Basisobjekte\".\"XP_Bereiche\"")
        sQuery.append(whereClause)
        sQuery.append(" ORDER BY \"planName\", name")
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

    def accept(self):
        self.done(1)

    def showQueryError(self, query):
        QtGui.QMessageBox.warning(None, "Database Error", \
            QtCore.QString("%1 \n %2").arg(query.lastError().text()).arg(query.lastQuery()))

