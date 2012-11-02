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

from PyQt4 import QtCore, QtGui, QtSql

class XPlanGML(object):
    '''Abstrakte Oberklasse, die alle Methoden enthält, die Unterklassen brauchen'''

    def __init__(self,  mp):
        self.mp = mp
        self.db = self.mp.db

    def showQueryError(self, query):
        QtGui.QMessageBox.warning(None, "Database Error", \
            QtCore.QString("%1 \n %2").arg(query.lastError().text()).arg(query.lastQuery()))

class XP_Plan(XPlanGML):
    '''Abstrakte Oberklasse für alle Klassen von raumbezogenen Plänen'''

    def __init__(self, mp,  gid=None):
        XPlanGML.__init__(self,  mp)
        self.gid = gid

        if self.gid:
            self.__readXP_PlanAttributes()

            if self.gid:
                self.__readXP_PlanReferenzes()

        if not self.gid:
            self.name = QtCore.QString()
            self.nummer = QtCore.QString()
            self.beschreibung = QtCore.QString()
            self.kommentar = QtCore.QString()
            self.technHerstellDatum = QtCore.QDate()
            self.untergangsDatum = QtCore.QDate()
            self.erstellungsMassstab = -9999
            self.xPlanGMLVersion = QtCore.QString("4.0")
            self.bezugshoehe = -9999.0

    def __readXP_PlanAttributes(self):
        sql="SELECT \"name\", \"nummer\", \"beschreibung\", \"kommentar\", \"technHerstellDatum\", \"untergangsDatum\", \"erstellungsMassstab\", \"xPlanGMLVersion\", \"bezugshoehe\" \
            FROM \"XP_Basisobjekte\".\"XP_Plan\" \
            WHERE gid = :gid;"

        query = QtSql.QSqlQuery(self.db)
        query.prepare(sql)
        query.bindValue("gid",  QtCore.QVariant(self.gid))
        query.exec_()

        if query.isActive():
            if query.size() == 0:
                self.gid = None

            while query.next():
                if query.value(0).isNull():
                    self.name = QtCore.QString()
                else:
                    self.name = unicode(query.value(0).toString())

                if query.value(1).isNull():
                    self.nummer = QtCore.QString()
                else:
                    self.nummer = unicode(query.value(1).toString())

                if query.value(2).isNull():
                    self.beschreibung = QtCore.QString()
                else:
                    self.beschreibung = unicode(query.value(2).toString())

                if query.value(3).isNull():
                    self.kommentar = QtCore.QString()
                else:
                    self.kommentar = unicode(query.value(3).toString())

                if query.value(4).isNull():
                    self.technHerstellDatum = QtCore.QDate()
                else:
                    self.technHerstellDatum = unicode(query.value(4).toDate())

                if query.value(5).isNull():
                    self.untergangsDatum = QtCore.QDate()
                else:
                    self.untergangsDatum = unicode(query.value(5).toDate())

                if query.value(6).isNull():
                    self.erstellungsMassstab = -9999
                else:
                    self.erstellungsMassstab = unicode(query.value(6).toInt()[0])

                if query.value(7).isNull():
                    self.xPlanGMLVersion = QtCore.QString("4.0")
                else:
                    self.xPlanGMLVersion = unicode(query.value(7).toString())

                if query.value(8).isNull():
                    self.bezugshoehe = -9999.0
                else:
                    self.bezugshoehe = unicode(query.value(8).toReal()[0])

            query.finish()

        else:
            self.showQueryError(query)
            self.gid = None

        def __readXP_PlanReferenzes(self):
            pass
