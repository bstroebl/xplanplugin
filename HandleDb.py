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
from PyQt4 import QtCore
from PyQt4 import QtSql
from qgis.gui import QgsMessageBar
import qgis.core

class DbHandler():
    '''class to handle a QtSql.QSqlDatabase connnection to a PostgreSQL server'''

    def __init__(self, iface):
        self.iface = iface
        self.db = None

    def dbConnect(self, thisPassword = None):
        s = QtCore.QSettings( "XPlanung", "XPlanung-Erweiterung" )
        service = ( s.value( "service", "" ) )
        host = ( s.value( "host", "" ) )
        port = ( s.value( "port", "5432" ) )
        database = ( s.value( "dbname", "" ) )
        username = ( s.value( "uid", "" ) )
        passwd = ( s.value( "pwd", "" ) )
        authcfg = s.value( "authcfg", "" )

        if authcfg != "" and hasattr(qgis.core,'QgsAuthManager'):
            amc = qgis.core.QgsAuthMethodConfig()
            qgis.core.QgsAuthManager.instance().loadAuthenticationConfig( authcfg, amc, True)
            username = amc.config( "username", username )
            passwd = amc.config( "password", passwd )
        else:
            authcfg = None

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
            level=QgsMessageBar.CRITICAL)
            return None
        else:
            return db

    def dbDisconnect(self, db):
        db.close()
        db = None

