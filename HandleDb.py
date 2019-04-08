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
from builtins import object
from qgis.PyQt import QtCore, QtSql

from qgis.gui import *
from qgis.core import *

class DbHandler(object):
    '''class to handle a QtSql.QSqlDatabase connnection to a PostgreSQL server'''

    def __init__(self, iface, tools):
        self.iface = iface
        self.tools = tools
        self.db = None

    def dbConnect(self, thisPassword = None):
        s = QtCore.QSettings( "XPlanung", "XPlanung-Erweiterung" )
        service = ( s.value( "service", "" ) )
        host = ( s.value( "host", "" ) )
        port = ( s.value( "port", "5432" ) )
        database = ( s.value( "dbname", "" ) )
        authcfg = s.value( "authcfg", "" )
        username, passwd, authcfg = self.tools.getAuthUserNamePassword(authcfg)

        if authcfg == None:
            username = ( s.value( "uid", "" ) )
            passwd = ( s.value( "pwd", "" ) )

        if thisPassword:
            passwd = thisPassword

        # connect to DB
        db = QtSql.QSqlDatabase.addDatabase ("QPSQL", "XPlanung")
        db.setHostName(host)
        db.setPort(int(port))
        db.setDatabaseName(database)
        db.setUserName(username)
        db.setPassword(passwd)
        db.authcfg = authcfg # für DDIM
        ok2 = db.open()

        if not ok2:
            self.iface.messageBar().pushMessage("Fehler", \
            u"Konnte keine Verbindung mit der Datenbank aufbauen", \
            level=Qgis.Critical)
            return None
        else:
            return db

    def dbDisconnect(self, db):
        db.close()
        db = None

