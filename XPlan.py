# -*- coding: utf-8 -*-
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
import sys
from HandleDb import DbHandler
from XPTools import XPTools
from XPlanDialog import XPlanungConf
from XPlanDialog import LoadObjektart
from XPlanDialog import StilauswahlDialog

class XpError(object):
    '''General error'''
    def __init__(self, value, iface = None):
        self.value = value

        if iface == None:
            QtGui.QMessageBox.warning(None, "XPlanung", value)
        else:
            iface.messageBar().pushMessage("XPlanung", value,
                level=QgsMessageBar.CRITICAL)
    def __str__(self):
        return repr(self.value)

class XPlan():
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.app = QgsApplication.instance()
        self.dbHandler = DbHandler(self.iface)
        self.db = None
        self.tools = XPTools(self.iface)
        self.aktiveBereiche = []
        self.addedGeometries = {}
        self.layerLayer = None
        # Liste der implementierten Fachschemata
        self.implementedSchemas = ["FP"]

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
                self.app.ddManager
            except AttributeError:
                ddManager = ddmanager.DdManager(self.iface)
                self.app.ddManager = ddManager
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

        self.action_1 = QtGui.QAction(u"Einstellungen", self.iface.mainWindow())
        self.action_1.triggered.connect(self.setSettings)
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
        self.action4 = QtGui.QAction(u"Auswahl den aktiven Bereichen zuordnen", self.iface.mainWindow())
        self.action4.setToolTip(u"aktiver Layer: ausgewählte Elemente den aktiven Bereichen zuweisen. " +\
                                u"Damit werden sie zum originären Inhalt des Planbereichs.")
        self.action4.triggered.connect(self.aktivenBereichenZuordnenSlot)
        self.action5 = QtGui.QAction(u"Auswahl nachrichtlich übernehmen", self.iface.mainWindow())
        self.action5.setToolTip(u"aktiver Layer: ausgewählte Elemente nachrichtlich " + \
            "den aktiven Bereichen zuweisen.")
        self.action5.triggered.connect(self.aktivenBereichenNachrichtlichZuordnenSlot)
        self.action6 = QtGui.QAction(u"Layer darstellen", self.iface.mainWindow())
        self.action6.setToolTip(u"aktiver Layer: gespeicherten Stil anwenden")
        self.action6.triggered.connect(self.layerStyleSlot)
        self.action7 = QtGui.QAction(u"Layerstil speichern", self.iface.mainWindow())
        self.action7.setToolTip(u"aktiver Layer: Stil speichern")
        self.action7.triggered.connect(self.saveStyleSlot)
        self.action8 = QtGui.QAction(u"gespeicherten Layerstil ändern", self.iface.mainWindow())
        self.action8.setToolTip(u"aktiver Layer: einen vorhandenen Layerstil bearbeiten")
        self.action8.triggered.connect(self.changeSavedStyleSlot)

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

        self.xpMenu.addActions([self.action_1,
            self.action0, self.action20, self.action2,
            self.action6, self.action7, self.action8])
        self.bereichMenu.addActions([self.action1,  self.action3,  self.action4,  self.action5])
        self.bpMenu.addActions([self.action21])
        self.fpMenu.addActions([self.action22])
        self.lpMenu.addActions([self.action23])
        self.soMenu.addActions([self.action24])
        # Add toolbar button and menu item
        self.tmpAct = QtGui.QAction(self.iface.mainWindow())
        self.iface.addPluginToVectorMenu("tmp", self.tmpAct) # sicherstellen, dass das VektorMenu da ist
        self.vectorMenu = self.iface.vectorMenu()
        self.vectorMenu.addMenu(self.xpMenu)
        self.vectorMenu.addMenu(self.bereichMenu)
        self.vectorMenu.addMenu(self.bpMenu)
        self.vectorMenu.addMenu(self.fpMenu)
        self.vectorMenu.addMenu(self.lpMenu)
        self.vectorMenu.addMenu(self.soMenu)
        self.iface.removePluginVectorMenu("tmp", self.tmpAct)

    def unload(self):
        self.app.ddManager.quit()
        self.iface.addPluginToVectorMenu("tmp", self.tmpAct)
        self.vectorMenu.removeAction(self.xpMenu.menuAction())
        self.vectorMenu.removeAction(self.bereichMenu.menuAction())
        self.vectorMenu.removeAction(self.bpMenu.menuAction())
        self.vectorMenu.removeAction(self.fpMenu.menuAction())
        self.vectorMenu.removeAction(self.lpMenu.menuAction())
        self.iface.removePluginVectorMenu("tmp", self.tmpAct)

    def debug(self, msg):
        QgsMessageLog.logMessage("Debug" + "\n" + msg)

    def loadLayerLayer(self):
        layerLayerDdTable = self.app.ddManager.createDdTable(
            self.db, "QGIS", "layer",
            withOid = False, withComment = False)

        if layerLayerDdTable != None:
            self.layerLayer = self.app.ddManager.findPostgresLayer(
                self.db, layerLayerDdTable)

            if self.layerLayer == None:
                self.layerLayer = self.app.ddManager.loadPostGISLayer(
                    self.db, layerLayerDdTable)

                if self.layerLayer == None:
                    XpError(u"Kann Tabelle QGIS.layer nicht laden!", self.iface)
                    return False

            self.layerLayer.layerDeleted.connect(self.onLayerLayerDeleted)
            return True
        else:
            return False

    def getLayerStyle(self, layer, bereichGid = -9999):
        '''gibt den Style für einen Layer für den Bereich mit der übergebenen gid zurück,
        wenn es für diesen Bereich keinen Stil gibt, wird der allgemeine Stil zurückgegeben
        (XP_Bereich_gid = NULL), falls es den auch nicht gibt wird None zurückgegeben'''

        relation = self.tools.getPostgresRelation(layer)

        if relation:
            sel = "SELECT l.id, COALESCE(b.name,\'kein Bereich\'), l.style \
            FROM \"QGIS\".\"layer\" l \
            LEFT JOIN \"XP_Basisobjekte\".\"XP_Bereich\" b ON l.\"XP_Bereich_gid\" = b.gid \
            WHERE l.schemaname = :schema \
                AND l.tablename = :table"

            if bereichGid != -9999:
                sel += " AND (l.\"XP_Bereich_gid\" = :bereichGid" + \
                    " OR l.\"XP_Bereich_gid\" IS NULL)"

            sel += " ORDER BY \"XP_Bereich_gid\" NULLS "

            if bereichGid == -9999:
                sel = sel + "FIRST"
            else:
                sel = sel + "LAST"

            query = QtSql.QSqlQuery(self.db)
            query.prepare(sel)
            query.bindValue(":schema", relation[0])
            query.bindValue(":table", relation[1])

            if bereichGid != -9999:
                query.bindValue(":bereichGid", bereichGid)

            query.exec_()

            if query.isActive():
                if query.size() == 0:
                    self.iface.messageBar().pushMessage(
                        "XPlanung", u"Für den Layer " + layer.name() + u" sind keine Stile gespeichert",
                        level=QgsMessageBar.WARNING)
                    query.finish()
                    stilId = None
                elif query.size() == 1:
                    while query.next():
                        stilId = query.value(0)
                        style = unicode(query.value(2))
                        import sys
                        self.debug(sys.getdefaultencoding())

                    query.finish()
                else:
                    bereiche = {}
                    stile = {}

                    while query.next():
                        stilId = query.value(0)
                        bereich = query.value(1)
                        style = unicode(query.value(2))

                        if bereichGid != -9999:
                            break
                        else:
                            stile[stilId] = style
                            bereiche[stilId] = bereich

                    query.finish()

                    if bereichGid == -9999:
                        dlg = StilauswahlDialog(self.iface, bereiche)
                        dlg.show()
                        stilId = dlg.exec_()

                        if stilId == -1:
                            stilId = None
                        else:
                            style = stile[stilId]

                if stilId == None:
                    return None
                else:
                    return [stilId, style]
            else:
                self.showQueryError(query)
                query.finish()
                return None
        else:
            return None

    #Slots
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
            dlg = LoadObjektart(objektart, self.db)
            dlg.show()
            result = dlg.exec_()

            if result == 1:
                for aSel in dlg.selection:
                    schemaName = aSel[0]
                    tableName = aSel[1]
                    geomColumn = aSel[2]
                    description = aSel[3]
                    ddTable = self.app.ddManager.createDdTable(self.db,
                        schemaName, tableName, withOid = False,
                        withComment = False)

                    if ddTable != None:
                        layer = self.app.ddManager.loadPostGISLayer(self.db,
                            ddTable, geomColumn = geomColumn)

                        if layer != None:
                            layer.setTitle(tableName)
                            layer.setAbstract(description)
                            ddInit = self.layerInitialize(layer)

                            if ddInit:
                                self.app.ddManager.addAction(layer,
                                    actionName = "XP_Sachdaten")

                            grpIdx = self.getGroupIndex(schemaName)

                            if grpIdx == -1:
                                grpIdx = self.createGroup(schemaName)

                            self.iface.legendInterface().moveLayer(layer, grpIdx)

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
            else:
                self.aktiveBereiche = bereichsAuswahl # keine Auswahl => keine aktiven Bereiche

    def layerInitializeSlot(self):
        layer = self.iface.activeLayer()

        if layer != None:
            if self.db == None:
                self.initialize(False)
            self.layerInitialize(layer)
            self.app.ddManager.addAction(layer, actionName = "XP_Sachdaten")
            self.iface.mapCanvas().refresh() # neuzeichnen

    def saveStyleSlot(self):
        layer = self.iface.activeLayer()

        if layer != None:
            if self.db == None:
                self.initialize(False)

        if self.layerLayer == None:
            if not self.loadLayerLayer():
                return None

        self.app.ddManager.removeAction(layer, actionName = "XP_Sachdaten")
        newFeat = self.tools.createFeature(self.layerLayer)
        doc = self.tools.getXmlLayerStyle(layer)

        if doc != None:
            newFeat[self.layerLayer.fieldNameIndex("style")] = doc.toString()
            layerDdTable = self.app.ddManager.makeDdTable(layer, self.db)

            if layerDdTable != None:
                newFeat[self.layerLayer.fieldNameIndex("schemaname")] = layerDdTable.schemaName
                newFeat[self.layerLayer.fieldNameIndex("tablename")] = layerDdTable.tableName

                if self.tools.setEditable(self.layerLayer, True, self.iface):
                    if self.layerLayer.addFeature(newFeat):
                        self.app.ddManager.showFeatureForm(
                            self.layerLayer, newFeat, askForSave = False)

        self.app.ddManager.addAction(layer, actionName = "XP_Sachdaten")

    def changeSavedStyleSlot(self):
        layer = self.iface.activeLayer()

        if layer != None:
            if self.db == None:
                self.initialize(False)

            styleList = self.getLayerStyle(layer)

            if styleList != None:
                if self.layerLayer == None:
                    if not self.loadLayerLayer():
                        return None

                stilId = styleList[0]
                feat = QgsFeature()

                if self.layerLayer.getFeatures(
                        QgsFeatureRequest().setFilterFid(stilId).setFlags(
                        QgsFeatureRequest.NoGeometry)).nextFeature(feat):
                    self.app.ddManager.removeAction(layer, actionName = "XP_Sachdaten")
                    doc = self.tools.getXmlLayerStyle(layer)

                    if doc != None:
                        feat[self.layerLayer.fieldNameIndex("style")] = doc.toString()

                        if self.app.ddManager.showFeatureForm(
                                self.layerLayer, feat) != 0:
                            if self.tools.setEditable(self.layerLayer):
                                self.layerLayer.changeAttributeValue(
                                    stilId, self.layerLayer.fieldNameIndex("style"),
                                    doc.toString())
                                if not self.layerLayer.commitChanges():
                                    XpError(u"Konnte Änderungen an " + \
                                    self.layerLayer.name() + u"nicht speichern!",
                                    self.iface)

                    self.app.ddManager.addAction(layer, actionName = "XP_Sachdaten")

    def layerStyleSlot(self):
        layer = self.iface.activeLayer()

        if layer != None:

            if self.db == None:
                self.initialize(False)

            ddInit = self.layerInitialize(layer)
            aStyleList = self.getLayerStyle(layer)

            if aStyleList != None :
                aStyle = aStyleList[1] # 0 ist die styleId

                if ddInit:
                    self.layerJoinParent(layer)
                    self.layerJoinXP_Objekt(layer)

                self.tools.styleLayer(layer,  aStyle)

            if ddInit:
                self.app.ddManager.addAction(layer, actionName = "XP_Sachdaten")

            self.iface.mapCanvas().refresh() # neuzeichnen

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

    def getGroupIndex(self, groupName):
        '''Finde den Gruppenindex für Gruppe groupName'''
        retValue = -1
        groups = self.iface.legendInterface().groups()

        for i in range(len(groups)):
            if groups[i] == groupName:
                retValue = i
                break

        return retValue

    def layerJoinParent(self,  layer):
        ddTable = self.app.ddManager.ddLayers[layer.id()][0]
        parents = self.ddUi.getParents(ddTable,  self.db)

        if len(parents) > 0:
            parentLayer = self.app.ddManager.findPostgresLayer(self.db,  parents[0])

            if parentLayer == None:
                parentLayer = self.app.ddManager.loadPostGISLayer(self.db,  parents[0])

            prefix = parents[0].tableName + "."
            self.tools.joinLayer(layer, parentLayer, prefix = prefix, memoryCache = True)

    def layerJoinXP_Objekt(self,  layer):
        '''den Layer XP_Objekt an den Layer joinen'''
        xpObjektDdTable = self.app.ddManager.createDdTable(
            self.db, "XP_Basisobjekte", "XP_Objekt",
            withOid = False, withComment = False)

        if xpObjektDdTable != None:
            xpObjektLayer = self.app.ddManager.findPostgresLayer(self.db, xpObjektDdTable)

            if xpObjektLayer == None:
                xpObjektLayer = self.app.ddManager.loadPostGISLayer(self.db, xpObjektDdTable)

            self.tools.joinLayer(layer, xpObjektLayer, memoryCache = True,
                prefix = "XP_Objekt.")

    def layerInitialize(self,  layer,  msg = False,  layerCheck = True):
        '''einen XP_Layer initialisieren, gibt Boolschen Wert zurück'''
        ddInit = False

        if 0 == layer.type(): # Vektorlayer
            layerRelation = self.tools.getPostgresRelation(layer)

            if layerRelation != None: # PostgreSQL-Layer
                try:
                    self.app.ddManager.ddLayers[layer.id()] # bereits initialisiert
                    ddInit = True
                except KeyError:
                    ddInit = self.app.ddManager.initLayer(layer,  skip = [], createAction = False,  db = self.db)

                if layerRelation[2]: # Layer hat Geometrien
                    schema = layerRelation[0]
                    table = layerRelation[1]

                    if schema != "XP_Praesentationsobjekte":
                        schemaTyp = schema[:2]

                        if table != schemaTyp + "_Plan" and table != schemaTyp + "_Bereich":
                            if self.implementedSchemas.count(schemaTyp) > 0:
                                layer.committedFeaturesAdded.connect(self.featuresAdded)
                                layer.editingStopped.connect(self.editingHasStopped)
                                self.addedGeometries[layer.id()] = []

                                if layerCheck:
                                    self.aktiverBereichLayerCheck(layer)

                        #spezielle Aktionen mit speziellen Layern
                        if table == "FP_GemeinbedarfFlaeche" or \
                            table == "FP_GemeinbedarfLinie" or \
                            table == "FP_GemeinbedarfPunkt":
                            zweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Gemeinbedarf_Spiel_und_Sportanlagen",
                                "FP_Gemeinbedarf_zweckbestimmung",
                                withOid = False, withComment = False)

                            if zweckbestDdTable != None:
                                zweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, zweckbestDdTable)

                                if zweckbestLayer == None:
                                    zweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, zweckbestDdTable)

                                if zweckbestLayer != None:
                                    self.tools.joinLayer(layer, zweckbestLayer,
                                        prefix = "XP_ZweckbestimmungGemeinbedarf.")

                            besZweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Gemeinbedarf_Spiel_und_Sportanlagen",
                                "FP_Gemeinbedarf_besondereZweckbestimmung",
                                withOid = False, withComment = False)

                            if besZweckbestDdTable != None:
                                besZweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, besZweckbestDdTable)

                                if besZweckbestLayer == None:
                                    besZweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, besZweckbestDdTable)

                                if besZweckbestLayer != None:
                                    self.tools.joinLayer(layer, besZweckbestLayer,
                                        prefix = "XP_BesondereZweckbestGemeinbedarf.")

                        elif table == "FP_GruenFlaeche" or \
                            table == "FP_GruenLinie" or \
                            table == "FP_GruenPunkt":
                            zweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Landwirtschaft_Wald_und_Gruen",
                                "FP_Gruen_zweckbestimmung",
                                withOid = False, withComment = False)

                            if zweckbestDdTable != None:
                                zweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, zweckbestDdTable)

                                if zweckbestLayer == None:
                                    zweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, zweckbestDdTable)

                                if zweckbestLayer != None:
                                    self.tools.joinLayer(layer, zweckbestLayer,
                                        prefix = "XP_ZweckbestimmungGruen.")

                            besZweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Landwirtschaft_Wald_und_Gruen",
                                "FP_Gruen_besondereZweckbestimmung",
                                withOid = False, withComment = False)

                            if besZweckbestDdTable != None:
                                besZweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, besZweckbestDdTable)

                                if besZweckbestLayer == None:
                                    besZweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, besZweckbestDdTable)

                                if besZweckbestLayer != None:
                                    self.tools.joinLayer(layer, besZweckbestLayer,
                                        prefix = "XP_BesondereZweckbestGruen.")
                        elif table == "FP_PrivilegiertesVorhabenFlaeche" or \
                            table == "FP_PrivilegiertesVorhabenLinie" or \
                            table == "FP_PrivilegiertesVorhabenPunkt":
                            zweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Sonstiges",
                                "FP_PrivilegiertesVorhaben_zweckbestimmung",
                                withOid = False, withComment = False)

                            if zweckbestDdTable != None:
                                zweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, zweckbestDdTable)

                                if zweckbestLayer == None:
                                    zweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, zweckbestDdTable)

                                if zweckbestLayer != None:
                                    self.tools.joinLayer(layer, zweckbestLayer,
                                        prefix = "FP_ZweckbestimmungPrivilegiertesVorhaben.")

                            besZweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Sonstiges",
                                "FP_PrivilegiertesVorhaben_besondereZweckbestimmung",
                                withOid = False, withComment = False)

                            if besZweckbestDdTable != None:
                                besZweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, besZweckbestDdTable)

                                if besZweckbestLayer == None:
                                    besZweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, besZweckbestDdTable)

                                if besZweckbestLayer != None:
                                    self.tools.joinLayer(layer, besZweckbestLayer,
                                        prefix = "FP_BesondZweckbestPrivilegiertesVorhaben.")
                        elif table == "FP_VerEntsorgungFlaeche" or \
                            table == "FP_VerEntsorgungLinie" or \
                            table == "FP_VerEntsorgungPunkt":
                            zweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Ver_und_Entsorgung",
                                "FP_VerEntsorgung_zweckbestimmung",
                                withOid = False, withComment = False)

                            if zweckbestDdTable != None:
                                zweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, zweckbestDdTable)

                                if zweckbestLayer == None:
                                    zweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, zweckbestDdTable)

                                if zweckbestLayer != None:
                                    self.tools.joinLayer(layer, zweckbestLayer,
                                        prefix = "FP_ZweckbestimmungVerEntsorgung.")

                            besZweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Ver_und_Entsorgung",
                                "FP_VerEntsorgung_besondereZweckbestimmung",
                                withOid = False, withComment = False)

                            if besZweckbestDdTable != None:
                                besZweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, besZweckbestDdTable)

                                if besZweckbestLayer == None:
                                    besZweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, besZweckbestDdTable)

                                if besZweckbestLayer != None:
                                    self.tools.joinLayer(layer, besZweckbestLayer,
                                        prefix = "FP_BesondZweckbestVerEntsorgung.")
                        elif table == "FP_SpielSportanlageFlaeche" or \
                            table == "FP_SpielSportanlageLinie" or \
                            table == "FP_SpielSportanlagePunkt":
                            zweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Gemeinbedarf_Spiel_und_Sportanlagen",
                                "FP_SpielSportanlage_zweckbestimmung",
                                withOid = False, withComment = False)

                            if zweckbestDdTable != None:
                                zweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, zweckbestDdTable)

                                if zweckbestLayer == None:
                                    zweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, zweckbestDdTable)

                                if zweckbestLayer != None:
                                    self.tools.joinLayer(layer, zweckbestLayer,
                                        prefix = "XP_ZweckbestimmungSpielSportanlage.")
                        elif table == "FP_KennzeichnungFlaeche" or \
                            table == "FP_KennzeichnungLinie" or \
                            table == "FP_KennzeichnungPunkt":
                            zweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Sonstiges",
                                "FP_Kennzeichnung_zweckbestimmung",
                                withOid = False, withComment = False)

                            if zweckbestDdTable != None:
                                zweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, zweckbestDdTable)

                                if zweckbestLayer == None:
                                    zweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, zweckbestDdTable)

                                if zweckbestLayer != None:
                                    self.tools.joinLayer(layer, zweckbestLayer,
                                        prefix = "XP_ZweckbestimmungKennzeichnung.")
                        elif table == "FP_WaldFlaeche":
                            zweckbestDdTable = self.app.ddManager.createDdTable(
                                self.db, "FP_Landwirtschaft_Wald_und_Gruen",
                                "FP_WaldFlaeche_zweckbestimmung",
                                withOid = False, withComment = False)

                            if zweckbestDdTable != None:
                                zweckbestLayer = self.app.ddManager.findPostgresLayer(
                                    self.db, zweckbestDdTable)

                                if zweckbestLayer == None:
                                    zweckbestLayer = self.app.ddManager.loadPostGISLayer(
                                        self.db, zweckbestDdTable)

                                if zweckbestLayer != None:
                                    self.tools.joinLayer(layer, zweckbestLayer,
                                        prefix = "XP_ZweckbestimmungWald.")
            else:
                if msg:
                    XpError("Der Layer " + layer.name() + " ist kein PostgreSQL-Layer!",
                        self.iface)
        else: # not a vector layer
            if msg:
                XpError("Der Layer " + layer.name() + " ist kein VektorLayer!",
                    self.iface)

        return ddInit

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
                        if len(self.aktiveBereiche) == 0:
                            thisChoice = QtGui.QMessageBox.question(None, "Keine aktiven Bereiche",
                            u"Wollen Sie aktive Bereiche festlegen? ",
                            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

                            if thisChoice == QtGui.QMessageBox.Yes:
                                self.aktiveBereicheFestlegen()
                            else:
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
                                    "Objektbereichen: aktive Bereiche = " + bereichTyp + ", " + layer.name() + " = " + \
                                    schemaTyp + ". Wollen Sie die aktiven Bereiche ändern? ",
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
                # da nur Bereiche einer Art ausgewählt werden können, reicht es den Typ des ersten Bereiches festzustellen
                gehoertZuSchema = bereichTyp + "_Basisobjekte"
                gehoertZuTable = "gehoertZu" + bereichTyp + "_Bereich"
                gehoertZuDdTable = self.app.ddManager.createDdTable(
                    self.db, gehoertZuSchema, gehoertZuTable,
                    withOid = False,  withComment = False)

                if gehoertZuDdTable != None:
                    gehoertZuLayer = self.app.ddManager.findPostgresLayer(
                        gehoertZuDdTable, self.db.databaseName())

                    if gehoertZuLayer == None:
                        gehoertZuLayer = self.app.ddManager.loadPostGISLayer(
                            self.db, gehoertZuDdTable)

                        if gehoertZuLayer == None:
                            return False

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
                    layers = self.tools.getLayerInBereich(self.db,  bereich)
                    #rausbekommen, welche Layer nachrichtlich Elemente im Bereich haben?
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
                        "FROM \""+ bereichTyp + "_Basisobjekte\".\"gehoertZu" + bereichTyp + "_Bereich\" " + \
                        "WHERE \"" + bereichTyp + "_Bereich_gid\" = " + str(bereich) + ")"

                    for aLayerType in layers:
                        for aKey in aLayerType.iterkeys():
                            for aRelName in aLayerType[aKey]:
                                aDdTable = self.app.ddManager.createDdTable(self.db,
                                    aKey, aRelName, withOid = False, withComment = False)

                                if aDdTable != None:
                                    aLayer = self.app.ddManager.loadPostGISLayer(self.db,
                                        aDdTable, geomColumn = 'position',
                                        whereClause = filter)

                                    # layer initialisieren
                                    if self.layerInitialize(aLayer,  msg=True,  layerCheck = False):
                                        # Stil des Layers aus der DB holen und anwenden
                                        aStyleList = self.getLayerStyle(aLayer, bereich)

                                        if aStyleList != None:
                                            aStyle = aStyleList[1]
                                            self.layerJoinParent(aLayer)

                                            if not self.tools.styleLayer(aLayer,  aStyle):
                                                break

                                        self.app.ddManager.addAction(aLayer, actionName = "XP_Sachdaten")

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
