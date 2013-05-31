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
from XPlanDialog import BereichsauswahlDialog

class XPTools():
    def __init__(self,  iface):
        self.iface = iface
    
    def chooseBereich(self,  db):
        '''Starte Dialog zur Bereichsauswahl'''
        dlg = BereichsauswahlDialog(self.iface,  db)
        dlg.show()
        return dlg.exec_()
        
    def getBereichTyp(self,  db,  bereichGid):
        
        sel = "SELECT substring(\"Objektart\",1,2) FROM \"XP_Basisobjekte\".\"XP_Bereiche\" WHERE gid = :bereichGid"
        query = QtSql.QSqlQuery(db)
        query.prepare(sel)
        query.bindValue(":bereichGid", QtCore.QVariant(bereichGid))
        query.exec_()

        if query.isActive():

            while query.next(): # returns false when all records are done
                bereichTyp = query.value(0).toString()
            
            query.finish()
            return bereichTyp
        else:
            self.showQueryError(query)
            query.finish()
            return None
        
    def getLayerInBereich(self,  db,  bereichGid):
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
    
    def showQueryError(self, query):
        QtGui.QMessageBox.warning(None, "Database Error", \
            QtCore.QString("%1 \n %2").arg(query.lastError().text()).arg(query.lastQuery()))
