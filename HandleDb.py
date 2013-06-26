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

class DbHandler():
    '''class to handle a QtSql.QSqlDatabase connnection to a PostgreSQL server'''

    def __init__(self):
        self.db = None

    def __listDatabases(self):
        dbList = []
        settings = QtCore.QSettings()
        settings.beginGroup("/PostgreSQL/connections")

        for key in settings.childGroups():
            dbList.append(key)
            #QMessageBox.information(self.mainWindow, "title", str(key) + '\n' + str(key.value))

        settings.endGroup()
        return dbList

    def dbChoose(self):
        pass

    def __dbGetSelected(self):
        settings = QtCore.QSettings()
        selected = unicode(settings.value("/PostgreSQL/connections/selected",  "",  type=str))
        return selected

    def dbConnectSelected(self,  thisPassword = None):
        if len(self.__listDatabases()) == 0:
            QtGui.QMessageBox.information(None, "No connections", "No Conn")
            return None

        selected = self.__dbGetSelected()
        self.db = self.__dbConnect(selected,  thisPassword)
        return self.db

    def __dbConnect(self, selected,  thisPassword = None):
        settings = QtCore.QSettings()

        # if there's an open database already, get rid of it
        if self.db:
            self.dbDisconnect()

        # get connection details from QSettings
        settings.beginGroup(u"/PostgreSQL/connections/" + selected)

        if not settings.contains("database"): # non-existent entry?
            QtGui.QMessageBox.critical(None, self.msgBoxTitle,
                "Unable to connect: there is no defined database connection \"%s\"." % selected)
            return None

        get_value_str = lambda x: unicode(settings.value(x,  type=str))
        host, database, username, passwd = map(get_value_str, ["host", "database", "username", "password"])
        port = settings.value("port",  5432,  type=int)

        if thisPassword:
            passwd = thisPassword
        else:
            if not (settings.value("save", False, type=bool) or settings.value("savePassword", False,  type=bool)):
                # qgis1.5 use 'savePassword' instead of 'save' setting
                (passwd, ok) = QtGui.QInputDialog.getText(None, "Enter password", \
                "Enter password for connection \"%s\":" % selected, QtGui.QLineEdit.Password)

                if not ok:
                    return None

        settings.endGroup()

        # connect to DB
        db = QtSql.QSqlDatabase.addDatabase ("QPSQL")
        db.setHostName(host)
        #db.setHostName("foo")
        db.setDatabaseName(database)
        db.setUserName(username)
        db.setPassword(passwd)
        ok2 = db.open()

        if not ok2:
            QtGui.QMessageBox.critical(None, self.msgBoxTitle, u"Konnte keine Verbindung mit der Datenbank aufbauen")
            return None
        else:
            # set as default in QSettings
            settings.setValue("/PostgreSQL/connections/selected", selected)
            return db

    def dbDisconnect(self):

        if self.db:
            self.db.close()

        self.db = None
