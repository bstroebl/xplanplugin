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
from PyQt4 import QtCore, QtGui
from qgis.core import *
from qgis.gui import *
import sys
from HandleDb import DbHandler
from XPTools import XPTools

class XpError(object):
    '''General error'''
    def __init__(self,  value):
        self.value = value
        QtGui.QMessageBox.warning(None, "XPlanung",  value)
    def __str__(self):
        return repr(self.value)

class XPlan():
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.app = QgsApplication.instance()
        self.dbHandler = DbHandler()
        self.db = None
        self.tools = XPTools(self.iface)
        self.aktiveBereiche = []
        self.addedGeometries = {}
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
            from DataDrivenInputMask import ddui,  ddmanager
            self.ddUi = ddui.DataDrivenUi(self.iface)

            try:
                self.app.ddManager
            except AttributeError:
                ddManager = ddmanager.DdManager(self.iface)
                self.app.ddManager = ddManager
        except ImportError:
            self.unload()
            XpError("Bitte installieren Sie das Plugin DataDrivenInputMask aus dem QGIS Official Repository!")

    def initGui(self):
        # Code von fTools

        self.xpMenu = QtGui.QMenu(u"XPlanung")
        self.bereichMenu = QtGui.QMenu(u"XP_Bereich")
        self.bereichMenu.setToolTip(u"Ein Planbereich fasst die Inhalte eines Plans nach bestimmten Kriterien zusammen.")
        self.bpMenu = QtGui.QMenu(u"BPlan")
        self.bpMenu.setToolTip(u"Fachschema BPlan für Bebauungspläne")
        self.fpMenu = QtGui.QMenu(u"FPlan")
        self.fpMenu.setToolTip(u"Fachschema FPlan für Flächennutzungspläne")
        self.lpMenu = QtGui.QMenu(u"LPlan")
        self.lpMenu.setToolTip(u"Fachschema LPlan für Landschaftspläne")

        self.action0 = QtGui.QAction(u"Initialisieren", self.iface.mainWindow())
        self.action0.triggered.connect(self.initialize)
        self.action1 = QtGui.QAction(u"Bereich laden", self.iface.mainWindow())
        self.action1.setToolTip(u"Alle zu einem Bereich gehörenden Elemente laden und nach PlZVO darstellen")
        self.action1.triggered.connect(self.bereichLaden)
        self.action2 = QtGui.QAction(u"Layer initialisieren", self.iface.mainWindow())
        self.action2.setToolTip(u"aktiver Layer: Eingabemaske erzeugen, neue Features den aktiven Bereichen zuweisen.")
        self.action2.triggered.connect(self.layerInitializeSlot)
        self.action3 = QtGui.QAction(u"Aktive Bereiche festlegen", self.iface.mainWindow())
        self.action3.setToolTip(u"Elemente von Layern können automatisch oder händisch den aktiven Bereichen zugewiesen werden. \
                                Damit werden sie zum originären Inhalt des Planbereichs.")
        self.action3.triggered.connect(self.aktiveBereicheFestlegen)
        self.action4 = QtGui.QAction(u"Auswahl den aktiven Bereichen zuordnen", self.iface.mainWindow())
        self.action4.setToolTip(u"aktiver Layer: ausgewählte Elemente den aktiven Bereichen zuweisen. \
                                Damit werden sie zum originären Inhalt des Planbereichs.")
        self.action4.triggered.connect(self.aktivenBereichenZuordnenSlot)
        self.action5 = QtGui.QAction(u"Auswahl nachrichtlich übernehmen", self.iface.mainWindow())
        self.action5.setToolTip(u"aktiver Layer: ausgewählte Elemente nachrichtlich den aktiven Bereichen zuweisen.")
        self.action5.triggered.connect(self.aktivenBereichenNachrichtlichZuordnenSlot)
        self.action6 = QtGui.QAction(u"Layer PlZVO-konform darstellen", self.iface.mainWindow())
        self.action6.setToolTip(u"aktiver Layer: gespeicherten Stil anwenden")
        self.action6.triggered.connect(self.layerStyleSlot)

        self.xpMenu.addActions([self.action0,  self.action2,  self.action6])
        self.bereichMenu.addActions([self.action1,  self.action3,  self.action4,  self.action5])
        # Add toolbar button and menu item
        self.tmpAct = QtGui.QAction(self.iface.mainWindow())
        self.iface.addPluginToVectorMenu("tmp", self.tmpAct) # sicherstellen, dass das VektorMenu da ist
        self.vectorMenu = self.iface.vectorMenu()
        self.vectorMenu.addMenu(self.xpMenu)
        self.vectorMenu.addMenu(self.bereichMenu)
        self.vectorMenu.addMenu(self.bpMenu)
        self.vectorMenu.addMenu(self.fpMenu)
        self.vectorMenu.addMenu(self.lpMenu)
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

    def debug(self,  msg):
        QtGui.QMessageBox.information(None, "Debug",  msg)

    #Slots

    def initialize(self,  aktiveBereiche = True):
        self.db = self.dbHandler.dbConnectSelected()

        if self.db != None:
            if not self.tools.isXpDb(self.db):
                QtGui.QMessageBox.warning(None, "Falsche Datenbank",
                u"Die aktive Datenbank ist keine XPlan-Datenbank. Bitte \
                verbinden Sie sich mit einer solchen und initialisieren \
                Sie dann erneut.")
                self.dbHandler.dbDisconnect()
                self.db = None
            else:
                if aktiveBereiche:
                    self.aktiveBereicheFestlegen()

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

    def layerStyleSlot(self):
        layer = self.iface.activeLayer()

        if layer != None:
            if self.db == None:
                self.initialize(False)
            ddInit = self.layerInitialize(layer)
            aStyle = self.tools.getLayerStyle(self.db,  layer)

            if aStyle:
                if ddInit:
                    self.layerJoinParent(layer)
                    self.layerJoinXP_Objekt(layer)
                self.tools.styleLayer(layer,  aStyle)

            if ddInit:
                self.app.ddManager.addAction(layer, actionName = "XP_Sachdaten")

            self.iface.mapCanvas().refresh() # neuzeichnen

    def layerJoinParent(self,  layer):
        ddTable = self.app.ddManager.ddLayers[layer.id()][0]
        parents = self.ddUi.getParents(ddTable,  self.db)

        if len(parents) > 0:
            parentLayer = self.app.ddManager.findPostgresLayer(self.db,  parents[0])

            if parentLayer == None:
                parentLayer = self.app.ddManager.loadPostGISLayer(self.db,  parents[0])

            self.tools.joinLayer(layer,  parentLayer,  memoryCache = True)

    def layerJoinXP_Objekt(self,  layer):
        '''den Layer XP_Objekt an den Layer joinen'''
        xpObjektLayer = self.tools.findPostgresLayer("XP_Basisobjekte",  "XP_Objekt", self.db.databaseName(), self.db.hostName())

        if xpObjektLayer:
            self.tools.joinLayer(layer,  xpObjektLayer,  memoryCache = True)

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

                    if schema !="XP_Praesentationsobjekte":
                        schemaTyp = schema[:2]

                        if  table != schemaTyp + "_Plan" and table != schemaTyp + "_Bereich":
                            if self.implementedSchemas.count(schemaTyp) > 0:
                                layer.committedFeaturesAdded.connect(self.featuresAdded)
                                layer.editingStopped.connect(self.editingHasStopped)
                                self.addedGeometries[layer.id()] = []

                                if layerCheck:
                                    self.aktiverBereichLayerCheck(layer)
            else:
                if msg:
                    XpError("Der Layer " + layer.name() + " ist kein PostgreSQL-Layer!")
        else: # not a vector layer
            if msg:
                XpError("Der Layer " + layer.name() + " ist kein VektorLayer!")

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
                                u"Die momentan aktiven Bereiche und der Layer stammen aus unterschiedlichen \
                    Objektbereichen: aktive Bereiche = " + bereichTyp + ", " + layer.name() + " = " +
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
                gehoertZuLayer = self.tools.findPostgresLayer(gehoertZuSchema, gehoertZuTable,  self.db.databaseName(),  self.db.hostName())

                if gehoertZuLayer == None:
                    gehoertZuLayer = self.tools.loadPostGISLayer(self.db,  gehoertZuSchema,  gehoertZuTable)

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
                        XpError(u"Bereichszuordnung: Bitte speichern Sie zuerst den Layer " + layer.name())
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
            self.db = self.dbHandler.dbConnectSelected()

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
                                aLayer = self.tools.loadPostGISLayer(self.db,  aKey,  aRelName, geomColumn = 'position',
                                                                whereClause = filter)

                                # layer initialisieren
                                if self.layerInitialize(aLayer,  msg=True,  layerCheck = False):
                                    # Stil des Layers aus der DB holen und anwenden
                                    aStyle = self.tools.getLayerStyle(self.db,  aLayer,  bereich)

                                    if aStyle:
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
                            XpError(u"Konnte Änderungen am Layer " + gehoertZuLayer.name() + " nicht speichern!")
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
