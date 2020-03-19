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
from builtins import str
from builtins import object
from qgis.PyQt import QtSql, QtGui
import qgis.core
from qgis.gui import *
from processing.tools.system import isWindows
import subprocess
import os

class XPImporter(object):
    def __init__(self, db, tools, params):
        self.db = db
        self.tools = tools
        self.params = params

    def importGml(self):
        '''
        Importiere GML-Dtei mit ogr2ogr in die DB
        '''
        importSchema = self.params["importSchema"]
        neuesSchema = self.params["neuesSchema"]
        ueberschreiben = self.params["ueberschreiben"]

        if neuesSchema == "1":
            if self.__impExecuteSql("SELECT \"QGIS\".imp_create_schema('" + \
                importSchema + "'," + str(int(ueberschreiben)) + ");") == -1:
                return [1, "Schema " + importSchema + " konnte nicht angelegt werden"]

        dbSettings = self.__impReadSettings()
        arguments = ['-f PostgreSQL',
            'PG:"host=' + dbSettings["host"] + ' dbname=' + dbSettings["database"] + ' user=' + dbSettings["username"] + ' password=' + dbSettings["passwd"] + '"',
                '-s_srs ' + self.params["s_srs"],
                '-t_srs ' + self.params["t_srs"],
                '-lco SCHEMA=' + importSchema,
                '-lco LAUNDER=NO',
                #'-nlt PROMOTE_TO_MULTI', funktionierte beim Test auf Win nicht
                '-nlt CONVERT_TO_LINEAR',
                '-oo XSD=' + self.params["xsd"],
                '-oo REMOVE_UNUSED_LAYERS=YES',
                'GMLAS:' + self.params["datei"]]
        loglines = []
        loglines.append('XPlan-Importer')

        if isWindows():
            commands = ['cmd.exe', '/C ', 'ogr2ogr.exe'] + arguments
        else:
            commands = ['ogr2ogr'] + arguments

        fused_command = ' '.join([str(c) for c in commands])

        try:
            proc = subprocess.check_output(
                fused_command,
                shell=True,
                stdin=open(os.devnull),
                stderr=subprocess.STDOUT
            )
            for line in proc:
                loglines.append(line)
            loglines = ' '.join([str(c) for c in loglines])
            success = 0
        except subprocess.CalledProcessError as e:
            success = e.returncode
            loglines = e.output

        if success == 0:
            tableSql = self.__impGetTableSql()
            tableQuery = QtSql.QSqlQuery(self.db)
            tableQuery.prepare(tableSql)
            tableQuery.bindValue(":import1", importSchema)
            tableQuery.bindValue(":import2", importSchema)
            tableQuery.exec_()

            if tableQuery.isActive():
                if tableQuery.size() == 0:
                    return [1,  u"Keine Tabellen im Importschema " + importSchema + \
                        u" gefunden!"]
                else:
                    while tableQuery.next(): # returns false when all records are done
                        importRelname = tableQuery.value(5)
                        if self.__impCreateGidField(importSchema, importRelname) == -1:
                            return[1, u"Konnte xp_gid-Feld für " + importSchema + "." + \
                                importRelname + " nicht anlegen"]

        return [success, str(loglines)]

    def importPlan(self):
        if not self.db.transaction():
            self.tools.showError("Konnte keine Transaktion auf der DB starten")
            return None
        importSchema = self.params["importSchema"]
        planResult = self.__impPlan(importSchema)
        numPlaene = planResult[0]
        impPlanRelname = planResult[1]

        if numPlaene <= 0:
            self.tools.showWarning(u"Konnte Plan nicht importieren")

            if not self.db.rollback():
                self.tools.showWarning(u"Konnte Transaktion micht zurückrollen")
            return None

        bereichResult = self.__impBereich(importSchema, impPlanRelname)
        numBereiche = bereichResult[0]
        impBereichRelname = bereichResult[1]

        if numBereiche <= 0:
            self.tools.showWarning(u"Konnte Bereich nicht importieren")

            if not self.db.rollback():
                self.tools.showWarning(u"Konnte Transaktion micht zurückrollen")
            return None

        if self.__impObjekte(importSchema, impPlanRelname, impBereichRelname):
            if not self.db.commit():
                self.tools.showWarning(u"Konnte Transaktion micht committen")
                return None
            else:
                return self.importMsg
        else:
            self.tools.showWarning(u"Konnte Objekte nicht importieren")

            if not self.db.rollback():
                self.tools.showWarning(u"Konnte Transaktion micht zurückrollen")
            return None

    def debug(self, msg):
        qgis.core.QgsMessageLog.logMessage("Debug" + "\n" + msg,  "XPlanung")

    def __impReadSettings(self):
        s = QtCore.QSettings( "XPlanung", "XPlanung-Erweiterung" )
        #service = ( s.value( "service", "" ) )
        host = ( s.value( "host", "" ) )
        port = ( s.value( "port", "5432" ) )
        database = ( s.value( "dbname", "" ) )
        authcfg = s.value( "authcfg", "" )
        username, passwd, authcfg = self.tools.getAuthUserNamePassword(authcfg)

        if authcfg == None:
            username = ( s.value( "uid", "" ) )
            passwd = ( s.value( "pwd", "" ) )

        retValue = {}
        retValue["host"] = host
        retValue["port"] = port
        retValue["database"] = database
        retValue["username"] = username
        retValue["passwd"] = passwd
        return retValue

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

    def __impAppendCodeListSql(self, codeList, impField, importSchema, impRelname, isArrayField):

        appendCodeListSql = "INSERT INTO " + codeList + " \
            (\"Bezeichner\") "

        if isArrayField:
            appendCodeListSql += "SELECT DISTINCT UNNEST(\"" + impField + "\")"
        else:
            appendCodeListSql += "SELECT DISTINCT \"" + impField + "\""

        appendCodeListSql += " FROM \"" + importSchema + "\".\"" + impRelname + "\" imp \
            LEFT JOIN " + codeList + " cl ON \
            imp.\"" + impField + "\" = cl.\"Bezeichner\" \
            WHERE cl.\"Bezeichner\" IS NULL \
            AND imp.\"" + impField + "\" IS NOT NULL;"

        return appendCodeListSql

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

    def __impCreateGidField(self, importSchema, importRelname):
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
            return 1
        else:
            self.showQueryError(createGidQuery)
            return -1

    def __impUpdateGidField(self, importSchema, importRelname,
        parentNspname, parentRelname, pkField = "gid"):

        if parentRelname == "XP_AbstraktesPraesentationsobjekt":
            seqName = "XP_APObjekt_gid_seq"
        else:
            seqName = parentRelname + "_" + pkField + "_seq"

        updateGidSql = "UPDATE \"" + importSchema + "\".\"" + importRelname + \
            "\" SET xp_gid = nextval('\"" + parentNspname + "\".\"" + seqName + \
            "\"');"
        return self.__impExecuteSql(updateGidSql)

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
        '''
        Diese Felder bleiben in _impPerformUpdateXP unberücksichtigt
        '''
        return ["gehoertZuPlan", "gehoertZuBereich", "id"] + self.__impSkipCodeListFields()

    def __impSkipCodeListFields(self):
        return ["gesetzlicheGrundlage"]

    def __impUseCodeListFields(self):
        '''
        gibt ein Dict zurück:
        key = Name des Feldes, das auf die CodeList referenziert
        item = array mit arrays:
            0 CodeList (Schema.Relation)
            1 array mit
                0 Schema und
                1 Relation in der das Feld auftaucht und für die dann diese CodeList gültig ist
                0 und 1 können auch None sein, dann gilt die CodeList für alle Relationen, in
                der ein Feld des Namens key auftaucht
        '''
        return {
            "abweichendeBauweise": [
                ["\"BP_Bebauung\".\"BP_AbweichendeBauweise\"",
                    [None,None] #BP_BaugebietBauweise,BP_BesondererNutzungszweckFlaeche,BP_GemeinbedarfsFlaeche
                ]
            ],
            "auspraegung": [
                ["\"FP_Ver_und_Entsorgung\".\"FP_ZentralerVersorgungsbereichAuspraegung\"",
                    ["FP_Ver_und_Entsorgung", "FP_ZentralerVersorgungsbereich"]
                ]
            ],
            "baumArt": [
                ["\"BP_Naturschutz_Landschaftsbild_Naturhaushalt\".\"BP_VegetationsobjektTypen\"",
                    ["BP_Naturschutz_Landschaftsbild_Naturhaushalt", "BP_AnpflanzungBindungErhaltung"]
                ]
            ],
            "detailArtDerFestlegung": [
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizNachSonstigemRecht\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_SonstigesRecht"]
                ],
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizNachStrassenverkehrsrecht\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_Strassenverkehrsrecht"]
                ],
                ["\"SO_Schutzgebiete\".\"SO_DetailKlassifizSchutzgebietNaturschutzrecht\"",
                    ["SO_Schutzgebiete", "SO_SchutzgebietNaturschutzrecht"]
                ],
                ["\"SO_Schutzgebiete\".\"SO_DetailKlassifizSchutzgebietWasserrecht\"",
                    ["SO_Schutzgebiete", "SO_SchutzgebietWasserrecht"]
                ],
                ["\"SO_Schutzgebiete\".\"SO_DetailKlassifizSchutzgebietSonstRecht\"",
                    ["SO_Schutzgebiete", "SO_SchutzgebietSonstigesRecht"]
                ],
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizGewaesser\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_Gewaesser"]
                ],
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizNachWasserrecht\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_Wasserrecht"]
                ],
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizNachForstrecht\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_Forstrecht"]
                ],
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizNachDenkmalschutzrecht\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_Denkmalschutzrecht"]
                ],
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizNachSchienenverkehrsrecht\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_Schienenverkehrsrecht"]
                ],
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizNachLuftverkehrsrecht\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_Luftverkehrsrecht"]
                ],
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizNachBodenschutzrecht\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_Bodenschutzrecht"]
                ],
                ["\"SO_NachrichtlicheUebernahmen\".\"SO_DetailKlassifizBauverbot\"",
                    ["SO_NachrichtlicheUebernahmen", "SO_Bauverbotszone"]
                ],
                ["\"SO_Schutzgebiete\".\"SO_DetailKlassifizNachForstrecht\"",
                    ["SO_Schutzgebiete", "SO_SchutzgebietNaturschutzrecht"]
                ]
            ],
            "detaillierteArtDerBaulNutzung": [
                ["\"BP_Bebauung\".\"BP_DetailArtDerBaulNutzung\"",
                    ["BP_Bebauung", "BP_BaugebietsTeilFlaeche"]
                ],
                ["\"FP_Bebauung\".\"FP_DetailArtDerBaulNutzung\"",
                    ["FP_Bebauung", "FP_BebauungsFlaeche"]
                ]
            ],
            "detaillierteDachform": [
                ["\"BP_Bebauung\".\"BP_DetailDachform\"",
                    [None,None] #"BP_Bebauung", "BP_Dachgestaltung" und "BP_Bebauung"."BP_GestaltungBaugebiet"
                ]
            ],
            "detaillierteFunktion": [
                ["\"LP_Erholung\".\"LP_ErholungFreizeitDetailFunktionen\"",
                    ["LP_Erholung", "LP_ErholungFreizeit"]
                ]
            ],
            "detaillierteTechnVorkehrung": [
                ["\"BP_Umwelt\".\"BP_DetailTechnVorkehrungImmissionsschutz\"",
                    ["BP_Umwelt", "BP_Immissionsschutz"]
                ]
            ],
            "detaillierteZweckbestimmung": [
                ["\"BP_Wasser\".\"BP_DetailZweckbestGewaesser\"",
                    ["BP_Wasser", "BP_GewaesserFlaeche"]
                ],
                ["\"BP_Wasser\".\"BP_DetailZweckbestWasserwirtschaft\"",
                    ["BP_Wasser", "BP_WasserwirtschaftsFlaeche"]
                ],
                ["\"BP_Landwirtschaft_Wald_und_Gruen\".\"BP_DetailZweckbestLandwirtschaft\"",
                    ["BP_Landwirtschaft_Wald_und_Gruen", "BP_Landwirtschaft"]
                ],
                ["\"BP_Landwirtschaft_Wald_und_Gruen\".\"BP_DetailZweckbestWaldFlaeche\"",
                    ["BP_Landwirtschaft_Wald_und_Gruen", "BP_WaldFlaeche"]
                ],
                ["\"BP_Landwirtschaft_Wald_und_Gruen\".\"BP_DetailZweckbestGruenFlaeche\"",
                    ["BP_Landwirtschaft_Wald_und_Gruen", "BP_GruenFlaeche"]
                ],
                ["\"BP_Bebauung\".\"BP_DetailZweckbestGemeinschaftsanlagen\"",
                    ["BP_Bebauung", "BP_GemeinschaftsanlagenFlaeche"]
                ],
                ["\"BP_Bebauung\".\"BP_DetailZweckbestNebenanlagen\"",
                    ["BP_Bebauung", "BP_NebenanlagenFlaeche"]
                ],
                ["\"BP_Gemeinbedarf_Spiel_und_Sportanlagen\".\"BP_DetailZweckbestGemeinbedarf\"",
                    ["BP_Gemeinbedarf_Spiel_und_Sportanlagen", "BP_GemeinbedarfsFlaeche"]
                ],
                ["\"BP_Gemeinbedarf_Spiel_und_Sportanlagen\".\"BP_DetailZweckbestSpielSportanlage\"",
                    ["BP_Gemeinbedarf_Spiel_und_Sportanlagen", "BP_SpielSportanlagenFlaeche"]
                ],
                ["\"BP_Verkehr\".\"BP_DetailZweckbestStrassenverkehr\"",
                    ["BP_Verkehr", "BP_VerkehrsFlaecheBesondererZweckbestimmung"]
                ],
                ["\"BP_Ver_und_Entsorgung\".\"BP_DetailZweckbestVerEntsorgung\"",
                    ["BP_Ver_und_Entsorgung", "BP_VerEntsorgung"]
                ],
                ["\"FP_Gemeinbedarf_Spiel_und_Sportanlagen\".\"FP_DetailZweckbestGemeinbedarf\"",
                    ["FP_Gemeinbedarf_Spiel_und_Sportanlagen", "FP_Gemeinbedarf"]
                ],
                ["\"FP_Gemeinbedarf_Spiel_und_Sportanlagen\".\"FP_DetailZweckbestSpielSportanlage\"",
                    ["FP_Gemeinbedarf_Spiel_und_Sportanlagen", "FP_SpielSportanlage"]
                ],
                ["\"FP_Landwirtschaft_Wald_und_Gruen\".\"FP_DetailZweckbestWaldFlaeche\"",
                    ["FP_Landwirtschaft_Wald_und_Gruen", "FP_WaldFlaeche"]
                ],
                ["\"FP_Landwirtschaft_Wald_und_Gruen\".\"FP_DetailZweckbestLandwirtschaftsFlaeche\"",
                    ["FP_Landwirtschaft_Wald_und_Gruen", "FP_Landwirtschaft"]
                ],
                ["\"FP_Landwirtschaft_Wald_und_Gruen\".\"FP_DetailZweckbestGruen\"",
                    ["FP_Landwirtschaft_Wald_und_Gruen", "FP_Gruen"]
                ],
                ["\"FP_Ver_und_Entsorgung\".\"FP_DetailZweckbestVerEntsorgung\"",
                    ["FP_Ver_und_Entsorgung", "FP_VerEntsorgung"]
                ],
                ["\"FP_Verkehr\".\"FP_DetailZweckbestStrassenverkehr\"",
                    ["FP_Verkehr", "FP_Strassenverkehr"]
                ],
                ["\"FP_Wasser\".\"FP_DetailZweckbestGewaesser\"",
                    ["FP_Wasser", "FP_Gewaesser"]
                ],
                ["\"FP_Wasser\".\"FP_DetailZweckbestWasserwirtschaft\"",
                    ["FP_Wasser", "FP_Wasserwirtschaft"]
                ]
            ],
            "detailTyp": [
                ["\"BP_Sonstiges\".\"BP_DetailAbgrenzungenTypen\"",
                    ["BP_Sonstiges", "BP_NutzungsartenGrenze"]
                ],
                ["\"LP_SchutzgebieteObjekte\".\"LP_BodenschutzrechtDetailTypen\"",
                    ["LP_SchutzgebieteObjekte", "LP_Bodenschutzrecht"]
                ],
                ["\"LP_SchutzgebieteObjekte\".\"LP_WaldschutzDetailTypen\"",
                    ["LP_SchutzgebieteObjekte", "LP_Forstrecht"]
                ],
                ["\"LP_SchutzgebieteObjekte\".\"LP_InternatSchutzobjektDetailTypen\"",
                    ["LP_SchutzgebieteObjekte", "LP_SchutzobjektInternatRecht"]
                ],
                ["\"LP_SchutzgebieteObjekte\".\"LP_SchutzobjektLandesrechtDetailTypen\"",
                    ["LP_SchutzgebieteObjekte", "LP_SchutzobjektLandesrecht"]
                ],
                ["\"LP_SchutzgebieteObjekte\".\"LP_SonstRechtDetailTypen\"",
                    ["LP_SchutzgebieteObjekte", "LP_SonstigesRecht"]
                ],
                ["\"LP_SchutzgebieteObjekte\".\"LP_WasserrechtGemeingebrEinschraenkungNaturschutzDetailTypen\"",
                    ["LP_SchutzgebieteObjekte", "LP_WasserrechtGemeingebrEinschraenkungNaturschutz"]
                ],
                ["\"LP_SchutzgebieteObjekte\".\"LP_WasserrechtSchutzgebietDetailTypen\"",
                    ["LP_SchutzgebieteObjekte", "LP_WasserrechtSchutzgebiet"]
                ],
                ["\"LP_SchutzgebieteObjekte\".\"LP_WasserrechtWirtschaftAbflussHochwSchutzDetailTypen\"",
                    ["LP_SchutzgebieteObjekte", "LP_WasserrechtWirtschaftAbflussHochwSchutz"]
                ]
            ],
            "massnahme": [
                ["\"LP_Sonstiges\".\"LP_MassnahmeLandschaftsbild\"",
                    ["LP_Sonstiges", "LP_Landschaftsbild"]
                ]
            ],
            "nutzung": [
                ["\"BP_Bebauung\".\"BP_NutzungNichUueberbaubGrundstFlaeche\"",
                    ["BP_Bebauung", "BP_NichtUeberbaubareGrundstuecksflaeche"]
                ]
            ],
            "pflanzart": [
                ["\"LP_MassnahmenNaturschutz\".\"LP_AnpflanzungBindungErhaltung_pflanzart\"",
                    ["LP_MassnahmenNaturschutz", "LP_Pflanzart"]
                ]
            ],
            "planArt": [
                ["\"SO_Basisobjekte\".\"SO_PlanArt\"",
                    ["SO_Basisobjekte", "SO_Plan"]
                ]
            ],
            "sonstGebietsArt": [
                ["\"SO_SonstigeGebiete\".\"SO_SonstGebietsArt\"",
                    ["SO_SonstigeGebiete", "SO_Gebiet"]
                ]
            ],
            "sonstPlanArt": [
                ["\"BP_Basisobjekte\".\"BP_SonstPlanArt\"",
                    ["BP_Basisobjekte", "BP_Plan"]
                ],
                ["\"FP_Basisobjekte\".\"FP_SonstPlanArt\"",
                    ["FP_Basisobjekte", "FP_Plan"]
                ],
                ["\"LP_Basisobjekte\".\"LP_SonstPlanArt\"",
                    ["LP_Basisobjekte", "LP_Plan"]
                ],
                ["\"RP_Basisobjekte\".\"RP_SonstPlanArt\"",
                    ["RP_Basisobjekte", "RP_Plan"]
                ]
            ],
            "sonstRechtscharakter": [
                ["\"SO_Basisobjekte\".\"SO_SonstRechtscharakter\"",
                    ["SO_Basisobjekte", "SO_Objekt"]
                ]
            ],
            "sonstRechtsstandGebiet": [
                ["\"SO_SonstigeGebiete\".\"SO_SonstRechtsstandGebietTyp\"",
                    ["SO_SonstigeGebiete", "SO_Gebiet"]
                ]
            ],
            "sonstTyp": [
                ["\"SO_Sonstiges\".\"SO_SonstGrenzeTypen\"",
                    ["SO_Sonstiges", "SO_Grenze"]
                ],
                ["\"BP_Bebauung\".\"BP_spezielleBauweiseSonstTypen\"",
                    ["BP_Bebauung", "BP_SpezielleBauweise"]
                ],
                ["\"RP_Sonstiges\".\"RP_SonstGrenzeTypen\"",
                    ["RP_Sonstiges", "RP_Grenze"]
                ]
            ],
            "spezifischePraegung": [
                ["\"FP_Basisobjekte\".\"FP_SpezifischePraegungTypen\"",
                    ["FP_Basisobjekte", "FP_Objekt"]
                ]
            ],
            "status": [
                ["\"BP_Basisobjekte\".\"BP_Status\"",
                    ["BP_Basisobjekte", "BP_Plan"]
                ],
                ["\"FP_Basisobjekte\".\"FP_Status\"",
                    ["FP_Basisobjekte", "FP_Plan"]
                ],
                ["\"RP_Basisobjekte\".\"RP_Status\"",
                    ["RP_Basisobjekte", "RP_Plan"]
                ]
            ],
            "stylesheetId": [
                ["\"XP_Praesentationsobjekte\".\"XP_StylesheetListe\"", [None, None]]
            ],
            "typ": [
                ["\"RP_Sonstiges\".\"RP_GenerischesObjektTypen\"",
                    ["RP_Sonstiges", "RP_GenerischesObjekt"]
                ],
                ["\"LP_SchutzgebieteObjekte\".\"LP_WasserrechtSonstigeTypen\"",
                    ["LP_SchutzgebieteObjekte", "LP_WasserrechtSonstige"]
                ]
            ],
            "zweckbestimmung": [
                ["\"BP_Sonstiges\".\"BP_ZweckbestimmungGenerischeObjekte\"",
                    ["BP_Sonstiges", "BP_GenerischesObjekt"]
                ],
                ["\"FP_Sonstiges\".\"FP_ZweckbestimmungGenerischeObjekte\"",
                    ["FP_Sonstiges", "FP_GenerischesObjekt"]
                ],
                ["\"LP_Sonstiges\".\"LP_ZweckbestimmungGenerischeObjekte\"",
                    ["LP_Sonstiges", "LP_GenerischesObjekt"]
                ]
            ]
        }

    def __impIsCodeListField(self, codeListField, xpNspname, xpRelname):
        '''
        prüft, ob das CodeList-Feld wirklich eins ist
        GenerischesObjekt.zweckbestimmung sind CodeLists, andere zweckbestimmung nicht
        '''
        if codeListField == "zweckbestimmung":
            if xpRelname.find("Gener") != -1:
                return True
            else:
                return False
        else:
            return True

    def __impAppendCodeList(self, codeListField, impField, importSchema, impRelname, xpNspname, xpRelname, isArrayField):
        '''
        Eine CodeList mit neuen Werten ergänzen
        Eine CodeList ist eine Relation mit den Feldern Code und Bezeichner
        xpNspname.xpRelname ist die Relation, bei deren Import ein CodeList-Wert gefunden wurde
        '''

        if not self.__impIsCodeListField(codeListField, xpNspname, xpRelname):
            return 0

        codeList = self.__impGetCodeList(codeListField, xpNspname, xpRelname)

        if codeList != "":
            codeListSql = self.__impAppendCodeListSql(codeList, impField, importSchema, impRelname, isArrayField)
            return self.__impExecuteSql(codeListSql)
        else:
            return -1

    def __impGetCodeList(self, codeListField, xpNspname, xpRelname):
        '''
        Gibt die CodeList-Relation für ein übergebenes CodeListFeld zurück
        '''

        useCodeLists = self.__impUseCodeListFields()

        try:
            codeListArray = useCodeLists[codeListField]
        except:
            return ""

        if not self.__impIsCodeListField(codeListField, xpNspname, xpRelname):
            return ""

        matchFound = False

        for anItem in codeListArray:
            aCodeList = anItem[0]
            aRelation = anItem[1]
            aSchemaName = aRelation[0]

            if aSchemaName == None:
                matchFound = True
                break
            else:
                if aSchemaName == xpNspname:
                    aRelName = aRelation[1]

                    if aRelName == xpRelname:
                        matchFound = True
                        break

        if matchFound:
            return aCodeList
        else:
            return ""

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
        return: Anzahl eingefügter Datensätze oder -1 (= Fehler)
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
                    valueSql += ", CASE WHEN geometrytype(\"" + impField + "\") LIKE 'MULTI%' \
                        THEN \"" + impField + "\"::" + xpType + " ELSE \
                        ST_Multi(\"" + impField + "\")::" + xpType + " END"
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

        self.debug("__impUpdateXP: \n" + importSchema + "." + impRelname + ": " + str(numUpdate))
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
        xpOid, xpNspname, xpRelname, pkField = "gid", arrayFields = []):
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
                elif xpField in list(self.__impUseCodeListFields().keys()) and \
                    self.__impIsCodeListField(xpField, xpNspname, xpRelname):
                    codeListSucces = self.__impAppendCodeList(xpField, impField,
                        importSchema, impRelname, xpNspname, xpRelname, isArrayField = False)
                        #TODO: rauskkriegen, ob arrayfield

                    if codeListSucces == -1:
                        self.tools.showWarning("CodeListError " + xpNspname + "." + xpRelname + "." + xpField)
                        return -1

                if updateSql == "":
                    updateSql = "UPDATE \"" + xpNspname + "\".\"" + xpRelname + "\" ziel SET ("
                    valuesSql = "(SELECT "
                    joinSql = ""
                else:
                    updateSql += ","
                    valuesSql += ","

                updateSql +=  "\"" + xpField + "\""

                if xpField == "uuid":
                    valuesSql += " COALESCE(\"" + impField + "\",id)::" + xpType
                elif xpField in list(self.__impUseCodeListFields().keys()) and\
                    self.__impIsCodeListField(xpField, xpNspname, xpRelname):

                    codeList = self.__impGetCodeList(xpField, xpNspname, xpRelname)

                    if codeList != "":
                        valuesSql += " " + xpField + ".\"Code\""
                                        # xpField dient hier als alias für die angejointe CodeList--Tabelle
                        joinSql += " LEFT JOIN " + codeList + " as " + xpField + \
                            " ON quelle.\"" + impField + "\" = " + xpField + ".\"Bezeichner\"" # alias setzen
                            # LEFT JOIN, weil das Feld ja nicht belegt sein muß
                else:
                    valuesSql += "\"" + impField + "\"::" + xpType
            xpAttrQuery.finish()
        else:
            self.showQueryError(xpAttrQuery)
            return -1

        updateSql += ") = "
        valuesSql += " FROM \"" + importSchema + "\".\"" + impRelname + \
                    "\" quelle " + joinSql + \
                    " WHERE quelle.xp_gid = ziel." + pkField +\
                    ") WHERE " + pkField + " IN (SELECT xp_gid FROM \"" + \
                    importSchema + "\".\"" + impRelname + "\");"
        updateSql += valuesSql
        self.debug("updateSql \n"+ updateSql)
        return self.__impExecuteSql(updateSql)

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
        planSql = tableSql + " WHERE c2.relname ILIKE '%p_plan' and c2.relkind = 'r'"
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
        '''
        Importiere das Planobjekt
        '''

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

        if self.__impUpdateGidField(importSchema, impRelname,
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
        '''
        Importiere den Bereich/die Bereiche
        '''

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

        if self.__impUpdateGidField(importSchema, impRelname,
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
        self.debug("__impBereich: \n" + importSchema + "." + impRelname + ": " + str(numUpdated))

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
        '''
        Objekte importieren
        '''
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
                    elif parents == []: # keine Kindklassen, sondern eigenständige
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

                        if self.__impUpdateGidField(importSchema, impRelname,
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
                            self.debug("__impObjekte: \n" + importSchema + "." + impRelname + ": " + str(numUpdated))

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
            if self.__impUpdateGidField(importSchema, impRelname,
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
