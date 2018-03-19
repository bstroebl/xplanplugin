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

try:
    from DataDrivenInputMask.ddattribute import DdTable
except:
    pass

import sys, os

BASEDIR = os.path.dirname( unicode(__file__,sys.getfilesystemencoding()) )

from HandleDb import DbHandler
from XPTools import XPTools
from XPlanDialog import XPlanungConf
from XPlanDialog import ChooseObjektart
from XPlanDialog import XPNutzungsschablone

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
        self.app.xpPlugin = self
        self.nutzungsschablone = None
        self.dbHandler = DbHandler(self.iface)
        self.db = None
        self.tools = XPTools(self.iface, self.standardName, self.simpleStyleName)
        self.aktiveBereiche = {}
        self.xpLayers = {} # dict, key = layerId
            # item = [layer (QgsVectorLayer), maxGid (long), featuresHaveBeenAdded (Bolean)]
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

        # Layer der die Zuordnung von Objekten zu Bereichen enthält
        self.gehoertZuLayer = None

        qs = QtCore.QSettings( "QGIS", "QGIS2" )
        svgpaths = qs.value( "svg/searchPathsForSVG", "", type=str ).split("|")
        svgpath = os.path.abspath( os.path.join( BASEDIR, "svg" ) )
        if not svgpath.upper() in map(unicode.upper, svgpaths):
            svgpaths.append( svgpath )
            qs.setValue( "svg/searchPathsForSVG", u"|".join( svgpaths ) )

        self.initializeAllLayers()

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
        self.rpMenu = QtGui.QMenu(u"Regionalplan")
        self.rpMenu.setToolTip(u"Fachschema für Regionalpläne")
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
        self.action3.triggered.connect(self.aktiveBereicheFestlegenSlot)
        self.action3a = QtGui.QAction(u"Aktive Bereiche entfernen", self.iface.mainWindow())
        self.action3a.setToolTip(u"")
        self.action3a.setEnabled(False)
        self.action3a.triggered.connect(self.aktiveBereicheLoeschen)
        self.action3b = QtGui.QAction(u"Nur Objekte in aktiven Bereichen anzeigen", self.iface.mainWindow())
        self.action3b.setToolTip(u"")
        self.action3b.triggered.connect(self.aktiveBereicheFilternSlot)
        self.action4 = QtGui.QAction(u"Auswahl den aktiven Bereichen zuordnen", self.iface.mainWindow())
        self.action4.setToolTip(u"aktiver Layer: ausgewählte Elemente den aktiven Bereichen zuweisen. " +\
                                u"Damit werden sie zum originären Inhalt des Planbereichs.")
        self.action4.triggered.connect(self.aktivenBereichenZuordnenSlot)
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
        self.action27 = QtGui.QAction(u"Objektart laden", self.iface.mainWindow())
        self.action27.triggered.connect(self.loadRP)
        self.action28 = QtGui.QAction(u"Nutzungsschablone konfigurieren", self.iface.mainWindow())
        self.action28.triggered.connect(self.konfiguriereNutzungsschablone)
        self.action29 = QtGui.QAction(u"Stylesheetparameter konfigurieren", self.iface.mainWindow())
        self.action29.triggered.connect(self.konfiguriereStylesheet)

        self.xpMenu.addActions([self.action20, self.action25, self.action29,
            self.action6, self.action10])
        self.bereichMenu.addActions([self.action1, self.action3, self.action3a,
            self.action3b, self.action4])
        self.bpMenu.addActions([self.action21, self.action26, self.action28])
        self.fpMenu.addActions([self.action22])
        self.lpMenu.addActions([self.action23])
        self.rpMenu.addActions([self.action27])
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
        self.vectorMenu.addMenu(self.rpMenu)
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
            self.vectorMenu.removeAction(self.rpMenu.menuAction())
            self.vectorMenu.removeAction(self.soMenu.menuAction())
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

    def erzeugeNutzungsschablone(self, gid):
        '''
        die Werte für die Nutzungsschablone aus der DB auslesen
        und als String zurückgeben
        '''
        returnValue = [None, None, None]

        if self.nutzungsschablone != None:
            # Anzeahl Zeilen und Spalten feststellen
            if self.nutzungsschablone[1] != None or \
                    self.nutzungsschablone[3] != None or \
                    self.nutzungsschablone[5] != None:
                anzSpalten = 2
            else:
                anzSpalten = 1

            if self.nutzungsschablone[2] != None or \
                    self.nutzungsschablone[3] != None:
                anzZeilen = 2

                if self.nutzungsschablone[4] != None or \
                        self.nutzungsschablone[5] != None:
                    anzZeilen = 3
            else:
                anzZeilen = 1

            # Abfrage bauen
            sQuery = "SELECT "

            for fld in self.nutzungsschablone:
                if fld == None:
                    fld = "NULL"
                else:
                    fld = "\"" + fld + "\""

                if sQuery != "SELECT ":
                    sQuery += ","

                sQuery += fld

            sQuery += " FROM \"BP_Bebauung\".\"BP_BaugebietsTeilFlaeche\" b \
            JOIN \"BP_Bebauung\".\"BP_BaugebietObjekt\" o ON b.gid = o.gid \
            JOIN \"BP_Bebauung\".\"BP_FestsetzungenBaugebiet\" f ON b.gid = f.gid \
            WHERE b.gid = :gid;"
            query = QtSql.QSqlQuery(self.db)
            query.prepare(sQuery)
            query.bindValue(":gid", gid)
            # DB abfragen
            query.exec_()

            if query.isActive():
                werte = []
                while query.next():
                    for i in range(len(self.nutzungsschablone)):
                        werte.append(query.value(i))

                query.finish()
            else:
                self.tools.showQueryError(query)
                return returnValue

            #Text zusammenbauen
            allgArtBlNtzg = {1000:"W", 2000:"M", 3000:"G", 4000:"S", 9999:"Sonst"}
            besArtBlNtzg = {1000:"WS", 1100:"WR", 1200:"WA", 1300:"WB", 1400:"MD", 1500:"MI",
                1600:"MK", 1700:"GE", 1800:"GI", 2000:"SO", 2100:"SO", 3000:"SO", 4000:"SO", 9999:"Sonst"}
            bauweise = {1000:"o", 2000:"g"}
            #bebArt = {1000:"E", 2000:"D", 3000:"H", 4000:"ED", 5000:"EH", 6000:"DH", 7000:"R"}
            geschoss = {1:"I", 2:"II", 3:"III", 4:"IV", 5:"V", 6:"VI", 7:"VII", 8:"VIII", 9:"IX", 10:"X",
                11:"XI", 12:"XII", 13:"XIII", 14:"XIV", 15:"XV", 16:"XVI", 17:"XVII", 18:"XVIII", 19:"XIX", 20:"XX"}
            schablonenText = ""
            loc = QtCore.QLocale.system()

            for i in range(len(self.nutzungsschablone)):
                fld = self.nutzungsschablone[i]
                wert = werte[i]

                if fld != None and wert != None:
                    if fld == "allgArtDerBaulNutzung":
                        thisStr = allgArtBlNtzg[wert]
                    elif fld == "besondereArtDerBaulNutzung":
                        thisStr = besArtBlNtzg[wert]
                    elif fld == "bauweise":
                        thisStr = bauweise[wert]
                    elif fld == "GFZ" or fld == "GFZmin":
                        thisStr = "GFZ " + loc.toString(wert)
                    elif fld == "GFZmax":
                        thisStr = "bis " + loc.toString(wert)
                    elif fld == "GF" or fld == "GFmin":
                        thisStr = "GF " + str(wert) + u" m²"
                    elif fld == "GFmax":
                        thisStr = "bis " + str(wert) + u" m²"
                    elif fld == "BMZ" or fld == "BMZmin":
                        thisStr = "BMZ " + loc.toString(wert)
                    elif fld == "BMZmax":
                        thisStr = "bis " + loc.toString(wert)
                    elif fld == "BM" or fld == "BMmin":
                        thisStr = "BM " + str(wert) + u" m³"
                    elif fld == "BMmax":
                        thisStr = "bis " + str(wert) + u" m³"
                    elif fld == "GRZ" or fld == "GRZmin":
                        thisStr = "GRZ " + loc.toString(wert)
                    elif fld == "GRZmax":
                        thisStr = "bis " + loc.toString(wert)
                    elif fld == "GR" or fld == "GRmin":
                        thisStr = "GR " + str(wert) + u" m²"
                    elif fld == "GRmax":
                        thisStr = "bis " + str(wert) + u" m²"
                    elif fld == "Z" or  fld == "Zmin":
                        thisStr = geschoss[wert]
                    elif fld == "Zmax":
                        thisStr = " - " + geschoss[wert]
                else:
                    thisStr = ""

                if i in [0, 2, 4]:
                    zeile = " " + thisStr
                else:
                    while len(zeile) < 10:
                        zeile += " " # mit Leerzeichen auffüllen

                    zeile += thisStr

                    if (i == 1 and anzZeilen > 1) or (i == 3 and anzZeilen > 2):
                        zeile += "\n"

                    schablonenText += zeile

            returnValue = [anzSpalten, anzZeilen, schablonenText]
        return returnValue

    def plaziereNutzungsschablone(self, gid, x, y):
        ''' gid von BP_Baugebietsteilflaeche'''

        if self.nutzungsschablone == None:
            self.konfiguriereNutzungsschablone()

        if self.db == None:
            self.initialize((self.willAktivenBereich and len(self.aktiveBereiche) == 0))

        if self.db != None:
            anzSpalten,  anzZeilen, schablonenText = self.erzeugeNutzungsschablone(gid)

            if anzSpalten == None and anzZeilen == None:
                return None

            nutzungsschabloneLayer = self.getLayerForTable(
                "XP_Praesentationsobjekte", "XP_Nutzungsschablone",
                geomColumn = "position")

            if nutzungsschabloneLayer == None:
                return None
            else:
                self.layerInitialize(nutzungsschabloneLayer)

            tpoLayer = self.getLayerForTable(
                "XP_Praesentationsobjekte", "XP_TPO")

            if tpoLayer == None:
                return None

            nutzungsschabloneFeat = self.tools.createFeature(nutzungsschabloneLayer)
            nutzungsschabloneFeat[nutzungsschabloneLayer.fieldNameIndex("spaltenAnz")] = anzSpalten
            nutzungsschabloneFeat[nutzungsschabloneLayer.fieldNameIndex("zeilenAnz")] = anzZeilen
            nutzungsschabloneFeat.setGeometry(QgsGeometry.fromPoint(QgsPoint(x, y)))

            if self.tools.setEditable(nutzungsschabloneLayer):
                if not nutzungsschabloneLayer.addFeature(nutzungsschabloneFeat):
                    self.tools.showError(u"Konnte neue Nutzungsschablone nicht hinzufügen")
                    return None
                else:
                    if not nutzungsschabloneLayer.commitChanges():
                        self.tools.showError(u"Konnte neue Nutzungsschablone nicht speichern")
                        return None
                    else:
                        expr = "round($x,2) = round(" + str(x) + ",2) and round($y,2) = round(" + str(y) + ",2)"
                        #runden wegen unterschiedlicher Präzision
                        savedFeat = QgsFeature()

                        if nutzungsschabloneLayer.getFeatures(
                                QgsFeatureRequest().setFilterExpression(expr)).nextFeature(savedFeat):
                            newGid = savedFeat[nutzungsschabloneLayer.fieldNameIndex("gid")]
                        else:
                            self.tools.showError(u"Neu angelegtes Objekt nicht gefunden!")
                            return None

                        if self.tools.setEditable(tpoLayer):
                            expr = "gid = " + str(newGid)
                            tpoFeat = QgsFeature()

                            if tpoLayer.getFeatures(
                                    QgsFeatureRequest().setFilterExpression(expr)).nextFeature(tpoFeat):
                                tpoLayer.changeAttributeValue(tpoFeat.id(), tpoLayer.fieldNameIndex("schriftinhalt"),
                                    schablonenText)
                                if not tpoLayer.commitChanges():
                                    self.tools.showError(u"Konnte Schriftinhalt nicht speichern")
                                    return None

    #Slots
    def konfiguriereNutzungsschablone(self):
        dlg = XPNutzungsschablone(self.nutzungsschablone)
        dlg.show()
        result = dlg.exec_()

        if result == 1:
            self.nutzungsschablone = dlg.nutzungsschablone

    def konfiguriereStylesheet(self, isChecked = False, forCode = None):
        if self.db == None:
            self.initialize()

        stylesheetParameterLayer = self.getLayerForTable("QGIS","XP_StylesheetParameter")
        stylesheetLayer = self.getLayerForTable("XP_Praesentationsobjekte","XP_StylesheetListe")

        if stylesheetParameterLayer != None and stylesheetLayer != None:
            if forCode == None:
                forCode, ok = QtGui.QInputDialog.getInt(None, u"Stylesheetparameter konfigurieren",
                    u"Code des Stylesheets eingeben", min = 1)
            else:
                ok = True

            if ok:
                paraFeat = QgsFeature()
                expr = "\"Code\" = " + str(forCode)

                if stylesheetParameterLayer.getFeatures(QgsFeatureRequest().setFilterExpression(expr)).nextFeature(paraFeat):
                    # gibt es bereits; editieren
                    self.app.xpManager.showFeatureForm(
                            stylesheetParameterLayer, paraFeat, askForSave = False)
                else:
                    # prüfen, ob es das stylesheet schon gibt, ansonsten anlegen
                    styleFeat = QgsFeature()

                    if not stylesheetLayer.getFeatures(QgsFeatureRequest().setFilterExpression(expr)).nextFeature(styleFeat):
                        styleFeat = self.tools.createFeature(stylesheetLayer)

                        if styleFeat != None and self.tools.setEditable(stylesheetLayer, True, self.iface):
                            if not stylesheetLayer.addFeature(styleFeat):
                                self.tools.showError(u"Konnte neues Stylesheetfeature nicht einfügen")
                                stylesheetLayer.rollBack()
                                return None
                            else:
                                if not stylesheetLayer.changeAttributeValue(
                                        styleFeat.id(), stylesheetLayer.fieldNameIndex("Code"), forCode):
                                    self.tools.showError(u"Konnte Code für stylesheet nicht ändern")
                                    stylesheetLayer.rollBack()
                                    return None
                                else:
                                    if not stylesheetLayer.changeAttributeValue(
                                            styleFeat.id(), stylesheetLayer.fieldNameIndex("Bezeichner"), "Code " + str(forCode)):
                                        self.tools.showError(u"Konnte Bezeichner für stylesheet nicht ändern")
                                        stylesheetLayer.rollBack()
                                        return None
                                    else:
                                        if not stylesheetLayer.commitChanges():
                                            self.tools.showError(u"Konnte Änderungen in XP_StylesheetListe nicht speichern")
                                            return None
                                        else:
                                            self.konfiguriereStylesheet(forCode = forCode)
                    else:
                        paraFeat = self.tools.createFeature(stylesheetParameterLayer)

                        if paraFeat != None and self.tools.setEditable(stylesheetParameterLayer, True, self.iface):
                            if not stylesheetParameterLayer.addFeature(paraFeat):
                                self.tools.showError(u"Konnte neues StylesheetParameterfeature nicht einfügen")
                                stylesheetParameterLayer.rollBack()
                                return None
                            else:
                                if not stylesheetParameterLayer.changeAttributeValue(
                                        paraFeat.id(), stylesheetParameterLayer.fieldNameIndex("Code"), forCode):
                                    self.tools.showError(u"Konnte Code für stylesheetParameter nicht ändern")
                                    stylesheetParameterLayer.rollBack()
                                    return None
                                else:
                                    if not stylesheetParameterLayer.commitChanges():
                                        self.tools.showError(u"Konnte Änderungen in XP_StylesheetParamenter nicht speichern")
                                        return None
                                    else:
                                        # zeige die DataDrivenInputMask
                                        if stylesheetParameterLayer.getFeatures(
                                                QgsFeatureRequest().setFilterExpression(expr)).nextFeature(paraFeat):
                                            self.app.xpManager.showFeatureForm(
                                                    stylesheetParameterLayer, paraFeat, askForSave = False)


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
        dlg = XPlanungConf(self.dbHandler, self.tools)
        dlg.show()
        result = dlg.exec_()

        if result == 1:
            self.initialize()

    def initializeAllLayers(self):
        for layer in self.iface.legendInterface().layers():
            self.layerInitialize(layer)

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
            dlg = ChooseObjektart(objektart, self.db, self.aktiveBereiche)
            dlg.show()
            result = dlg.exec_()

            if result == 1:
                withDisplay = dlg.withDisplay
                nurAktiveBereiche = dlg.aktiveBereiche

                if nurAktiveBereiche:
                    if len(self.aktiveBereiche) == 0:
                        if self.aktiveBereicheFestlegen():
                            if len(self.aktiveBereiche) == 0:
                                nurAktiveBereiche = False

                    aktiveBereiche = self.aktiveBereicheGids()

                for aSel in dlg.selection:
                    schemaName = aSel[0]
                    tableName = aSel[1]
                    geomColumn = aSel[2]
                    description = aSel[3]
                    displayName = tableName + " (editierbar)"
                    editLayer, isView = self.loadTable(schemaName, tableName,
                        geomColumn, displayName = displayName)

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

                            if nurAktiveBereiche:
                                self.layerFilterBereich(editLayer, aktiveBereiche)

                            if tableName == "BP_BaugebietsTeilFlaeche":
                                actionNutzungsschablone = u"Nutzungsschablone plazieren"
                                createNewAction= True

                                for i in range(editLayer.actions().size()):
                                    act = editLayer.actions().at(i)

                                    if act.name() == actionNutzungsschablone:
                                        createNewAction = False
                                        break

                                if createNewAction:
                                    editLayer.actions().addAction(1, actionNutzungsschablone, # actionType 1: Python
                                        "app=QgsApplication.instance();app.xpPlugin.plaziereNutzungsschablone(" + \
                                        "[% \"gid\" %],[% $clickx %],[% $clicky %]);")

                            if withDisplay:
                                displayLayer, isView = self.loadTable(schemaName, tableName + "_qv",
                                    geomColumn)

                                if displayLayer == None:
                                    # lade Layer als Darstelllungsvariante
                                    # eigene Darstellungsvarianten gibt es nur, wenn nötig
                                    displayLayer, isView = self.loadTable(schemaName, tableName,
                                        geomColumn)

                                if displayLayer != None:
                                    if nurAktiveBereiche:
                                        self.layerFilterBereich(displayLayer, aktiveBereiche)

                                    self.iface.legendInterface().moveLayer(
                                        displayLayer, grpIdx)

                                    if stile != None:
                                        self.tools.applyStyles(displayLayer, stile)
                                        stil = self.tools.chooseStyle(displayLayer)

                                        if stil != None:
                                            self.tools.useStyle(displayLayer, stil)

    def loadTable(self,  schemaName, tableName, geomColumn,
            displayName = None, filter = None):
        '''eine Relation als Layer laden'''
        thisLayer = None

        if displayName == None:
            displayName = tableName

        if self.db != None:
            ddTable = self.app.xpManager.createDdTable(self.db,
                schemaName, tableName, withOid = False,
                withComment = False)

            isView = ddTable == None

            if isView:
                ddTable = DdTable(schemaName = schemaName, tableName = tableName)

            if self.app.xpManager.existsInDb(ddTable, self.db):
                thisLayer = self.app.xpManager.loadPostGISLayer(self.db,
                    ddTable, displayName = displayName,
                    geomColumn = geomColumn, keyColumn = "gid",
                    whereClause = filter,  intoDdGroup = False)

        return [thisLayer, isView]

    def loadXP(self):
        self.loadObjektart("XP")

    def loadBP(self):
        self.loadObjektart("BP")

    def loadFP(self):
        self.loadObjektart("FP")

    def loadLP(self):
        self.loadObjektart("LP")

    def loadRP(self):
        self.loadObjektart("RP")

    def loadSO(self):
        self.loadObjektart("SO")

    def aktiveBereicheGids(self):
        bereiche = []

        for aKey, aValue in self.aktiveBereiche.iteritems():
            bereiche.append(aKey)

        return bereiche

    def aktiveBereicheFestlegenSlot(self):
        self.willAktivenBereich = True
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
                    return None
                except KeyError:
                    self.aktiveBereiche = bereichsAuswahl

                self.willAktivenBereich = True

                if self.gehoertZuLayer == None:
                   self.createBereichZuordnungsLayer()

                self.initializeAllLayers()
            else:
                self.aktiveBereiche = bereichsAuswahl # keine Auswahl => keine aktiven Bereiche

        self.action3a.setEnabled(len(self.aktiveBereiche) > 0)
        return True

    def aktiveBereicheLoeschen(self):
        self.aktiveBereiche = []
        self.willAktivenBereich = True
        self.action3a.setEnabled(False)

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
        tableName = tableName.replace("_qv", "")
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
                schema = layerRelation[0]
                table = layerRelation[1]

                if table[:3] in ["XP_", "BP_", "FP_", "LP_", "RP_", "SO_"] and table[len(table) -3:] != "_qv":
                    try:
                        self.app.xpManager.ddLayers[layer.id()] # bereits initialisiert
                        ddInit = True
                    except KeyError:
                        ddInit = self.app.xpManager.initLayer(layer,  skip = [], createAction = False,  db = self.db)

                    if layerRelation[2]: # Layer hat Geometrien
                        schemaTyp = schema[:2]

                        if table != schemaTyp + "_Plan" and table != schemaTyp + "_Bereich":
                            if schema != "XP_Praesentationsobjekte":
                                if self.implementedSchemas.count(schemaTyp) > 0:
                                    if layerCheck:
                                        self.aktiverBereichLayerCheck(layer)

                            # disconnect slots in case they are already connected
                            try:
                                layer.committedFeaturesAdded.disconnect(self.onCommitedFeaturesAdded)
                            except:
                                pass

                            try:
                                layer.editingStopped.disconnect(self.onEditingStopped)
                            except:
                                pass

                            try:
                                layer.editingStarted.disconnect(self.onEditingStarted)
                            except:
                                pass

                            layer.committedFeaturesAdded.connect(self.onCommitedFeaturesAdded)
                            layer.editingStopped.connect(self.onEditingStopped)
                            layer.editingStarted.connect(self.onEditingStarted)
                            self.xpLayers[layer.id()] = [layer, None, False]
            else:
                if msg:
                    XpError("Der Layer " + layer.name() + " ist kein PostgreSQL-Layer!",
                        self.iface)
        else: # not a vector layer
            if msg:
                XpError("Der Layer " + layer.name() + " ist kein VektorLayer!",
                    self.iface)

        return ddInit

    def layerFilterBereich(self, layer, bereiche):
        ''' wende einen Filter auf layer an, so dass nur Objekte in bereiche dargestellt werden'''

        if len(bereiche) > 0:
            bereichTyp = self.tools.getBereichTyp(self.db, bereiche[0])
            relation = self.tools.getPostgresRelation(layer)

            if relation != None:
                schemaName = relation[0]
                relName = relation[1]
                filter = self.getBereichFilter(schemaName, relName, bereiche)

                if layer.setSubsetString(filter):
                    layer.reload()

    def aktiverBereichLayerCheck(self,  layer):
        '''
        Prüfung, ob übergebener Layer Präsentationsobjekt oder XP_Objekt ist und ob es aktive Bereiche gibt
        0 = kein passender Layer oder kein aktiver Bereich
        1 = XP_Objekt und aktiver Bereich
        2 = Päsentationsobjekt
        '''

        retValue = 0
        layerRelation = self.tools.getPostgresRelation(layer)

        if layerRelation != None: #  PostgreSQL-Layer
            if layerRelation[2]: # Geometrielayer
                schema = layerRelation[0]

                if schema == "XP_Praesentationsobjekte":
                    retValue = 2
                else:
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
                            retValue = 1
                            break

        return retValue

    def createBereichZuordnungsLayer(self):
        self.gehoertZuLayer = self.getLayerForTable(
            "XP_Basisobjekte", "XP_Objekt_gehoertZuBereich")

        if self.gehoertZuLayer != None:
            self.gehoertZuLayer.layerDeleted.connect(self.onGehoertZuLayerDeleted)

    def aktiveBereicheFilternSlot(self):
        layer = self.iface.activeLayer()

        if layer == None:
            self.tools.noActiveLayerWarning
        else:
            layerCheck = self.aktiverBereichLayerCheck(layer)

            if layerCheck == 1:
                bereiche = self.aktiveBereicheGids()
                self.layerFilterBereich(layer, bereiche)

    def aktivenBereichenZuordnenSlot(self):
        layer = self.iface.activeLayer()

        if layer == None:
            self.tools.noActiveLayerWarning()
        else:
            self.willAktivenBereich = True
            self.aktivenBereichenZuordnen(layer)

    def aktivenBereichenZuordnen(self,  layer):
        '''fügt alle ausgewählten Features im übergebenen Layer den aktiven Bereichen zu
        Rückgabe: Bool (Erfolg)'''
        if self.db == None:
            self.initialize()

        if self.db:
            checkResult = self.aktiverBereichLayerCheck(layer)

            if checkResult == 1:
                if not self.tools.setEditable(self.gehoertZuLayer, True, self.iface):
                    self.debug("no edit")
                    return False

                if len(layer.selectedFeaturesIds()) == 0:
                    XpError(u"Bereichszuordnung: Der Layer " + layer.name() + u" hat keine Auswahl!",
                        self.iface)
                    return False

                bereichFld = self.gehoertZuLayer.fieldNameIndex("gehoertZuBereich")
                objektFld = self.gehoertZuLayer.fieldNameIndex("XP_Objekt_gid")

                gids = self.tools.getSelectedFeaturesGids(layer)

                if gids == []:
                    return False
                else:
                    bereitsZugeordnet = self.tools.getBereicheFuerFeatures(self.db,  gids)

                self.gehoertZuLayer.beginEditCommand(
                    u"Ausgewählte Features von " + layer.name() + u" den aktiven Bereichen zugeordnet.")
                newFeat = None #ini
                zugeordnet = 0 # Zähler

                for aGid in gids:
                    for aBereichGid in self.aktiveBereiche.iterkeys():
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
                            newFeat = self.tools.createFeature(self.gehoertZuLayer)
                            self.gehoertZuLayer.addFeature(newFeat,  False)
                            self.gehoertZuLayer.changeAttributeValue(newFeat.id(),  bereichFld, aBereichGid)
                            self.gehoertZuLayer.changeAttributeValue(newFeat.id(),  objektFld, aGid)
                            zugeordnet += 1

                if newFeat == None: # keine neuen Einträge
                    self.gehoertZuLayer.destroyEditCommand()
                    self.gehoertZuLayer.rollBack()

                    if aGid < 0:
                        return False
                    else:
                        self.tools.showInfo(u"Alle Objekte waren bereits zugeordnet")
                        return True
                else:
                    self.gehoertZuLayer.endEditCommand()

                    if not self.gehoertZuLayer.commitChanges():
                        self.tools.showError(u"Konnte Änderungen an " + self.gehoertZuLayer.name() + " nicht speichern!")
                        return False
                    else:
                        if zugeordnet == 1:
                            infoMsg = u"Ein Objekt "
                        else:
                            infoMsg = str(zugeordnet) + u" Objekte "

                        infoMsg += "im Layer " + layer.name() + " "

                        if len(self.aktiveBereiche) == 1:
                            infoMsg += u"dem Bereich " + self.aktiveBereiche[aBereichGid]
                        else:
                            infoMsg += str(len(self.aktiveBereiche)) + u" Bereichen"

                        infoMsg += u" zugeordnet"
                        self.tools.showInfo(infoMsg)
                        return True
            elif checkResult == 2: # Präsentationsobjekt
                return self.apoGehoertZuBereichFuellen(layer)
            else:
                return False
        else:
                return False

    def apoGehoertZuBereichFuellen(self, layer):
        '''
        Präsentationsobjekte können nur in einem Bereich sein, dafür gibt es das Feld
        XP_AbstraktesPraesentationsobjekt.gehoertZuBereich; es wird hier gefüllt,
        wenn aktive Bereiche festgelegt wurden.
        '''

        if len(self.aktiveBereiche) == 0:
            self.tools.showWarning(u"Keine aktiven Bereiche festgelegt")
            return False
        elif len(self.aktiveBereiche) > 1:
            self.tools.showError(u"Präsentationsobjekte können nur einem Bereich zugeordnet werden!")
            return False
        else:
            for k in self.aktiveBereiche.iterkeys():
                bereichGid = k

            apoLayer = self.getLayerForTable("XP_Praesentationsobjekte",
                "XP_AbstraktesPraesentationsobjekt")

            if apoLayer != None:
                if not self.tools.setEditable(apoLayer, True):
                    return False
                else:
                    fldIdx = apoLayer.fieldNameIndex("gehoertZuBereich")

                    for fid in layer.selectedFeaturesIds():
                        if not apoLayer.changeAttributeValue(fid, fldIdx, bereichGid):
                            self.tools.showError(u"Konnte XP_AbstraktesPraesentationsobjekt.gehoertZuBereich nicht ändern!")
                            apoLayer.rollBack()
                            return False

                    if not apoLayer.commitChanges():
                        self.tools.showError(u"Konnte Layer XP_AbstraktesPraesentationsobjekt nicht speichern")
                        return False
                    else:
                        return True
            else:
                return False

    def getBereichFilter(self, aSchemaName, aRelName, bereiche):
        ''' einen passenden Filter für aSchemaName.aRelName machen,
        der nur Objekte aus bereiche lädt'''
        sBereiche = self.tools.intListToString(bereiche)

        if aSchemaName == "XP_Praesentationsobjekte":
            filter = "gid IN (SELECT \"gid\" " + \
                    "FROM \"XP_Praesentationsobjekte\".\"XP_AbstraktesPraesentationsobjekt\" " + \
                    "WHERE \"gehoertZuBereich\" IN (" + sBereiche + "))"
        else:
            filter = "gid IN (SELECT \"XP_Objekt_gid\" " + \
                    "FROM \"XP_Basisobjekte\".\"XP_Objekt_gehoertZuBereich\" " + \
                    "WHERE \"gehoertZuBereich\" IN (" + sBereiche + "))"

        return filter

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
                    bereichTyp = self.tools.getBereichTyp(self.db,  bereich)
                    # rausbekommen, welche Layer Elemente im Bereich haben, auch nachrichtlich
                    layers = self.tools.getLayerInBereich(self.db, [bereich])

                    if len(layers) == 0:
                        self.iface.messageBar().pushMessage(
                            "XPlanung", u"In diesem Bereich sind keine Objekte vorhanden!",
                            level=QgsMessageBar.WARNING, duration = 10)
                        return None
                    else: # den Bereich selbst reintun
                        layers[2][bereichTyp + "_Basisobjekte"] = [bereichTyp + "_Bereich"]

                    # eine Gruppe für den Bereich machen
                    lIface = self.iface.legendInterface()
                    groupIdx = self.tools.createGroup(bereichDict[bereich])

                    if groupIdx == -1:
                        return None

                    # Layer in die Gruppe laden und features entsprechend einschränken
                    for aLayerType in layers:
                        for aKey in aLayerType.iterkeys():
                            for aRelName in aLayerType[aKey]:
                                filter = self.getBereichFilter(aKey, aRelName, [bereich])

                                # lade view, falls vorhanden
                                if aRelName == bereichTyp + "_Bereich":
                                    geomFld = "geltungsbereich"
                                else:
                                    geomFld = "position"

                                aLayer, isView = self.loadTable(aKey, aRelName + "_qv",  geomFld,
                                    displayName = aRelName, filter = filter)

                                if aLayer == None:
                                    # lade Tabelle
                                    aLayer, isView = self.loadTable(aKey, aRelName,  geomFld,
                                        displayName = aRelName, filter = filter)

                                if aLayer != None:
                                    # Stil des Layers aus der DB holen und anwenden
                                    stile = self.tools.getLayerStyles(self.db,
                                        aLayer, aKey, aRelName)

                                    if stile != None:
                                        self.tools.applyStyles(aLayer, stile)
                                        self.tools.useStyle(aLayer, bereichDict[bereich])

                                    lIface.moveLayer(aLayer,  groupIdx)
                                    lIface.setLayerVisible(aLayer,  True)
            self.iface.mapCanvas().refresh() # neuzeichnen

    def onEditingStarted(self):
        if len(self.aktiveBereiche) > 0:
            for layer in self.iface.legendInterface().layers():
                layerId = layer.id()

                try:
                    self.xpLayers[layerId]
                except:
                    continue

                layerRelation = self.tools.getPostgresRelation(layer)

                if layerRelation != None: # PostgreSQL-Layer
                    schema = layerRelation[0]
                    table = layerRelation[1]
                    maxGid = self.tools.getMaxGid(self.db, schema, table)
                    self.xpLayers[layerId][1] = maxGid
                    self.xpLayers[layerId][2] = False

    def onEditingStopped(self):
        if len(self.aktiveBereiche) > 0:
            for layer in self.iface.legendInterface().layers():
                layerId = layer.id()

                try:
                    hasChanges = self.xpLayers[layerId][2]

                    if hasChanges and not layer.isEditable():
                        # layer.isEditable() = True für diesen Layer wurde das Editieren nicht beendet
                        maxGid = self.xpLayers[layerId][1]

                        if maxGid == None: # Fehler bei Ermittlung der maxGid
                            continue

                        layer.reload() # damit neue gids geladen werden
                        newIds = []
                        request = QgsFeatureRequest()
                        request.setFilterExpression("gid > " + str(maxGid))

                        for aNewFeat in layer.getFeatures(request):
                            newIds.append(aNewFeat.id())

                        layer.selectByIds(newIds)

                        if layer.selectedFeatureCount() > 0:
                            if not self.aktivenBereichenZuordnen(layer):
                                if self.gehoertZuLayer == None:
                                    XpError("Layer XP_Objekt_gehoertZu_XP_Bereich nicht (mehr) vorhanden",
                                        self.iface)

                            layer.removeSelection()
                except:
                    continue

        self.iface.mapCanvas().refresh() # neuzeichnen

    def onGehoertZuLayerDeleted(self): # Slot
        self.gehoertZuLayer = None

    def onCommitedFeaturesAdded(self,  layerId,  featureList):
        '''
        Slot der aufgerufen wird, wenn neue Features in einen XP-Layer eingefügt werden
        wird vor editingStopped aufgerufen
        '''

        try:
            self.xpLayers[layerId][2] = True
        except:
            XpError(u"Fehler in xpLayers, layerId " + layerId + " nicht gefunden!",
                self.iface)

    def showQueryError(self, query):
        self.tools.showQueryError(query)
