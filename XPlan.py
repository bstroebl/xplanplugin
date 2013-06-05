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
# Import the PyQt and QGIS libraries
from PyQt4 import QtCore, QtGui, QtSql
# Initialize Qt resources from file resources.py
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
from HandleDb import DbHandler
import XPTools
from DataDrivenInputMask import ddui

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
        
        try:
            self.app.ddManager
        except AttributeError:
            ddManager = ddui.DdManager(self.iface)
            self.app.ddManager = ddManager

    def initGui(self):
        # Code von fTools
        
        self.xpMenu = QtGui.QMenu(u"XPlanung")
        self.bpMenu = QtGui.QMenu(u"BPlan")
        self.fpMenu = QtGui.QMenu(u"FPlan")
        self.lpMenu = QtGui.QMenu(u"LPlan")
        
        self.action1 = QtGui.QAction(u"Bereich laden", self.iface.mainWindow())
        # connect the action to the run method
        #QtCore.QObject.connect(self.action1, QtCore.SIGNAL("triggered()"), self.bereichLaden)
        self.action1.triggered.connect(self.bereichLaden)

        # Create action that will start plugin configuration
        self.action2 = QtGui.QAction(u"Datenmaske initialisieren", self.iface.mainWindow())
        # connect the action to the run method
        #QtCore.QObject.connect(self.action2, QtCore.SIGNAL("triggered()"), self.layerInitialize)
        self.action2.triggered.connect(self.layerInitialize)
        
        self.xpMenu.addActions([self.action1,  self.action2])
        # Add toolbar button and menu item
        self.tmpAct = QtGui.QAction(self.iface.mainWindow())
        self.iface.addPluginToVectorMenu("tmp", self.tmpAct) # sicherstellen, dass das VektorMenu da ist
        self.vectorMenu = self.iface.vectorMenu()
        self.vectorMenu.addMenu(self.xpMenu)
        self.vectorMenu.addMenu(self.bpMenu)
        self.vectorMenu.addMenu(self.fpMenu)
        self.vectorMenu.addMenu(self.lpMenu)
        self.iface.removePluginVectorMenu("tmp", self.tmpAct)

    def unload(self):
        self.app.ddManager.quit()
        self.iface.addPluginToVectorMenu("tmp", self.tmpAct)
        self.vectorMenu.removeAction(self.xpMenu.menuAction())
        self.vectorMenu.removeAction(self.bpMenu.menuAction())
        self.vectorMenu.removeAction(self.fpMenu.menuAction())
        self.vectorMenu.removeAction(self.lpMenu.menuAction())
        self.iface.removePluginVectorMenu("tmp", self.tmpAct)

    #Slots

    # run method that performs all the real work
    def layerInitialize(self):
        layer = self.iface.activeLayer()
        if 0 != layer.type():   # not a vector layer
            XpError("Der Layer " + layer.name() + " ist kein VektorLayer!")
        else:
            self.app.ddManager.initLayer(layer,  skip = [])

    def bereichLaden(self):
        if self.db == None:
            self.db = self.dbHandler.dbConnectSelected()
            
        if self.db:
            bereich = self.tools.chooseBereich(self.db)

            if bereich >= 0:
                # rausbekommen, welche Layer Elemente im Bereich haben
                bereichTyp = self.tools.getBereichTyp(self.db,  bereich)
                layers = self.tools.getLayerInBereich(self.db,  bereichTyp)
                # eine Gruppe für den Bereich machen
                # qml für Layer aus DB holen
                # Layer in die Gruppe laden und features entsprechend einschränken
            
            self.dbHandler.dbDisconnect()
            
    def action01Slot(self):
        '''gebundenes Präsentationsobjekt
        Voraussetzung: aktives Layer ist XPlan-Layer und hat
        Features gewählt'''

        self.initLayers('XP_Praesentationsobjekte') # lädt in FSManangement festgelegte Layer
        title = u"gebundenes Präsentationsobjekt"
        #Voraussetzung prüfen
        xpLayer = self.iface.activeLayer()
        errMsg = ""

        if self.isXPlanLayer(xpLayer):
            xpCount = xpLayer.selectedFeatureCount()

            if xpCount > 0:
                #Anzeigewerte
                if xpCount == 1:
                    xpMsg = u"das gewählte XP-Objekt"
                else:
                    xpMsg = u"die gewählten XP-Objekte"

                poType = self.choosePoType(title)

                if poType:
                    poLayerValues = self.findLayerBySource("xp_praesentationsobjekte",
                                                     "xp_" + poType, self.pathToUi)

                    if poLayerValues:
                        poLayer = poLayerValues[0]
                        tableAlias = poLayerValues[1]
                        serverName = poLayerValues[2]
                        dbName = poLayerValues[3]
                        schemaName = poLayerValues[4]
                        tableName = poLayerValues[5]
                        uiName = poLayerValues[6]
                        formHelper = poLayerValues[7]
                        styleName = poLayerValues[8] # wird von initLayers nicht berücksichtigt!
                        layerStyle = poLayerValues[9]
                        geomColumn = poLayerValues[10]
                        autoLoad = poLayerValues[11]
                        xmlStyle = poLayerValues[12]
                        keyColumn = poLayerValues[13]

                        if not poLayer:
                            #poLayer laden
                            if tableAlias.isNull():
                                tableAlias = None

                            poLayer = zqgis.loadPostGISLayer(self.mp.db, schemaName,
                                        tableName, tableAlias, geomColumn, None, keyColumn)

                            if poLayer:
                                self.styleLayer(poLayer, uiName, formHelper, None, layerStyle, xmlStyle)
                                self.iface.setActiveLayer(poLayer)
                            else:
                                errMsg = u"Layer xp_praesentationsobjekte.xp_" + \
                                     poType + u" konnte nicht geladen werden!"
                        else:
                            self.styleLayer(poLayer, uiName, formHelper, None, layerStyle, xmlStyle)
                    else:
                        return None

                    self.initializeXP_POLayer(poLayer)
                    poCount = poLayer.selectedFeatureCount()

                    if poCount == 0: #ist auch der Fall, wenn neu geladen
                        # Nutzer informieren, was zu tun ist
                        errMsg = u"Wählen Sie im aktiven PO-Layer das Feature, " +\
                            u"das an " + xpMsg + " im Layer " + \
                            xpLayer.name() + u" gebunden werden soll. \n" + \
                            u"Aktivieren Sie dann wieder den Layer " + \
                            xpLayer.name() + u" und rufen Sie diese Funktion nochmals auf."
                    else:
                        art = zqgis.chooseField(xpLayer, ["gid", "uuid"],  u"art",  \
                            u"Name des Attributs, das mit dem Präsentationsobjekt dargestellt werden soll")

                        if art:
                            self.mp.db.transaction()
                            breakXpLoop = False

                            for xpFeature in xpLayer.selectedFeatures():

                                if breakXpLoop:
                                    break

                                xpGid = xpFeature.id()

                                if xpGid <= 0:
                                    errMsg = u"Bitte den Layer " + xpLayer.name() + \
                                            " erst speichern!"
                                    breakXpLoop = True
                                    break

                                for poFeature in poLayer.selectedFeatures():
                                    poGid = poFeature.id()

                                    if poGid <= 0: # just digitized
                                        errMsg = u"Bitte den Layer " + poLayer.name() + \
                                            " erst speichern!"
                                        breakXpLoop = True
                                        break
                                    else:
                                        gZB = poFeature.attributeMap().get(poLayer.fieldNameIndex("gehoertZuBereich"))

                                        if gZB.isNull():
                                            query = QtSql.QSqlQuery(self.mp.db)
                                            query.prepare("INSERT INTO \
                                \"xp_praesentationsobjekte\".\"dientzurdarstellungvon\" \
                                (\"XP_APObjekt_gid\", \"XP_Objekt_gid\", \"art\") \
                                VALUES(:poGid, :xpGid, :art);")
                                            query.bindValue(":poGid", QtCore.QVariant(poGid))
                                            query.bindValue(":xpGid", QtCore.QVariant(xpGid))
                                            query.bindValue(":art", QtCore.QVariant(art))
                                            query.exec_()

                                            if query.isActive():
                                                query.finish()
                                            else:
                                                self.showQueryError(query)
                                                query.finish()
                                                breakXpLoop = True
                                                break
                                        else:
                                            errMsg = u"Gewähltes Präsentationsobjekt ist ein " + \
                                            " freies Präsentationsobjekt, da es dem Bereich " + \
                                            gZB.toString() + u" zugeordnet ist. Ein Präsentationsobjekt " + \
                                            u"kann nicht gleichzeitig gebunden und frei sein."
                                            breakXpLoop = True
                                            break

                            if breakXpLoop:
                                self.mp.db.rollback()
                            else:
                                self.mp.db.commit()
                                QtGui.QMessageBox.information(None,"",
                                    u"Bindung von " + str(poCount) + \
                                    u"Präsentationsobjekte(n) an " + xpMsg + \
                                    u"erfolgreich." )

            else:
                errMsg = u"Im aktiven XPlan-Layer muß mindestens ein Element ausgewählt sein!"
        else:
            errMsg = u"Aktiver Layer ist KEIN XPlan-Layer! \n" + \
                u"Bitte den XPlan-Layer aktivieren, für den ein gebundenes " + \
                u"Präsentationsobjekt erzeugt werden soll."

        if errMsg != "":
            QtGui.QMessageBox.warning(None, title, errMsg)


    def action02Slot(self):
        title = u"gebundenes Präsentationsobjekt trennen"
        self.initLayers('XP_Praesentationsobjekte') # lädt in FSManangement festgelegte Layer
        poLayer = self.iface.activeLayer()

        if self.isXP_POLayer(poLayer):
            numSel = poLayer.selectedFeatureCount()
            thisMsg = ""

            if numSel == 0:
                thisMsg = u"Es sind keine XP_Präsentationsobjekt-Features gewählt!"
            else:
                if numSel == 1:
                    qMsg = u"Es ist ein XP_Präsentationsobjekt-Feature gewählt. " + \
                        u"Sollen alle seine Bindungen gelöst werden?"
                else: qMsg = u"Es sind " + str(numSel) + \
                    u" XP_Präsentationsobjekt-Features gewählt. " + \
                    u"Sollen von allen alle Bindungen gelöst werden?"
                thisChoice = QtGui.QMessageBox.question(None, title, qMsg,
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

                if thisChoice == QtGui.QMessageBox.Yes:
                    self.mp.db.transaction()

                    for poFeature in poLayer.selectedFeatures():
                        poGid = poFeature.id()
                        query = QtSql.QSqlQuery(self.mp.db)
                        query.prepare("DELETE \
                            FROM \"xp_praesentationsobjekte\".\"dientzurdarstellungvon\" \
                            WHERE \"XP_APObjekt_gid\" = :poGid;")
                        query.bindValue(":poGid", QtCore.QVariant(poGid))
                        query.exec_()

                        if query.isActive():
                            query.finish()
                        else:
                            self.showQueryError(query)
                            query.finish()
                            self.mp.db.rollback()
                            thisMsg = u"Keine Trennung erfolgt."
                            break

                        if thisMsg == "":
                            self.mp.db.commit()
                            thisMsg = u"XP_Präsentationsobjekt-Features erfolgreich " + \
                                "getrennt."

            if thisMsg == "":
                poFeature = poLayer.selectedFeatures()[0]
                poGid = poFeature.id()

                if poGid <= 0: # just digitized
                    thisMsg = u"XP_Präsentationsobjekt-Feature ist nicht gebunden."

            if thisMsg == "":
                query = QtSql.QSqlQuery(self.mp.db)
                query.prepare("SELECT o.gid, class.relname || \': feature \' || CAST(o.gid as varchar) \
                    FROM \"xp_praesentationsobjekte\".\"dientzurdarstellungvon\" d \
                    JOIN xp_basisobjekte.xp_objekt o ON d.\"XP_Objekt_gid\" = o.gid \
                    JOIN pg_class class ON o.tableoid = class.oid \
                    WHERE \"XP_APObjekt_gid\" = :poGid;")
                query.bindValue(":poGid", QtCore.QVariant(poGid))
                query.exec_()

                if query.isActive():
                    xpObjekte = QtCore.QStringList()
                    xpGids = []

                    while query.next():
                        xpGids.append(query.value(0).toInt()[0])
                        xpObjekte.append(query.value(1).toString())

                    query.finish()
                else:
                    self.showQueryError(query)
                    query.finish()

                if xpObjekte.isEmpty():
                    thisMsg = u"XP_Präsentationsobjekt-Feature ist nicht gebunden."
                else:
                    thisObjekt, ok = QtGui.QInputDialog.getItem(None, title,
                        u"zu trennendes XP_Objekt wählen", xpObjekte, 0, False)

                    if ok:
                        remove = xpObjekte.indexOf(thisObjekt)
                        thisXpGid = xpGids[remove]
                        query = QtSql.QSqlQuery(self.mp.db)
                        query.prepare("DELETE \
                            FROM \"xp_praesentationsobjekte\".\"dientzurdarstellungvon\" \
                            WHERE \"XP_APObjekt_gid\" = :poGid \
                            AND \"XP_Objekt_gid\" = :thisXpGid;")
                        query.bindValue(":poGid", QtCore.QVariant(poGid))
                        query.bindValue(":thisXpGid", QtCore.QVariant(thisXpGid))
                        query.exec_()

                        if query.isActive():
                            thisMsg = u"XP_Präsentationsobjekt-Feature erfolgreich von " + \
                                thisObjekt + "getrennt."
                            query.finish()
                        else:
                            self.showQueryError(query)
                            query.finish()
        else:
            thisMsg = u"Der aktive Layer ist kein XP_Präsentationsobjekt-Layer!"

        if thisMsg != "":
             QtGui.QMessageBox.information(None, title, thisMsg)

    def action03Slot(self): #PO-Layer initialisieren
        self.initLayers('XP_Praesentationsobjekte') # lädt in FSManangement festgelegte Layer
        poLayer = self.iface.activeLayer()

        if self.isXP_POLayer(poLayer):
            self.initLayer(poLayer)
            self.initializeXP_POLayer(poLayer)
        else:
            QtGui.QMessageBox.information(None,"",
                u"Aktiver Layer ist kein Präsentationsobjekt-Layer!")

    def action04Slot(self):
        title = u"Bindung des gewählten Präsentationsobjekts anzeigen"
        self.initLayers('XP_Praesentationsobjekte') # lädt in FSManangement festgelegte Layer
        poLayer = self.iface.activeLayer()

        if self.isXP_POLayer(poLayer):
            numSel = poLayer.selectedFeatureCount()
            thisMsg = ""

            if numSel == 0:
                thisMsg = u"Es sind keine XP_Präsentationsobjekt-Features gewählt!"
            else:
                for poFeature in poLayer.selectedFeatures():
                    poGid = poFeature.id()
                    query = QtSql.QSqlQuery(self.mp.db)
                    query.prepare("SELECT d.\"XP_Objekt_gid\", o.text \
                        FROM \"xp_praesentationsobjekte\".\"dientzurdarstellungvon\" d \
                        JOIN \"xp_basisobjekte\".\"xp_objekt\" o ON d.\"XP_Objekt_gid\" = o.gid\
                        WHERE d.\"XP_APObjekt_gid\" = :poGid;")
                    query.bindValue(":poGid", QtCore.QVariant(poGid))
                    query.exec_()

                    if query.isActive():

                        if query.size() == 0:
                            QtGui.QMessageBox.information(None,  u"Präsentationsobjekt " + str(poGid),  u"ist nicht gebunden")
                        else:
                            while query.next():
                                bindMsg = u"ist an XP_Objekt " + query.value(0).toString() + ": \"" + query.value(1).toString() + "\" gebunden"
                                QtGui.QMessageBox.information(None,  u"Präsentationsobjekt " + str(poGid),  bindMsg)
                        query.finish()
                    else:
                        self.showQueryError(query)
                        query.finish()
                        break
        else:
            thisMsg = u"Der aktive Layer ist kein XP_Präsentationsobjekt-Layer!"

        if thisMsg != "":
             QtGui.QMessageBox.information(None, title, thisMsg)


    def action10Slot(self): #LPlan initialisieren
        self.initLayers('LP_Basisobjekte') # lädt in FSManangement festgelegte Layer

        for aLayer in self.iface.legendInterface().layers():
            if self.isLPlanLayer(aLayer):
                self.initializeLPlanLayer(aLayer)
                self.customizeStyle(aLayer)

        QtCore.QObject.connect(self.mlRegistry,
                               QtCore.SIGNAL("layerWasAdded(QgsMapLayer)"),
                               self.addedLPlanLayerSlot)

        self.LP_Settings()

    def action11Slot(self): # aktiven LPlan-Layer initialisieren
        layer = self.iface.activeLayer()

        if self.isLPlanLayer(layer):
            self.initializeLPlanLayer(layer)
            self.initLayer(layer)

    def action12Slot(self): # gewählte LP_Objekte den aktiven Bereichen zuweisen
        while len(self.aktiveLP_Bereiche) == 0:
            QtGui.QMessageBox.warning(None,"","Es sind keine LP_Bereiche aktiviert!")

            if self.LP_Settings() == 0:
                return None

        layer = self.iface.activeLayer()

        if layer:
            if not layer.isEditable():
                if not layer.startEditing():
                    QtGui.QMessageBox.warning(None,"", u"Der Layer muß editierbar sein!")
                    return None
                else:
                    layer.rollBack()

            if self.isLPlanLayer(layer):
                self.setLP_Bereich(layer)
        else:
            QtGui.QMessageBox.information(None,"",
                u"Aktivieren Sie den Layer, den Sie bearbeiten möchten!")

    def action13Slot(self): # LP_Objekte bearbeiten
        layer = self.iface.activeLayer()
        #QtGui.QMessageBox.information(None,"",u"lp_ObjektSelectSlot")

        if layer:
            if self.isLPlanLayer(layer):

                if layer.selectedFeatureCount() == 0:
                    QtGui.QMessageBox.information(None,"",
                        u"Es sind keine Features ausgewählt!")
                else:
                    if layer.isEditable():
                        self.mp.db.transaction()
                        result = 0

                        for featureId in layer.selectedFeaturesIds():

                            if featureId <= 0: # just digitized
                                QtGui.QMessageBox.information(None,"",
                                    u"Bitte den Layer erst speichern!")
                                self.mp.db.rollback()
                                break
                            else:
                                dlg = LP_Objekt(self.iface, featureId, self.mp.db, layer.isEditable())
                                dlg.show()
                                thisResult = dlg.exec_()

                                if result == 0: #check if user clicked "OK" yet
                                    result = thisResult

                    if layer.isEditable():
                        if result == 1: # user clicked OK at least once
                            self.mp.db.commit()
                        else:
                            self.mp.db.rollback()
            else:
                QtGui.QMessageBox.warning(None,"",u"Der aktive Layer ist kein LPlan-Layer!")

    def action14Slot(self):
        # alle Layer laden, die Features im entsprechenden LP_Bereich haben
        self.initLayers('LP_Basisobjekte')
        layer = self.findLayerByAlias("LP_Bereich")

        if not layer:
            return None

        bereiche = QtCore.QStringList()
        bereichIds = []
        nameFld = layer.fieldNameIndex("name")
        layer.removeSelection(False)
        layer.invertSelection()
        aFeature = QgsFeature()

        for fid in layer.selectedFeaturesIds():
            layer.featureAtId(fid, aFeature, False)
            bereiche.append(aFeature.attributeMap().get(nameFld).toString())
            bereichIds.append(fid)

        thisBereich, ok = QtGui.QInputDialog.getItem(None, "LP_Bereich laden",
            u"zu ladenden LP_Bereich wählen", bereiche, 0, False)

        if ok:
            thisBereichId = bereichIds[bereiche.indexOf(thisBereich)]

            whereClause = "gid in (SELECT \"LP_Objekt_gid\" \
            FROM lplan.gehoertzulp_bereich gzl \
            LEFT JOIN xp_praesentationsobjekte.dientzurdarstellungvon dzdv\
            ON gzl.\"LP_Objekt_gid\" = dzdv.\"XP_Objekt_gid\" \
            WHERE gzl.\"LP_Bereich_id\" = " + str(thisBereichId) + " \
            AND dzdv.\"XP_Objekt_gid\" IS NULL)" #schliesst diejenigen mit PO aus

            poWhereClause = "\"gehoertZuBereich\" = "  + str(thisBereichId)

            li = self.iface.legendInterface()

            groupNames = ["Punktobjekte", "Linienobjekte", "Flaechenobjekte"]
            schemaNames = ["lp_punktobjekt", "lp_linienobjekt", "lp_flaechenobjekt"]
            poNames =[["xp_ppo_frei", "xp_ppo_gebunden", "xp_pto_frei", "xp_pto_gebunden"],
                      ["xp_lpo_frei", "xp_lpo_gebunden", "xp_lto_frei", "xp_lto_gebunden"],
                      ["xp_fpo_frei", "xp_fpo_gebunden"]]

            for i in range(len(schemaNames)):
                aSchema = schemaNames[i]
                aGroup = groupNames[i]
                newGroupIdx = li.addGroup(aGroup + " (" + thisBereich + ")", False)
                query = QtSql.QSqlQuery(self.mp.db)
                query.prepare("SELECT COALESCE(ly.alias, t.table_name) as alias, \
                                    ly.dbserver, ly.dbname, \
                                    ly.schemaname, \
                                    COALESCE(ly.relname, t.table_name) as relname, \
                                    ly.uiname, \
                                    ly.formhelper, ly.stylename, \
                                    COALESCE(ly.layerstyle, 0) as layerstyle, \
                                    ly.geomcolumn, ly.autoload, ly.style \
                                FROM information_schema.tables t \
                                LEFT JOIN (" + self.selectLayer() + ") ly \
                                    ON t.table_name = ly.relname AND t.table_schema = ly.schemaname \
                                WHERE t.table_schema = :schema;")
                query.bindValue(":fachschale", QtCore.QVariant(self.fsName))
                query.bindValue(":schema", QtCore.QVariant(aSchema))
                query.exec_()

                if query.isActive():

                    while query.next():
                        tableAlias = query.value(0).toString()
                        #serverName = query.value(1).toString()
                        #dbName = query.value(2).toString()
                        #schemaName = query.value(3).toString()
                        tableName = query.value(4).toString()
                        uiName = query.value(5).toString()
                        formHelper = query.value(6).toString()
                        #styleName = query.value(7).toString()
                        layerStyle = int(str(query.value(8).toString()))
                        #geomColumn = (query.value(9).toString())
                        #autoLoad = int(str(query.value(10).toString()))
                        xmlStyle = query.value(11).toString()

                        if uiName.isNull():
                            uiName = None

                        if formHelper.isNull():
                            formHelper = None

                        if xmlStyle.isNull():
                            xmlStyle = None

                        newLayer = zqgis.loadPostGISLayer(self.mp.db, aSchema,
                                        tableName, tableAlias,
                                        'position', whereClause)

                        if newLayer:
                            self.styleLayer(newLayer, uiName, formHelper, None, layerStyle, xmlStyle)
                            li.moveLayer(newLayer, newGroupIdx + 1)
                    query.finish()

                    #Präsentationsobjekte
                    for poName in poNames[i]:
                        #abfregen, ob in fachschale.layer etwas definiert ist
                        query = QtSql.QSqlQuery(self.mp.db)
                        query.prepare(self.selectLayer() + \
                            " AND l.schemaname = :schema \
                            AND l.relname = :poName")
                        query.bindValue(":fachschale", QtCore.QVariant(self.fsName))
                        query.bindValue(":schema", QtCore.QVariant("lplan"))
                        query.bindValue(":poName", QtCore.QVariant(poName))
                        query.exec_()

                        if query.isActive():
                            tableAlias = None
                            layerStyle = 0
                            xmlStyle = None

                            while query.next():
                                tableAlias = query.value(0).toString()
                                layerStyle = int(str(query.value(8).toString()))
                                xmlStyle = query.value(11).toString()

                                if xmlStyle.isNull():
                                    xmlStyle = None

                                query.finish()
                        else:
                            self.showQueryError(query)
                            query.finish()

                        newLayer = zqgis.loadPostGISLayer(self.mp.db, "lplan",
                                        poName, tableAlias,
                                        'position', poWhereClause)
                        if newLayer:
                            self.styleLayer(newLayer, None, None, None, layerStyle, xmlStyle)
                            li.moveLayer(newLayer, newGroupIdx + 1)

                    li.setGroupVisible(newGroupIdx, False)
                else:
                    self.showQueryError(query)
                    query.finish()

    def groupIdxChangedSlot(self, oldIdx, newIdx):
        QtGui.QMessageBox.information(None,"groupIdxChangedSlot", str(oldIdx) + " -> " + str(newIdx))
        if oldIdx == self.bereichIdx:
            self.bereichIdx = newIdx
        elif oldIdx == self.currentGroupIdx:
            self.currentGroupIdx = newIdx

    def addedLPlanLayerSlot(self, layer):
        QtGui.QMessageBox.information(None,"","addedLPlanLayerSlot")
        if layer.type() == 0:
            if self.isLPlanLayer(layer):
                self.initializeLPlanLayer(layer)

    def xp_POFeatureChangedSlot(self, fid, fldIdx, value):
        #QtGui.QMessageBox.information(None,"", value.toString())
        poLayer = self.iface.activeLayer()

        if poLayer.fieldNameIndex("gehoertZuBereich") == fldIdx and (not value.isNull()):
            query = QtSql.QSqlQuery(self.mp.db)
            query.prepare("SELECT count(*) FROM  \
                \"xp_praesentationsobjekte\".\"dientzurdarstellungvon\" \
                WHERE \"XP_APObjekt_gid\" = :poGid;")
            query.bindValue(":poGid", QtCore.QVariant(fid))
            query.exec_()

            if query.isActive():
                if query.first():

                    if query.value(0).toInt()[0] != 0:
                        QtGui.QMessageBox.warning(None, "",
                            u"Ein gebundenes Präsentationsobjekt kann nicht gleichzeitig " + \
                            u"ein freies sein! Geben Sie ggfs. ein neues Präsentationsobjekt ein " + \
                            u"oder lösen Sie die Bindung.")
                        feat = QgsFeature()

                        if poLayer.featureAtId(fid, feat, False, True):
                            feat.changeAttribute(fldIdx, QtCore.QVariant("NULL"))

                query.finish()
            else:
                self.showQueryError(query)
                query.finish()

        #thisFeature = poLayer.featureAtId
    def featureAddedSlot(self, fid):
        layer = self.iface.activeLayer()
        layer.select(fid)

    def committedLPFeaturesAddedSlot(self, layerId, featureList):
        details = "Aktive LP_Bereiche:"

        for i in range(len(self.aktiveLP_Bereiche)):
            details = details + "\n" + self.aktiveLP_Bereiche[i][1]

        msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Question,
            "Speichern", u"Sollen die neuen Features den aktiven Bereichen zugewiesen werden?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

        msgBox.setDetailedText(details)
        applyBereich = msgBox.exec_()

        if applyBereich == QtGui.QMessageBox.Yes:
            while len(self.aktiveLP_Bereiche) == 0:
                QtGui.QMessageBox.warning(None,"","Es sind keine LP_Bereiche aktiviert!")
                if self.LP_Settings() == 0:
                    return None
            layer = QgsMapLayerRegistry.instance().mapLayer(layerId)
            self.setLP_Bereich(layer)

    def lp_ObjektSelectSlot(self, pnt, but):
        layer = self.iface.activeLayer()
        #QtGui.QMessageBox.information(None,"",u"lp_ObjektSelectSlot")

        if layer:
            if self.isLPlanLayer(layer):
                layer.select(QgsRectangle(pnt.x()-5, pnt.y()-5, pnt.x()+5, pnt.y()+5), False)

                if layer.selectedFeatureCount() > 0:
                    db = self.mp.db

                    if layer.isEditable():
                        db.transaction()
                        result = 0

                    for featureId in layer.selectedFeaturesIds():

                        if featureId > 0: # <= 0 just digitized
                            dlg = LP_Objekt(self.iface, featureId, db, layer.isEditable())
                            dlg.show()
                            thisResult = dlg.exec_()

                            if result == 0: #check if user clicked "OK" yet
                                result = thisResult

                    if layer.isEditable():
                        if result == 1: # user clicked OK at least once
                            db.commit()
                        else:
                            db.rollback()
            else:
                QtGui.QMessageBox.warning(None,"",u"Der aktive Layer ist kein LPlan-Layer!")

    def isXP_POLayer(self, layer):
        retValue = False

        poSchema = "xp_praesentationsobjekte"
        poLayers = ["xp_ppo", "xp_lpo", "xp_fpo", "xp_pto", "xp_lto"]

        if layer.source().contains(poSchema):
            for aName in poLayers:
                if layer.source().contains(aName):
                    retValue = True
                    break

        return retValue

    def isXPlanLayer(self, layer):
        retValue = self.isLPlanLayer(layer)

        if not retValue:
            # entsprechende Prüfungen für andere XPlan-Typen
            retValue = False

        return retValue

    def isLPlanLayer(self, layer):
        retValue = False
        lpSchemas = ["lp_flaechenobjekt", "lp_linienobjekt", "lp_punktobjekt"]

        for aSchema in lpSchemas:
            if layer.source().contains(aSchema):
                retValue = True
                break

        return retValue

    def isLP_BereichLayer(self, layer):
        return layer.source().contains("lp_bereich")

    def isLP_PlanLayer(self, layer):
        return layer.source().contains("lp_plan")

    def initializeXP_POLayer(self, layer):
        if layer.type() == 0:
            QtCore.QObject.disconnect(layer,
                   QtCore.SIGNAL("attributeValueChanged(int, int, QVariant)"),
                   self.xp_POFeatureChangedSlot)
            QtCore.QObject.connect(layer,
                   QtCore.SIGNAL("attributeValueChanged(int, int, QVariant)"),
                   self.xp_POFeatureChangedSlot)

    def initializeLPlanLayer(self, layer):
        if layer.type() == 0:
            QtCore.QObject.disconnect(layer,
                   QtCore.SIGNAL("featureAdded(int)"),
                   self.featureAddedSlot)
            QtCore.QObject.connect(layer,
                   QtCore.SIGNAL("featureAdded(int)"),
                   self.featureAddedSlot)
            QtCore.QObject.disconnect(layer,
                   QtCore.SIGNAL("committedFeaturesAdded(QString, QgsFeatureList)"),
                   self.committedLPFeaturesAddedSlot)
            QtCore.QObject.connect(layer,
                   QtCore.SIGNAL("committedFeaturesAdded(QString, QgsFeatureList)"),
                   self.committedLPFeaturesAddedSlot)

    #Voraussetzung: layer ist Kind von LP_Objekt
    def setLP_Bereich(self, layer):
        self.mp.db.transaction()

        for i in range(len(self.aktiveLP_Bereiche)):
            lp_BereichId = self.aktiveLP_Bereiche[i][0]

            for fid in layer.selectedFeaturesIds():

                if fid > 0: #saved dataset
                    query = QtSql.QSqlQuery(self.mp.db)
                    sQuery = 'SELECT \"LP_Objekt_gid\", \"LP_Bereich_id\" \
                                FROM lplan.gehoertzulp_bereich \
                                WHERE \"LP_Objekt_gid\" = :fid \
                                AND "LP_Bereich_id\" = :lp_BereichId;'
                    query.prepare(sQuery)
                    query.bindValue(":fid", QtCore.QVariant(fid))
                    query.bindValue(":lp_BereichId", QtCore.QVariant(lp_BereichId))
                    query.exec_()

                    if query.isActive():
                        if query.size() == 0:
                            query.finish()
                            insQuery = QtSql.QSqlQuery(self.mp.db)
                            sQuery = 'INSERT INTO lplan.gehoertzulp_bereich \
                                        (\"LP_Objekt_gid\", \"LP_Bereich_id\") \
                                        VALUES(:fid, :lp_BereichId);'
                            insQuery.prepare(sQuery)
                            insQuery.bindValue(":fid", QtCore.QVariant(fid))
                            insQuery.bindValue(":lp_BereichId", QtCore.QVariant(lp_BereichId))
                            insQuery.exec_()

                            if insQuery.isActive():
                                insQuery.finish()
                            else:
                                self.showQueryError(insQuery)
                                insQuery.finish()
                                self.mp.db.rollback()
                                return None

                    else:
                        self.showQueryError(query)
                        query.finish()
                        self.mp.db.rollback()
                        return None

        self.mp.db.commit()
        msg = str(layer.selectedFeatureCount()) + u" LP_Feature"

        if layer.selectedFeatureCount() > 1:
            msg = msg + "s"

        QtGui.QMessageBox.information(None,"LP_Bereich",
            u"Zuweisung für " + msg + u" erfolgreich.")

    def LP_Settings(self):
        dlg = LPlanSettings(self.iface, self.mp.db, self.aktiveLP_Bereiche)
        dlg.show()
        result = dlg.exec_()

        if result == 1:
            self.aktiveLP_Bereiche = dlg.activeBereiche

        return result


    def choosePoType(self, title = u"Präsentationsobjekt"):
        poTypes = QtCore.QStringList()
        poTypes.append(u"punktförmig")
        poTypes.append(u"linienförmig")
        poTypes.append(u"flächenförmig")
        poTypes.append(u"Text, punktförmig")
        poTypes.append(u"Text, linienförmig")

        thisType, ok = QtGui.QInputDialog.getItem(None, title,
            u"Typ des Präsentationsobjekts wählen", poTypes, 0, False)

       # QtGui.QMessageBox.warning(None, "Database Error", \
       #     QtCore.QString("%1 \n %2").arg(thisType).arg(str(ok)))

        if ok:

            if thisType == u"punktförmig":
                return "ppo"
            elif thisType == u"linienförmig":
                return "lpo"
            elif thisType == u"flächenförmig":
                return "fpo"
            elif thisType == u"Text, punktförmig":
                return "pto"
            elif thisType == u"Text, linienförmig":
                return "lto"
        else:
            return None

    def fillCbxWithEnumeration(self,  cbx,  db,  enumerationTable,  showValue,  nullsAllowed = True):
        '''Fills a given ComboBox with the values from an enumeration, returns boolean (success)'''

        sql = "SELECT bezeichner, wert from %s order by bezeichner" % enumerationTable

        if  zqt.fillComboBoxQt(cbx,  db,  sql,  nullsAllowed) == 1:
            zqt.cbxValueFromInt(cbx,  showValue)
            return True
        else:
            return False

    def showQueryError(self, query):
        self.tools.showQueryError(query)
