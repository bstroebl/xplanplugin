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
from PyQt4 import QtCore, QtGui, QtSql,  QtXml
# Initialize Qt resources from file resources.py
from qgis.core import *
from qgis.gui import *
from XPlanDialog import BereichsauswahlDialog

class XPTools():
    def __init__(self,  iface):
        self.iface = iface
        self.bereiche = {}
        # dictionary, um den Typ eines Bereichs zu speichern, so dass nur einmal pro Session und Bereich eine SQL-Abfrage nötig ist

    def chooseBereich(self,  db,  multiSelect = False,  title = "Bereichsauswahl"):
        '''Starte Dialog zur Bereichsauswahl'''
        dlg = BereichsauswahlDialog(self.iface,  db,  multiSelect,  title)
        dlg.show()
        result = dlg.exec_()

        if result == 0:
            return [-1]
        else:
            return dlg.selected

    def getBereichTyp(self,  db,  bereichGid):
        '''gibt den Typ (FP, BP etc) des Bereichs mit der übergebenen gid zurück'''
        bereichTyp = None

        try:
            bereichTyp = self.bereiche[bereichGid]
        except KeyError:
            sel = "SELECT substring(\"Objektart\",1,2) FROM \"XP_Basisobjekte\".\"XP_Bereiche\" WHERE gid = :bereichGid"
            query = QtSql.QSqlQuery(db)
            query.prepare(sel)
            query.bindValue(":bereichGid", QtCore.QVariant(bereichGid))
            query.exec_()

            if query.isActive():
                while query.next(): # returns false when all records are done
                    bereichTyp = query.value(0).toString()

                query.finish()
                self.bereiche[bereichGid]  = bereichTyp
            else:
                self.showQueryError(query)
                query.finish()
                bereichTyp = None

        return bereichTyp

    def getBereicheFuerFeatures(self,  db,  bereichTyp,  fids):
        retValue = {}
        sel = "SELECT gid, \"" + bereichTyp + "_Bereich_gid\"  \
            FROM \"" + bereichTyp + "_Basisobjekte\".\"" + bereichTyp + "_Objekte\" "
        whereClause = ""

        for aFid in fids:
            if whereClause == "":
                whereClause = "WHERE \"" + bereichTyp + "_Bereich_gid\" IS NOT NULL AND (gid=" + str(aFid)
            else:
                whereClause += " OR gid=" + str(aFid)

        sel += whereClause + ") ORDER BY gid"

        query = QtSql.QSqlQuery(db)
        query.prepare(sel)
        query.exec_()

        if query.isActive():
            lastGid = -9999
            bereiche = []

            while query.next(): # returns false when all records are done
                gid = query.value(0).toInt()[0]

                if gid != lastGid:
                    retValue[lastGid] = bereiche
                    lastGid = gid
                    bereiche = []

                bereiche.append(query.value(1).toInt()[0])
            retValue[lastGid] = bereiche # letzten noch rein
            query.finish()
        else:
            self.showQueryError(query)
            query.finish()

        return retValue

    def getLayerStyle(self,  db,  layer,  bereichGid = -9999):
        '''gibt den Style für einen Layers für den Bereich mit der übergebenen gid zurück,
        wenn es für diesen Bereich keinen Stil gibt, wird der allgemeine Stil zurückgegeben
        (XP_Bereich_gid = NULL), falls es den auch nicht gibt wird None zurückgegeben'''

        relation = self.getPostgresRelation(layer)
        style = None

        if relation:
            sel = "SELECT style \
            FROM \"QGIS\".\"layer\" \
            WHERE schemaname = \':schema\' \
                AND tablename = \':table\' \
                AND (\"XP_Bereich_gid\" = :bereichGid \
                     OR \"XP_Bereich_gid\" IS NULL) \
             ORDER BY \"XP_Bereich_gid\" NULLS "

            if bereichGid == -9999:
                sel = sel + "FIRST"
            else:
                sel = sel + "LAST"

            query = QtSql.QSqlQuery(db)
            query.prepare(sel)
            query.bindValue(":schema", QtCore.QVariant(relation[0]))
            query.bindValue(":table", QtCore.QVariant(relation[1]))
            query.bindValue(":bereichGid", QtCore.QVariant(bereichGid))
            query.exec_()

            if query.isActive():

                while query.next(): # returns false when all records are done
                    style = query.value(0).toString()
                    break
                query.finish()
            else:
                self.showQueryError(query)
                query.finish()

        return style

    def getPostgresRelation(self,  layer):
        '''gibt die Relation [schema, relation, Name_der_Geometriespalte] eines PostgreSQL-Layers zurück'''
        retValue = None

        if isinstance(layer, QgsVectorLayer):
            if layer.dataProvider().storageType().contains("PostgreSQL"):
                retValue = []
                for s in str(layer.source()).split(" "):
                    if s.startswith("table="):
                        for val in s.replace("table=", "").split("."):
                            retValue.append(val.replace('"',  ''))
                        if layer.geometryType() == 4: # geometrielos
                            retValue.append("")
                            break

                    elif s.startswith("("):
                        retValue.append(s.replace("(", "").replace(")", ""))

        return retValue

    def getLayerInBereich(self,  db,  bereichGid):
        '''gibt ein Array mit Arrays (Punkt, Linie, Fläche) aller Layer zurück, die Elemente
        im XP_Bereich mit der übergebenen gid haben'''
        bereichTyp = self.getBereichTyp(db,  bereichGid)

        if bereichTyp:
            sel = "SELECT \"Objektart\",  \
            CASE \"Objektart\" LIKE \'%Punkt\' WHEN true THEN \'Punkt\' ELSE \
                CASE \"Objektart\" LIKE \'%Linie\' WHEN true THEN \'Linie\' ELSE \'Flaeche\' \
                END \
            END as typ FROM ( \
            SELECT DISTINCT \"Objektart\" \
            FROM \"" + bereichTyp +"_Basisobjekte\".\"" + bereichTyp + "_Objekte\" \
            WHERE \"XP_Bereich_gid\" = :bereichGid) foo"
            query = QtSql.QSqlQuery(db)
            query.prepare(sel)
            query.bindValue(":bereichGid", QtCore.QVariant(bereichGid))
            query.exec_()

            if query.isActive():
                punktLayer = []
                linienLayer = []
                flaechenLayer = []

                while query.next(): # returns false when all records are done
                    layer = query.value(0).toString()
                    art = query.value(1).toString()

                    if art == QtCore.QString("Punkt"):
                        punktLayer.append(layer)
                    elif art == QtCore.QString("Linie"):
                        linienLayer.append(layer)
                    elif art == QtCore.QString("Flaeche"):
                        flaechenLayer.append(layer)

                query.finish()
                return [punktLayer,  linienLayer,  flaechenLayer]
        else:
            self.showQueryError(query)
            query.finish()
            return None

    def findPostgresLayer(self, schemaName,  tableName, dbName, dbServer, aliasName = None):
        '''Finde einen PostgreSQL-Layer, mit Namen aliasName (optional)'''
        layerList = self.iface.legendInterface().layers()
        procLayer = None # ini

        for layer in layerList:
            if isinstance(layer, QgsVectorLayer):
                if layer.dataProvider().storageType().contains(QtCore.QString("PostgreSQL")):
                    src = layer.source()

                    if src.contains(schemaName) and src.contains(tableName) and src.contains(dbName) and src.contains(dbServer):

                        if aliasName:
                            if QtCore.QString(aliasName) != layer.name():
                                continue

                        procLayer = layer
                        break

        return procLayer

    def loadPostGISLayer(self,  db, schemaName, tableName, displayName = None,
        geomColumn = "", whereClause = None, keyColumn = None):
        '''Lade einen PostGIS-Layer aus der Datenbank db'''

        if not displayName:
            displayName = schemaName + "." + tableName

        uri = QgsDataSourceURI()
        thisPort = db.port()

        if thisPort == -1:
            thisPort = 5432

        # set host name, port, database name, username and password
        uri.setConnection(db.hostName(), str(thisPort), db.databaseName(), db.userName(), db.password())
        # set database schema, table name, geometry column and optionaly subset (WHERE clause)
        uri.setDataSource(schemaName, tableName, geomColumn)

        if whereClause:
            uri.setSql(whereClause)

        if keyColumn:
            uri.setKeyColumn(keyColumn)

        vlayer = QgsVectorLayer(uri.uri(), displayName, "postgres")
        QgsMapLayerRegistry.instance().addMapLayers([vlayer])
        return vlayer

    def styleLayer(self,  layer,  xmlStyle):
        '''wende den übergebenen Stil auf den übergebenen Layer an'''
        doc = QtXml.QDomDocument()

        if doc.setContent(xmlStyle):
            rootNode = doc.firstChildElement()
            if layer.readSymbology(rootNode, QtCore.QString("Fehler beim Anwenden")):

                if rootNode.hasAttributes():
                    attrs = rootNode.attributes()

                    if attrs.contains(QtCore.QString("minimumScale")):
                        minScaleAttr = attrs.namedItem(QtCore.QString("minimumScale"))
                        layer.setMinimumScale(float(minScaleAttr.nodeValue()))

                    if attrs.contains(QtCore.QString("maximumScale")):
                        maxScaleAttr = attrs.namedItem(QtCore.QString("maximumScale"))
                        layer.setMaximumScale(float(maxScaleAttr.nodeValue()))

                    if attrs.contains(QtCore.QString("hasScaleBasedVisibilityFlag")):
                        scaleBasedVisAttr = attrs.namedItem(QtCore.QString("hasScaleBasedVisibilityFlag"))
                        layer.toggleScaleBasedVisibility(scaleBasedVisAttr.nodeValue() == "1")
                return True
            else:
                return False

    def createFeature(self,  layer, fid = None):
        '''Ein Feature für den übergebenen Layer erzeugen'''
        if isinstance(layer, QgsVectorLayer):
            if fid:
                newFeature = QgsFeature(fid)
            else:
                newFeature = QgsFeature()

            provider = layer.dataProvider()
            fields = layer.pendingFields()

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

    def showQueryError(self, query):
        QtGui.QMessageBox.warning(None, "Database Error", \
            QtCore.QString("%1 \n %2").arg(query.lastError().text()).arg(query.lastQuery()))

    def debug(self,  msg):
        QtGui.QMessageBox.information(None, "Debug",  msg)
