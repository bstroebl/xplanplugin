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
from Ui_LPlanSettings import Ui_LPlanSettings
from Ui_LP_Objekt import Ui_LP_Objekt


class LPlanSettings(QtGui.QDialog):
    def __init__(self, iface, db, activeBereiche = []):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_LPlanSettings()
        self.ui.setupUi(self)
        # keep reference to QGIS interface
        self.iface = iface

        # keep reference to Fachschale instance
        self.db = db
        self.activeBereiche = activeBereiche
        self.initializeValues()

    def initializeValues(self):
        self.treBereiche = self.ui.bereiche
        self.treBereiche.clear()
        query = QtSql.QSqlQuery(self.db)
        query.prepare("SELECT p.name, b.id, b.name \
                    FROM lplan.lp_bereich b \
                    JOIN lplan.lp_plan p ON b.\"gehoertZuPlan\" = p.id \
                    ORDER BY p.name, b.name;")
        query.exec_()

        if query.isActive():
            lastPlanName = ""

            while query.next():
                aPlanName = query.value(0).toString()
                aBereichId = int(query.value(1).toString())
                checked = QtCore.Qt.Unchecked

                for i in range(len(self.activeBereiche)):
                    if self.activeBereiche[i][0] == aBereichId:
                        checked = QtCore.Qt.Checked
                        break

                aBereichName = query.value(2).toString()

                if lastPlanName != aPlanName:
                    planItem = QtGui.QTreeWidgetItem(QtCore.QStringList(aPlanName))
                    planItem.bereichId = None
                    self.treBereiche.addTopLevelItem(planItem)
                    planItem.setExpanded(True)
                    lastPlanName = aPlanName

                bereichItem = QtGui.QTreeWidgetItem(QtCore.QStringList(aBereichName))
                bereichItem.bereichId = aBereichId
                bereichItem.setCheckState(0, checked)
                planItem.addChild(bereichItem)
            query.finish()

        else:
            self.showQueryError(query)
            query.finish()

    def accept(self):
        self.activeBereiche = []
        for i in range(self.treBereiche.topLevelItemCount()):
            aPlanItem = self.treBereiche.takeTopLevelItem(i)

            for j in range(aPlanItem.childCount()):
                aBereichItem = aPlanItem.child(j)

                if aBereichItem.checkState(0) == 2: #checked
                    self.activeBereiche.append(
                        [aBereichItem.bereichId, aBereichItem.text(0)])

        self.done(1)

    def showQueryError(self, query):
        QtGui.QMessageBox.warning(None, "Database Error", \
            QtCore.QString("%1 \n %2").arg(query.lastError().text()).arg(query.lastQuery()))

class LP_Objekt(QtGui.QDialog):
    def __init__(self, iface, lp_ObjektId, db, forEdit = False):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_LP_Objekt()
        self.ui.setupUi(self)
        # keep reference to QGIS interface
        self.iface = iface
        self.lp_ObjektId = lp_ObjektId
        # keep reference to Fachschale instance
        self.db = db
        self.forEdit = forEdit
        self.okBtn = self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save)
        self.okBtn.setEnabled(self.forEdit)
        self.initializeValues()

    def initializeValues(self):
        self.setWindowTitle("LP_Objekt gid " + str(self.lp_ObjektId))

        if zqt.fillMultiChoice(self.ui.bereich, self.db, \
            "SELECT b.id, b.name || \' (\' || p.name || \')\' as name, \n \
            CASE COALESCE(lnk.\"LP_Objekt_gid\", 0) WHEN 0 THEN 0 ELSE 2 END as checked \n \
            FROM lplan.lp_bereich b JOIN lplan.lp_plan p ON b.\"gehoertZuPlan\" = p.id \n \
            LEFT JOIN (SELECT * FROM lplan.gehoertzulp_bereich WHERE \"LP_Objekt_gid\" = :featureId) lnk \n \
            ON b.id = lnk.\"LP_Bereich_id\" \n \
            ORDER BY p.name, b.name;" ,
            self.lp_ObjektId) == 0:
            self.done(0)

    def accept(self):
        if zqt.saveMultiChoice(self.ui.bereich, self.db,
            "DELETE FROM lplan.gehoertzulp_bereich WHERE \"LP_Objekt_gid\" = :featureId",
            "INSERT INTO lplan.gehoertzulp_bereich(\"LP_Objekt_gid\", \"LP_Bereich_id\") \n \
            VALUES(:featureId, :itemId);", int(self.lp_ObjektId)) == 1:
            self.done(1)
        else:
            self.done(0)



