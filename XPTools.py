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
from __future__ import absolute_import
from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt import QtSql, QtXml

# Initialize Qt resources from file resources.py
from qgis.core import *
from qgis.gui import *
from .XPlanDialog import BereichsauswahlDialog
from .XPlanDialog import StilauswahlDialog

class XPTools():
    def __init__(self, iface, standardName, simpleStyleName):
        self.iface = iface
        self.standardName = standardName # Name des Standardstils
        self.simpleStyleName = simpleStyleName
        self.bereiche = {}
        self.bereichsAuswahlDlg = None
        # dictionary, um den Typ eines Bereichs zu speichern, so dass nur
        # einmal pro Session und Bereich eine SQL-Abfrage nötig ist

    def chooseBereich(self,  db,  multiSelect = False,  title = "Bereichsauswahl"):
        '''Starte Dialog zur Bereichsauswahl'''

        if self.bereichsAuswahlDlg == None:
            self.bereichsAuswahlDlg = BereichsauswahlDialog(self.iface,  db,  multiSelect,  title)

        self.bereichsAuswahlDlg.show()
        result = self.bereichsAuswahlDlg.exec_()

        if result == 0: #Abbruch
            return {-1: -1}
        else:
            return self.bereichsAuswahlDlg.selected

    def chooseStyle(self, layer):
        '''
        Biete Auswahl der für diesen Layer zur Verfügung stehenden Stile an
        und gib den Namen des ausgewählten Stils zurück
        '''

        stile = {}
        styleMan = layer.styleManager()
        i = 0
        standardStil = None

        for aStyle in styleMan.styles():
            if aStyle != u"":
               i += 1
               stile[i] = aStyle

               if aStyle == self.standardName:
                   standardStil = aStyle

        if len(stile) == 0:
            self.noStyleWarning(layer)
            return None
        else:
            if standardStil == None:
                standardStil = stile[1]

        if len(stile) <= 2:
            return standardStil # entweder einfarbig oder default
        else:
            dlg = StilauswahlDialog(self.iface, stile, title = layer.name() + " - Stilauswahl")
            dlg.show()
            stilId = dlg.exec_()

            if stilId == -1:
                return None
            else:
                return stile[stilId]

    def getLayerStyles(self, db, layer, schema, table, showWarning = False):
        '''
        Liste alle für diesen Layer in der DB gespeicherten XP-Stile
        auf und gibt sie als Dict zurück layer.id:[Bereichsname, Stil(XML)],
        9999:[simpleStyleName, default_color (hex)]
        '''

        sel = "SELECT l.id, COALESCE(b.name,\'" + \
            self.standardName + "\'), l.style, l.default_color \
            FROM \"QGIS\".\"layer\" l \
            LEFT JOIN \"XP_Basisobjekte\".\"XP_Bereich\" b ON l.\"XP_Bereich_gid\" = b.gid \
            WHERE l.schemaname = :schema \
                AND l.tablename = :table \
            ORDER BY \"XP_Bereich_gid\" NULLS FIRST"

        query = QtSql.QSqlQuery(db)
        query.prepare(sel)
        query.bindValue(":schema", schema)
        query.bindValue(":table", table)
        query.exec_()

        if query.isActive():
            if query.size() == 0:
                if showWarning:
                    self.noStyleWarning(layer)
                query.finish()
                return None
            else:
                stile = {}

                while query.next():
                    styleId = query.value(0)
                    bereich = query.value(1)
                    style = unicode(query.value(2))
                    defaultColor = query.value(3)

                    if defaultColor != None:
                        stile[9999] = [self.simpleStyleName, defaultColor]

                    stile[styleId] = [bereich, style]

                query.finish()
                return stile
        else:
            self.showQueryError(query)
            query.finish()
            return None

    def applyStyles(self, layer, stile):
        '''
        die Stile dieses Layers laden und auf den Layer anwenden
        '''
        styleMan = layer.styleManager()
        # den unbenannten Stil umbenennen
        styleMan.renameStyle(u"default", self.simpleStyleName)

        if stile != None:
            for key, value in list(stile.items()):
                bereich = value[0]
                stil = value[1]

                if bereich == self.simpleStyleName:
                    styleMan.setCurrentStyle(self.simpleStyleName)

                    if layer.wkbType() in [1, 4]:
                        sl = QgsMarkerSymbol.createSimple({"color":stil})
                    elif layer.wkbType() in [2, 5]:
                        sl = QgsLineSymbol.createSimple({"color":stil})
                    elif layer.wkbType() in [3, 6]:
                        sl = QgsFillSymbol.createSimple({"color":stil})

                    layer.renderer().setSymbol(sl)
                    self.iface.layerTreeView().refreshLayerSymbology(layer.id())
                else:
                    styleMan.renameStyle(bereich, bereich + "_old") # falls schon vorhanden
                    style = QgsMapLayerStyle(stil)
                    styleMan.addStyle(bereich, style)
                    styleMan.removeStyle(bereich + "_old")

    def useStyle(self, layer, bereich):
        '''
        benutze den Stil der den Namen "bereich" hat
        '''
        styleMan = layer.styleManager()

        if styleMan.setCurrentStyle(bereich):
            self.iface.layerTreeView().refreshLayerSymbology(layer.id())
        else:
            if styleMan.setCurrentStyle(self.standardName):
                self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def createAction(self, layer, actionName, actionString, type = "Python",
            actionScopes = {"Canvas"}):

        createAction = True # store if an action with this name already exists

        for act in layer.actions().actions():
            if act.name() == actionName:
                createAction = False
                break

        if createAction:
            if type == "Python":
                actionType = 1 # actionType 1: Python
            else:
                actionType = 1

            newAction = QgsAction(actionType,  actionName, actionString)
            newAction.setActionScopes(actionScopes)
            layer.actions().addAction(newAction)

    def getBereichTyp(self,  db,  bereichGid):
        '''gibt den Typ (FP, BP etc) des Bereichs mit der übergebenen gid zurück'''
        bereichTyp = None

        try:
            bereichTyp = self.bereiche[bereichGid]
        except KeyError:
            sel = "SELECT substring(\"Objektart\",1,2) FROM \"XP_Basisobjekte\".\"XP_Bereiche\" WHERE gid = :bereichGid"
            query = QtSql.QSqlQuery(db)
            query.prepare(sel)
            query.bindValue(":bereichGid", bereichGid)
            query.exec_()

            if query.isActive():
                while query.next(): # returns false when all records are done
                    bereichTyp = query.value(0)

                query.finish()
                self.bereiche[bereichGid]  = bereichTyp
            else:
                self.showQueryError(query)
                query.finish()
                bereichTyp = None

        return bereichTyp

    def getBereicheFuerFeatures(self,  db,  gids):
        retValue = {}

        aList = self.intListToString(gids)

        sel = "SELECT \"XP_Objekt_gid\", \"gehoertZuBereich\"  \
            FROM \"XP_Basisobjekte\".\"XP_Objekt_gehoertZuBereich\" \
            WHERE \"XP_Objekt_gid\" IN (" + aList + ") \
            ORDER BY \"XP_Objekt_gid\""

        query = QtSql.QSqlQuery(db)
        query.prepare(sel)
        query.exec_()

        if query.isActive():
            lastGid = -9999
            bereiche = []

            while query.next(): # returns false when all records are done
                gid = query.value(0)

                if gid != lastGid:
                    retValue[lastGid] = bereiche
                    lastGid = gid
                    bereiche = []

                bereiche.append(query.value(1))
            retValue[lastGid] = bereiche # letzten noch rein
            query.finish()
        else:
            self.showQueryError(query)
            query.finish()

        return retValue

    def getMaxGid(self, db, schemaName, tableName, pkFieldName = "gid"):
        retValue = -9999
        sel = "SELECT " + pkFieldName + " FROM \"" + schemaName + "\".\"" + tableName + \
            "\" ORDER BY 1 DESC LIMIT 1;"

        query = QtSql.QSqlQuery(db)
        query.prepare(sel)
        query.exec_()

        if query.isActive():
            if query.size() > 0:
                while query.next():
                    retValue = query.value(0)

                query.finish()
        else:
            self.showQueryError(query)
            query.finish()
            return None

        return retValue

    def getSelectedFeaturesGids(self, layer):
        gidFld = layer.fields().lookupField("gid")
        gids = []

        for aFeat in layer.selectedFeatures():
            if aFeat.id() < 0:
                self.showError("Bitte speichern Sie zuerst den Layer " + layer.name())
                return []
            else:
                gids.append(aFeat[gidFld])

        return gids

    def getFeatures(self, layer):
        '''gibt entweder die selektierten Features oder,
        wenn keine Selektion besteht, alle Features zurück
        aus Processing'''

        class Features(object):

            def __init__(self, layer):
                self.layer = layer
                self.selection = False
                self.iter = layer.getFeatures()
                selected = layer.selectedFeatures()
                if len(selected) > 0:
                    self.selection = True
                    self.iter = iter(selected)

            def __iter__(self):
                return self.iter

            def __len__(self):
                if self.selection:
                    return int(self.layer.selectedFeatureCount())
                else:
                    return int(self.layer.featureCount())

        return Features(layer)

    def intListToString(self, list):
        result = ""
        for i in range(len(list)):
            if i > 0:
                result += ","

            result += str(list[i])

        return result

    def joinLayer(self, sourceLayer, joinLayer, targetField = "gid",
            joinField = "gid", prefix = None, memoryCache = True,
            joinedFields = []):
        '''Zwei Layer joinen
        sourceLayer ist der Layer, an den der joinLayer angeknüpft wird
        targetField ist das Feld im sourceLayer, an das geknüpft wird, joinField
        ist das Feld im joinLayer
        joinedFields ist ein Array mit den Feldnamen der Felder,
        die gejoined werden sollen
        seit QGIS 2.14 nicht mehr benötigt, da virtualLayer'''

        for aJoinInfo in sourceLayer.vectorJoins():
            if aJoinInfo.joinLayerId == joinLayer.id():
                sourceLayer.removeJoin(joinLayer.id())

        joinInfo = QgsVectorLayerJoinInfo()
        joinInfo.targetFieldIndex = sourceLayer.fields().lookupField(targetField)
        joinInfo.joinFieldIndex = joinLayer.fields().lookupField(joinField)
        joinInfo.joinFieldName = joinField
        joinInfo.targetFieldName = targetField
        joinInfo.joinLayerId = joinLayer.id()
        joinInfo.memoryCache = memoryCache

        if prefix != None:
            joinInfo.prefix = prefix

        if len(joinedFields) > 0:
            joinInfo.setJoinFieldNamesSubset(joinedFields)

        sourceLayer.addJoin(joinInfo)

    def getPostgresRelation(self,  layer):
        '''gibt die Relation [schema, relation, Name_der_Geometriespalte] eines PostgreSQL-Layers zurück'''
        retValue = None

        if isinstance(layer, QgsVectorLayer):
            if layer.dataProvider().storageType().find("PostgreSQL") != -1:
                retValue = []
                try:
                    layerSource = str(layer.source())
                except:
                    return None

                for s in layerSource.split(" "):
                    if s.startswith("table="):
                        for val in s.replace("table=", "").split("."):
                            retValue.append(val.replace('"',  ''))
                        if layer.geometryType() == 4: # geometrielos
                            retValue.append("")
                            break

                    elif s.startswith("("):
                        retValue.append(s.replace("(", "").replace(")", ""))

        return retValue

    def getBereichInPlan(self, db, planGid):
        '''gibt ein Array mit den gids der Bereiche zurück,
        die zum Plan mit der gid planGid gehören'''
        bereiche = []
        sql = "SELECT gid from \"QGIS\".\"XP_Bereiche\" WHERE plangid = :planGid"
        query = QtSql.QSqlQuery(db)
        query.prepare(sql)
        query.bindValue(":planGid", planGid)
        query.exec_()

        if query.isActive():
            if query.size() == 0:
                return []

            while query.next(): # returns false when all records are done
                bereiche.append(query.value(0))

            query.finish()
            return bereiche
        else:
            self.showQueryError(query)
            query.finish()
            return []

    def getLayerInBereich(self, db, bereichGids):
        '''gibt ein Array mit Arrays (Punkt, Linie, Fläche) aller Layer zurück, die Elemente
        im XP_Bereich mit den übergebenen gids haben'''

        if len(bereichGids) > 0:
            modellBereiche = []
            sel = "SELECT \"Kurz\" FROM public.\"XP_Modellbereich\";"
            query = QtSql.QSqlQuery(db)
            query.prepare(sel)
            query.exec_()

            if query.isActive():
                while query.next():
                    modellBereiche.append(query.value(0))
            else:
                    self.showQueryError(query)
                    query.finish()
                    return []

            bereiche = self.intListToString(bereichGids)

            sel = "SELECT \"Objektart\",  \
            typ, \
            \"Objektartengruppe\", \
            flaechenschluss \
            FROM ( \
            SELECT DISTINCT \"Objektart\", \'XP_Praesentationsobjekte\' as \"Objektartengruppe\", \
            \'Label\' as typ, NULL::Boolean as flaechenschluss \
            FROM \"XP_Praesentationsobjekte\".\"XP_AbstraktePraesentationsobjekte\" \
            WHERE \"gehoertZuBereich\" IN (" + bereiche + ")"

            for mBereich in modellBereiche:
                sel += " UNION \
            SELECT DISTINCT \"Objektart\", \"Objektartengruppe\", typ, flaechenschluss \
            FROM \"" + mBereich +"_Basisobjekte\".\"" + mBereich + "_Objekte\" \
            WHERE \"XP_Bereich_gid\" IN (" + bereiche + ")"

            sel += ") foo ORDER BY flaechenschluss"
            query = QtSql.QSqlQuery(db)
            query.prepare(sel)
            query.exec_()

            if query.isActive():
                if query.size() == 0:
                    return []

                labelLayer = {}
                punktLayer = {}
                linienLayer = {}
                flaechenLayer = {}
                flaechenschlussLayer = {}

                while query.next(): # returns false when all records are done
                    layer = query.value(0)
                    art = query.value(1)
                    gruppe = query.value(2)

                    if art == "Label":
                        try:
                            lLayerList = labelLayer[gruppe]
                            lLayerList.append(layer)
                        except KeyError:
                            labelLayer[gruppe] = [layer]
                    elif art == "Punkt":
                        try:
                            pLayerList = punktLayer[gruppe]
                            pLayerList.append(layer)
                        except KeyError:
                            punktLayer[gruppe] = [layer]
                    elif art == "Linie":
                        try:
                            lLayerList = linienLayer[gruppe]
                            lLayerList.append(layer)
                        except KeyError:
                            linienLayer[gruppe] = [layer]
                    elif art == "Flaeche":
                        flaechenschluss = query.value(3)
                        # falls in einem Layer true und false vorkommen, ist true immer
                        # der zweite Wert (ORDER BY flaechenschluss)
                        # Einzelne Objekte können flaechenschluss = true sein, ohne dass
                        # alle Objekte der  Objektart zwingend Flaechenschlussobjekte sind

                        if flaechenschluss:
                            # prüfen, ob bereits in fLayerList
                            try:
                                fLayerList = flaechenLayer[gruppe]
                                bereitsInFlaechenLayer = (fLayerList.count(layer) > 0)
                            except KeyError:
                                bereitsInFlaechenLayer = False

                            if not bereitsInFlaechenLayer:
                                try:
                                    fsLayerList = flaechenschlussLayer[gruppe]
                                    fsLayerList.append(layer)
                                except KeyError:
                                    flaechenschlussLayer[gruppe] = [layer]
                        else:
                            try:
                                fLayerList = flaechenLayer[gruppe]
                                fLayerList.append(layer)
                            except KeyError:
                                flaechenLayer[gruppe] = [layer]

                query.finish()
                return [flaechenschlussLayer, flaechenLayer, linienLayer, punktLayer, labelLayer]
            else:
                self.showQueryError(query)
                query.finish()
                return []
        else:
            return []

    def getXmlLayerStyle(self, layer):
        '''erzeuge ein XML-Style-Dokument'''
        doc=QtXml.QDomDocument()
        rootNode = doc.createElement("qgis")
        versionAttr = doc.createAttribute("version")
        versionAttr.setValue(Qgis.QGIS_VERSION)
        rootNode.setAttributeNode(versionAttr)
        minScaleAttr = doc.createAttribute("minimumScale")
        minScaleAttr.setValue(str(layer.minimumScale()))
        rootNode.setAttributeNode(minScaleAttr)
        maxScaleAttr = doc.createAttribute("maximumScale")
        maxScaleAttr.setValue(str(layer.maximumScale()))
        rootNode.setAttributeNode(maxScaleAttr)
        scaleBasedVisAttr = doc.createAttribute("hasScaleBasedVisibilityFlag")
        scaleBasedVisAttr.setValue(str(int(layer.hasScaleBasedVisibility())))
        rootNode.setAttributeNode(scaleBasedVisAttr)
        doc.appendChild(rootNode)

        if layer.writeSymbology(rootNode,doc,"Fehler", QgsReadWriteContext()):
            return doc
        else:
            return None

    def setLayerVisible(self, layer, visible = True):
        root = QgsProject.instance().layerTreeRoot()
        layerTreeLayer = root.findLayer(layer.id())

        if layerTreeLayer != None:
            layerTreeLayer.setItemVisibilityChecked(visible)

    def createFeature(self,  layer, fid = None):
        '''Ein Feature für den übergebenen Layer erzeugen'''
        if isinstance(layer, QgsVectorLayer):
            newFeature = QgsVectorLayerUtils.createFeature(layer)

            if fid:
                newFeaturesetId(fid)

            provider = layer.dataProvider()
            fields = layer.fields()
            newFeature.initAttributes(fields.count())

            for i in range(fields.count()):
                newFeature.setAttribute(i,provider.defaultValue(i))

            return newFeature
        else:
            return None

    def isXpDb(self,  db):
        retValue = False
        sel = "SELECT * FROM pg_namespace WHERE nspname = \'XP_Basisobjekte\'"
        query = QtSql.QSqlQuery(db)
        query.prepare(sel)
        query.exec_()

        if query.isActive():
            retValue = (query.size() == 1)
        else:
            self.showQueryError(query)

        return retValue

    def setEditable(self, layer, showErrorMsg = False, iface = None):
    # is it a vectorLayer?
        ok = isinstance(layer, QgsVectorLayer)
        title = "Editierfehler"

        if ok:
            ok = layer.isEditable() # is already in editMode

            if not ok:
                # try to start editing
                ok = layer.startEditing()

                if not ok and showErrorMsg:
                    msg = u"Bitte sorgen Sie dafür, dass der Layer " + \
                        layer.name() + u" editierbar ist!"
                    self.showError(msg, title)
        else:
            if showErrorMsg:
                msg = u"Der Layer " + layer.name() + u" ist kein Vektorlayer " + \
                    u" und damit nicht editierbar!"
                self.showError(msg, title)

        return ok

    def noActiveLayerWarning(self):
        self.showWarning(u"Kein aktiver Layer")

    def showQueryError(self, query):
        self.showError(
            "%(error)s" % {"error": query.lastError().text()}, "DB-Fehler")
        self.showError(
            "%(query)s" % {"query": query.lastQuery()},
            "Abfrage war")

    def showInfo(self, msg, title = "XPlanung"):
        self.iface.messageBar().pushMessage(
            title, msg, duration = 10)
        #self.log(msg, "info")

    def showWarning(self, msg, title = "XPlanung"):
        self.iface.messageBar().pushMessage(title, msg,
            level=Qgis.Warning, duration = 10)
        #self.log(msg, "warn")

    def showError(self, msg, title = "XPlanung"):
        self.iface.messageBar().pushMessage(title,
            msg, level=Qgis.Critical, duration = 10)
        self.log(msg, "error")

    def noStyleWarning(self, layer):
        self.showWarning(u"Für den Layer " + layer.name() + u" sind keine Stile gespeichert")

    def debug(self,  msg):
        self.log("Debug" + "\n" + msg)

    def log(self, msg, type = 'info'):
        if type == 'info':
            msgType = Qgis.Info
        if type == 'warn':
            msgType = Qgis.Warning
        if type == 'error':
            msgType = Qgis.Critical
        QgsMessageLog.logMessage(msg, "XPlanung", msgType)

    def getAuthUserNamePassword(self, authcfg):
        username = None
        password = None

        if authcfg != "" and authcfg != None:
            amc = QgsAuthMethodConfig()
            success, amc = QgsApplication.instance().authManager().loadAuthenticationConfig(
            authcfg, amc, True)

            if success: # es gibt die authcfg
                username = amc.config( "username" )
                password = amc.config( "password" )
            else:
                authcfg = None
        else:
            authcfg = None

        return [username, password, authcfg]
