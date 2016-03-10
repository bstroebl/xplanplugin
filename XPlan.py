﻿# -*- coding: utf-8 -*-
"""
/***************************************************************************
XPlan
A QGIS plugin
Fachschale XPlan für XPlanung
                             -------------------
begin                : 2013-03-08
copyright            : (C) 2013 by Bernhard Stroebl, KIJ/DV
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
from DataDrivenInputMask.ddattribute import DdTable
import sys
from HandleDb import DbHandler
from XPTools import XPTools
from XPlanDialog import XPlanungConf
from XPlanDialog import ChooseObjektart

class XpError(object):
    '''General error'''
    def __init__(self, value, iface = None):
        self.value = value

        if iface == None:
            QtGui.QMessageBox.warning(None, "XPlanung", value, duration = 10)
        else:
            iface.messageBar().pushMessage("XPlanung", value,
                level=QgsMessageBar.CRITICAL)
    def __str__(self):
        return repr(self.value)

class XPlan():
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.standardName = u"XP-Standard"
        self.simpleStyleName = "einfarbig"
        self.tmpAct = QtGui.QAction(self.iface.mainWindow()) # eine nicht benötigte QAction
        self.app = QgsApplication.instance()
        self.dbHandler = DbHandler(self.iface)
        self.db = None
        self.tools = XPTools(self.iface, self.standardName, self.simpleStyleName)
        self.aktiveBereiche = []
        self.addedGeometries = {}
        self.layerLayer = None
        # Liste der implementierten Fachschemata
        self.implementedSchemas = []
        self.willAktivenBereich = True # Nutzer möchte aktive Bereiche festlegen

        #importiere DataDrivenInputMask
        pluginDir = QtCore.QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/"
        maskDir = pluginDir + "DataDrivenInputMask"
        maskFound = False

        for p in sys.path:
            if p == maskDir:
                maskFound = True
                break

        if not maskFound:
            sys.path.append(maskDir)

        try:
            from DataDrivenInputMask import ddui, ddmanager
            self.ddUi = ddui.DataDrivenUi(self.iface)

            try:
                self.app.xpManager
            except AttributeError:
                ddManager = ddmanager.DdManager(self.iface)
                self.app.xpManager = ddManager
        except ImportError:
            self.unload()
            XpError(u"Bitte installieren Sie das Plugin " + \
                "DataDrivenInputMask aus dem QGIS Official Repository!",
                self.iface)

    def initGui(self):
        # Code von fTools

        self.xpMenu = QtGui.QMenu(u"XPlanung")
        self.bereichMenu = QtGui.QMenu(u"XP_Bereich")
        self.bereichMenu.setToolTip(u"Ein Planbereich fasst die Inhalte eines Plans " +\
            u"nach bestimmten Kriterien zusammen.")
        self.bpMenu = QtGui.QMenu(u"BPlan")
        self.bpMenu.setToolTip(u"Fachschema BPlan für Bebauungspläne")
        self.fpMenu = QtGui.QMenu(u"FPlan")
        self.fpMenu.setToolTip(u"Fachschema FPlan für Flächennutzungspläne")
        self.lpMenu = QtGui.QMenu(u"LPlan")
        self.lpMenu.setToolTip(u"Fachschema LPlan für Landschaftspläne")
        self.soMenu = QtGui.QMenu(u"SonstigePlanwerke")
        self.soMenu.setToolTip(u"Fachschema zur Modellierung nachrichtlicher Übernahmen " + \
            u"aus anderen Rechtsbereichen und sonstiger raumbezogener Pläne nach BauGB. ")
        self.xpDbMenu = QtGui.QMenu(u"XPlanung")

        self.action9 = QtGui.QAction(u"Einstellungen", self.iface.mainWindow())
        self.action9.triggered.connect(self.setSettings)
        self.action0 = QtGui.QAction(u"Initialisieren", self.iface.mainWindow())
        self.action0.triggered.connect(self.initialize)
        self.action1 = QtGui.QAction(u"Bereich laden", self.iface.mainWindow())
        self.action1.setToolTip(u"Alle zu einem Bereich gehörenden Elemente " + \
            u"laden und mit gespeichertem Stil darstellen")
        self.action1.triggered.connect(self.bereichLaden)
        self.action2 = QtGui.QAction(u"Layer initialisieren", self.iface.mainWindow())
        self.action2.setToolTip(u"aktiver Layer: Eingabemaske erzeugen, neue Features den aktiven " +\
            u"Bereichen zuweisen.")
        self.action2.triggered.connect(self.layerInitializeSlot)
        self.action3 = QtGui.QAction(u"Aktive Bereiche festlegen", self.iface.mainWindow())
        self.action3.setToolTip(u"Elemente von Layern können automatisch oder händisch den aktiven " +\
            u"Bereichen zugewiesen werden. Damit werden sie zum originären Inhalt des Planbereichs.")
        self.action3.triggered.connect(self.aktiveBereicheFestlegen)
        self.action3a = QtGui.QAction(u"Aktive Bereiche löschen", self.iface.mainWindow())
        self.action3a.setToolTip(u"Elemente von Layern können automatisch oder händisch den aktiven " +\
            u"Bereichen zugewiesen werden. Damit werden sie zum originären Inhalt des Planbereichs.")
        self.action3a.triggered.connect(self.aktiveBereicheLoeschen)
        self.action4 = QtGui.QAction(u"Auswahl den aktiven Bereichen zuordnen", self.iface.mainWindow())
        self.action4.setToolTip(u"aktiver Layer: ausgewählte Elemente den aktiven Bereichen zuweisen. " +\
                                u"Damit werden sie zum originären Inhalt des Planbereichs.")
        self.action4.triggered.connect(self.aktivenBereichenZuordnenSlot)
        self.action5 = QtGui.QAction(u"Auswahl nachrichtlich übernehmen", self.iface.mainWindow())
        self.action5.setToolTip(u"aktiver Layer: ausgewählte Elemente nachrichtlich " + \
            "den aktiven Bereichen zuweisen.")
        self.action5.triggered.connect(self.aktivenBereichenNachrichtlichZuordnenSlot)
        self.action6 = QtGui.QAction(u"Layer darstellen (nach PlanZV)", self.iface.mainWindow())
        self.action6.setToolTip(u"aktiver Layer: gespeicherten Stil anwenden")
        self.action6.triggered.connect(self.layerStyleSlot)
        self.action10 = QtGui.QAction(u"Mehrfachdateneingabe", self.iface.mainWindow())
        self.action10.setToolTip(u"Eingabe für alle gewählten Objekte")
        self.action10.triggered.connect(self.layerMultiEditSlot)
        self.action7 = QtGui.QAction(u"Layerstil speichern", self.iface.mainWindow())
        self.action7.setToolTip(u"aktiver Layer: Stil speichern")
        self.action7.triggered.connect(self.saveStyleSlot)
        self.action8 = QtGui.QAction(u"gespeicherten Layerstil löschen", self.iface.mainWindow())
        self.action8.setToolTip(u"aktiver Layer: aktien Layerstil löschen")
        self.action8.triggered.connect(self.deleteStyleSlot)

        self.action20 = QtGui.QAction(u"Objektart laden", self.iface.mainWindow())
        self.action20.triggered.connect(self.loadXP)
        self.action21 = QtGui.QAction(u"Objektart laden", self.iface.mainWindow())
        self.action21.triggered.connect(self.loadBP)
        self.action22 = QtGui.QAction(u"Objektart laden", self.iface.mainWindow())
        self.action22.triggered.connect(self.loadFP)
        self.action23 = QtGui.QAction(u"Objektart laden", self.iface.mainWindow())
        self.action23.triggered.connect(self.loadLP)
        self.action24 = QtGui.QAction(u"Objektart laden", self.iface.mainWindow())
        self.action24.triggered.connect(self.loadSO)
        self.action25 = QtGui.QAction(u"ExterneReferenz anlegen", self.iface.mainWindow())
        self.action25.triggered.connect(self.createExterneReferenz)
        self.action26 = QtGui.QAction(u"räuml. Geltungsbereiche neu berechnen",
            self.iface.mainWindow())
        self.action26.triggered.connect(self.geltungsbereichBerechnen)

        self.xpMenu.addActions([self.action20, self.action25,
            self.action6, self.action10])
        self.bereichMenu.addActions([self.action1, self.action3, self.action3a,
            self.action4, self.action5])
        self.bpMenu.addActions([self.action21, self.action26])
        self.fpMenu.addActions([self.action22])
        self.lpMenu.addActions([self.action23])
        self.soMenu.addActions([self.action24])
        self.xpDbMenu.addActions([self.action9, self.action7, self.action8])
        # Add toolbar button and menu item

        self.iface.addPluginToVectorMenu("tmp", self.tmpAct) # sicherstellen, dass das VektorMenu da ist
        self.vectorMenu = self.iface.vectorMenu()
        self.vectorMenu.addMenu(self.xpMenu)
        self.vectorMenu.addMenu(self.bereichMenu)
        self.vectorMenu.addMenu(self.bpMenu)
        self.vectorMenu.addMenu(self.fpMenu)
        self.vectorMenu.addMenu(self.lpMenu)
        self.vectorMenu.addMenu(self.soMenu)
        self.iface.removePluginVectorMenu("tmp", self.tmpAct)
        self.iface.addPluginToDatabaseMenu("tmp", self.tmpAct)
        self.databaseMenu = self.iface.databaseMenu()
        self.databaseMenu.addMenu(self.xpDbMenu)
        self.iface.removePluginDatabaseMenu("tmp", self.tmpAct)

    def unload(self):
        try:
            self.app.xpManager.quit()
            self.iface.addPluginToVectorMenu("tmp", self.tmpAct)
            self.vectorMenu.removeAction(self.xpMenu.menuAction())
            self.vectorMenu.removeAction(self.bereichMenu.menuAction())
            self.vectorMenu.removeAction(self.bpMenu.menuAction())
            self.vectorMenu.removeAction(self.fpMenu.menuAction())
            self.vectorMenu.removeAction(self.lpMenu.menuAction())
            self.iface.removePluginVectorMenu("tmp", self.tmpAct)
            self.iface.addPluginToDatabaseMenu("tmp", self.tmpAct)
            self.databaseMenu.removeAction(self.xpDbMenu.menuAction())
            self.iface.removePluginDatabaseMenu("tmp", self.tmpAct)
        except:
            pass

    def debug(self, msg):
        QgsMessageLog.logMessage("Debug" + "\n" + msg)

    def loadLayerLayer(self):
        self.layerLayer = self.getLayerForTable("QGIS", "layer")

        if self.layerLayer == None:
            XpError(u"Kann Tabelle QGIS.layer nicht laden!", self.iface)
            return False
        else:
            self.layerLayer.layerDeleted.connect(self.onLayerLayerDeleted)
            return True


    def getStyleId(self, schemaName, tableName, bereich):
        sel = "SELECT id, COALESCE(\"XP_Bereich_gid\",-9999) \
            FROM \"QGIS\".\"layer\" l \
            LEFT JOIN \"XP_Basisobjekte\".\"XP_Bereiche\" b ON l.\"XP_Bereich_gid\" = b.gid \
            WHERE l.schemaname = :schema \
            AND l.tablename = :table \
            AND b.name"

        if bereich == self.standardName:
            sel += " IS NULL"
        else:
            sel += " = :bereich"

        query = QtSql.QSqlQuery(self.db)
        query.prepare(sel)
        query.bindValue(":schema", schemaName)
        query.bindValue(":table", tableName)

        if bereich != self.standardName:
            query.bindValue(":bereich", bereich)

        query.exec_()

        if query.isActive():
            stilId = None

            while query.next(): # returns false when all records are done
                stilId = query.value(0)

            query.finish()
            return stilId
        else:
            self.showQueryError(query)
            return None

    #Slots
    def geltungsbereichBerechnen(self):
        '''raeumlicherGeltungsbereich für alle (selektierten)
        BP_Plan aus den Geltungsbereichen
        von BP_Bereich berechnen'''
        if self.db == None:
            self.initialize(False)

        if self.db != None:
            bpPlanLayer = self.getLayerForTable(
                "BP_Basisobjekte","BP_Plan",
                geomColumn = "raeumlicherGeltungsbereich")

            if bpPlanLayer == None:
                return None

            bpBereichLayer = self.getLayerForTable(
                "BP_Basisobjekte","BP_Bereich",
                geomColumn = "geltungsbereich")

            if bpBereichLayer != None:
                bpPlaene = {}

                for bpPlanFeat in self.tools.getFeatures(bpPlanLayer):
                    bpPlaene[bpPlanFeat.id()] = []

                if len(bpPlaene) > 0:
                    if self.tools.setEditable(bpPlanLayer, True, self.iface):
                        bpBereichLayer.selectAll()
                        gehoertZuPlanFld = bpBereichLayer.fieldNameIndex("gehoertZuPlan")

                        for bereichFeat in self.tools.getFeatures(bpBereichLayer):
                            bpPlanId = bereichFeat[gehoertZuPlanFld]

                            if bpPlanId in bpPlaene:
                                bpPlaene[bpPlanId].append(QgsGeometry(bereichFeat.geometry()))

                        bpBereichLayer.invertSelection()
                        bpPlanLayer.beginEditCommand(u"XPlan: räumliche Geltungsbereiche erneuert")

                        for fid, geomList in bpPlaene.iteritems():
                            if len(geomList) == 0:
                                continue

                            first = True
                            for aGeom in geomList:
                                if first:
                                    outGeom = aGeom
                                    first = False
                                else:
                                    outGeom = QgsGeometry(outGeom.combine(aGeom))

                            bpPlanLayer.changeGeometry(fid, outGeom)
                        bpPlanLayer.endEditCommand()

    def createExterneReferenz(self):
        if self.db == None:
            self.initialize(False)

        if self.db != None:
            extRefLayer = self.getLayerForTable("XP_Basisobjekte",
                "XP_ExterneReferenz")
            if extRefLayer != None:
                newFeat = self.tools.createFeature(extRefLayer)

                if self.tools.setEditable(extRefLayer, True, self.iface):
                    if extRefLayer.addFeature(newFeat):
                        self.app.xpManager.showFeatureForm(
                            extRefLayer, newFeat, askForSave = False)
                    else:
                        XpError(u"Kann in Tabelle XP_Basisobjekte.XP_ExterneReferenz \
                            kein Feature einfügen!", self.iface)

    def onLayerLayerDeleted(self):
        self.layerLayer = None

    def setSettings(self):
        dlg = XPlanungConf(self.dbHandler)
        dlg.show()
        result = dlg.exec_()

        if result == 1:
            self.initialize()

    def initialize(self,  aktiveBereiche = True):
        self.db = self.dbHandler.dbConnect()

        if self.db != None:
            # implementedSchemas feststellen
            query = QtSql.QSqlQuery(self.db)
            query.prepare("SELECT substr(nspname,0,3) \
                        FROM pg_namespace \
                        WHERE nspname ILIKE \'%Basisobjekte%\' \
                        ORDER BY nspname;")
            query.exec_()

            if query.isActive():
                while query.next():
                    self.implementedSchemas.append(query.value(0))

                query.finish()
            else:
                self.showQueryError(query)

            if not self.tools.isXpDb(self.db):
                XpError(u"Die konfigurierte Datenbank ist keine XPlan-Datenbank. Bitte " +\
                u"konfigurieren Sie eine solche und initialisieren " +\
                u"Sie dann erneut.", self.iface)
                self.dbHandler.dbDisconnect(self.db)
                self.db = None
                self.setSettings()
            else:
                if aktiveBereiche:
                    self.aktiveBereicheFestlegen()

    def loadObjektart(self, objektart):
        if self.db == None:
            self.initialize(False)

        if self.db != None:
            dlg = ChooseObjektart(objektart, self.db)
            dlg.show()
            result = dlg.exec_()

            if result == 1:
                withDisplay = dlg.withDisplay

                for aSel in dlg.selection:
                    schemaName = aSel[0]
                    tableName = aSel[1]
                    geomColumn = aSel[2]
                    description = aSel[3]
                    ddTable = self.app.xpManager.createDdTable(self.db,
                        schemaName, tableName, withOid = False,
                        withComment = False)

                    isView = ddTable == None

                    if isView:
                        ddTable = DdTable(schemaName = schemaName, tableName = tableName)

                    editLayer = self.app.xpManager.loadPostGISLayer(self.db,
                        ddTable, displayName = tableName + " (editierbar)",
                        geomColumn = geomColumn, keyColumn = "gid")

                    if editLayer != None:
                        grpIdx = self.getGroupIndex(schemaName)

                        if grpIdx == -1:
                            grpIdx = self.createGroup(schemaName)

                        self.iface.legendInterface().moveLayer(editLayer, grpIdx)
                        editLayer.setAbstract(description)
                        stile = self.tools.getLayerStyles(self.db,
                            editLayer, schemaName, tableName)

                        if stile != None:
                            self.tools.applyStyles(editLayer, stile)
                            self.tools.useStyle(editLayer, self.simpleStyleName)

                        if not isView:
                            ddInit = self.layerInitialize(editLayer,
                                layerCheck = self.willAktivenBereich)

                            if ddInit:
                                self.app.xpManager.addAction(editLayer,
                                    actionName = "XP_Sachdaten",
                                    ddManagerName = "xpManager")

                            if withDisplay:
                                displayLayer = self.createVirtualLayer(editLayer, tableName)

                                if displayLayer != None:
                                    self.iface.legendInterface().moveLayer(
                                        displayLayer, grpIdx)

                                    if stile != None:
                                        self.tools.applyStyles(displayLayer, stile)
                                        stil = self.tools.chooseStyle(displayLayer)

                                        if stil != None:
                                            self.tools.useStyle(displayLayer, stil)

    def loadXP(self):
        self.loadObjektart("XP")

    def loadBP(self):
        self.loadObjektart("BP")

    def loadFP(self):
        self.loadObjektart("FP")

    def loadLP(self):
        self.loadObjektart("LP")

    def loadSO(self):
        self.loadObjektart("SO")

    def aktiveBereicheFestlegen(self):
        '''Auswahl der Bereiche, in die neu gezeichnete Elemente eingefügt werden sollen'''
        if self.db == None:
            self.initialize(False)

        if self.db:
            bereichsAuswahl = self.tools.chooseBereich(self.db,  True,  u"Aktive Bereiche festlegen")

            if len(bereichsAuswahl) > 0: # Auswahl wurde getroffen oder es wurde abgebrochen
                try:
                    bereichsAuswahl[-1] #Abbruch; bisherigen aktive Bereiche bleiben aktiv
                except KeyError:
                    self.aktiveBereiche = bereichsAuswahl

                self.willAktivenBereich = True
            else:
                self.aktiveBereiche = bereichsAuswahl # keine Auswahl => keine aktiven Bereiche

    def aktiveBereicheLoeschen(self):
        self.aktiveBereiche = []
        self.willAktivenBereich = True

    def layerInitializeSlot(self):
        layer = self.iface.activeLayer()

        if layer != None:
            if self.db == None:
                self.initialize(False)
            self.layerInitialize(layer)
            self.app.xpManager.addAction(layer, actionName = "XP_Sachdaten",
                ddManagerName = "xpManager")
            self.iface.mapCanvas().refresh() # neuzeichnen


    def deleteStyleSlot(self):
        layer = self.iface.activeLayer()

        if layer == None:
            return None

        if self.layerLayer == None:
            if not self.loadLayerLayer():
                return None

        if self.db == None:
            self.initialize(False)

        styleMan = layer.styleManager()
        bereich = styleMan.currentStyle()

        if bereich == u"":
            return None

        relation = self.tools.getPostgresRelation(layer)
        schemaName = relation[0]
        tableName = relation[1]
        stilId = self.getStyleId(schemaName, tableName, bereich)

        if stilId != None: # Eintrag löschen
            feat = QgsFeature()

            if self.layerLayer.getFeatures(
                    QgsFeatureRequest().setFilterFid(stilId).setFlags(
                    QgsFeatureRequest.NoGeometry)).nextFeature(feat):
                if self.tools.setEditable(self.layerLayer):
                    if self.layerLayer.deleteFeature(stilId):
                        if self.layerLayer.commitChanges():
                            self.iface.messageBar().pushMessage("XPlanung",
                                u"Stil " + bereich + u" gelöscht",
                                level=QgsMessageBar.INFO, duration = 10)
                        else:
                            XpError(u"Konnte Änderungen an " + \
                                self.layerLayer.name() + u"nicht speichern!",
                                self.iface)

    def saveStyleSlot(self):
        layer = self.iface.activeLayer()

        if layer == None:
            return None

        if self.db == None:
            self.initialize(False)

        if self.layerLayer == None:
            if not self.loadLayerLayer():
                return None

        styleMan = layer.styleManager()
        bereich = styleMan.currentStyle()

        if bereich == u"":
            bereich = self.standardName

        relation = self.tools.getPostgresRelation(layer)
        schemaName = relation[0]
        tableName = relation[1]
        stilId = self.getStyleId(schemaName, tableName, bereich)
        self.app.xpManager.removeAction(layer, actionName = "XP_Sachdaten")
        doc = self.tools.getXmlLayerStyle(layer)

        if doc != None:
            if stilId != None: # Eintrag ändern
                reply = QtGui.QMessageBox.question(
                    None, u"Stil vorhanden",
                    u"Vorhandenen Stil für Bereich %s ersetzen?" % bereich,
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel,
                    defaultButton = QtGui.QMessageBox.No)

                if reply == QtGui.QMessageBox.Yes:
                    changeStyle = True
                elif reply == QtGui.QMessageBox.No:
                    changeStyle = False
                else:
                    return None
            else:
                changeStyle = False

            if changeStyle:
                feat = QgsFeature()

                if self.layerLayer.getFeatures(
                        QgsFeatureRequest().setFilterFid(stilId).setFlags(
                        QgsFeatureRequest.NoGeometry)).nextFeature(feat):
                    feat[self.layerLayer.fieldNameIndex("style")] = doc.toString()

                    if self.app.xpManager.showFeatureForm(
                            self.layerLayer, feat) != 0:
                        if self.tools.setEditable(self.layerLayer):
                            self.layerLayer.changeAttributeValue(
                                stilId, self.layerLayer.fieldNameIndex("style"),
                                doc.toString())
                            if not self.layerLayer.commitChanges():
                                XpError(u"Konnte Änderungen an " + \
                                self.layerLayer.name() + u"nicht speichern!",
                                self.iface)
            else: # neuer Eintrag
                newFeat = self.tools.createFeature(self.layerLayer)
                # füge den neuen Stil in das Feature ein
                newFeat[self.layerLayer.fieldNameIndex("style")] = doc.toString()
                # vergebe eine Fake-Id, damit kein Fehler kommt, id wird aus Sequenz vergeben
                newFeat[self.layerLayer.fieldNameIndex("id")] = 1
                newFeat[self.layerLayer.fieldNameIndex("schemaname")] = schemaName
                newFeat[self.layerLayer.fieldNameIndex("tablename")] = tableName

                if self.tools.setEditable(self.layerLayer, True, self.iface):
                    if self.layerLayer.addFeature(newFeat):
                        self.app.xpManager.showFeatureForm(
                            self.layerLayer, newFeat, askForSave = False)

        self.app.xpManager.addAction(layer, actionName = "XP_Sachdaten",
            ddManagerName = "xpManager")

    def layerMultiEditSlot(self):
        layer = self.iface.activeLayer()

        if layer != None:
            sel = layer.selectedFeatures()

            if len(sel) > 0:
                self.app.xpManager.showFeatureForm(layer, sel[0], multiEdit = True)

    def layerStyleSlot(self):
        layer = self.iface.activeLayer()

        if layer != None:

            if self.db == None:
                self.initialize(False)

            if self.layerInitialize(layer):
                stil = self.tools.chooseStyle(layer)

                if stil != None:
                    self.tools.useStyle(layer, stil)


    def createGroup(self,  grpName):
        grpIdx = self.iface.legendInterface().addGroup(grpName,  False) # False = expand

        if QGis.QGIS_VERSION_INT >= 20400:
            # Gruppe an der Spitze des LAyerbaums einfügen
            root=QgsProject.instance().layerTreeRoot()
            group = root.findGroup(grpName)
            group2 = group.clone()
            root.insertChildNode(0,  group2)
            root.removeChildNode(group)
            grpIdx = self.getGroupIndex(grpName)

        return grpIdx


    def getLayerForTable(self, schemaName, tableName,
        geomColumn = None, showMsg = True):
        '''Den Layer schemaName.tableName finden bzw. laden.
        Wenn geomColumn == None wird geoemtrielos geladen'''

        ddTable = self.app.xpManager.createDdTable(
            self.db, schemaName, tableName,
            withOid = False, withComment = False)

        if ddTable != None:
            layer = self.app.xpManager.findPostgresLayer(
                self.db, ddTable)

            if layer == None:
                layer = self.app.xpManager.loadPostGISLayer(
                    self.db, ddTable, geomColumn = geomColumn)

                if layer == None:
                    if showMsg:
                        XpError(u"Kann Tabelle %(schema)s.%(table)s nicht laden!" % \
                            {"schema":schemaName, "table":tableName},
                            self.iface)
                    return None
                else:
                    return layer
            else:
                return layer
        else:
            if showMsg:
                XpError(u"Kann ddTable %(schema)s.%(table)s nicht erzeugen!" % \
                    {"schema":schemaName, "table":tableName},
                    self.iface)
            return None

    def getGroupIndex(self, groupName):
        '''Finde den Gruppenindex für Gruppe groupName'''
        retValue = -1
        groups = self.iface.legendInterface().groups()

        for i in range(len(groups)):
            if groups[i] == groupName:
                retValue = i
                break

        return retValue

    def layerInitialize(self,  layer,  msg = False,  layerCheck = True):
        '''einen XP_Layer initialisieren, gibt Boolschen Wert zurück'''
        ddInit = False

        if 0 == layer.type(): # Vektorlayer
            layerRelation = self.tools.getPostgresRelation(layer)

            if layerRelation != None: # PostgreSQL-Layer
                try:
                    self.app.xpManager.ddLayers[layer.id()] # bereits initialisiert
                    ddInit = True
                except KeyError:
                    ddInit = self.app.xpManager.initLayer(layer,  skip = [], createAction = False,  db = self.db)

                if layerRelation[2]: # Layer hat Geometrien
                    schema = layerRelation[0]
                    table = layerRelation[1]

                    if schema != "XP_Praesentationsobjekte":
                        schemaTyp = schema[:2]

                        if table != schemaTyp + "_Plan" and table != schemaTyp + "_Bereich":
                            if self.implementedSchemas.count(schemaTyp) > 0:
                                # disconnect slots in case they are already connected
                                try:
                                    layer.committedFeaturesAdded.disconnect(self.featuresAdded)
                                except:
                                    pass

                                try:
                                    layer.editingStopped.disconnect(self.editingHasStopped)
                                except:
                                    pass

                                layer.committedFeaturesAdded.connect(self.featuresAdded)
                                layer.editingStopped.connect(self.editingHasStopped)
                                self.addedGeometries[layer.id()] = []

                                if layerCheck:
                                    self.aktiverBereichLayerCheck(layer)
            else:
                if msg:
                    XpError("Der Layer " + layer.name() + " ist kein PostgreSQL-Layer!",
                        self.iface)
        else: # not a vector layer
            if msg:
                XpError("Der Layer " + layer.name() + " ist kein VektorLayer!",
                    self.iface)

        return ddInit

    def createVirtualLayer(self, editLayer, table):
        '''
        Laden von weiteren Tabellen und erzeugen des virtualLayer
        '''

        parentJoins = []
        tablesWithParentJoins = ["BP_BaugebietsTeilFlaeche",
            "BP_AnpflanzungBindungErhaltungFlaeche",
            "BP_AnpflanzungBindungErhaltungLinie",
            "BP_AnpflanzungBindungErhaltungPunkt",
            "BP_SchutzgebietFlaeche", "BP_SchutzgebietLinie",
            "BP_SchutzgebietPunkt", "BP_StrassenkoerperFlaeche",
            "BP_StrassenkoerperLinie", "BP_StrassenVerkehrsFlaeche",
            "BP_VerEntsorgungLinie"]

        if tablesWithParentJoins.count(table) != 0:
            ddTable = self.app.xpManager.ddLayers[editLayer.id()][0]
            parents = self.ddUi.getParents(ddTable, self.db)

            while len(parents) > 0:
                parentLayer = self.app.xpManager.findPostgresLayer(self.db, parents[0])

                if parentLayer == None:
                    parentLayer = self.app.xpManager.loadPostGISLayer(self.db, parents[0])


                parentJoins.append(parentLayer)
                parents = self.ddUi.getParents(parents[0], self.db)

        joins = []
        # array, das alle Infos zu Joins aufnimmt:
        # 0: layer, der gejoint wird
        # 1: Feld in 0, an das gejoint wird (entspricht gid von schema.table)
        # 2: Feld in 0, das den relevanten Inhalt enthält

        if table == "FP_GemeinbedarfFlaeche" or \
                table == "FP_GemeinbedarfLinie" or \
                table == "FP_GemeinbedarfPunkt":
            joinLayer1 = self.getLayerForTable(
                "FP_Gemeinbedarf_Spiel_und_Sportanlagen",
                "FP_Gemeinbedarf_zweckbestimmung")
            joins.append([joinLayer1, "FP_Gemeinbedarf_gid", "zweckbestimmung"])

            joinLayer2 = self.getLayerForTable(
                "FP_Gemeinbedarf_Spiel_und_Sportanlagen",
                "FP_Gemeinbedarf_besondereZweckbestimmung")
            joins.append([joinLayer2, "FP_Gemeinbedarf_gid", "besondereZweckbestimmung"])

        elif table == "FP_GruenFlaeche" or \
                table == "FP_GruenLinie" or \
                table == "FP_GruenPunkt":
            joinLayer1 = self.getLayerForTable(
                "FP_Landwirtschaft_Wald_und_Gruen",
                "FP_Gruen_zweckbestimmung")
            joins.append([joinLayer1, "FP_Gruen_gid", "zweckbestimmung"])

            joinLayer2 = self.getLayerForTable(
                "FP_Landwirtschaft_Wald_und_Gruen",
                "FP_Gruen_besondereZweckbestimmung")
            joins.append([joinLayer2, "FP_Gruen_gid", "besondereZweckbestimmung"])

        elif table == "FP_PrivilegiertesVorhabenFlaeche" or \
                table == "FP_PrivilegiertesVorhabenLinie" or \
                table == "FP_PrivilegiertesVorhabenPunkt":
            joinLayer1 = self.getLayerForTable(
                "FP_Sonstiges",
                "FP_PrivilegiertesVorhaben_zweckbestimmung")
            joins.append([joinLayer1, "FP_PrivilegiertesVorhaben_gid", "zweckbestimmung"])

            joinLayer2 = self.getLayerForTable(
                "FP_Sonstiges",
                "FP_PrivilegiertesVorhaben_besondereZweckbestimmung")
            joins.append([joinLayer2, "FP_PrivilegiertesVorhaben_gid", "besondereZweckbestimmung"])

        elif table == "FP_VerEntsorgungFlaeche" or \
                table == "FP_VerEntsorgungLinie" or \
                table == "FP_VerEntsorgungPunkt":
            joinLayer1 = self.getLayerForTable(
                "FP_Ver_und_Entsorgung",
                "FP_VerEntsorgung_zweckbestimmung")
            joins.append([joinLayer1, "FP_VerEntsorgung_gid", "zweckbestimmung"])

            joinLayer2 = self.getLayerForTable(
                "FP_Ver_und_Entsorgung",
                "FP_VerEntsorgung_besondereZweckbestimmung")
            joins.append([joinLayer2, "FP_VerEntsorgung_gid", "besondereZweckbestimmung"])

        elif table == "FP_SpielSportanlageFlaeche" or \
                table == "FP_SpielSportanlageLinie" or \
                table == "FP_SpielSportanlagePunkt":
            joinLayer1 = self.getLayerForTable(
                "FP_Gemeinbedarf_Spiel_und_Sportanlagen",
                "FP_SpielSportanlage_zweckbestimmung")
            joins.append([joinLayer1, "FP_SpielSportanlage_gid", "zweckbestimmung"])

        elif table == "FP_KennzeichnungFlaeche" or \
                table == "FP_KennzeichnungLinie" or \
                table == "FP_KennzeichnungPunkt":
            joinLayer1 = self.getLayerForTable(
                "FP_Sonstiges",
                "FP_Kennzeichnung_zweckbestimmung")
            joins.append([joinLayer1, "FP_Kennzeichnung_gid", "zweckbestimmung"])

        elif table == "FP_WaldFlaeche":
            joinLayer1 = self.getLayerForTable(
                "FP_Landwirtschaft_Wald_und_Gruen",
                "FP_WaldFlaeche_zweckbestimmung")
            joins.append([joinLayer1, "FP_WaldFlaeche_gid", "zweckbestimmung"])

        elif table == "FP_GenerischesObjektFlaeche" or \
                table == "FP_GenerischesObjektLinie" or \
                table == "FP_GenerischesObjektPunkt":
            joinLayer1 = self.getLayerForTable(
                "FP_Sonstiges",
                "FP_GenerischesObjekt_zweckbestimmung")
            joins.append([joinLayer1, "FP_GenerischesObjekt_gid", "zweckbestimmung"])

        elif table == "BP_GruenFlaeche":
            joinLayer1 = self.getLayerForTable(
                "BP_Landwirtschaft_Wald_und_Gruen",
                "BP_GruenFlaeche_zweckbestimmung")
            joins.append([joinLayer1, "BP_GruenFlaeche_gid", "zweckbestimmung"])

            joinLayer2 = self.getLayerForTable(
                "BP_Landwirtschaft_Wald_und_Gruen",
                "BP_GruenFlaeche_besondereZweckbestimmung")
            joins.append([joinLayer2, "BP_GruenFlaeche_gid", "besondereZweckbestimmung"])

        elif table == "BP_WaldFlaeche":
            joinLayer1 = self.getLayerForTable(
                "BP_Landwirtschaft_Wald_und_Gruen",
                "BP_WaldFlaeche_zweckbestimmung")
            joins.append([joinLayer1, "BP_WaldFlaeche_gid", "zweckbestimmung"])

        elif table == "BP_GemeinbedarfsFlaeche":
            joinLayer1 = self.getLayerForTable(
                "BP_Gemeinbedarf_Spiel_und_Sportanlagen",
                "BP_GemeinbedarfsFlaeche_zweckbestimmung")
            joins.append([joinLayer1, "BP_GemeinbedarfsFlaeche_gid", "zweckbestimmung"])

            joinLayer2 = self.getLayerForTable(
                "BP_Gemeinbedarf_Spiel_und_Sportanlagen",
                "BP_GemeinbedarfsFlaeche_besondereZweckbestimmung")
            joins.append([joinLayer2, "BP_GemeinbedarfsFlaeche_gid", "besondereZweckbestimmung"])

        elif table == "BP_SpielSportanlagenFlaeche":
            joinLayer1 = self.getLayerForTable(
                "BP_Gemeinbedarf_Spiel_und_Sportanlagen",
                "BP_SpielSportanlagenFlaeche_zweckbestimmung")
            joins.append([joinLayer1, "BP_SpielSportanlagenFlaeche_gid", "zweckbestimmung"])

        elif table == "BP_KennzeichnungsFlaeche":
            joinLayer1 = self.getLayerForTable(
                "BP_Sonstiges",
                "BP_KennzeichnungsFlaeche_zweckbestimmung")
            joins.append([joinLayer1, "BP_KennzeichnungsFlaeche_gid", "zweckbestimmung"])

        elif table == "BP_VerEntsorgungFlaeche" or \
                table == "BP_VerEntsorgungPunkt":
            joinLayer1 = self.getLayerForTable(
                "BP_Ver_und_Entsorgung",
                "BP_VerEntsorgung_zweckbestimmung")
            joins.append([joinLayer1, "BP_VerEntsorgung_gid", "zweckbestimmung"])

            joinLayer2 = self.getLayerForTable(
                "BP_Ver_und_Entsorgung",
                "BP_VerEntsorgung_besondereZweckbestimmung")
            joins.append([joinLayer2, "BP_VerEntsorgung_gid", "besondereZweckbestimmung"])

        # den virtualLayer machen
        selectSql = "?query=SELECT g.gid, g.geometry"
        fromSql = " FROM \"" + editLayer.name() + "\" g" \

        for i in range(len(parentJoins)):
            parentTableAlias = "p" + str(i)
            selectSql += ", " + parentTableAlias + ".*"
            fromSql += " JOIN \"" + parentJoins[i].name() + "\" " + parentTableAlias + \
                " ON g.gid = " + parentTableAlias + ".gid"

        for i in range(len(joins)):
            aJoin = joins[i]
            joinTableAlias = "j" + str(i)
            selectSql += ", " + joinTableAlias + ".\"" + aJoin[2] + "\""
            fromSql += " LEFT JOIN \"" + aJoin[0].name() + "\" " + joinTableAlias + \
                " ON g.gid = " + joinTableAlias + ".\"" + aJoin[1] + "\""

        sSql = selectSql + fromSql
        newLayer = QgsVectorLayer(sSql, table, "virtual")

        if newLayer.isValid():
            QgsMapLayerRegistry.instance().addMapLayers([newLayer])
        else:
            newLayer = None

        return newLayer

    def aktiverBereichLayerCheck(self,  layer):
        '''Prüfung, ob übergebener Layer und aktive Bereiche dem selben Objektbereich entsammen'''
        layerRelation = self.tools.getPostgresRelation(layer)
        retValue = False

        if layerRelation != None: #  PostgreSQL-Layer
            if layerRelation[2]: # Geometrielayer
                schema = layerRelation[0]

                if schema !="XP_Praesentationsobjekte":
                    schemaTyp = schema[:2] # z.B. FP, LP

                    while(True):
                        if len(self.aktiveBereiche) == 0 and self.willAktivenBereich:
                            thisChoice = QtGui.QMessageBox.question(None, "Keine aktiven Bereiche",
                            u"Wollen Sie aktive Bereiche festlegen? ",
                            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

                            if thisChoice == QtGui.QMessageBox.Yes:
                                self.aktiveBereicheFestlegen()
                            else:
                                self.willAktivenBereich = False
                                break

                        if len(self.aktiveBereiche) > 0:
                            for k in self.aktiveBereiche.iterkeys():
                                bereichGid = k
                                break

                            bereichTyp = self.tools.getBereichTyp(self.db,  bereichGid)

                            if bereichTyp == schemaTyp:
                                retValue = True
                                break
                            else:
                                thisChoice = QtGui.QMessageBox.question(None, "Falscher Objektbereich",
                                    u"Die momentan aktiven Bereiche und der Layer stammen aus unterschiedlichen " + \
                                    u"Objektbereichen: aktive Bereiche = " + bereichTyp + ", " + layer.name() + " = " + \
                                    schemaTyp + u". Wollen Sie die aktiven Bereiche ändern? ",
                                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

                                if thisChoice == QtGui.QMessageBox.Yes:
                                    self.aktiveBereicheFestlegen()
                                else:
                                    break

        return retValue

    def aktivenBereichenZuordnenSlot(self):
        layer = self.iface.activeLayer()
        self.aktivenBereichenZuordnen(layer)

    def aktivenBereichenZuordnen(self,  layer):
        '''fügt alle ausgewählten Features im übergebenen Layer den aktiven Bereichen zu
        Rückgabe: Bool (Erfolg)'''
        if self.db == None:
            self.initialize()

        if self.db:
            if self.aktiverBereichLayerCheck(layer):
                for k in self.aktiveBereiche.iterkeys():
                    bereichGid = k
                    break

                bereichTyp = self.tools.getBereichTyp(self.db,  bereichGid) #
                # da nur Bereiche einer Art ausgewählt werden können,
                # reicht es, den Typ des ersten Bereiches festzustellen
                gehoertZuSchema = bereichTyp + "_Basisobjekte"
                gehoertZuTable = "gehoertZu" + bereichTyp + "_Bereich"
                gehoertZuLayer = self.getLayerForTable(
                    gehoertZuSchema, gehoertZuTable)

                if gehoertZuLayer == None:
                    return False
                else:
                    if not gehoertZuLayer.isEditable():
                        if not gehoertZuLayer.startEditing():
                            return False

                    bereichFld = gehoertZuLayer.fieldNameIndex(bereichTyp + "_Bereich_gid")
                    objektFld = gehoertZuLayer.fieldNameIndex(bereichTyp + "_Objekt_gid")
                    bereitsZugeordnet = self.tools.getBereicheFuerFeatures(self.db,  bereichTyp,  layer.selectedFeaturesIds())

                    gehoertZuLayer.beginEditCommand(u"Ausgewählte Features von " + layer.name() + u" den aktiven Bereichen zugeordnet.")
                    newFeat = None #ini

                    for aGid in layer.selectedFeaturesIds():
                        if aGid < 0:
                            XpError(u"Bereichszuordnung: Bitte speichern Sie zuerst den Layer " + layer.name(),
                                self.iface)
                            gehoertZuLayer.destroyEditCommand()
                        else:
                            for aBereichGid in self.aktiveBereiche:
                                doInsert = True
                                #prüfen, ob dieses XP_Objekt bereits diesem XP_Bereich zugewiesen ist
                                try:
                                    objektBereiche = bereitsZugeordnet[aGid]
                                except KeyError:
                                    objektBereiche = []

                                for objektBereich in objektBereiche:

                                    if objektBereich == aBereichGid:
                                        doInsert = False
                                        break

                                if doInsert:
                                    newFeat = self.tools.createFeature(gehoertZuLayer)
                                    gehoertZuLayer.addFeature(newFeat,  False)
                                    gehoertZuLayer.changeAttributeValue(newFeat.id(),  bereichFld, aBereichGid)
                                    gehoertZuLayer.changeAttributeValue(newFeat.id(),  objektFld, aGid)

                    if newFeat == None: # keine neuen Einträge
                        gehoertZuLayer.destroyEditCommand()
                        return False
                    else:
                        gehoertZuLayer.endEditCommand()
                        return True
            else:
                return False
        else:
            return False

    def aktivenBereichenNachrichtlichZuordnenSlot(self):
        layer = self.iface.activeLayer()
        self.aktivenBereichenNachrichtlichZuordnen(layer)

    def aktivenBereichenNachrichtlichZuordnen(self):
        pass

    def bereichLaden(self):
        '''Laden aller Layer, die Elemente in einem auszuwählenden Bereich haben'''
        if self.db == None:
            self.db = self.dbHandler.dbConnect()

        if self.db:
            bereichDict = self.tools.chooseBereich(self.db)

            if len(bereichDict) > 0:
                for k in bereichDict.iterkeys():
                    bereich = k
                    break

                if bereich >= 0:
                    # rausbekommen, welche Layer Elemente im Bereich haben
                    layers = self.tools.getLayerInBereich(self.db, [bereich])
                    #rausbekommen, welche Layer nachrichtlich Elemente im Bereich haben?

                    if len(layers) == 0:
                        self.iface.messageBar().pushMessage(
                            "XPlanung", u"In diesem Bereich sind keine Objekte vorhanden!",
                            level=QgsMessageBar.WARNING, duration = 10)
                        return None

                    # eine Gruppe für den Bereich machen
                    lIface = self.iface.legendInterface()
                    lIface.addGroup(bereichDict[bereich],  False)
                    groupIdx = self.tools.getGroupIndex(bereichDict[bereich])

                    if groupIdx == -1:
                        return None

                    lIface.setGroupExpanded(groupIdx, False)

                    # Layer in die Gruppe laden und features entsprechend einschränken
                    bereichTyp = self.tools.getBereichTyp(self.db,  bereich)
                    filter = "gid IN (SELECT \"" + bereichTyp + "_Objekt_gid\" " + \
                        "FROM \""+ bereichTyp + "_Basisobjekte\".\"" + \
                        bereichTyp + "_Objekt_gehoertZu" + bereichTyp + "_Bereich\" " + \
                        bereichTyp + "_Objekt_gehoertZu" + bereichTyp + "_Bereich\" " + \
                        "WHERE \"" + bereichTyp + "_Bereich_gid\" = " + str(bereich) + ")"

                    for aLayerType in layers:
                        for aKey in aLayerType.iterkeys():
                            for aRelName in aLayerType[aKey]:
                                aDdTable = self.app.xpManager.createDdTable(self.db,
                                    aKey, aRelName, withOid = False, withComment = False)

                                if aDdTable != None:
                                    aLayer = self.app.xpManager.loadPostGISLayer(self.db,
                                        aDdTable, geomColumn = 'position',
                                        whereClause = filter)

                                    # layer initialisieren
                                    if self.layerInitialize(aLayer,  msg=True,  layerCheck = False):
                                        # Stil des Layers aus der DB holen und anwenden
                                        self.tools.useStyle(layer, bereichDict[bereich])
                                        self.app.xpManager.addAction(aLayer, actionName = "XP_Sachdaten",
                                            ddManagerName = "xpManager")

                                    lIface.moveLayer(aLayer,  groupIdx)
                                    lIface.setLayerVisible(aLayer,  True)
            self.iface.mapCanvas().refresh() # neuzeichnen

    def editingHasStopped(self):
        if len(self.aktiveBereiche) > 0:
            selLayers = self.iface.legendInterface().selectedLayers()
            for layer in selLayers:
                try:
                    newGeoms = self.addedGeometries[layer.id()]
                    layer.reload() # damit gids geladen werden
                    newGids = []

                    for aGeom in newGeoms:
                        layer.removeSelection()
                        layer.select(aGeom.boundingBox(),  True)

                        for selFeature in layer.selectedFeatures():
                            if selFeature.geometry().isGeosEqual(aGeom):
                                newGid = selFeature["gid"]
                                newGids.append(newGid)
                                break

                    layer.removeSelection()
                    layer.select(newGids)

                    if self.aktivenBereichenZuordnen(layer):
                        if not gehoertZuLayer.commitChanges():
                            XpError(u"Konnte Änderungen am Layer " + \
                                gehoertZuLayer.name() + " nicht speichern!",
                                self.iface)
                except KeyError:
                    continue

        self.iface.mapCanvas().refresh() # neuzeichnen

    def featuresAdded(self,  layerId,  featureList):
        newGeoms = []

        for aFeature in featureList:
            newGeoms.append(QgsGeometry(aFeature.geometry())) # Kopie der Geometrie

        self.addedGeometries[layerId] = newGeoms

    def showQueryError(self, query):
        self.tools.showQueryError(query)
