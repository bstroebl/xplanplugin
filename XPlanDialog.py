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
from PyQt4 import QtCore, QtGui, QtSql,  uic
from qgis.core import *
from qgis.gui import *
import qgis.gui
import os
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

class XP_Chooser(QtGui.QDialog, CHOOSER_CLASS):
    '''Ein Dialog mit einem TreeWidget um ein Element auszuwählen, abstrakt'''

    def __init__(self, objektart, db, title):
        QtGui.QDialog.__init__(self)
        self.objektart = objektart
        self.db = db
        self.setupUi(self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.okBtn = self.buttonBox.button(QtGui.QDialogButtonBox.Ok)
        self.okBtn.setEnabled(False)
        self.setWindowTitle(title)
        self.initialize()

    def reject(self):
        self.done(0)

    def showQueryError(self, query):
        QtGui.QMessageBox.warning(None, "DBError",  "Database Error: \
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

                parentItem = QtGui.QTreeWidgetItem([parent])
                parentItem.gid = planGid
                self.layerChooser.addTopLevelItem(parentItem)
                childItem = QtGui.QTreeWidgetItem([nummer])
                childItem.parent = parent
                childItem.gid = planGid
                parentItem.addChild(childItem)
            query.finish()
        else:
            self.showQueryError(query)
            query.finish()

        self.layerChooser.resizeColumnToContents(0)

    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem, int)
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
                    parentItem = QtGui.QTreeWidgetItem([parent])
                    parentItem.geomColumn = None
                    self.layerChooser.addTopLevelItem(parentItem)
                    lastParent = parent

                childItem = QtGui.QTreeWidgetItem([child])
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

    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem, int)
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

class XPlanungConf(QtGui.QDialog,  CONF_CLASS):
    def __init__(self, dbHandler, tools):
        QtGui.QDialog.__init__(self)
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

class BereichsauswahlDialog(QtGui.QDialog, BEREICH_CLASS):
    def __init__(self, iface, db,  multiSelect,  title = "Bereichsauswahl"):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.setWindowTitle(title)
        #self.bereich.currentItemChanged.connect(self.enableOk)
        self.iface = iface
        self.db = db
        self.selected = {} # dict, das id: Name der ausgewählten Bereiche enthält
        self.okBtn = self.buttonBox.button(QtGui.QDialogButtonBox.Ok)
        self.okBtn.setEnabled(False)

        if multiSelect:
            self.bereich.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        self.initializeValues()

    def initializeValues(self):
        # fülle QGroupBox Bereichsauswahl (planArt)
        planArt = self.planArt
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
                            parentItem = QtGui.QTreeWidgetItem([parent])
                            parentItem.parentId = parentId
                            parentItem.childId = None
                            self.bereich.addTopLevelItem(parentItem)
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
            "query": query.lastQuery()}, level=QgsMessageBar.CRITICAL)

class StilauswahlDialog(QtGui.QDialog, STIL_CLASS):
    def __init__(self, iface, aDict, title = "Stilauswahl"):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.setWindowTitle(title)
        #self.bereich.currentItemChanged.connect(self.enableOk)
        self.iface = iface
        self.aDict = aDict
        self.selected = -1 # id des ausgewälten Stils
        self.okBtn = self.buttonBox.button(QtGui.QDialogButtonBox.Ok)
        self.okBtn.setEnabled(False)

        self.initializeValues()

    def initializeValues(self):
        self.fillStilList()

    def debug(self,  msg):
        QtGui.QMessageBox.information(None, "Debug",  msg)

    def fillStilList(self):
        self.stil.clear()

        for key, value in self.aDict.items():
            anItem = QtGui.QListWidgetItem(value)
            anItem.id = key
            self.stil.addItem(anItem)

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
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
            "query": query.lastQuery()}, level=QgsMessageBar.CRITICAL)

class XPNutzungsschablone(QtGui.QDialog, SCHABLONE_CLASS):
    '''Ein Dialog zur Konfiguraton der Nutzungsschablone (BPlan'''

    def __init__(self, nutzungsschablone):
        QtGui.QDialog.__init__(self)

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

class BereichsmanagerDialog(QtGui.QDialog, BEREICHSMANAGER_CLASS):
    def __init__(self, xplanplugin):
        QtGui.QDialog.__init__(self)
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

        for key, value in self.xplanplugin.xpLayers.items():
            try:
                aLayer = value[0]
                aLayerName = aLayer.name()
            except:
                continue

            featuresHaveBeenAdded = value[2]
            bereichsFilterAktiv = aLayer.subsetString() != ""

            if not featuresHaveBeenAdded:
                anItem = QtGui.QListWidgetItem(aLayerName)
                anItem.layer = aLayer
                anItem.bereichsFilterAktiv = bereichsFilterAktiv
                self.layerList.addItem(anItem)

        for key, value in self.xplanplugin.displayLayers.items():
            try:
                aLayer = value[0]
                aLayerName = aLayer.name()
            except:
                continue

            bereichsFilterAktiv = aLayer.subsetString() != ""
            anItem = QtGui.QListWidgetItem(aLayerName)
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

            for key, value in self.xplanplugin.aktiveBereiche.items():
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

    @QtCore.pyqtSlot( QtGui.QListWidgetItem  )
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
