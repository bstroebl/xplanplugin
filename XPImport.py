# -*- coding: utf-8 -*-
"""
/***************************************************************************
XPImport
A QGIS plugin
Fachschale XPlan für XPlanung
                             -------------------
begin                : 2018-07-04
copyright            : (C) 2018 by Bernhard Stroebl, KIJ/DV
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
from PyQt4 import QtSql, QtGui
from qgis.core import *
from qgis.gui import *

class XPImporter():
    def __init__(self, db, tools):
        self.db = db
        self.tools = tools

    def importPlan(self, importSchema):
        planResult = self.__impPlan(importSchema)
        numPlaene = planResult[0]
        impPlanRelname = planResult[1]

        if numPlaene <= 0:
            return None

        bereichResult = self.__impBereich(importSchema, impPlanRelname)
        numBereiche = bereichResult[0]
        impBereichRelname = bereichResult[1]

        if numBereiche <= 0:
            return None

        if self.__impObjekte(importSchema, impPlanRelname, impBereichRelname):
            return self.importMsg
        else:
            return None

    def debug(self, msg):
        QgsMessageLog.logMessage("Debug" + "\n" + msg)

    def __impGetAllAttributesSql(self):
        '''
        SQL, das die :oid(pg_class.oid), und die Attribute (Name und Typ)
        von  :nspname.:relname liefert
        '''
        return "SELECT cl.oid,attname,ty.typname \
            FROM pg_attribute att \
            JOIN pg_type ty ON atttypid = ty.oid \
            JOIN pg_class cl ON attrelid = cl.oid \
            join pg_namespace ns on cl.relnamespace = ns.oid \
            WHERE nspname = :nspname \
            AND relname = :relname \
            AND att.attnum > 0 \
            AND att.attisdropped = false;"

    def __impFindArrayFieldsSql(self):
        '''
        SQL, das den Namen von Feldern in :oid (pg_class.oid) liefert, die Arrays sind
        '''
        return "SELECT attname FROM pg_attribute att \
            WHERE attrelid = :oid \
            AND attnum > 0 \
            AND attisdropped = false \
            AND attndims != 0;"

    def __impGetPkFieldSql(self):
        '''
        SQL, das den Namen des PK-Feldes für :oid (pg_class.oid) liefert
        '''
        return "SELECT \
            att.attname \
            FROM pg_attribute att \
            JOIN pg_constraint con ON att.attrelid = con.conrelid AND att.attnum = ANY (con.conkey) \
            WHERE att.attnum > 0 \
            AND att.attisdropped = false \
            AND att.attrelid = :oid \
            AND con.contype = 'p'"

    def __impGetNspnameSql(self):
        '''
        SQL, das alle nicht-Xplanungs-Schemas in der DB liefert
        '''
        return "SELECT nspname from pg_namespace \
            WHERE nspowner != 10 \
            AND nspname not like 'BP_%' \
            AND nspname not like 'FP_%' \
            AND nspname not like 'LP_%' \
            AND nspname not like 'RP_%'\
            AND nspname not like 'SO_%' \
            AND nspname not like 'XP_%' \
            AND nspname != 'QGIS';"

    def __impGetChildTablesSql(self):
        '''
        SQL, das alle Kindtabellen mit Punkt/Linie/Flaeche für :oid (pg_class.oid) liefert
        '''
        return "SELECT cl.oid,n.nspname,cl.relname \
            FROM pg_constraint pcon \
            JOIN pg_constraint fcon ON pcon.conrelid = fcon.confrelid \
            JOIN pg_constraint pcon2 ON fcon.conrelid = pcon2.conrelid \
            JOIN pg_class cl on fcon.conrelid = cl.oid \
            JOIN pg_namespace n ON cl.relnamespace = n.oid \
            WHERE pcon.conrelid = :oid \
            AND pcon.contype = 'p' \
            AND fcon.contype = 'f' \
            AND pcon2.contype = 'p' \
            AND cardinality(pcon2.conkey) = 1 \
            AND (right(relname,5) IN ('Punkt', 'Linie') OR right(relname,7) = 'Flaeche') \
            ORDER BY cl.relname;"

    def __impGetTableSql(self):
        '''
        SQL, dass gleichnamige Tabellen im Importschema und in den Nicht-Importschemas liefert
        '''
        return "SELECT c2.xp_oid,c2.nspname,c2.relname,c2.relkind,c1.imp_oid,c1.relname \
            FROM ( \
                SELECT pg_class.oid as imp_oid,nspname,relname FROM pg_class \
                JOIN pg_namespace ON relnamespace = pg_namespace.oid \
                WHERE relkind = 'r' \
                and nspname = :import1 \
            ) c1 \
            LEFT JOIN ( \
                SELECT c.oid as xp_oid,nspname,relname,relkind FROM pg_class c \
                JOIN pg_namespace n ON c.relnamespace = n.oid \
                WHERE relkind in ('r','v') \
                AND nspname != :import2 \
                AND nspname != 'QGIS' \
                AND (nspname like 'BP_%' OR nspname like 'FP_%' \
                    OR nspname like 'LP_%' OR nspname  like 'RP_%' \
                    OR nspname like 'SO_%' OR nspname like 'XP_%' \
                ) \
            ) c2 on lower(c1.relname) = lower(c2.relname)"

    def __impGetParentTableSql(self):
        '''
        SQL, das eine Elterntabelle für :oid (pg_class.oid) liefert
        '''
        return "SELECT \
            c.oid,ns.nspname, c.relname \
            FROM pg_attribute att \
                JOIN (SELECT * FROM pg_constraint WHERE contype = 'f') fcon ON att.attrelid = fcon.conrelid AND att.attnum = ANY (fcon.conkey) \
                JOIN (SELECT * FROM pg_constraint WHERE contype = 'p') pcon ON att.attrelid = pcon.conrelid AND att.attnum = ANY (pcon.conkey) \
                JOIN pg_class c ON fcon.confrelid = c.oid \
                JOIN pg_namespace ns ON c.relnamespace = ns.oid \
            WHERE att.attnum > 0 \
                AND att.attisdropped = false \
                AND att.attrelid = :oid \
                AND array_length(pcon.conkey, 1) = 1"

    def __impGetMatchingAttributesSql(self):
        '''
        SQL, das gleichnamige Attribute in den Relationen :xp_oid (pg_class.oid)
        und :imp_oid (pg_class.oid) liefert
        '''
        return "SELECT att1.attname as xp_attname, \
            att2.attname as imp_attname, \
            t.typname as xp_typename \
            FROM pg_attribute att1 \
            join pg_attribute att2 on lower(att1.attname) = lower(att2.attname) \
            join pg_type t on att1.atttypid = t.oid \
            WHERE att1.attrelid = :xp_oid \
            AND att1.attnum > 0 \
            AND att2.attrelid = :imp_oid \
            AND att2.attnum > 0"

    def __impFindArrayFields(self, thisOid):
        arrayFieldSql = self.__impFindArrayFieldsSql()
        arrayFieldQuery = QtSql.QSqlQuery(self.db)
        arrayFieldQuery.prepare(arrayFieldSql)
        arrayFieldQuery.bindValue(":oid", thisOid)
        arrayFieldQuery.exec_()
        arrayFields = []

        if arrayFieldQuery.isActive():
            while arrayFieldQuery.next():
                arrayFields.append(arrayFieldQuery.value(0))

            arrayFieldQuery.finish()
            return arrayFields
        else:
            self.showQueryError(arrayFieldQuery)
            return None

    def __impGetPkField(self, thisOid):
        pkSql = self.__impGetPkFieldSql()
        pkQuery = QtSql.QSqlQuery(self.db)
        pkQuery.prepare(pkSql)
        pkQuery.bindValue(":oid", thisOid)
        pkQuery.exec_()
        thisPkField = []

        if pkQuery.isActive():
            while pkQuery.next():
                thisPkField.append(pkQuery.value(0))

            pkQuery.finish()
            return thisPkField
        else:
            self.showQueryError(pkQuery)
            return None

    def impChooseSchema(self):
        schemaSql = self.__impGetNspnameSql()
        schemaQuery = QtSql.QSqlQuery(self.db)
        schemaQuery.prepare(schemaSql)
        schemaQuery.exec_()
        schemas = []

        if schemaQuery.isActive():
            while schemaQuery.next():
                schemas.append(schemaQuery.value(0))
            schemaQuery.finish()
            thisSchema, ok = QtGui.QInputDialog.getItem(None, u"Schemaauswahl",
                u"Schema mit importiertem Plan auswählen", schemas)

            if not ok:
                return None
            else:
                return thisSchema
        else:
            self.showQueryError(schemaQuery)
            return None

    def __impCreateGidField(self, importSchema, importRelname,
        parentNspname, parentRelname, pkField = "gid"):
        '''
        Füge der Importtabelle ein Feld xp_gid zu und fülle es mit Werten aus der passenden Sequenz
        parentNspname und parentRelname ist die oberste Elterntabelle, also z.B. XP_Objekt
        '''

        createGidSql = "SELECT \"QGIS\".imp_create_xp_gid(:schema,:table);"
        createGidQuery = QtSql.QSqlQuery(self.db)
        createGidQuery.prepare(createGidSql)
        createGidQuery.bindValue(":schema", importSchema)
        createGidQuery.bindValue(":table", importRelname)
        createGidQuery.exec_()

        if createGidQuery.isActive():
            createGidQuery.finish()
        else:
            self.showQueryError(createGidQuery)
            return -1

        if parentRelname == "XP_AbstraktesPraesentationsobjekt":
            seqName = "XP_APObjekt_gid_seq"
        else:
            seqName = parentRelname + "_" + pkField + "_seq"

        updateGidSql = "UPDATE \"" + importSchema + "\".\"" + importRelname + \
            "\" SET xp_gid = nextval('\"" + parentNspname + "\".\"" + seqName + \
            "\"');"
        updateGidQuery = QtSql.QSqlQuery(self.db)
        updateGidQuery.prepare(updateGidSql)
        updateGidQuery.exec_()

        if updateGidQuery.isActive():
            numAff = updateGidQuery.numRowsAffected()
            updateGidQuery.finish()
            return numAff
        else:
            self.showQueryError(updateGidQuery)
            return -1

    def __impGetChildTables(self, thisOid):
        childSql = self.__impGetChildTablesSql()
        childQuery = QtSql.QSqlQuery(self.db)
        childQuery.prepare(childSql)
        childQuery.bindValue(":oid", thisOid)
        childQuery.exec_()
        retValue = []

        if childQuery.isActive():
            while childQuery.next(): # returns false when all records are done
                childOid = childQuery.value(0)
                childNspname = childQuery.value(1)
                childRelname = childQuery.value(2)
                retValue.append([childOid, childNspname, childRelname])

            childQuery.finish()
        else:
            self.showQueryError(childQuery)
            return None

        return retValue

    def __impGetAllParentTables(self, childOid):
        retValue = []

        while True:
            nextParent = self.__impGetParentTable(childOid)

            if nextParent == None:
                return None
            elif nextParent == []:
                break
            else:
                retValue.append(nextParent)
                childOid = nextParent[0]

        return retValue

    def __impGetParentTable(self, childOid):
        parentSql = self.__impGetParentTableSql()
        parentQuery = QtSql.QSqlQuery(self.db)
        parentQuery.prepare(parentSql)
        parentQuery.bindValue(":oid", childOid)
        parentQuery.exec_()

        if parentQuery.isActive():
            if parentQuery.size() == 0:
                retValue = []
            while parentQuery.next(): # returns false when all records are done
                parentOid = parentQuery.value(0)
                parentNspname = parentQuery.value(1)
                parentRelname = parentQuery.value(2)
                retValue = [parentOid, parentNspname, parentRelname]

            parentQuery.finish()
        else:
            self.showQueryError(parentQuery)
            return None

        return retValue

    def __impSkipTheseFields(self):
        return ["gehoertZuPlan", "gehoertZuBereich", "id"] + self.__impSkipCodeLists()

    def __impSkipCodeLists(self):
        return ["gesetzlicheGrundlage"]

    def __impUpdateGmlId(self, importSchema, impRelname,
        xpNspname, xpRelname, pkField = "gid"):
        updateSql = "UPDATE \"" + xpNspname + "\".\"" + xpRelname + "\" z \
        SET gml_id = (SELECT id FROM \"" + importSchema + "\".\"" + impRelname + "\" q \
        WHERE q.xp_gid = z." + pkField + ") \
        WHERE z." + pkField + " IN (SELECT xp_gid FROM \"" + importSchema + "\".\"" + impRelname + "\")"
        return self.__impExecuteSql(updateSql)

    def __impInsertInXP(self, impOid, importSchema, impRelname,
        xpOid, xpNspname, xpRelname, arrayFields, pkField = "gid"):
        '''
        Füge ein neues Objekt in eine XP-Tabelle ein
        return: Anzahl eingefügter Datensätze oder None (= Fehler)
        '''

        numInserted = self.__impPerformInsertInXP(impOid, importSchema, impRelname,
            xpOid, xpNspname, xpRelname, pkField = pkField)

        if numInserted == -1:
            return -1
        elif numInserted == 0:
            return numInserted
        else:
            if len(arrayFields) > 0:
                if self.__impHandleArrays(impOid, importSchema, impRelname,
                        xpOid, xpNspname, xpRelname, arrayFields, pkField = pkField) == -1:
                    return -1
                else:
                    return numInserted
            else:
                return numInserted

    def __impPerformInsertInXP(self, impOid, importSchema, impRelname,
        xpOid, xpNspname, xpRelname, pkField = "gid"):
        attributeSql = self.__impGetMatchingAttributesSql()
        xpAttrQuery = QtSql.QSqlQuery(self.db)
        xpAttrQuery.prepare(attributeSql)
        xpAttrQuery.bindValue(":imp_oid", impOid)
        xpAttrQuery.bindValue(":xp_oid", xpOid)
        xpAttrQuery.exec_()

        if xpAttrQuery.isActive():
            insertSql = "INSERT INTO \"" + xpNspname + "\".\"" + \
                        xpRelname + "\" (" + pkField
            valueSql = " SELECT xp_gid"

            while xpAttrQuery.next(): # returns false when all records are done
                xpField = xpAttrQuery.value(0)
                impField = xpAttrQuery.value(1)
                xpType = xpAttrQuery.value(2)

                if xpField in self.__impSkipTheseFields():
                    continue

                insertSql += ", \"" + xpField + "\""

                if xpField in ["raeumlicherGeltungsbereich","geltungsbereich","position"]:
                    valueSql += ", ST_Multi(\"" + impField + "\")::" + xpType
                else:
                    if xpField == "uuid":
                        valueSql += ", COALESCE(id,\"" + impField + "\")::" + xpType
                        # übernehme die gml-id und nur, wenn leer, dann die uuid
                        # Zweck: wird bei der Bereichszuordnung als Referenz benutzt (s. Spezialfälle)
                    else:
                        valueSql += ", \"" + impField + "\"::" + xpType

            xpAttrQuery.finish()
        else:
            self.showQueryError(xpAttrQuery)
            return -1

        valueSql += " FROM \"" + importSchema + "\".\"" + impRelname + "\""
        insertSql += ")" + valueSql

        if xpRelname[len(xpRelname) - 7:] == "Flaeche":
            insertSql += " WHERE lower(geometrytype(position)) IN ('polygon','multipolygon');"
        elif xpRelname[len(xpRelname) - 5:] == "Linie":
            insertSql += " WHERE lower(geometrytype(position)) IN ('linestring','multilinestring');"
        elif xpRelname[len(xpRelname) - 5:] == "Punkt":
            insertSql += " WHERE lower(geometrytype(position)) IN ('point','multipoint');"
        else:
            insertSql += ";"

        return self.__impExecuteSql(insertSql)

    def __impUpdateXP(self, impOid, importSchema, impRelname,
        xpOid, xpNspname, xpRelname, arrayFields, pkField = "gid"):

        numUpdate = self.__impPerformUpdateXP(impOid, importSchema, impRelname,
            xpOid, xpNspname, xpRelname, pkField = pkField)

        if numUpdate == -1:
            return -1
        else:
            if len(arrayFields) > 0:
                if self.__impHandleArrays(impOid, importSchema, impRelname,
                        xpOid, xpNspname, xpRelname, arrayFields, pkField = pkField) == -1:
                    return -1
                else:
                    return numUpdate
            else:
                return numUpdate

    def __impPerformUpdateXP(self, impOid, importSchema, impRelname,
        xpOid, xpNspname, xpRelname, pkField = "gid"):
        '''
        Update xpRelname aus den gleichnamigen Feldern von impRelname
        '''

        attributeSql = self.__impGetMatchingAttributesSql()
        xpAttrQuery = QtSql.QSqlQuery(self.db)
        xpAttrQuery.prepare(attributeSql)
        xpAttrQuery.bindValue(":imp_oid", impOid)
        xpAttrQuery.bindValue(":xp_oid", xpOid)
        xpAttrQuery.exec_()

        if xpAttrQuery.isActive():
            if xpAttrQuery.size() == 0:
                xpAttrQuery.finish()
                return 0

            updateSql = ""

            while xpAttrQuery.next(): # returns false when all records are done
                xpField = xpAttrQuery.value(0)
                impField = xpAttrQuery.value(1)
                xpType = xpAttrQuery.value(2)

                if xpField in self.__impSkipTheseFields():
                    continue

                if updateSql == "":
                    updateSql = "UPDATE \"" + xpNspname + "\".\"" + xpRelname + "\" ziel SET ("
                    valuesSql = "(SELECT "
                else:
                    updateSql += ","
                    valuesSql += ","

                updateSql +=  "\"" + xpField + "\""

                if xpField == "uuid":
                    valuesSql += " COALESCE(\"" + impField + "\",id)::" + xpType
                else:
                    valuesSql += "\"" + impField + "\"::" + xpType
            xpAttrQuery.finish()
        else:
            self.showQueryError(xpAttrQuery)
            return -1

        updateSql += ") = "
        valuesSql += " FROM \"" + importSchema + "\".\"" + impRelname + \
                    "\" quelle WHERE quelle.xp_gid = ziel." + pkField +\
                    ") WHERE " + pkField + " IN (SELECT xp_gid FROM \"" + \
                    importSchema + "\".\"" + impRelname + "\");"
        updateSql += valuesSql
        updateQuery = QtSql.QSqlQuery(self.db)
        updateQuery.prepare(updateSql)
        updateQuery.exec_()

        if updateQuery.isActive():
            numUpdate = updateQuery.numRowsAffected()
            updateQuery.finish()
            return numUpdate
        else:
            self.showQueryError(updateQuery)
            return -1

    def __impGetAllFields(self, nspName, relName):
        retValue = []
        fieldSql = self.__impGetAllAttributesSql()
        fieldQuery = QtSql.QSqlQuery(self.db)
        fieldQuery.prepare(fieldSql)
        fieldQuery.bindValue(":nspname", nspName)
        fieldQuery.bindValue(":relname", relName)
        fieldQuery.exec_()

        if fieldQuery.isActive():
            while fieldQuery.next():
                fieldName = fieldQuery.value(1) # value(0) ist pg_class.oid
                fieldType = fieldQuery.value(2)
                retValue.append([fieldName, fieldType])
            fieldQuery.finish()
            return retValue
        else:
            self.showQueryError(fieldQuery)
            return None

    def __impHandleArrays(self, impOid, importSchema, impRelname,
        xpOid, xpNspname, xpRelname, arrayFields, pkField = "gid"):

        for anArrayField in arrayFields:
            # gibt es eine Tabelle importSchema.importRelname_anArrayField?
            # Lese Felder der Tabelle (im Idealfall zwei, nämlich xpRelname_gid und anArrayField)
            allFields = self.__impGetAllFields(xpNspname,  xpRelname + "_" + anArrayField)

            if allFields == None:
                return -1
            else:
                gidField = None
                relField = None

                for aValue in allFields:
                    fieldName = aValue[0]
                    fieldType = aValue[1]

                    if fieldName[(len(fieldName) - 1 - len(pkField)):] == "_" + pkField \
                            and fieldType == "int8":
                        gidField = fieldName
                    elif fieldName == anArrayField:
                        relField = fieldName
                        relType = fieldType

                if gidField != None and relField != None:
                    insertSql = "INSERT INTO \"" + xpNspname + "\".\""+ xpRelname + "_" + anArrayField + \
                        "\"(\"" + gidField + "\", \"" + relField + "\") SELECT xp_gid, unnest(\"" + \
                        anArrayField + "\")::" + relType + \
                        " FROM \"" + importSchema + "\".\"" + impRelname + "\";"
                        # leere Arrays erzeugen bei unnest keinen Datensatz
                    insertQuery = QtSql.QSqlQuery(self.db)
                    insertQuery.prepare(insertSql)
                    insertQuery.exec_()

                    if insertQuery.isActive():
                        insertQuery.finish()
                    else:
                        self.showQueryError(insertQuery)
                        return -1

                return 0

    def __impFindPlan(self, importSchema):
        tableSql = self.__impGetTableSql()
        planSql = tableSql + " WHERE c2.relname ILIKE '%_plan' and c2.relkind = 'r'"
        planQuery = QtSql.QSqlQuery(self.db)
        planQuery.prepare(planSql)
        planQuery.bindValue(":import1", importSchema)
        planQuery.bindValue(":import2", importSchema)
        planQuery.exec_()

        if planQuery.isActive():
            if planQuery.size() == 0:
                self.tools.showWarning(u"Kein Planobjekt im Importschema " + importSchema + \
                    u" gefunden!")
                return None
            elif planQuery.size() > 1:
                self.tools.showWarning(u"Mehrere Planobjektklassen im Importschema " + importSchema + \
                    u" oder mehrere Importschemas gefunden! \
            Es kann immer nur eine Klasse aus einem Schema importiert werden.")
                return None
            else:
                while planQuery.next(): # returns false when all records are done
                    planOid = planQuery.value(0)
                    planNspname = planQuery.value(1)
                    planRelname = planQuery.value(2)
                    impOid = planQuery.value(4)
                    impRelname = planQuery.value(5)

            planQuery.finish()
            return [planOid, planNspname, planRelname, impOid, impRelname]
        else:
            self.showQueryError(planQuery)
            return None

    def __impPlan(self, importSchema):
        planInfo = self.__impFindPlan(importSchema)

        if planInfo == None:
            return [-1, None]
        else:
            planOid = planInfo[0]
            planNspname = planInfo[1]
            planRelname = planInfo[2]
            impOid = planInfo[3]
            impRelname = planInfo[4]

        arrayFields = self.__impFindArrayFields(impOid)
        parentPlan = self.__impGetParentTable(planOid)

        if parentPlan == None:
            return [-1, None]
        else:
            parentOid = parentPlan[0]
            parentNspname = parentPlan[1]
            parentRelname = parentPlan[2]

        if self.__impCreateGidField(importSchema, impRelname,
            parentNspname, parentRelname) == -1:
            return [-1, None]

        if self.__impInsertInXP(impOid, importSchema,
            impRelname, planOid, planNspname, planRelname, arrayFields) == -1:
            return [-1, None]

        if self.__impUpdateName(importSchema,
            impRelname, parentNspname, parentRelname) == -1:
            return [-1, None]

        if self.__impUpdateGmlId(importSchema,
            impRelname, parentNspname, parentRelname) == -1:
            return [-1, None]

        numUpdated = self.__impUpdateXP(impOid, importSchema,
            impRelname, parentOid, parentNspname, parentRelname, arrayFields)

        if numUpdated == -1:
            return [-1, None]
        else:
            if numUpdated == 1:
                self.importMsg = u"1 Planobjekt "
            else:
                self.importMsg = str(numUpdated) + u" Planobjekte "

            self.importMsg +=  "aus " + impRelname + " importiert\n"
            return [numUpdated, impRelname]

    def __impUpdateName(self, importSchema, impRelname, parentNspname, parentRelname):
        # das Feld name wird als xplan_name importiert
        updateSql = "UPDATE \"" + parentNspname + "\".\"" + parentRelname + \
            "\" ziel SET \"name\" = (SELECT \"xplan_name\" FROM \"" + \
            importSchema + "\".\"" + impRelname + \
            "\" quelle WHERE quelle.xp_gid = ziel.gid) WHERE gid IN (SELECT xp_gid FROM \"" + \
                    importSchema + "\".\"" + impRelname + "\");"

        updateQuery = QtSql.QSqlQuery(self.db)
        updateQuery.prepare(updateSql)
        updateQuery.exec_()

        if updateQuery.isActive():
            numUpdated = updateQuery.numRowsAffected()
            updateQuery.finish()
            return numUpdated
        else:
            self.showQueryError(updateQuery)
            return -1

    def __impBereich(self, importSchema, impPlanRelname):
        tableSql = self.__impGetTableSql()
        bereichSql = tableSql + " WHERE c2.relname ILIKE '%_bereich' and c2.relkind = 'r'"
        bereichQuery = QtSql.QSqlQuery(self.db)
        bereichQuery.prepare(bereichSql)
        bereichQuery.bindValue(":import1", importSchema)
        bereichQuery.bindValue(":import2", importSchema)
        bereichQuery.exec_()

        if bereichQuery.isActive():
            if bereichQuery.size() == 0:
                self.tools.showWarning(u"Kein Bereichsobjekt im Importschema " + importSchema + \
                    u" gefunden!")
                return [-1, None]
            else:
                while bereichQuery.next(): # returns false when all records are done
                    bereichOid = bereichQuery.value(0)
                    bereichNspname = bereichQuery.value(1)
                    bereichRelname = bereichQuery.value(2)
                    impOid = bereichQuery.value(4)
                    impRelname = bereichQuery.value(5)

            bereichQuery.finish()
        else:
            self.showQueryError(bereichQuery)
            return [-1, None]

        arrayFields = self.__impFindArrayFields(impOid)
        parentBereich = self.__impGetParentTable(bereichOid)

        if parentBereich == None:
            return [-1, None]
        else:
            parentOid = parentBereich[0]
            parentNspname = parentBereich[1]
            parentRelname = parentBereich[2]

        if self.__impCreateGidField(importSchema, impRelname,
            parentNspname, parentRelname) == -1:
            return [-1, None]

        numInserted = self.__impInsertInXP(impOid, importSchema,
            impRelname, bereichOid, bereichNspname, bereichRelname,
            arrayFields)

        if numInserted == -1:
            return [-1, None]

        if self.__impUpdateGmlId(importSchema,
            impRelname, parentNspname, parentRelname) == -1:
            return [-1, None]

        numUpdated = self.__impUpdateXP(impOid, importSchema,
            impRelname, parentOid, parentNspname, parentRelname,
            arrayFields)

        if numUpdated == -1:
            return [-1, None]

        if numInserted != numUpdated:
            self.tools.showWarning(u"Bereich: Anzahl eingefügter entstpricht \
        nicht Anzahl geupdateter Datensätze.")
            return [-1, None]

        numUpdated = self.__impUpdateName(importSchema, impRelname, parentNspname, parentRelname)

        if numUpdated == 1:
            self.importMsg += u"1 Bereichsobjekt "
        else:
            self.importMsg += str(numUpdated) + u" Bereichsbjekte "

        self.importMsg +=  "aus " + impRelname + " importiert\n"
        return [numUpdated, impRelname]

    def __impObjekte(self, importSchema, impPlanRelname, impBereichRelname):
        tableSql = self.__impGetTableSql()
        objektSql = tableSql + " WHERE (c2.relname not ILIKE '%_bereich' \
        AND c2.relname not ILIKE '%_plan') OR c2.relname IS NULL \
        ORDER BY c1.relname DESC" # damit xp_gemeinde (falls vorh.) vor bla_plan_gemeinde kommt
        objektQuery = QtSql.QSqlQuery(self.db)
        objektQuery.prepare(objektSql)
        objektQuery.bindValue(":import1", importSchema)
        objektQuery.bindValue(":import2", importSchema)
        objektQuery.exec_()

        if objektQuery.isActive():
            if objektQuery.size() == 0:
                self.tools.showWarning(u"Keine Objekte im Importschema " + importSchema + \
                    u" gefunden!")
                return False
            else:
                spezialfaelle = []

                while objektQuery.next(): # returns false when all records are done
                    objektOid = objektQuery.value(0)
                    objektNspname = objektQuery.value(1)
                    objektRelname = objektQuery.value(2)
                    impOid = objektQuery.value(4)
                    impRelname = objektQuery.value(5)
                    parents = self.__impGetAllParentTables(objektOid)

                    if parents == None:
                        return False
                    elif parents == []:
                        spezialfaelle.append([impOid, impRelname])
                        continue
                    else:
                        arrayFields = self.__impFindArrayFields(impOid)
                        lastParent = parents[len(parents) - 1] # idR. XP_Objekt
                        parentOid = lastParent[0]
                        parentNspname = lastParent[1]
                        parentRelname = lastParent[2]
                        pkFields = self.__impGetPkField(parentOid)

                        if pkFields == None or pkFields == []:
                            return False
                        else:
                            if len(pkFields) > 1:
                                return False
                            else:
                                pkField = pkFields[0]

                        if self.__impCreateGidField(importSchema, impRelname,
                            parentNspname, parentRelname, pkField = pkField) == -1:
                            return False

                        childs = self.__impGetChildTables(objektOid)

                        if childs == None:
                            return False
                        elif childs == []:
                            if self.__impInsertInXP(impOid, importSchema,
                                impRelname, objektOid, objektNspname, objektRelname,
                                arrayFields, pkField = pkField) == -1:
                                return False
                        else:
                            for aChild in childs:
                                childOid = aChild[0]
                                childNspname = aChild[1]
                                childRelname = aChild[2]

                                if self.__impInsertInXP(impOid, importSchema,
                                    impRelname, childOid, childNspname, childRelname,
                                    arrayFields) == -1:
                                    return False

                            if self.__impUpdateXP(impOid, importSchema,
                                impRelname, objektOid, objektNspname, objektRelname,
                                arrayFields, pkField = pkField) == -1:
                                return False

                        if self.__impUpdateGmlId(importSchema,
                            impRelname, parentNspname, parentRelname,
                            pkField = pkField) == -1:
                            return False

                        for aParent in parents:
                            parentOid = aParent[0]
                            parentNspname = aParent[1]
                            parentRelname = aParent[2]

                            numUpdated = self.__impUpdateXP(impOid, importSchema,
                                impRelname, parentOid, parentNspname, parentRelname,
                                arrayFields, pkField = pkField)

                            if numUpdated == -1:
                                return False

                        if numUpdated == 0:
                            self.importMsg += "Keine Objekte aus "
                        elif numUpdated == 1:
                            self.importMsg += "1 Objekt aus "
                        else:
                            self.importMsg += str(numUpdated) + " Objekte aus "

                        self.importMsg  +=  impRelname + " importiert\n"

            objektQuery.finish()

            # Spezialfaelle erst, wenn alle anderen Objekte importiert wurden
            if len(spezialfaelle) > 0:
                for spezialfall in spezialfaelle:
                    spezialOid = spezialfall[0]
                    spezialRelname = spezialfall[1]
                    numCopied = self.__impSpezialfaelle(spezialOid, importSchema, spezialRelname,
                        impPlanRelname, impBereichRelname)

                    if numCopied == -1:
                        self.importMsg += "Nicht importiert: "  + spezialRelname + "\n"
                    elif numCopied == 1:
                        self.importMsg += u"1 Datensatz aus " +  \
                            spezialRelname + " importiert \n"
                    else:
                        self.importMsg += str(numCopied) + u" Datensätze aus " + \
                            spezialRelname + " importiert \n"
            return True
        else:
            self.showQueryError(objektQuery)
            return False

    def __impSpezialfaelle(self, impOid, importSchema, impRelname,
            impPlanRelname, impBereichRelname):

        modellbereich = impPlanRelname[:2].upper()

        if impRelname.lower() == "xp_gemeinde":
            if self.__impCreateGidField(importSchema, impRelname,
                "XP_Sonstiges", "XP_Gemeinde", pkField = "id") > 0:
                # Gemeinde könnte schon vorhanden sein
                update1Sql = "UPDATE  \"" + importSchema + "\".\"" + impRelname + "\" z \
                SET xp_gid = NULL WHERE ags IN (SELECT ags FROM \
                \"XP_Sonstiges\".\"XP_Gemeinde\")"

                numVorhanden = self.__impExecuteSql(update1Sql)

                if numVorhanden== -1:
                    return -1

                #Gemeinde(n) einfügen
                insertSql = "INSERT INTO \"XP_Sonstiges\".\"XP_Gemeinde\" \
                (id,ags,rs,\"gemeindeName\",\"ortsteilName\") \
                SELECT xp_gid,ags,rs,gemeindename, \
                ortsteilname FROM \"" + importSchema + "\".\"" + impRelname + "\" \
                WHERE xp_gid IS NOT NULL;"
                numInserted = self.__impExecuteSql(insertSql)

                if numInserted == -1:
                    return -1
                elif numInserted == 0 and numVorhanden == 0:
                    return 0
                else:
                    if numVorhanden > 0:
                        update2Sql = "UPDATE \"" + importSchema + "\".\"" + impRelname + "\" z \
                SET xp_gid = (SELECT id FROM \
                \"XP_Sonstiges\".\"XP_Gemeinde\" g WHERE z.ags = g.ags);"

                        if self.__impExecuteSql(update2Sql) == -1:
                            return -1

                    return numInserted

        elif impRelname.lower() == impPlanRelname + "_gemeinde":
            insertSql = "INSERT INTO \
        \"" + modellbereich + "_Basisobjekte\".\"" + modellbereich + "_Plan_gemeinde\" \
        (\"" + modellbereich + "_Plan_gid\",\"gemeinde\") \
        SELECT p.xp_gid,g.xp_gid \
        FROM \"" + importSchema + "\".\"" + impRelname + "\" i \
        JOIN \"" + importSchema + "\".\"" + impPlanRelname + "\" p \
            ON i.parent_id = p.id \
        JOIN \"" + importSchema + "\".\"xp_gemeinde\" g \
            ON i.xp_gemeinde_pkid = g.ogr_pkid;"
            return self.__impExecuteSql(insertSql)
        elif impRelname.lower() == impBereichRelname + "_planinhalt":
            insertSql = "INSERT INTO \"XP_Basisobjekte\".\"XP_Objekt_gehoertZuBereich\" \
            (\"gehoertZuBereich\",\"XP_Objekt_gid\") \
                SELECT b.xp_gid,o.gid \
                FROM \"" + importSchema + "\".\"" + impBereichRelname + "_planinhalt\" p \
                JOIN \"XP_Basisobjekte\".\"XP_Objekt\" o ON p.href = '#' || o.gml_id \
                JOIN \"" + importSchema + "\".\"" + impBereichRelname + "\" b ON \
                p.parent_id = b.id;"
            return self.__impExecuteSql(insertSql)
        elif impRelname.lower() == impPlanRelname + "_texte":
            insertSql = "INSERT INTO \"XP_Basisobjekte\".\"XP_Plan_texte\" \
            (\"texte\",\"XP_Plan_gid\") \
                SELECT a.xp_gid,p.xp_gid \
                FROM \"" + importSchema + "\".\"" + impPlanRelname + "_texte\" t \
                JOIN \"" + importSchema + "\".\"" + impPlanRelname + "\" p ON t.parent_id = p.id \
                JOIN \"" + importSchema + "\".\"" + impBereichRelname[:2] + "_textabschnitt\" a ON \
                t.href = '#' || a.id;"
            return self.__impExecuteSql(insertSql)
        elif impRelname.lower() == impBereichRelname + "_praesentationsobjekt":
            updateSql = "UPDATE \"XP_Praesentationsobjekte\".\"XP_AbstraktesPraesentationsobjekt\" z \
            SET \"gehoertZuBereich\" = \
                (SELECT b.gid \
                FROM \"XP_Basisobjekte\".\"XP_Bereich\" b \
                JOIN \"" + importSchema + "\".\"" + impRelname + "\" i \
                    ON b.gml_id = i.parent_id WHERE i.href = '#' || z.gml_id) \
            WHERE '#' || z.gml_id IN (SELECT href FROM \"" + importSchema + "\".\"" + impRelname + "\");"
            self.debug(updateSql)
            return self.__impExecuteSql(updateSql)
        elif impRelname.lower() == impPlanRelname.lower() + "_bereich": # zB bp_plan_bereich
            #Bereich dem Plan zuweisen
            gehoertZuPlanSql = "UPDATE \"" + modellbereich + "_Basisobjekte\".\"" + modellbereich + "_Bereich\" \
        z SET \"gehoertZuPlan\" = (SELECT p.gid FROM  \
        \"XP_Basisobjekte\".\"XP_Plan\" p \
        JOIN \"" + importSchema + "\".\"" + impRelname + "\" i \
        ON p.gml_id = i.parent_id \
        JOIN \"XP_Basisobjekte\".\"XP_Bereich\" b \
        ON i.href = '#' || b.gml_id \
        WHERE i.href = '#' || b.gml_id) \
        WHERE gid IN (SELECT gid FROM \"XP_Basisobjekte\".\"XP_Bereich\" b2 \
            JOIN \"" + importSchema + "\".\"" + impRelname + "\" i2 ON '#' || b2.gml_id = i2.href);"
            return self.__impExecuteSql(gehoertZuPlanSql)
        else:
            return -1

    def __impExecuteSql(self, thisSql):
        '''
        Führe eine beliebige INSERT/UPDATE-Anweisung aus
        '''
        thisQuery = QtSql.QSqlQuery(self.db)
        thisQuery.prepare(thisSql)
        thisQuery.exec_()

        if thisQuery.isActive():
            numDatasets = thisQuery.numRowsAffected()
            thisQuery.finish()
            return numDatasets
        else:
            self.showQueryError(thisQuery)
            return -1

    def showQueryError(self, query):
        self.tools.showQueryError(query)
