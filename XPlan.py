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
            from DataDrivenInputMask import ddui

            try:
                self.app.ddManager
            except AttributeError:
                ddManager = ddui.DdManager(self.iface)
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
        self.fpMenu = QtGui.QMenu(u"FPlan")
        self.lpMenu = QtGui.QMenu(u"LPlan")

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

        self.xpMenu.addActions([self.action0,  self.action2])
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

    def initialize(self):
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
                self.aktiveBereicheFestlegen()

    def aktiveBereicheFestlegen(self):
        '''Auswahl der Bereiche, in die neu gezeichnete Elemente eingefügt werden sollen'''
        if self.db == None:
            self.initialize()

        if self.db:
            bereichsAuswahl = self.tools.chooseBereich(self.db,  True,  u"Aktive Bereiche festlegen")

            if len(bereichsAuswahl) > 0: # Auswahl wurde getroffen oder es wurde abgebrochen
                if bereichsAuswahl[0] != -1: # Auswahl vorhanden, da [-1] = Abbruch;
                                                            #bei Abbruch bleiben die bisherigen aktiven Bereiche
                    self.aktiveBereiche = bereichsAuswahl
            else:
                self.aktiveBereiche = bereichsAuswahl # keine Auswahl => keine aktiven Bereiche

    def layerInitializeSlot(self):
        layer = self.iface.activeLayer()

        if layer != None:
            self.layerInitialize(layer)

    def layerInitialize(self,  layer,  msg = False):
        '''einen XP_Layer initialisieren'''

        if 0 == layer.type(): # Vektorlayer
            layerRelation = self.tools.getPostgresRelation(layer)

            if layerRelation != None: # PostgreSQL-Layer
                self.app.ddManager.initLayer(layer,  skip = [])

                if layerRelation[2]: # Geometrielayer
                    schema = layerRelation[0]
                    table = layerRelation[1]

                    if schema !="XP_Praesentationsobjekte":
                        schemaTyp = schema[:2]

                        if  table != schemaTyp + "_Plan" and table != schemaTyp + "_Bereich":
                            if schemaTyp == "FP" or schemaTyp == "BP" or schemaTyp == "LP":
                                layer.committedFeaturesAdded.connect(self.featuresAdded)
                                layer.editingStopped.connect(self.editingHasStopped)
                                self.addedGeometries[layer.id()] = []
                                self.aktiverBereichLayerCheck(layer)
            else:
                if msg:
                    XpError("Der Layer " + layer.name() + " ist kein PostgreSQL-Layer!")
        else: # not a vector layer
            if msg:
                XpError("Der Layer " + layer.name() + " ist kein VektorLayer!")

    def aktiverBereichLayerCheck(self,  layer):
        '''Prüfung, ob übergebener Layer und aktive Bereiche dem selben Objektbereich entsammen'''
        layerRelation = self.tools.getPostgresRelation(layer)
        retValue = False

        if layerRelation != None: #  PostgreSQL-Layer
            if layerRelation[2]: # Geometrielayer
                schema = layerRelation[0]

                if schema !="XP_Praesentationsobjekte":
                    schemaTyp = schema[:2]

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
                            bereichTyp = self.tools.getBereichTyp(self.db,  self.aktiveBereiche[0])

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
                bereichTyp = self.tools.getBereichTyp(self.db,  self.aktiveBereiche[0]) #
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

                self.debug(str(newFeat))

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
            bereich = self.tools.chooseBereich(self.db)
            if len(bereich) > 0:
                if bereich[0] >= 0:
                    # rausbekommen, welche Layer Elemente im Bereich haben
                    bereichTyp = self.tools.getBereichTyp(self.db,  bereich)
                    layers = self.tools.getLayerInBereich(self.db,  bereichTyp)
                    # eine Gruppe für den Bereich machen
                    # qml für Layer aus DB holen
                    # Layer in die Gruppe laden und features entsprechend einschränken

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
                                newGid = selFeature["gid"].toInt()[0]
                                newGids.append(newGid)
                                break

                    layer.removeSelection()
                    layer.select(newGids)

                    if self.aktivenBereichenZuordnen(layer):
                        if not gehoertZuLayer.commitChanges():
                            XpError(u"Konnte Änderungen am Layer " + gehoertZuLayer.name() + " nicht speichern!")
                except KeyError:
                    continue

    def featuresAdded(self,  layerId,  featureList):
        newGeoms = []

        for aFeature in featureList:
            newGeoms.append(QgsGeometry(aFeature.geometry())) # Kopie der Geometrie

        self.addedGeometries[layerId] = newGeoms

    def showQueryError(self, query):
        self.tools.showQueryError(query)
