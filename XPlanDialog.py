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
from qgis.PyQt import QtCore, QtWidgets, QtSql, uic
from qgis.PyQt.QtWidgets import QAction
from builtins import str
from builtins import range
from qgis.core import *
from qgis.gui import *
import qgis.gui
import os
import glob
#from Ui_Bereichsauswahl import Ui_Bereichsauswahl
#from Ui_Stilauswahl import Ui_Stilauswahl
#from Ui_conf import Ui_conf
#from Ui_ObjektartLaden import Ui_ObjektartLaden
#from Ui_Nutzungsschablone import Ui_Nutzungsschablone

CHOOSER_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_ObjektartLaden.ui'))

CONF_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_conf.ui'))

BEREICH_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_Bereichsauswahl.ui'))

STIL_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_Stilauswahl.ui'))

SCHABLONE_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_Nutzungsschablone.ui'))

BEREICHSMANAGER_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_Bereichsmanager.ui'))

REFERENZMANAGER_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_Referenzmanager.ui'))

HOEHENMANAGER_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_Hoehenmanager.ui'))

IMPORT_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_Import.ui'))

class XP_Chooser(QtWidgets.QDialog, CHOOSER_CLASS):
    '''Ein Dialog mit einem TreeWidget um ein Element auszuwählen, abstrakt'''

    def __init__(self, objektart, db, title):
        QtWidgets.QDialog.__init__(self)
        self.objektart = objektart
        self.db = db
        self.setupUi(self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.okBtn = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        self.okBtn.setEnabled(False)
        self.setWindowTitle(title)
        self.initialize()

    def reject(self):
        self.done(0)

    def showQueryError(self, query):
        QtWidgets.QMessageBox.warning(None, "DBError",  "Database Error: \
            %(error)s \n %(query)s" % {"error": query.lastError().text(),
            "query": query.lastQuery()})

class ChoosePlan(XP_Chooser):
    def __init__(self, objektart, db):
        XP_Chooser.__init__(self, objektart, db, u"Plan auswählen")

    def initialize(self):
        sQuery = "select name, gid, nummer \
                FROM \"XP_Basisobjekte\".\"XP_Plaene\" \
                WHERE \"Objektart\" = :objektart \
                ORDER BY name"

        query = QtSql.QSqlQuery(self.db)
        query.prepare(sQuery)
        query.bindValue(":objektart", self.objektart)
        query.exec_()

        if query.isActive():
            while query.next():
                parent = query.value(0)
                planGid = query.value(1)
                nummer = query.value(2)

                parentItem = QtWidgets.QTreeWidgetItem([parent])
                parentItem.gid = planGid
                self.layerChooser.addTopLevelItem(parentItem)
                childItem = QtWidgets.QTreeWidgetItem([nummer])
                childItem.parent = parent
                childItem.gid = planGid
                parentItem.addChild(childItem)
            query.finish()
        else:
            self.xplanplugin.tools.showQueryError(query)
            query.finish()

        self.layerChooser.resizeColumnToContents(0)

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def on_layerChooser_itemDoubleClicked(self, thisItem, thisColumn):
        if thisItem.gid == None:
            if thisItem.isExpanded():
                self.layerChooser.collapseItem(thisItem)
            else:
                self.layerChooser.expandItem(thisItem)
        else:
            self.accept()

    @QtCore.pyqtSlot()
    def on_layerChooser_itemSelectionChanged(self):
        enable = len(self.layerChooser.selectedItems()) > 0

        for item in self.layerChooser.selectedItems():
            if item.gid == None:
                enable = False
                break

        self.okBtn.setEnabled(enable)

    def accept(self):
        self.selection = []

        for item in self.layerChooser.selectedItems():
            if item.gid != None:
                # Info per ausgewähltem Layer
                self.selection.append([item.gid])
        self.done(1)


class ChooseObjektart(XP_Chooser):
    def __init__(self, objektart, db, bereiche = []):
        self.bereiche = bereiche
        XP_Chooser.__init__(self, objektart, db, u"Objektart laden")

    def initialize(self):
        sQuery = "select f_table_schema, f_table_name,f_geometry_column, COALESCE(description,\'\') \
            from geometry_columns \
            LEFT JOIN \
            (SELECT c.oid,nspname,relname,description \
                FROM pg_class c \
                JOIN pg_namespace n ON c.relnamespace = n.oid \
                LEFT JOIN pg_description d ON d.objoid = c.oid \
                WHERE objsubid = 0 or objsubid IS NULL \
            ) cl \
                ON f_table_schema = nspname AND f_table_name = relname \
            WHERE substring(f_table_schema,1,2) = :objektart \
            AND f_table_name NOT LIKE '%_qv' \
            order by f_table_schema, f_table_name"

        query = QtSql.QSqlQuery(self.db)
        query.prepare(sQuery)
        query.bindValue(":objektart", self.objektart)
        query.exec_()

        if query.isActive():
            lastParent = ""

            while query.next():
                parent = query.value(0)
                child = query.value(1)
                geomColumn = query.value(2)
                description = query.value(3)

                if parent != lastParent:
                    parentItem = QtWidgets.QTreeWidgetItem([parent])
                    parentItem.geomColumn = None
                    self.layerChooser.addTopLevelItem(parentItem)
                    lastParent = parent

                childItem = QtWidgets.QTreeWidgetItem([child])
                childItem.parent = parent
                childItem.geomColumn = geomColumn
                childItem.description = description
                parentItem.addChild(childItem)
            query.finish()
        else:
            self.showQueryError(query)
            query.finish()

        self.layerChooser.resizeColumnToContents(0)

        if len(self.bereiche) > 1:
            self.chkBereich.setLabel(u"nur Objekte der aktiven Bereiche laden")

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def on_layerChooser_itemDoubleClicked(self, thisItem, thisColumn):
        if thisItem.geomColumn == None:
            if thisItem.isExpanded():
                self.layerChooser.collapseItem(thisItem)
            else:
                self.layerChooser.expandItem(thisItem)
        else:
            self.accept()

    @QtCore.pyqtSlot()
    def on_layerChooser_itemSelectionChanged(self):
        enable = len(self.layerChooser.selectedItems()) > 0

        for item in self.layerChooser.selectedItems():
            if item.geomColumn == None:
                enable = False
                break

        self.okBtn.setEnabled(enable)

    def accept(self):
        self.selection = []

        for item in self.layerChooser.selectedItems():
            if item.geomColumn != None:
                # Info per ausgewähltem Layer
                self.selection.append([item.parent, # Schema
                    item.data(0, 0), # Tabelle
                    item.geomColumn, # Geometriespalte
                    item.description]) # Beschreibung

        self.withDisplay = self.chkDisplay.isChecked()
        self.aktiveBereiche = self.chkAktiverBereich.isChecked()
        self.done(1)

class XPlanungConf(QtWidgets.QDialog,  CONF_CLASS):
    def __init__(self, dbHandler, tools):
        QtWidgets.QDialog.__init__(self)
        self.dbHandler = dbHandler
        self.tools = tools
        self.setupUi(self)

        s = QtCore.QSettings( "XPlanung", "XPlanung-Erweiterung" )
        self.wasService = s.value( "service", "" )
        self.leSERVICE.setText( self.wasService )
        self.wasHost = s.value( "host", "" )
        self.leHOST.setText( self.wasHost )
        self.lePORT.setText( s.value( "port", "5432" ) )
        self.wasDbName = s.value( "dbname", "" )
        self.leDBNAME.setText( self.wasDbName )
        self.leUID.setText( s.value( "uid", "" ) )
        self.lePWD.setText( s.value( "pwd", "" ) )

        if hasattr(qgis.gui,'QgsAuthConfigSelect'):
            self.authCfgSelect = QgsAuthConfigSelect( self, "postgres" )
            self.tabWidget.insertTab( 1, self.authCfgSelect, "Konfigurationen" )
            authcfg = s.value( "authcfg", "" )

            if authcfg:
                self.tabWidget.setCurrentIndex( 1 )
                self.authCfgSelect.setConfigId( authcfg );

    def accept(self):
        s = QtCore.QSettings( "XPlanung", "XPlanung-Erweiterung" )
        isService = self.leSERVICE.text()
        s.setValue( "service", isService )
        isHost = self.leHOST.text()
        s.setValue( "host", isHost )
        s.setValue( "port", self.lePORT.text() )
        isDbName = self.leDBNAME.text()
        s.setValue( "dbname", isDbName )
        s.setValue( "uid", self.leUID.text() )
        s.setValue( "pwd", self.lePWD.text() )

        if hasattr(qgis.gui,'QgsAuthConfigSelect'):
            s.setValue( "authcfg", self.authCfgSelect.configId() )

        db = self.dbHandler.dbConnect()

        if db != None:
            self.dbHandler.dbDisconnect(db)

            if (self.wasService != "" and self.wasService != isService) or \
                    (self.wasHost != "" and self.wasHost != isHost) or \
                    (self.wasDbName != "" and self.wasDbName != isDbName):
                self.tools.showWarning(u"Nach einem Wechsel der DB-Verbindung wird empfohlen, QGIS neu zu starten")
            self.done(1)

class BereichsauswahlDialog(QtWidgets.QDialog, BEREICH_CLASS):
    def __init__(self, iface, db,  multiSelect,  title = "Bereichsauswahl"):
        QtWidgets.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.setWindowTitle(title)
        #self.bereich.currentItemChanged.connect(self.enableOk)
        self.iface = iface
        self.db = db
        self.selected = {} # dict, das id: Name der ausgewählten Bereiche enthält
        self.okBtn = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        self.okBtn.setEnabled(False)

        if multiSelect:
            self.bereich.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.initializeValues()

    def initializeValues(self):
        # fülle QGroupBox Bereichsauswahl (planArt)
        planArt = self.planArt
        lyPlanArt = planArt.layout() # Layout der QGroupBox planArt
        planArten = []

        for i in range(lyPlanArt.count()):
            planArten.append(lyPlanArt.itemAt(i).widget().text())

        query = QtSql.QSqlQuery(self.db)
        query.prepare("SELECT DISTINCT \"planart\"  \
                    FROM \"QGIS\".\"XP_Bereiche\" \
                    ORDER BY \"planart\";")
        query.exec_()

        if query.isActive():
            firstRecord = True

            while query.next():
                aPlanArt = query.value(0)

                if aPlanArt not in planArten:
                    radPlanArt = QtWidgets.QRadioButton(aPlanArt,  planArt)
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
        QtWidgets.QMessageBox.information(None, "Debug",  msg)

    def fillBereichTree(self):
        self.bereich.clear()
        planArt = self.planArt
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
                            parentItem = QtWidgets.QTreeWidgetItem([parent])
                            parentItem.parentId = parentId
                            parentItem.childId = None
                            self.bereich.addTopLevelItem(parentItem)
                            lastParentId = parentId

                        childItem = QtWidgets.QTreeWidgetItem([child])
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

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem,  int)
    def on_bereich_itemDoubleClicked(self,  thisItem,  thisColumn):
        if thisItem.childId == None:
            if thisItem.isExpanded():
                self.bereich.collapseItem(thisItem)
            else:
                self.bereich.expandItem(thisItem)
        else:
            self.accept()

    @QtCore.pyqtSlot(   )
    def on_bereich_itemSelectionChanged(self):
        enable = len(self.bereich.selectedItems()) > 0

        for item in self.bereich.selectedItems():
            if item.parentId:
                enable = False
                break

        self.okBtn.setEnabled(enable)

    @QtCore.pyqtSlot(   )
    def on_btnRefresh_clicked(self):
        self.initializeValues()

    def on_anyRadioButton_toggled(self,  isChecked):
        self.fillBereichTree()

    def accept(self):
        self.selected = {}
        for item in self.bereich.selectedItems():
            if item.childId:
                self.selected[item.childId] = item.data(0,  0)

        self.done(1)

    def reject(self):
        self.done(0)

    def showQueryError(self, query):
        self.iface.messageBar().pushMessage(
            "DBError",  "Database Error: \
            %(error)s \n %(query)s" % {"error": query.lastError().text(),
            "query": query.lastQuery()}, level=Qgis.Critical)

class StilauswahlDialog(QtWidgets.QDialog, STIL_CLASS):
    def __init__(self, iface, aDict, title = "Stilauswahl"):
        QtWidgets.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.setWindowTitle(title)
        #self.bereich.currentItemChanged.connect(self.enableOk)
        self.iface = iface
        self.aDict = aDict
        self.selected = -1 # id des ausgewälten Stils
        self.okBtn = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        self.okBtn.setEnabled(False)

        self.initializeValues()

    def initializeValues(self):
        self.fillStilList()

    def debug(self,  msg):
        QtWidgets.QMessageBox.information(None, "Debug",  msg)

    def fillStilList(self):
        self.stil.clear()

        for key, value in list(self.aDict.items()):
            anItem = QtWidgets.QListWidgetItem(value)
            anItem.id = key
            self.stil.addItem(anItem)

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def on_stil_itemDoubleClicked(self, thisItem):
        self.selected = thisItem.id
        self.accept()

    @QtCore.pyqtSlot(   )
    def on_stil_itemSelectionChanged(self):
        enable = len(self.stil.selectedItems()) > 0
        self.okBtn.setEnabled(enable)

    def accept(self):
        if self.selected == -1:
            for item in self.stil.selectedItems():
                self.selected = item.id

        self.done(self.selected)

    def reject(self):
        self.done(-1)

    def showQueryError(self, query):
        self.iface.messageBar().pushMessage(
            "DBError",  "Database Error: \
            %(error)s \n %(query)s" % {"error": query.lastError().text(),
            "query": query.lastQuery()}, level=Qgis.Critical)

class XPNutzungsschablone(QtWidgets.QDialog, SCHABLONE_CLASS):
    '''Ein Dialog zur Konfiguraton der Nutzungsschablone (BPlan'''

    def __init__(self, nutzungsschablone):
        QtWidgets.QDialog.__init__(self)

        if nutzungsschablone == None:
            self.nutzungsschablone = [None, None, None, None, None, None]
        else:
            self.nutzungsschablone = nutzungsschablone


        self.setupUi(self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.cbxList = [self.z1s1, self.z1s2, self.z2s1,  self.z2s2,  self.z3s1,  self.z3s2]
        self.initialize()

    def initialize(self):
        thisDict = { \
            None:"",
            "allgArtDerBaulNutzung": u"allgemeine Art d. baul. Nutzung",
            "besondereArtDerBaulNutzung": u"besondere Art d. baul. Nutzung",
            "bauweise":"Bauweise",
            "GFZ":u"Geschoßflächenzahl",
            "GFZmin":u"Geschoßflächenzahl (min)",
            "GFZmax":u"Geschoßflächenzahl (max)",
            "GF":u"Geschoßfläche",
            "GFmin":u"Geschoßfläche (min)",
            "GFmax":u"Geschoßfläche (max)",
            "BMZ":u"Baumassenzahl",
            "BMZmin":u"Baumassenzahl (min)",
            "BMZmax":u"Baumassenzahl (max)",
            "BM":u"Baumasse",
            "BMmin":u"Baumasse (min)",
            "BMmax":u"Baumasse (max)",
            "GRZ":u"Grundflächenzahl",
            "GRZmin":u"Grundflächenzahl (min)",
            "GRZmax":u"Grundflächenzahl (max)",
            "GR":u"Grundfläche",
            "GRmin":u"Grundfläche (min)",
            "GRmax":u"Grundfläche (max)",
            "Z":u"Zahl der Vollgeschosse (Höchstmaß)",
            "Zmin":u"Zahl der Vollgeschosse (min)",
            "Zmax":u"Zahl der Vollgeschosse (max)"}

        keys = [None,  "allgArtDerBaulNutzung",
            "besondereArtDerBaulNutzung",  "bauweise",
            "BM", "BMmin",  "BMmax", "BMZ", "BMZmin",  "BMZmax",
            "GF",  "GFmin", "GFmax", "GFZ", "GFZmin", "GFZmax",
            "GR", "GRmin", "GRmax", "GRZ", "GRZmin", "GRZmax",
            "Z", "Zmin", "Zmax"]

        for i in range(len(self.cbxList)):
            cbx = self.cbxList[i]

            for key in keys:
                value = thisDict[key]
                cbx.addItem( value, key )

            nutzung = self.nutzungsschablone[i]

            for j in range( cbx.count() ):
                if cbx.itemData(j) == nutzung:
                    cbx.setCurrentIndex(j)
                    break

    def reject(self):
        self.done(0)

    def accept(self):
        for i in range(len(self.cbxList)):
            cbx = self.cbxList[i]
            nutzung = cbx.itemData(cbx.currentIndex())
            self.nutzungsschablone[i] = nutzung

        self.done(1)

class BereichsmanagerDialog(QtWidgets.QDialog, BEREICHSMANAGER_CLASS):
    def __init__(self, xplanplugin):
        QtWidgets.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.xplanplugin = xplanplugin
        self.initialize()

    def initialize(self):
        self.setTitle = "Bereichsmanager"
        self.aktiverBereichChanged()
        self.fillLayerList()
        self.on_layerList_itemSelectionChanged()

    def fillLayerList(self):
        self.layerList.clear()

        for key, value in list(self.xplanplugin.xpLayers.items()):
            try:
                aLayer = value[0]
                aLayerName = aLayer.name()
            except:
                continue

            featuresHaveBeenAdded = value[2]
            bereichsFilterAktiv = aLayer.subsetString() != ""

            if not featuresHaveBeenAdded:
                anItem = QtWidgets.QListWidgetItem(aLayerName)
                anItem.layer = aLayer
                anItem.bereichsFilterAktiv = bereichsFilterAktiv
                self.layerList.addItem(anItem)

        for key, value in list(self.xplanplugin.displayLayers.items()):
            try:
                aLayer = value[0]
                aLayerName = aLayer.name()
            except:
                continue

            bereichsFilterAktiv = aLayer.subsetString() != ""
            anItem = QtWidgets.QListWidgetItem(aLayerName)
            anItem.layer = aLayer
            anItem.bereichsFilterAktiv = bereichsFilterAktiv
            self.layerList.addItem(anItem)

        self.layerList.sortItems()

    def aktiverBereichChanged(self):
        if len(self.xplanplugin.aktiveBereiche) == 0:
            grpTitle = "aktiver Bereich"
            lblText = "kein aktiver Bereich"
            lblToolTip = "z.Zt. ist kein Bereich aktiv"
            aendernToolTip = u"Bereich aktivieren"
            deaktToolTip = ""
        else:
            lblText = ""

            if len(self.xplanplugin.aktiveBereiche) == 1:
                grpTitle = "aktiver Bereich"
                lblToolTip = "z.Zt. aktiver Bereich"
                aendernToolTip = u"aktiven Bereich ändern"
                deaktToolTip = "aktiven Bereich deaktivieren"
            else: # > 1
                grpTitle = "aktive Bereiche"
                lblToolTip = "z.Zt. aktive Bereiche"
                aendernToolTip = u"aktive Bereiche ändern"
                deaktToolTip = "aktive Bereiche deaktivieren"

            for key, value in list(self.xplanplugin.aktiveBereiche.items()):
                if lblText == "":
                    lblText = value
                else:
                    lblText += ", \n" + value

        self.grpAktiverBereich.setTitle(grpTitle)
        self.lblAktiverBereich.setText(lblText)
        self.lblAktiverBereich.setToolTip(lblToolTip)
        self.btnAktiverBereichAendern.setToolTip(aendernToolTip)
        self.btnAktiverBereichDeaktivieren.setEnabled(len(self.xplanplugin.aktiveBereiche) > 0)
        self.btnAktiverBereichDeaktivieren.setToolTip(deaktToolTip)
        self.on_layerList_itemSelectionChanged()

    @QtCore.pyqtSlot( QtWidgets.QListWidgetItem  )
    def on_layerList_itemDoubleClicked(self, anItem):
        self.xplanplugin.aktiveBereicheFiltern(anItem.layer)
        anItem.bereichsFilterAktiv = True
        self.on_layerList_itemSelectionChanged()

    @QtCore.pyqtSlot(   )
    def on_btnAktiverBereichAendern_clicked(self):
        if self.xplanplugin.aktiveBereicheFestlegen():
            self.aktiverBereichChanged()

    @QtCore.pyqtSlot(   )
    def on_btnAktiverBereichDeaktivieren_clicked(self):
        self.xplanplugin.aktiveBereiche = {}
        self.aktiverBereichChanged()

    @QtCore.pyqtSlot(   )
    def on_btnFilter_clicked(self):
        for anItem in self.layerList.selectedItems():
            self.xplanplugin.aktiveBereicheFiltern(anItem.layer)
            anItem.bereichsFilterAktiv = True

        self.on_layerList_itemSelectionChanged()

    @QtCore.pyqtSlot(   )
    def on_btnFilterEntfernen_clicked(self):
        for anItem in self.layerList.selectedItems():
            self.xplanplugin.layerFilterRemove(anItem.layer)
            anItem.bereichsFilterAktiv = False

        self.on_layerList_itemSelectionChanged()

    @QtCore.pyqtSlot(   )
    def on_layerList_itemSelectionChanged(self):
        enableEntfernen = False

        for anItem in self.layerList.selectedItems():
            if anItem.bereichsFilterAktiv:
                enableEntfernen = True
                break

        self.btnFilterEntfernen.setEnabled(enableEntfernen)

        if len(self.xplanplugin.aktiveBereiche) > 0:
            self.btnFilter.setEnabled(len(self.layerList.selectedItems()) > 0)
        else:
            self.btnFilter.setEnabled(False)

    def accept(self):
        if self.selected == -1:
            for item in self.stil.selectedItems():
                self.selected = item.id

        self.done(self.selected)
        


class HoehenmanagerDialog(QtWidgets.QDialog, HOEHENMANAGER_CLASS):
    
    class featureSelector(QgsMapToolIdentifyFeature):
        
        def __init__(self, canvas, layer, manager):
            super().__init__(canvas)
            self.layer = layer
            self.manager = manager
        
        def canvasReleaseEvent(self, e):
            super().canvasReleaseEvent(e)
            ident_result = self.identify(
                e.pixelPoint().x(),
                e.pixelPoint().y(),
                mode = self.IdentifyMode(3),
                layerList= [self.layer]
            )
            if len(ident_result)>0:
                sfeature = ident_result[0].mFeature
                self.manager.selectedFeature = sfeature
                self.featureIdentified.emit(sfeature)
    
    def __init__(self, xplanplugin, hoehenLayer):
        QtWidgets.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.xplanplugin = xplanplugin
        self.hoehenLayer = hoehenLayer
        self.selectedFeature = None
        self.relator = None
        
        #canvas
        refSchema = "BP_Basisobjekte"
        refTable = "BP_Flaechenobjekte" #this is a view for qgis!
        if list(self.xplanplugin.aktiveBereicheGids())==[]:
            filter=''
        else:
            filter = self.xplanplugin.getBereichFilter(refSchema, refTable, self.xplanplugin.aktiveBereicheGids())
        self.flaechenobjekteLayer, isView = self.xplanplugin.loadTable(
            refSchema, 
            refTable,  
            'position',
            displayName = refTable + " (für Höheneditor - temporär)", 
            filter = filter
        )
        self.canvas.setExtent(self.flaechenobjekteLayer.extent())
        self.canvas.setLayers([self.flaechenobjekteLayer])
        # QgsProject.instance().removeMapLayer(flaechenobjekteLayer)
        self.canvas.setCanvasColor(QtCore.Qt.white) #does this work like this?
        self.canvas.enableAntiAliasing(True)
        
        # create the map tools
        self.actionZoomIn = QAction("Zoom in", self)
        self.actionZoomIn.triggered.connect(self.zoomIn)
        self.toolZoomIn = QgsMapToolZoom(self.canvas, False) # false = in
        self.toolZoomIn.setAction(self.actionZoomIn)
        
        self.actionZoomOut = QAction("Zoom out", self)
        self.actionZoomOut.triggered.connect(self.zoomOut)
        self.toolZoomOut = QgsMapToolZoom(self.canvas, True) # true = out
        self.toolZoomOut.setAction(self.actionZoomOut)
        
        self.actionPan = QAction("Pan", self)
        self.actionPan.triggered.connect(self.pan)
        self.toolPan = QgsMapToolPan(self.canvas)
        self.toolPan.setAction(self.actionPan)
        
        self.toolIdentify = self.featureSelector(self.canvas, self.flaechenobjekteLayer, self)
        self.toolIdentify.featureIdentified.connect(self.showRelatedHoehen)
        
        self.identify()
        #!canvas
        
        self.hoehen.customContextMenuRequested.connect(self.on_hoehen_customContextMenuRequested)
        self.hoehen.contextMenu = QtWidgets.QMenu(self.hoehen)
        
        self.editAction = QtWidgets.QAction("Bearbeiten", self.hoehen.contextMenu)
        self.editAction.triggered.connect(self.editHoehen)
        self.hoehen.contextMenu.addAction(self.editAction)
        
        self.removeAction = QtWidgets.QAction(u"Löschen", self.hoehen.contextMenu)
        self.removeAction.triggered.connect(self.removeHoehen)
        self.hoehen.contextMenu.addAction(self.removeAction)
        
        self.newAction = QtWidgets.QAction("Neue externeHoehen", self.hoehen.contextMenu)
        self.newAction.triggered.connect(self.newHoehen)
        self.hoehen.contextMenu.addAction(self.newAction)
        
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(self.initialize)
        
        self.initialize()
        
    def zoomIn(self):
        self.canvas.setMapTool(self.toolZoomIn)

    def zoomOut(self):
        self.canvas.setMapTool(self.toolZoomOut)

    def pan(self):
        self.canvas.setMapTool(self.toolPan)
    
    def identify(self):
        self.canvas.setMapTool(self.toolIdentify)
        
    def showRelatedHoehen(self, sfeature=None):
        """Code called when the feature is selected by the user"""
        if sfeature is None: sfeature =self.selectedFeature
        self.selectedFeature = sfeature
        self.flaechenobjekteLayer.deselect(self.flaechenobjekteLayer.selectedFeatureIds())
        self.flaechenobjekteLayer.select([sfeature.id()]) #id is correct
        self.fillHoehen([sfeature['gid']]) #gid is correct
    
    def unselectFeature(self):
        self.flaechenobjekteLayer.removeSelection()
        
    def initialize(self):
        self.txlFilter.setText("")
        #self.btnFilter.setEnabled(False)
        self.setTitle = "Hoehenmanager"
        self.fillHoehen()
        
    def getRelatorTable(self):
        sql = """ 
SELECT 
    a.id,
    --a.*, 
    b."XP_Objekt_gid", 
    --c.uuid, c.gml_id, 
    --d.position as geom_poly, 
    --e.position as geom_line, 
    --f.position as geom_point, 
    g."gehoertZuBereich"--, 
    --h."nummer" as nr_bereich, h."name" as name_bereich 
FROM 
(select * from "XP_Sonstiges"."XP_Hoehenangabe") a
    right join 
(select * from "XP_Basisobjekte"."XP_Objekt_hoehenangabe") b
on a.id=b.hoehenangabe
    left join
(select * from "XP_Basisobjekte"."XP_Objekt") c
on b."XP_Objekt_gid"=c.gid
--    left join
--(select * from "BP_Basisobjekte"."BP_Flaechenobjekte") d
--on c.gid=d.gid
--    left join
--(select * from "BP_Basisobjekte"."BP_Linienobjekte") e
--on c.gid=e.gid
--    left join
--(select * from "BP_Basisobjekte"."BP_Punktobjekte") f
--on c.gid=f.gid
    left join
(select * from "XP_Basisobjekte"."XP_Objekt_gehoertZuBereich") g
on c.gid=g."XP_Objekt_gid"
    left join 
(select gid, nummer, name from "XP_Basisobjekte"."XP_Bereich") h
on g."gehoertZuBereich"=h.gid
"""
        addendum = """where "gehoertZuBereich" = ANY( {}::int[] );
        """.format("'" + str(tuple(self.xplanplugin.aktiveBereicheGids())).replace('(','{').rsplit(',',1)[0] + "}'")
        if (len(self.xplanplugin.aktiveBereicheGids())>0):
            sql = sql + addendum
        # self.showError(sql)
        
        if (self.relator is None):    
            query = QtSql.QSqlQuery(self.xplanplugin.db)
            query.prepare(sql)
            query.exec_()
    
            if query.isActive():
                table = {}
                lastId = -1
                while query.next(): # returns false when all records are done
                    rec_dict = {}
                    for i in range(query.record().count()):
                        rec_dict[query.record().field(i).name()] = query.record().value(i)
                    table[query.record().value("id")] = rec_dict
                    lastId = query.record().value("id")
    
                query.finish()
                self.relator = table, lastId
                return self.relator
            else:
                self.xplanplugin.tools.showQueryError(query)
                return None
        else:
            # self.showError('relator is loaded from cache')
            return self.relator
        
    def fillHoehen(self, xp_objekt_gids =[]):
        self.hoehen.clear()
        filter = self.txlFilter.text()
        
        if filter == "":
            self.hoehenLayer.removeSelection()
            self.hoehenLayer.invertSelection()
        else:
            abfrage = "\"id\" like '%" + filter + "%'"
            self.hoehenLayer.selectByExpression(abfrage)
        
        try:
            relator, lastId = self.getRelatorTable()
        except TypeError as e:
            self.showError('An TypeError occured unexpected. Please fix this!')
            relator = self.getRelatorTable()
            relator_selector = {}
        else:
            if (xp_objekt_gids==[]):
                relator_selector = relator
            else:
                relator_selector = {k: v for k, v in relator.items() if v['XP_Objekt_gid'] in xp_objekt_gids}
        
        for i, aFeat in enumerate(self.hoehenLayer.selectedFeatures()):
            # self.showError('feat nr: ' + str(i))
            # self.showError('id: ' + str(aFeat["id"]))
            if aFeat.id() > 0 and aFeat["id"] in relator_selector.keys():
                # if xp_objekt_gids!=[]: self.showError('found id: ' + str(aFeat["id"]))
                anItem = QtWidgets.QListWidgetItem(str( ( aFeat["id"], aFeat['hoehenbezug'], aFeat['bezugspunkt'], (aFeat['h'],aFeat['hMin'],aFeat['hMax'],aFeat['hZwingend']))))
                anItem.feature = aFeat
                self.hoehen.addItem(anItem)
        self.hoehen.sortItems()
        
    def editFeature(self, thisFeature):
        # self.showError(str(thisFeature.id()))
        # self.showError(str(thisFeature.attributes()))
        # self.showError(str(self.hoehenLayer))
        self.xplanplugin.app.xpManager.showFeatureForm(self.hoehenLayer, thisFeature)
        self.showRelatedHoehen()
        
    def highlightFeature(self, thisFeature):
        pass
        
    def editHoehen(self):
        self.editFeature(self.hoehen.currentItem().feature)

    def newHoehen(self):
        if self.xplanplugin.db == None:
            self.showError(u"Es ist keine Datenbank verbunden")
            self.done(0)
        else:
            if not (self.selectedFeature is None):
                
                firstItem = next(self.hoehenLayer.getFeatures())
                self.showError(str(dict(firstItem.attributeMap())))
                newFeat = QgsFeature(firstItem.fields(),-1)
                
                if self.xplanplugin.tools.setEditable(self.hoehenLayer, True, self.xplanplugin.iface):
                    self.hoehenLayer.addFeature(newFeat)
                    if self.hoehenLayer.commitChanges():
                        maxIdHoehe = self.xplanplugin.tools.getMaxGid(self.xplanplugin.db, "XP_Sonstiges",
                            "XP_Hoehenangabe", pkFieldName = "id")
                        expr = '"id" >= ' + str(maxIdHoehe)
                        self.hoehenLayer.selectByExpression(expr)
                        
                        if len(self.hoehenLayer.selectedFeatures()) == 1:
                            thisFeat = self.hoehenLayer.selectedFeatures()[0]
                            self.editFeature(thisFeat)
                        
                        
                        refSchema = "XP_Basisobjekte"
                        refTable = "XP_Objekt_hoehenangabe"
                        hoehenAngLayer = self.xplanplugin.getLayerForTable(refSchema, refTable)
                        
                        if hoehenAngLayer != None:
                            maxId = self.xplanplugin.tools.getMaxGid(self.xplanplugin.db, refSchema,
                                refTable, pkFieldName = "XP_Objekt_gid")
                                
                            if not (maxId is None):
                                newLink = self.xplanplugin.tools.createFeature(hoehenAngLayer)
                                newLink.setAttribute("XP_Objekt_gid", self.selectedFeature['gid'])
                                newLink.setAttribute("hoehenangabe", thisFeat['id'])
                        
                                if self.xplanplugin.tools.setEditable(hoehenAngLayer, True, self.xplanplugin.iface):
                                    if hoehenAngLayer.addFeature(newLink):
                                        
                                        if hoehenAngLayer.commitChanges(): ## THIS doesn't work, because if using XP_Objekt_hohenangabe, 
                                                                           ## the related XP_Objekt must be known (and associated) already. 
                                                                           ## So wee need a chooser dialog in between 
                                                                           ## ("click the XP_Object you like to relate to"?)
                                            hoehenAngLayer.reload()
                                            expr = '"XP_Objekt_gid" >= ' + str(maxId)
                                            hoehenAngLayer.selectByExpression(expr)
            
                                            if len(hoehenAngLayer.selectedFeatures()) == 1:
                                                linkFeat = hoehenAngLayer.selectedFeatures()[0]
                                                self.editFeature(linkFeat)
                                            else:
                                                self.showError(u"Neues Feature nicht gefunden! " + expr)
                                    else:
                                        self.showError(u"Kann in Tabelle " + refSchema + "." + refTable + \
                                            u" kein Feature einfügen!")
                                else:
                                    self.showError(u"Zuerst muss ein Bezugsobjekt auf der Karte ausgewählt werden!")
    
    def removeHoehen(self):
        feat2Remove = self.hoehen.currentItem().feature

        if self.xplanplugin.tools.setEditable(self.hoehenLayer, True, self.xplanplugin.iface):
            if self.hoehenLayer.deleteFeature(feat2Remove.id()):
                if self.hoehenLayer.commitChanges():
                    self.showRelatedHoehen()
                else:
                    self.showError(u"Konnte Änderungen nicht speichern")
            else:
                self.showError(u"Konnte Hoehen nicht löschen")
        else:
            self.showError(u"Kann Layer " + self.hoehenLayer.name() + " nicht editieren")

    def showError(self, msg):
        self.xplanplugin.tools.showError(msg)

    @QtCore.pyqtSlot( str )
    def on_txlFilter_textChanged(self, currentText):
        self.btnFilter.setEnabled(len(currentText) > 0)

    @QtCore.pyqtSlot(  )
    def on_txlFilter_returnPressed(self):
        if len(self.txlFilter.text()) > 3:
            self.btnFilter.click()

    @QtCore.pyqtSlot(  )
    def on_btnFilter_clicked(self):
        self.fillHoehen()

    @QtCore.pyqtSlot( QtWidgets.QListWidgetItem )
    def on_hoehen_itemDoubleClicked(self, clickedItem):
        self.editFeature(clickedItem.feature)
        
    @QtCore.pyqtSlot( QtWidgets.QListWidgetItem )
    def on_hoehen_itemClicked(self, clickedItem):
        self.highlightFeature(clickedItem.feature)

    @QtCore.pyqtSlot( QtCore.QPoint)
    def on_hoehen_customContextMenuRequested(self, atPoint):
        clickedItem = self.hoehen.itemAt(atPoint)
        self.editAction.setVisible(clickedItem != None)
        self.removeAction.setVisible(clickedItem != None)

        if clickedItem != None:
            self.hoehen.setCurrentItem(clickedItem)

        self.hoehen.contextMenu.resize(self.hoehen.contextMenu.sizeHint())
        self.hoehen.contextMenu.popup(self.hoehen.mapToGlobal(QtCore.QPoint(atPoint)))

    @QtCore.pyqtSlot()
    def reject(self):
        self.done(0)

class ReferenzmanagerDialog(QtWidgets.QDialog, REFERENZMANAGER_CLASS):
    def __init__(self, xplanplugin, referenzenLayer):
        QtWidgets.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.xplanplugin = xplanplugin
        self.referenzenLayer = referenzenLayer
        self.referenzen.customContextMenuRequested.connect(self.on_referenzen_customContextMenuRequested)
        self.referenzen.contextMenu = QtWidgets.QMenu(self.referenzen)
        self.editAction = QtWidgets.QAction("Bearbeiten", self.referenzen.contextMenu)
        self.editAction.triggered.connect(self.editReferenz)
        self.referenzen.contextMenu.addAction(self.editAction)
        self.removeAction = QtWidgets.QAction(u"Löschen", self.referenzen.contextMenu)
        self.removeAction.triggered.connect(self.removeReferenz)
        self.referenzen.contextMenu.addAction(self.removeAction)
        self.newAction = QtWidgets.QAction("Neue externeReferenz", self.referenzen.contextMenu)
        self.newAction.triggered.connect(self.newReferenz)
        self.referenzen.contextMenu.addAction(self.newAction)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(self.initialize)
        self.initialize()

    def initialize(self):
        self.txlFilter.setText("")
        #self.btnFilter.setEnabled(False)
        self.setTitle = "Referenzmanager"
        self.fillReferenzen()

    def fillReferenzen(self):
        self.referenzen.clear()
        filter = self.txlFilter.text()

        if filter == "":
            self.referenzenLayer.removeSelection()
            self.referenzenLayer.invertSelection()
        else:
            abfrage = "\"referenzName\" like '%" + filter + "%'"
            self.referenzenLayer.selectByExpression(abfrage)

        for aFeat in self.referenzenLayer.selectedFeatures():
            if aFeat.id() > 0:
                anItem = QtWidgets.QListWidgetItem(aFeat["referenzName"])
                anItem.feature = aFeat
                self.referenzen.addItem(anItem)

        self.referenzen.sortItems()

    def editFeature(self, thisFeature):
        self.xplanplugin.app.xpManager.showFeatureForm(self.referenzenLayer, thisFeature)
        self.fillReferenzen()

    def editReferenz(self):
        self.editFeature(self.referenzen.currentItem().feature)

    def newReferenz(self):
        if self.xplanplugin.db == None:
            self.showError(u"Es ist keine Datenbank verbunden")
            self.done(0)
        else:
            refSchema = "XP_Basisobjekte"
            refTable = "XP_SpezExterneReferenz"
            extRefLayer = self.xplanplugin.getLayerForTable(refSchema, refTable)

            if extRefLayer != None:
                maxId = self.xplanplugin.tools.getMaxGid(self.xplanplugin.db, refSchema,
                    refTable, pkFieldName = "id")

                if maxId != None:
                    newFeat = self.xplanplugin.tools.createFeature(extRefLayer)
                    if self.xplanplugin.tools.setEditable(extRefLayer, True, self.xplanplugin.iface):
                        if extRefLayer.addFeature(newFeat):
                            if extRefLayer.commitChanges():
                                extRefLayer.reload()
                                self.referenzenLayer.reload()
                                expr = "id > " + str(maxId)
                                self.referenzenLayer.selectByExpression(expr)

                                if len(self.referenzenLayer.selectedFeatures()) == 1:
                                    thisFeat = self.referenzenLayer.selectedFeatures()[0]
                                    self.editFeature(thisFeat)
                                else:
                                    self.showError(u"Neues Feature nicht gefunden! " + expr)
                        else:
                            self.showError(u"Kann in Tabelle " + refSchema + "." + refTable + \
                                u" kein Feature einfügen!")

    def removeReferenz(self):
        feat2Remove = self.referenzen.currentItem().feature

        if self.xplanplugin.tools.setEditable(self.referenzenLayer, True, self.xplanplugin.iface):
            if self.referenzenLayer.deleteFeature(feat2Remove.id()):
                if self.referenzenLayer.commitChanges():
                    self.fillReferenzen()
                else:
                    self.showError(u"Konnte Änderungen nicht speichern")
            else:
                self.showError(u"Konnte Referenz nicht löschen")
        else:
            self.showError(u"Kann Layer " + self.referenzenLayer.name() + " nicht editieren")

    def showError(self, msg):
        self.xplanplugin.tools.showError(msg)

    @QtCore.pyqtSlot( str )
    def on_txlFilter_textChanged(self, currentText):
        self.btnFilter.setEnabled(len(currentText) > 0)

    @QtCore.pyqtSlot(  )
    def on_txlFilter_returnPressed(self):
        if len(self.txlFilter.text()) > 3:
            self.btnFilter.click()

    @QtCore.pyqtSlot(  )
    def on_btnFilter_clicked(self):
        self.fillReferenzen()

    @QtCore.pyqtSlot( QtWidgets.QListWidgetItem )
    def on_referenzen_itemDoubleClicked(self, clickedItem):
        self.editFeature(clickedItem.feature)

    @QtCore.pyqtSlot( QtCore.QPoint)
    def on_referenzen_customContextMenuRequested(self, atPoint):
        clickedItem = self.referenzen.itemAt(atPoint)
        self.editAction.setVisible(clickedItem != None)
        self.removeAction.setVisible(clickedItem != None)

        if clickedItem != None:
            self.referenzen.setCurrentItem(clickedItem)

        self.referenzen.contextMenu.resize(self.referenzen.contextMenu.sizeHint())
        self.referenzen.contextMenu.popup(self.referenzen.mapToGlobal(QtCore.QPoint(atPoint)))

    @QtCore.pyqtSlot()
    def reject(self):
        self.done(0)

class ImportDialog(QtWidgets.QDialog, IMPORT_CLASS):
    def __init__(self, xplanplugin):
        QtWidgets.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.xplanplugin = xplanplugin
        self.neuString = "neues Schema"
        self.cbxSchema.setToolTip("\"" + self.neuString + "\" legt " + \
            u"ein neues Schema an\n" + \
            u"und importiert die GML-Datei in dieses Schema.\n" + \
            u"Ist \"Überschreiben\" angehakt, wird ein " +\
            u"eventuell vorhandenes \ngleichnamiges " + \
            u"Schema gelöscht. \n" + \
            u"Wird ein vorhandenes Schema ausgewählt, so wird angenommen,\n" + \
            u"dass die GML-Datei bereits dorthin importiert wurde,\ndie Übernahme in " + \
            u"die Zieltabellen in der Datenbank \naber nicht funktioniert hat.")
        self.versions = {}
        self.initialize()
        self.txlDatei.textChanged.connect(self.enableOk)
        self.txlS_SRS.textChanged.connect(self.enableOk)
        self.enableOk()
        #self.cbxVersion.currentIndexChanged.connect(self.enableOk)
        #self.cbxSchema.currentIndexChanged.connect(self.enableOk)

    def __getSchemas(self):
        '''
        Abfrage, die alle User-erzeugten nicht-Xplanungs-Schemas in der DB liefert
        '''
        schemaSql = "SELECT nspname from pg_namespace \
            WHERE nspname not in ('information_schema', 'pg_catalog', 'public', 'QGIS') \
            AND nspname not like 'pg_toast%' \
            AND nspname not like 'pg_temp_%' \
            AND nspname not like 'BP_%' \
            AND nspname not like 'FP_%' \
            AND nspname not like 'LP_%' \
            AND nspname not like 'RP_%'\
            AND nspname not like 'SO_%' \
            AND nspname not like 'XP_%';"

        schemaQuery = QtSql.QSqlQuery(self.xplanplugin.db)
        schemaQuery.prepare(schemaSql)
        schemaQuery.exec_()
        schemas = []

        if schemaQuery.isActive():
            while schemaQuery.next():
                schemas.append(schemaQuery.value(0))
            schemaQuery.finish()
            return schemas
        else:
            self.xplanplugin.tools.showQueryError(schemaQuery)
            self.reject()

    def initialize(self):
        s = QtCore.QSettings( "XPlanung", "XPlanung-Erweiterung" )
        s.beginGroup("import")
        datei = ( s.value( "datei", "" ) )
        s_srs = ( s.value( "s_srs", "" ) )
        t_srs = ( s.value( "t_srs", "" ) )
        xsd = ( s.value( "xsd", "" ) )
        importSchema = ( s.value( "importSchema", "" ) )
        neuesSchema =  ( s.value( "neuesSchema", "" ) )
        schritt1 =  ( bool(int(s.value( "schritt1", "1" ) )))
        schritt2 =  ( bool(int(s.value( "schritt2", "1" ) )))
        ueberschreiben =  ( bool(int(s.value( "ueberschreiben", "1" ) )))
        s.endGroup()

        self.txlDatei.setText(datei)
        self.txlS_SRS.setText(s_srs)
        self.txlT_SRS.setText(t_srs)
        self.chkSchritt1.setChecked(schritt1)
        self.frmSchritt1.setEnabled(schritt1)
        self.chkSchritt2.setChecked(schritt2)
        self.chkUeberschreiben.setChecked(ueberschreiben)

        xsdPath = os.path.abspath(os.path.dirname(__file__) + '/schema')
        versions = glob.glob(xsdPath + "/*")
        showIndex = 0

        for i in range(len(versions)):
            v = versions[i]
            versionNumber = v[(len(v) - 3):]
            self.versions[versionNumber] = v
            self.cbxVersion.addItem(versionNumber)

            if xsd.find(v) != -1:
                showIndex = i

        self.cbxVersion.setCurrentIndex(showIndex)

        schemas = self.__getSchemas()
        schemas = [self.neuString] + schemas
        self.cbxSchema.addItems(schemas)
        foundIndex = self.cbxSchema.findText(importSchema)

        if foundIndex == -1:
            foundIndex = 0

        self.cbxSchema.setCurrentIndex(foundIndex)

        if self.cbxSchema.currentText == self.neuString:
            self.txlSchema.setText(neuesSchema)

    def chooseEPSG(self):
        sel = QgsProjectionSelectionDialog()
        result = sel.exec_()

        if result == 0:
            return None
        else:
            return sel.crs().authid()

    def enableTxlSchema(self):
        if self.cbxSchema.currentText() == self.neuString:
            self.txlSchema.setEnabled(True)
            self.chkUeberschreiben.setEnabled(True)
            self.txlSchema.setFocus()
            self.txlSchema.setCursorPosition(0)
        else:
            self.txlSchema.setEnabled(False)
            self.chkUeberschreiben.setEnabled(False)

    def enableOk(self):
        okBtn = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        schritt1 = self.chkSchritt1.isChecked()
        schritt2 = self.chkSchritt2.isChecked()
        neuesSchema = (self.cbxSchema.currentText() == self.neuString)

        schemaOk = ((neuesSchema and self.txlSchema.text().strip() not in ["", "public"]) or\
            not neuesSchema)

        doEnable = False #ini

        if schritt1:
            doEnable = (schemaOk and self.txlDatei.text().strip() != "" and \
                self.txlS_SRS.text().strip() != "")
        else:
            if schritt2:
                doEnable = (not neuesSchema)

        okBtn.setEnabled(doEnable)

    @QtCore.pyqtSlot(int)
    def on_cbxSchema_currentIndexChanged(self, index):
        if self.cbxSchema.currentText == self.neuString:
            self.txlSchema.setText("")

        self.enableTxlSchema()
        self.enableOk()

    @QtCore.pyqtSlot(int)
    def on_chkSchritt1_stateChanged(self, newState):
        schritt1 = self.chkSchritt1.isChecked()
        self.frmSchritt1.setEnabled(schritt1)
        self.enableOk()

    @QtCore.pyqtSlot(int)
    def on_chkSchritt2_stateChanged(self, newState):
        self.enableOk()

    @QtCore.pyqtSlot()
    def on_btnDatei_clicked(self):
        wasFileName = self.txlDatei.text()

        if  wasFileName != "":
            usePath = os.path.abspath(os.path.dirname(wasFileName))
        else:
            usePath = os.path.abspath(os.path.dirname("$HOME"))

        fileName, selFilter = QtWidgets.QFileDialog.getOpenFileName( \
            caption = u"XPlanGML-Datei wählen",
            directory = usePath, filter = "GML-Dateien (*.gml)")

        if fileName != "":
            self.txlDatei.setText(fileName)

    @QtCore.pyqtSlot()
    def on_btnS_SRS_clicked(self):
        epsg = self.chooseEPSG()

        if epsg != None:
            self.txlS_SRS.setText(epsg)

    @QtCore.pyqtSlot()
    def on_btnT_SRS_clicked(self):
        epsg = self.chooseEPSG()

        if epsg != None:
            self.txlT_SRS.setText(epsg)

    @QtCore.pyqtSlot(str)
    def on_txlSchema_textChanged(self, newText):
        self.enableOk()

    @QtCore.pyqtSlot()
    def accept(self):
        datei = self.txlDatei.text()
        s_srs = self.txlS_SRS.text()
        version = self.versions[self.cbxVersion.currentText()] + "/XPlanGML.xsd"
        t_srs = self.txlT_SRS.text()

        if t_srs == "":
            t_srs = s_srs

        schema = self.cbxSchema.currentText()

        if schema == self.neuString:
            neuesSchema = "1"
            schema = self.txlSchema.text()
        else:
            neuesSchema = "0"

        schritt1 = self.chkSchritt1.isChecked()
        schritt2 = self.chkSchritt2.isChecked()
        ueberschreiben = self.chkUeberschreiben.isChecked()

        s = QtCore.QSettings( "XPlanung", "XPlanung-Erweiterung" )
        s.beginGroup("import")
        s.setValue( "datei", datei )
        s.setValue( "s_srs", s_srs )
        s.setValue( "t_srs", t_srs )
        s.setValue( "xsd", version )
        s.setValue( "importSchema", schema )
        s.setValue( "neuesSchema", neuesSchema )
        s.setValue( "schritt1", str(int(schritt1) ))
        s.setValue( "schritt2", str(int(schritt2) ))
        s.setValue( "ueberschreiben", str(int(ueberschreiben) ))
        s.endGroup()

        self.params = {}
        self.params["datei"] = datei
        self.params["s_srs"] = s_srs
        self.params["t_srs"] = t_srs
        self.params["xsd"] = version
        self.params["importSchema"] = schema
        self.params["neuesSchema"] = neuesSchema
        self.params["schritt1"] = schritt1
        self.params["schritt2"] = schritt2
        self.params["ueberschreiben"] = ueberschreiben
        self.done(1)

    @QtCore.pyqtSlot()
    def reject(self):
        self.done(0)
