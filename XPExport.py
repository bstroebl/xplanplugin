# -*- coding: utf-8 -*-
"""
/***************************************************************************
XPEXport
A QGIS plugin
Fachschale XPlan für XPlanung
                             -------------------
begin                : 2022-04-12
copyright            : (C) 2022 by Lukas Hermeling
email                : lukas.hermeling@web.de
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
from ast import And, Break
from asyncio.windows_events import NULL
from builtins import str
from builtins import object
from weakref import ref
from qgis.PyQt import QtSql, QtGui
import qgis.core
from PyQt5.QtCore import QDate, Qt
from qgis.gui import *
from processing.tools.system import isWindows
import subprocess
import os
import json
import uuid # --> Erzeugen der GML-ID

class XPExporter(object):
    # Klasse Initialisieren
    def __init__(self, db, tools, params, planArt):
        self.db = db
        self.tools = tools
        self.params = params
        self.planart = planArt
    # Funktion zum exportieren von XPlanGML-Dateien 
    def exportGml(self):
        # Varibale für XPlanGML-Daten
        newGMLfile = None

        # Abfrage der Version von XPlanung
        # Hier wurde nur für Version 5.2 die folgenden Objekte für den B-Plan realisiert: 
        # BP_Plan, BP_Bereich, BP_BaugebietsTeilFlaeche, BP_StrassenVerkehrsFlaechen
        if str(self.params["xsdNr"]) == "5.0":
            self.tools.showError("Für die XPlanung Version " + str(self.params["xsdNr"]) + " wurde der Export noch nicht umgesetzt!")
        elif str(self.params["xsdNr"]) == "5.1":
            self.tools.showError("Für die XPlanung Version " + str(self.params["xsdNr"]) + " wurde der Export noch nicht umgesetzt!")
        elif str(self.params["xsdNr"]) == "5.2":
            # Abfrage der Planart
            if self.planart == "BP_Plan":
                newGMLfile = self.exportBP_5_2()
            elif self.planart == "FP_Plan":
                self.tools.showError("Für "+ self.planart+ " wurde der Export noch nicht umgesetzt!")
            elif self.planart == "LP_Plan":
                self.tools.showError("Für "+ self.planart+ " wurde der Export noch nicht umgesetzt!")
            elif self.planart == "RP_Plan":
                self.tools.showError("Für "+ self.planart+ " wurde der Export noch nicht umgesetzt!")  
            elif self.planart == "SO_Plan":
                self.tools.showError("Für "+ self.planart+ " wurde der Export noch nicht umgesetzt!")  

        # Erzeugen der GML-Date in Datei-Pfad
        if newGMLfile != None:
            # Boolean-Werte anpassen für die Validierung
            newGMLfile = newGMLfile.replace('True', 'true')
            newGMLfile = newGMLfile.replace('False', 'false')
            try:
                # Die entsprechende GML-Datei öffnen
                file = open(self.params["datei"], "w" )
                # Schreiben des Inhalts der GML-Datei
                file.write(newGMLfile)
                newGMLfile = self.params["plangebiet"]
                # Schließen der GML-Datei
                file.close()
            except IOError:
                self.tools.showError("Fehler beim Schreiben der GML-Datei!")

        return newGMLfile
    
    # Export für B-Pläne der Version 5.2
    def exportBP_5_2(self):
        # Header Daten
        # muss eindeutig für das XML Dokument sein
        self.gid = self.abf_gesamtGMLID()
        xPlan_xsd1 = self.params["xsdNr"] 
        xPlan_xsd1 = xPlan_xsd1.replace(".","/" )
        gml_BP = '<?xml version="1.0" encoding="utf-8"?>\n'+\
            '<xplan:XPlanAuszug xmlns:wfs="http://www.opengis.net/wfs" xmlns:gml="http://www.opengis.net/gml/3.2" '+\
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" '+\
            'xmlns:xlink="http://www.w3.org/1999/xlink" gml:id= "Gml_'+str(uuid.uuid4())+'" '+\
            'xsi:schemaLocation="http://www.xplanung.de/xplangml/'+ xPlan_xsd1 +' '+\
            'http://www.xplanungwiki.de/upload/XPlanGML/'+ self.params["xsdNr"] +'/Schema/XPlanung-Operationen.xsd" '+\
            'xmlns:xplan="http://www.xplanung.de/xplangml/'+ xPlan_xsd1 +'">\n'
        
        # Tab = Einrückung der GML-Daten (Hierarchie-Ebene)
        tab = 1
        # Abfrage der Daten für boundBy!!!
        self.epsg, koor_loCorner, koor_upCorner = self.abf_bounding_planGebiet()
        
        # Übergabe der abgefragt DB-Daten an die Funktion
        gml_BP += self.exp_boundBy(tab, koor_loCorner, koor_upCorner)

        # BP_Plan
        gml_BP += self.exp_plangebietGML(koor_loCorner, koor_upCorner)
        
        # BP_Bereiche
        if len(self.bereichGID):
            i =0
            for berGID in self.bereichGID:
                gml_BP += self.exp_bereichgebietGML(berGID, i)
                i += 1
        
        # Objekt BP_BaugebietsTeilFlaeche
        if len(self.bereichGID):
            for berGID in self.bereichGID:
                # Abfrage der Objekte in den Bereichen
                bgTF = self.abf_bauGTF_ID(berGID)
                if len(bgTF)>0:
                    for b in bgTF:
                        gml_BP += self.exp_bgtfObj_GML(b)
        
        # Objekt BP_StrassenVerkehrsFlaechen
        if len(self.bereichGID):
            for berGID in self.bereichGID:
                # Abfrage der Objekte in den Bereichen
                strVerk = self.abf_strVerkFlae_ID(berGID)
                if len(strVerk)>0:
                    for strV in strVerk:
                        gml_BP += self.exp_strVerkFlae_GML(strV)
        
        # Objekt XP_AbstraktesPraesentationsobjekt
        if len(self.bereichGID):
            for berGID in self.bereichGID:
                # Abfrage der Objekte in den Bereichen
                abstPrOb= self.abf_abstPrOb(berGID)
                if len(abstPrOb)>0:
                    for absP in abstPrOb:
                         gml_BP +=self.exp_APO(absP)


        # Ende der GML, Schließen des XPlanAuszug
        gml_BP += "</xplan:XPlanAuszug>"
        return gml_BP

    ### Abfragen-Abschnitt ###

    # Abfrage der GID und der GML-ID
    def abf_gesamtGMLID(self):
        gmlID_sql = "SELECT plan.\"gid\" FROM \"XP_Basisobjekte\".\"XP_Plan\" as plan JOIN \"XP_Basisobjekte\".\"XP_Plaene\" as plaene on (plan.\"gid\" = plaene.\"gid\") WHERE plan.\"name\" = '"+ self.params["plangebiet"] +"' and plaene.\"Objektart\" = '"+ self.planart +"'"
        gmlID_query = QtSql.QSqlQuery(self.db)
        gmlID_query.prepare(gmlID_sql)
        gmlID_query.exec_()
        
        if gmlID_query.isActive():
            if gmlID_query.size() != 0:
                while gmlID_query.next():
                    gid = str(gmlID_query.value(0))
                    
            else:
                self.tools.showError("Abfrage GID/GMLID: keine Daten Vorhanden!")
                return None
        else:
            self.tools.showError("Die Datenbankabfrage ist nicht aktiv!")
            return None

        return gid
    
    # Abfrage BoundBy-Daten XPlanAuszug
    def abf_bounding_planGebiet(self):
        boundByPG_sql = 'SELECT ST_AsGeoJSON(ST_Envelope("XP_Plaene"."raeumlicherGeltungsbereich"))  FROM "XP_Basisobjekte"."XP_Plaene" WHERE gid = \''+ self.gid +'\''
        boundByPG_query= QtSql.QSqlQuery(self.db)
        boundByPG_query.prepare(boundByPG_sql)
        boundByPG_query.exec_()
        if boundByPG_query.isActive():
            if boundByPG_query.size() != 0:
                while boundByPG_query.next():
                    bbJSON_planG = json.loads(boundByPG_query.value(0))
        # Abfrage der Daten zu der geometrischen Ausdehnung des Plangebiets
        epsg = bbJSON_planG["crs"]["properties"]["name"]
        koor_loCorner = str(bbJSON_planG["coordinates"][0][0][0]) +" "+ str(bbJSON_planG["coordinates"][0][0][1])
        koor_upCorner = str(bbJSON_planG["coordinates"][0][2][0]) +" "+ str(bbJSON_planG["coordinates"][0][2][1])
        return epsg, koor_loCorner, koor_upCorner

    ### Abfragen BP_Plan ####
    # Abfrage der XP_Plan Attribute
    def abf_xpPlan(self):
        xp_Plan_sql = "SELECT * FROM \"XP_Basisobjekte\".\"XP_Plan\" WHERE gid = '"+ self.gid +"'"
        xp_Plan_query = QtSql.QSqlQuery(self.db)
        xp_Plan_query.prepare(xp_Plan_sql) 
        xp_Plan_query.exec_()
        if xp_Plan_query.isActive():
            if xp_Plan_query.size() != 0:
                while xp_Plan_query.next():
                    num = xp_Plan_query.value(2)
                    intID = xp_Plan_query.value(3)
                    beschr = xp_Plan_query.value(4)
                    komm = xp_Plan_query.value(5)
                    technHerstellDatum = xp_Plan_query.value(6)
                    genehmDatum = xp_Plan_query.value(7)
                    untergangsDatum = xp_Plan_query.value(8)
                    erstellmassstab = xp_Plan_query.value(9)
                    bezugshoehe = xp_Plan_query.value(10)
                    techPlanerst = xp_Plan_query.value(11)
                    refExernalCodeList = xp_Plan_query.value(12)
                    gmlID = xp_Plan_query.value(13)

        return [num,intID, beschr, komm, technHerstellDatum, genehmDatum, untergangsDatum, erstellmassstab, bezugshoehe, techPlanerst, refExernalCodeList, gmlID]
    
    # Erste Abfrge der BP_Plan Daten
    def abf_bpPlan(self):
        bp_Plan_sql = "SELECT * FROM \"BP_Basisobjekte\".\"BP_Plan\" WHERE gid = '"+ self.gid +"'"
        bp_Plan_query = QtSql.QSqlQuery(self.db)
        bp_Plan_query.prepare(bp_Plan_sql)
        bp_Plan_query.exec_()
    
        if bp_Plan_query.isActive():
            if bp_Plan_query.size() != 0:
                while bp_Plan_query.next():
                    plangeber = bp_Plan_query.value(3)
                    sonstPlanArt = bp_Plan_query.value(4)
                    verfahren = bp_Plan_query.value(5)
                    rechtsstand = bp_Plan_query.value(6)
                    status = bp_Plan_query.value(7)
                    hoehenbezug = bp_Plan_query.value(8)
                    aendBisDat = bp_Plan_query.value(9)
                    aufstBeschlussDat = bp_Plan_query.value(10)
                    veraenSperreDat = bp_Plan_query.value(11)
                    auslegStartDat = bp_Plan_query.value(12)
                    auslegEndDat = bp_Plan_query.value(13)
                    traegbeteilStartDat = bp_Plan_query.value(14)
                    traegbeteilEndDat = bp_Plan_query.value(15)
                    satzBeschlussDat = bp_Plan_query.value(16)
                    rechtsverordDat = bp_Plan_query.value(17)
                    inkraftDat = bp_Plan_query.value(18)
                    ausfertDat = bp_Plan_query.value(19)
                    veraendSperre = bp_Plan_query.value(20)
                    staedtebauVertrag = bp_Plan_query.value(21)
                    erschlVertrag = bp_Plan_query.value(22)
                    durchfueVertrag = bp_Plan_query.value(23)
                    gruenordPlan = bp_Plan_query.value(24)
                    # Gesetze
                    versBauNVODat = bp_Plan_query.value(31)
                    versBauNVOText = bp_Plan_query.value(32)
                    versBauGBDat = bp_Plan_query.value(33)
                    versBauGBText = bp_Plan_query.value(34)
                    versSonstRechtgrundlageDat = bp_Plan_query.value(35)
                    versSonstRechtgrundlageText = bp_Plan_query.value(36)

        return [plangeber, sonstPlanArt, verfahren, rechtsstand, status, hoehenbezug, aendBisDat, aufstBeschlussDat,
        veraenSperreDat, auslegStartDat, auslegEndDat, traegbeteilStartDat, traegbeteilEndDat, satzBeschlussDat,rechtsverordDat,
        inkraftDat, ausfertDat, veraendSperre, staedtebauVertrag, erschlVertrag, durchfueVertrag, gruenordPlan, versBauNVODat,
        versBauNVOText, versBauGBDat, versBauGBText, versSonstRechtgrundlageDat, versSonstRechtgrundlageText]
    
    # Abfrage XP_Plan_aendert
    def abf_aendertPlan(self):
        xp_aend_sql = "SELECT aendert FROM \"XP_Basisobjekte\".\"XP_Plan_aendert\" WHERE \"XP_Plan_gid\" = '"+ self.gid + "'"
        xp_aend_query = QtSql.QSqlQuery(self.db)
        xp_aend_query.prepare(xp_aend_sql)
        xp_aend_query.exec_()
        aendList = []
        if xp_aend_query.isActive():
            if xp_aend_query.size() != 0:
                while xp_aend_query.next():
                    elem = self.abf_verbundPlan(xp_aend_query.value(0))
                    aendList.append(elem)
        return aendList
    
    # Abfrage der Element für aendert
    def abf_verbundPlan(self, id):
        aendElem_sql = "SELECT * FROM \"XP_Basisobjekte\".\"XP_VerbundenerPlan\" WHERE \"verbundenerPlan\" = "+ str(id)
        aendElem_query = QtSql.QSqlQuery(self.db)
        aendElem_query.prepare(aendElem_sql)
        aendElem_query.exec_()
        elem = []
        if aendElem_query.isActive():
            if aendElem_query.size() != 0:
                while aendElem_query.next():
                    elem.append(aendElem_query.value(0))
                    elem.append(aendElem_query.value(1))
                    elem.append(aendElem_query.value(2))
                    elem.append(aendElem_query.value(3))
        return elem

    # Abfrage wurdeGeaendertVon
    def abf_wgvPlan(self):
        xp_wgv_sql = "SELECT \"wurdeGeaendertVon\" FROM \"XP_Basisobjekte\".\"XP_Plan_wurdeGeaendertVon\" WHERE \"XP_Plan_gid\" = '"+ self.gid + "'"
        xp_wgv_query = QtSql.QSqlQuery(self.db)
        xp_wgv_query.prepare(xp_wgv_sql)
        xp_wgv_query.exec_()
        aendList = []
        if xp_wgv_query.isActive():
            if xp_wgv_query.size() != 0:
                while xp_wgv_query.next():
                    elem = self.abf_verbundPlan(xp_wgv_query.value(0))
                    aendList.append(elem)
        return aendList

    # Abfrage raeumlicherGeltungsbereich
    def abf_raeumlGeltPlan(self):
        xp_raeumG_sql = "SELECT ST_AsGeoJSON(\"raeumlicherGeltungsbereich\")FROM \"XP_Basisobjekte\".\"XP_RaeumlicherGeltungsbereich\" WHERE gid = '"+ str(self.gid) + "'"
        xp_raeumG_query = QtSql.QSqlQuery(self.db)
        xp_raeumG_query.prepare(xp_raeumG_sql)
        xp_raeumG_query.exec_()
        raeumlGelt = ""
        if xp_raeumG_query.isActive():
            if xp_raeumG_query.size() != 0:
                while xp_raeumG_query.next():
                    raeumlGelt=xp_raeumG_query.value(0)
        return raeumlGelt

    # Abfrage der Verfahrensmerkmale
    def abf_verfMerkPlan(self):
        xp_verfMerk_sql = "SELECT * FROM \"XP_Basisobjekte\".\"XP_VerfahrensMerkmal\" WHERE \"XP_Plan\" = "+ self.gid
        xp_verfMerk_query = QtSql.QSqlQuery(self.db)
        xp_verfMerk_query.prepare(xp_verfMerk_sql)
        xp_verfMerk_query.exec_()
        verM = []
        if xp_verfMerk_query.isActive():
            if xp_verfMerk_query.size() != 0:
                while xp_verfMerk_query.next():
                    verM.append([xp_verfMerk_query.value(1), xp_verfMerk_query.value(2), xp_verfMerk_query.value(3), xp_verfMerk_query.value(4)])
        return verM

    # Abfrage der Texte XP_Plan_texte
    def abf_XP_texAb(self, id):
        xp_texte_sql = 'SELECT * FROM "XP_Basisobjekte"."XP_Plan_texte" as tex\
	        JOIN "XP_Basisobjekte"."XP_TextAbschnitt" as texAb\
                ON(tex."texte" = texAb."id")\
                    WHERE tex."XP_Plan_gid" = '+ str(id)
        xp_texte_query = QtSql.QSqlQuery(self.db)
        xp_texte_query.prepare(xp_texte_sql)
        xp_texte_query.exec_()
        tex = []
        if xp_texte_query.isActive():
            if xp_texte_query.size() != 0:
                while xp_texte_query.next():
                    tex.append([xp_texte_query.value(3), xp_texte_query.value(4), xp_texte_query.value(5), xp_texte_query.value(6)])
        return tex

    # Abfrage XP_ExterneReferenz
    def abf_externRef(self, id_ref):
        xp_extRef_sql = 'SELECT * FROM \"XP_Basisobjekte\".\"XP_ExterneReferenz\" as extRef '\
            'JOIN \"XP_Basisobjekte\".\"XP_ExterneReferenzArt\" as extRefArt '\
            'on (extRef.\"art\" = extRefArt.\"Code\") '\
            'WHERE extRef.\"id\" = ' + str(id_ref)
        xp_extRef_query = QtSql.QSqlQuery(self.db)
        xp_extRef_query.prepare(xp_extRef_sql)
        xp_extRef_query.exec_()
        extRef=[]
        if xp_extRef_query.isActive():
            if xp_extRef_query.size() != 0:
                while xp_extRef_query.next():
                    extRef.append([xp_extRef_query.value(1),xp_extRef_query.value(2),xp_extRef_query.value(12),xp_extRef_query.value(4),
                    xp_extRef_query.value(5),xp_extRef_query.value(6),xp_extRef_query.value(7),xp_extRef_query.value(8),xp_extRef_query.value(9)])
        return extRef
    
    # Abfrage XP_BegruendungAbschnitt für XP_Plan
    def abf_begAbsch(self):
        xp_begAbsch_sql = 'SELECT * FROM "XP_Basisobjekte"."XP_Plan_begruendungsTexte" as begTex\
            JOIN "XP_Basisobjekte"."XP_BegruendungAbschnitt" as begAbsch\
                ON(begTex."begruendungsTexte" = begAbsch."id")\
                    WHERE begTex."XP_Plan_gid" = '+ self.gid
        xp_begAbsch_query = QtSql.QSqlQuery(self.db)
        xp_begAbsch_query.prepare(xp_begAbsch_sql)
        xp_begAbsch_query.exec_()
        begAb = []
        if xp_begAbsch_query.isActive():
            if xp_begAbsch_query.size() != 0:
                while xp_begAbsch_query.next():
                    begAb.append([xp_begAbsch_query.value(3),xp_begAbsch_query.value(4),xp_begAbsch_query.value(5)])
        return begAb
    
    # Abfrage XP_SpezExterneReferenz
    def abf_spezExRef(self, gid):
        xp_spezExRef_sql = 'SELECT * FROM "XP_Basisobjekte"."XP_Plan_externeReferenz" as pla\
            JOIN "XP_Basisobjekte"."XP_SpezExterneReferenz" as spe\
            ON(pla."externeReferenz"=spe."id")\
            WHERE pla."XP_Plan_gid" ='+ gid
        xp_spezExRef_query = QtSql.QSqlQuery(self.db)
        xp_spezExRef_query.prepare(xp_spezExRef_sql)
        xp_spezExRef_query.exec_()
        spezER = "NULL"
        if xp_spezExRef_query.isActive():
            if xp_spezExRef_query.size() != 0:
                while xp_spezExRef_query.next():
                    gid = xp_spezExRef_query.value(1)
                    spezER = xp_spezExRef_query.value(3)
        return [gid, spezER]

    # Abfrage BP_Gemeinde
    def abf_gemeinde(self):
        xp_gemeinde_sql = 'SELECT * FROM "BP_Basisobjekte"."BP_Plan_gemeinde" as bp_gem \
            JOIN "XP_Sonstiges"."XP_Gemeinde" as xp_gem \
                ON(bp_gem."gemeinde" = xp_gem."id") \
                    WHERE bp_gem."BP_Plan_gid" ='+ self.gid
        xp_gemeinde_query = QtSql.QSqlQuery(self.db)
        xp_gemeinde_query.prepare(xp_gemeinde_sql)
        xp_gemeinde_query.exec_()
        gemeinde=[]
        if xp_gemeinde_query.isActive():
            if xp_gemeinde_query.size() != 0:
                while xp_gemeinde_query.next():
                    gemeinde.append([xp_gemeinde_query.value(3), xp_gemeinde_query.value(4), 
                    xp_gemeinde_query.value(5), xp_gemeinde_query.value(6)])
        return gemeinde

    # Abfrage BP_planaufstellendeGemeinde
    def abf_planaufGemeinde(self):
        xp_planGem_sql = 'SELECT * FROM "BP_Basisobjekte"."BP_Plan_planaufstellendeGemeinde" as bp_gem \
            JOIN "XP_Sonstiges"."XP_Gemeinde" as xp_gem \
                ON(bp_gem."planaufstellendeGemeinde" = xp_gem."id") \
                    WHERE bp_gem."BP_Plan_gid" = '+ self.gid
        xp_planGem_query = QtSql.QSqlQuery(self.db)
        xp_planGem_query.prepare(xp_planGem_sql)
        xp_planGem_query.exec_()
        planGem=[]
        if xp_planGem_query.isActive():
            if xp_planGem_query.size() != 0:
                while xp_planGem_query.next():
                    planGem.append([xp_planGem_query.value(3), xp_planGem_query.value(4), 
                    xp_planGem_query.value(5), xp_planGem_query.value(6)])
        return planGem

    # Abfrage plangeber
    def abf_plangeber(self, pg_id):
        xp_plangeber_sql= 'SELECT * FROM "XP_Sonstiges"."XP_Plangeber" WHERE id =' + str(pg_id)
        xp_plangeber_query = QtSql.QSqlQuery(self.db)
        xp_plangeber_query.prepare(xp_plangeber_sql)
        xp_plangeber_query.exec_()
        plangeber =[]
        if xp_plangeber_query.isActive():
            if xp_plangeber_query.size() != 0:
                while xp_plangeber_query.next():
                    plangeber=[xp_plangeber_query.value(1), xp_plangeber_query.value(2)]
        return plangeber

    # Abfrage PlanArt
    def abf_planArt(self):
        bp_planArt_sql = 'SELECT * FROM "BP_Basisobjekte"."BP_Plan_planArt" WHERE "BP_Plan_gid" =' + self.gid
        bp_planArt_query = QtSql.QSqlQuery(self.db)
        bp_planArt_query.prepare(bp_planArt_sql)
        bp_planArt_query.exec_()
        planArt = []
        if bp_planArt_query.isActive():
            if bp_planArt_query.size() != 0:
                while bp_planArt_query.next():
                    planArt.append(bp_planArt_query.value(1))
        return planArt

    # Abfrage sonstPlanArt
    def abf_sonstPlanArt(self, id):
        bp_sonstPlanArt_sql= 'SELECT * FROM "BP_Basisobjekte"."BP_SonstPlanArt" WHERE "Code" ='+id
        bp_sonstPlanArt_query = QtSql.QSqlQuery(self.db)
        bp_sonstPlanArt_query.prepare(bp_sonstPlanArt_sql)
        bp_sonstPlanArt_query.exec_()
        if bp_sonstPlanArt_query.isActive():
            if bp_sonstPlanArt_query.size() != 0:
                while bp_sonstPlanArt_query.next():
                    sonstPlanArt=bp_sonstPlanArt_query.value(1)
        return sonstPlanArt
    
    # Abfrage GML-ID für Bereiche in Plangebiet
    def abf_bereichGMLID(self):
        bp_bereichGMLID_sql = 'SELECT xp."gml_id", xp."gid" FROM "BP_Basisobjekte"."BP_Bereich" as bp\
            JOIN "XP_Basisobjekte"."XP_Bereich" as xp\
                ON(bp."gid" = xp."gid")\
                    WHERE bp."gehoertZuPlan" = '+ self.gid
        bp_bereichGMLID_query = QtSql.QSqlQuery(self.db)
        bp_bereichGMLID_query.prepare(bp_bereichGMLID_sql)
        bp_bereichGMLID_query.exec_()
        self.gmlID_bereiche = []
        self.bereichGID = []
        if bp_bereichGMLID_query.isActive():
            if bp_bereichGMLID_query.size() != 0:
                while bp_bereichGMLID_query.next():
                    self.gmlID_bereiche.append(bp_bereichGMLID_query.value(0))
                    self.bereichGID.append(bp_bereichGMLID_query.value(1))
        

    ### Abfragen BP_Bereich ###

    # Abfrage Bereich BoundBy
    def abf_bereichBBy(self, id_Ber):
        boundByBer_sql = 'SELECT ST_AsGeoJSON (ST_Envelope("XP_Bereiche"."geltungsbereich"))  FROM "XP_Basisobjekte"."XP_Bereiche" WHERE gid = '+ str(id_Ber)
        boundByBer_query= QtSql.QSqlQuery(self.db)
        boundByBer_query.prepare(boundByBer_sql)
        boundByBer_query.exec_()
        if boundByBer_query.isActive():
            if boundByBer_query.size() != 0:
                while boundByBer_query.next():
                    bbJSON_bereichG = json.loads(boundByBer_query.value(0))
        # Abfrage der Daten zu der geometrischen Ausdehnung des Plangebiets
        koor_loCorner = str(bbJSON_bereichG["coordinates"][0][0][0]) +" "+ str(bbJSON_bereichG["coordinates"][0][0][1])
        koor_upCorner = str(bbJSON_bereichG["coordinates"][0][2][0]) +" "+ str(bbJSON_bereichG["coordinates"][0][2][1])
        return koor_loCorner, koor_upCorner 

    # Abfrage Attribute XP_Bereich
    def abf_xpBereich(self, gid_ber):
        xp_bereich_sql = 'SELECT * FROM "XP_Basisobjekte"."XP_Bereich" WHERE gid = '+str(gid_ber)
        xp_bereich_query = QtSql.QSqlQuery(self.db)
        xp_bereich_query.prepare(xp_bereich_sql)
        xp_bereich_query.exec_()
        if xp_bereich_query.isActive():
            if xp_bereich_query.size() != 0:
                while xp_bereich_query.next():
                    nummer = xp_bereich_query.value(1)
                    name = xp_bereich_query.value(2)
                    bedeutung = xp_bereich_query.value(3)
                    detailierteBedeutung = xp_bereich_query.value(4)
                    erstellungsMassstab = xp_bereich_query.value(5)
                    rasterBasis = xp_bereich_query.value(6)
        return [nummer, name, bedeutung, detailierteBedeutung, erstellungsMassstab, rasterBasis]
    
    # Abfrage geltungsbereich
    def abf_geltBereich(self, gidBer):
        xp_geltBer_sql = "SELECT ST_AsGeoJSON(\"geltungsbereich\")FROM \"BP_Basisobjekte\".\"BP_Bereich\" WHERE gid = '"+ str(gidBer) + "'"
        xp_geltBer_query = QtSql.QSqlQuery(self.db)
        xp_geltBer_query.prepare(xp_geltBer_sql)
        xp_geltBer_query.exec_()
        geltBer = ""
        if xp_geltBer_query.isActive():
            if xp_geltBer_query.size() != 0:
                while xp_geltBer_query.next():
                    geltBer=xp_geltBer_query.value(0)
        return geltBer

    # Abfrage refScan
    def abf_refScanBer(self,gidBer):
        xp_refScan_sql = 'SELECT * FROM "XP_Basisobjekte"."XP_Bereich_refScan" WHERE "XP_Bereich_gid" = '+ str(gidBer)
        xp_refScan_query = QtSql.QSqlQuery(self.db)
        xp_refScan_query.prepare(xp_refScan_sql)
        xp_refScan_query.exec_()
        refScan=[]
        if xp_refScan_query.isActive():
            if xp_refScan_query.size() != 0:
                while xp_refScan_query.next():
                    extRef = self.abf_externRef(xp_refScan_query[1])
                    refScan.append(extRef)
        return refScan
    
    # Abfrage Planinhalt Objekte
    def abf_ObjektGMLID(self, idBer):
        bp_objektGMLID_sql = 'SELECT obj."gml_id" FROM "XP_Basisobjekte"."XP_Objekt_gehoertZuBereich" as objZuBereich\
            JOIN "XP_Basisobjekte"."XP_Objekt" as obj\
                ON(objZuBereich."XP_Objekt_gid" = obj."gid")\
                    WHERE objZuBereich."gehoertZuBereich" = '+ str(idBer)
        bp_objektGMLID_query = QtSql.QSqlQuery(self.db)
        bp_objektGMLID_query.prepare(bp_objektGMLID_sql)
        bp_objektGMLID_query.exec_()
        gmlID_objekte = []
        if bp_objektGMLID_query.isActive():
            if bp_objektGMLID_query.size() != 0:
                while bp_objektGMLID_query.next():
                    gmlID_objekte.append(bp_objektGMLID_query.value(0))
        return gmlID_objekte

    #Abfrage Praesentationsobjekt im Bereich
    def abf_prObjektGMLID(self, idBer):
        bp_prObjektGMLID_sql = 'SELECT "gml_id" FROM "XP_Praesentationsobjekte"."XP_AbstraktesPraesentationsobjekt" WHERE "gehoertZuBereich" = '+ str(idBer)
        bp_prObjektGMLID_query = QtSql.QSqlQuery(self.db)
        bp_prObjektGMLID_query.prepare(bp_prObjektGMLID_sql)
        bp_prObjektGMLID_query.exec_()
        gmlID_prObjekte = []
        if bp_prObjektGMLID_query.isActive():
            if bp_prObjektGMLID_query.size() != 0:
                while bp_prObjektGMLID_query.next():
                    gmlID_prObjekte.append(bp_prObjektGMLID_query.value(0))
        return gmlID_prObjekte
    
    # Abfrage der Attribute BP_Bereich
    def abf_bpBereich(self, gid_Ber):
        bp_bereich_sql = 'SELECT * FROM "BP_Basisobjekte"."BP_Bereich" WHERE gid = '+str(gid_Ber)
        bp_bereich_query = QtSql.QSqlQuery(self.db)
        bp_bereich_query.prepare(bp_bereich_sql)
        bp_bereich_query.exec_()
        if bp_bereich_query.isActive():
            if bp_bereich_query.size() != 0:
                while bp_bereich_query.next():
                    versionBauNVODatum = bp_bereich_query.value(3)
                    versionBauNVOText = bp_bereich_query.value(4)
                    versionBauGBDatum = bp_bereich_query.value(5)
                    versionBauGBText = bp_bereich_query.value(6)
                    versionSonstRechtsgrundlageDatum = bp_bereich_query.value(7)
                    versionSonstRechtsgrundlageText = bp_bereich_query.value(8)
                    gehoertZuPlan = bp_bereich_query.value(9)
        return [versionBauNVODatum, versionBauNVOText, versionBauGBDatum, versionBauGBText, 
        versionSonstRechtsgrundlageDatum, versionSonstRechtsgrundlageText, gehoertZuPlan]
    
    ### Abfragen für BP_BaugebietsTeilFlaeche
    # Abfrage der GID
    def abf_bauGTF_ID(self, berGID):
        bd_bauGTF_sql = 'SELECT bgtf."gid" FROM "XP_Basisobjekte"."XP_Objekt_gehoertZuBereich" as obj\
            JOIN "BP_Bebauung"."BP_BaugebietsTeilFlaeche" as bgtf\
                ON(obj."XP_Objekt_gid" = bgtf."gid")\
                    WHERE obj."gehoertZuBereich" ='+ str(berGID)
        bd_bauGTF_query = QtSql.QSqlQuery(self.db)
        bd_bauGTF_query.prepare(bd_bauGTF_sql)
        bd_bauGTF_query.exec_()
        bgtf_ID = []
        if bd_bauGTF_query.isActive():
            if bd_bauGTF_query.size() != 0:
                while bd_bauGTF_query.next():
                    bgtf_ID.append(bd_bauGTF_query.value(0))
        return bgtf_ID

    # Abfrage für die Attribute aus XP_Objekt
    def abf_xpObj(self, gid):
        xp_obj_sql = 'SELECT * FROM "XP_Basisobjekte"."XP_Objekt" WHERE gid = ' + str(gid)
        xp_obj_query = QtSql.QSqlQuery(self.db)
        xp_obj_query.prepare(xp_obj_sql)
        xp_obj_query.exec_()
        if xp_obj_query.isActive():
            if xp_obj_query.size() != 0:
                while xp_obj_query.next():
                    uuid_ = xp_obj_query.value(1)
                    text = xp_obj_query.value(2)
                    rechtsstand = xp_obj_query.value(3)
                    gesetzlicheGrundlage = xp_obj_query.value(4)
                    gliederung1 = xp_obj_query.value(5)
                    gliederung2 = xp_obj_query.value(6)
                    ebene = xp_obj_query.value(7)
                    startBedingung = xp_obj_query.value(8)
                    endeBedingung = xp_obj_query.value(9)
                    gml_id = xp_obj_query.value(10)
                    aufschrift = xp_obj_query.value(11)
        return [uuid_, text, rechtsstand, gesetzlicheGrundlage, gliederung1, gliederung2,ebene, startBedingung, endeBedingung, gml_id, aufschrift]

    # 
    def abf_xpObjHoean(self, gid):
        xp_xpObjHoean_sql='SELECT * FROM "XP_Basisobjekte"."XP_Objekt_hoehenangabe" as obj_hoe\
            JOIN "XP_Sonstiges"."XP_Hoehenangabe" as hoeAng\
                ON (obj_hoe."hoehenangabe"=hoeAng."id")\
                    WHERE obj_hoe."XP_Objekt_gid" = '+str(gid)
        xp_xpObjHoean_query = QtSql.QSqlQuery(self.db)
        xp_xpObjHoean_query.prepare(xp_xpObjHoean_sql)
        xp_xpObjHoean_query.exec_()
        xpObjHoean =[]
        if xp_xpObjHoean_query.isActive():
            if xp_xpObjHoean_query.size() != 0:
                while xp_xpObjHoean_query.next():
                    xpObjHoean.append([xp_xpObjHoean_query.value(4), xp_xpObjHoean_query.value(3), xp_xpObjHoean_query.value(6),
                    xp_xpObjHoean_query.value(5), xp_xpObjHoean_query.value(7), xp_xpObjHoean_query.value(8), 
                    xp_xpObjHoean_query.value(9), xp_xpObjHoean_query.value(10)])
                    
        return xpObjHoean

    # Abfrage Baugebietsteilfläche XP_Objekt extReferenz
    def abf_extRef_bgtfObj(self, gid):
        xp_extRef_bgtfObj_sql = 'SELECT * FROM "XP_Basisobjekte"."XP_Objekt_externeReferenz" WHERE "XP_Objekt_gid" ='+ str(gid)
        xp_extRef_bgtfObj_query = QtSql.QSqlQuery(self.db)
        xp_extRef_bgtfObj_query.prepare(xp_extRef_bgtfObj_sql)
        xp_extRef_bgtfObj_query.exec_()
        extRef_bgtf=[]
        if xp_extRef_bgtfObj_query.isActive():
            if xp_extRef_bgtfObj_query.size() != 0:
                while xp_extRef_bgtfObj_query.next():
                    extRef_bgtf.append(self.abf_externRef(xp_extRef_bgtfObj_query.value(1)))
        return extRef_bgtf

    # gehörtzuBereich GML-ID
    def abf_gmlIDBereich_bgtfObj(self, gid):
        xp_gmlIDBereich_bgtfObj_sql = 'SELECT ber."gml_id" FROM "XP_Basisobjekte"."XP_Objekt_gehoertZuBereich" as zuge\
            JOIN "XP_Basisobjekte"."XP_Bereich" as ber\
                ON (zuge."gehoertZuBereich"=ber."gid")\
                    WHERE "XP_Objekt_gid" = '+ str(gid)
        xp_gmlIDBereich_bgtfObj_query = QtSql.QSqlQuery(self.db)
        xp_gmlIDBereich_bgtfObj_query.prepare(xp_gmlIDBereich_bgtfObj_sql)
        xp_gmlIDBereich_bgtfObj_query.exec_()
        gml_ID="NULL"
        if xp_gmlIDBereich_bgtfObj_query.isActive():
            if xp_gmlIDBereich_bgtfObj_query.size() != 0:
                while xp_gmlIDBereich_bgtfObj_query.next():
                    gml_ID = xp_gmlIDBereich_bgtfObj_query.value(0)
        return gml_ID
    
    # gehörtzuBereich GML-ID
    def abf_gmlIDPraes_bgtfObj(self, gid):
        xp_gmlIDPraes_bgtfObj_sql = 'SELECT "gml_id" FROM "XP_Praesentationsobjekte"."XP_AbstraktesPraesentationsobjekt" WHERE "gid" = '+ str(gid)
        xp_gmlIDPraes_bgtfObj_query = QtSql.QSqlQuery(self.db)
        xp_gmlIDPraes_bgtfObj_query.prepare(xp_gmlIDPraes_bgtfObj_sql)
        xp_gmlIDPraes_bgtfObj_query.exec_()
        gml_ID = []
        if xp_gmlIDPraes_bgtfObj_query.isActive():
            if xp_gmlIDPraes_bgtfObj_query.size() != 0:
                while xp_gmlIDPraes_bgtfObj_query.next():
                    gml_ID.append(xp_gmlIDPraes_bgtfObj_query.value(0))
        return gml_ID
    
    # Abfrage XP_BegruendungAbschnitt für XP_Objekte
    def abf_begrAbsch(self, gid):
        xp_begrAbsch_sql = 'SELECT * FROM "XP_Basisobjekte"."XP_Objekt_refBegruendungInhalt" as obj\
            JOIN "XP_Basisobjekte"."XP_BegruendungAbschnitt" as begAb\
                ON(obj."refBegruendungInhalt"= begAb."id")\
                    WHERE obj."XP_Objekt_gid" = ' + str(gid)
        xp_begrAbsch_query = QtSql.QSqlQuery(self.db)
        xp_begrAbsch_query.prepare(xp_begrAbsch_sql)
        xp_begrAbsch_query.exec_()
        begrAbsch = []
        if xp_begrAbsch_query.isActive():
            if xp_begrAbsch_query.size() != 0:
                while xp_begrAbsch_query.next():
                    begrAbsch.append([xp_begrAbsch_query.value(3), xp_begrAbsch_query.value(4), xp_begrAbsch_query.value(5)])
        return begrAbsch
    
    # Abfrage XP_WirksamkeitBedingung
    def abf_wirkBed(self, id_):
        xp_wirkBed_sql = 'SELECT * FROM "XP_Basisobjekte"."XP_WirksamkeitBedingung" WHERE id = ' + str(id_)
        xp_wirkBed_query = QtSql.QSqlQuery(self.db)
        xp_wirkBed_query.prepare(xp_wirkBed_sql)
        xp_wirkBed_query.exec_()
        if xp_wirkBed_query.isActive():
            if xp_wirkBed_query.size() != 0:
                while xp_wirkBed_query.next():
                    bedingung = xp_wirkBed_query.value(1)
                    datumAbsolut = xp_wirkBed_query.value(2)
                    datumRelativ = xp_wirkBed_query.value(3)
        return [bedingung, datumAbsolut, datumRelativ]

    # Abfrage BP_Objekt
    def abf_bpObj(self, gid):
        bp_objBgtf_sql = 'SELECT * FROM "BP_Basisobjekte"."BP_Objekt" WHERE gid = ' + str(gid)
        bp_objBgtf_query = QtSql.QSqlQuery(self.db)
        bp_objBgtf_query.prepare(bp_objBgtf_sql)
        bp_objBgtf_query.exec_()
        rechtscharakter = "NULL"
        laermkontingent = "NULL"
        zusatzkontingent = "NULL"
        if bp_objBgtf_query.isActive():
            if bp_objBgtf_query.size() != 0:
                while bp_objBgtf_query.next():
                    rechtscharakter = bp_objBgtf_query.value(1)
                    laermkontingent = bp_objBgtf_query.value(2)
                    zusatzkontingent = bp_objBgtf_query.value(3)
        return [rechtscharakter, laermkontingent, zusatzkontingent]
    
    # Abfrage BP_TextAbschnitt
    def abf_refTextIn(self, gid):
        bp_refTextIn_sql = 'SELECT * FROM "BP_Basisobjekte"."BP_Objekt_refTextInhalt" WHERE "BP_Objekt_gid" = ' + str(gid)
        bp_refTextIn_query = QtSql.QSqlQuery(self.db)
        bp_refTextIn_query.prepare(bp_refTextIn_sql)
        bp_refTextIn_query.exec_()
        rechtscharakter = []
        if bp_refTextIn_query.isActive():
            if bp_refTextIn_query.size() != 0:
                while bp_refTextIn_query.next():
                    rechtscharakter.append(bp_refTextIn_query.value(1))
        return rechtscharakter
    
    # abf_ausglFlae
    def abf_ausglFlae(self, gid):
        bp_ausglFlae_sql = 'SELECT ST_AsGeoJSON("position"), "ziel", "sonstZiel", "refMassnahmenText", "refLandschaftsplan" FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_AusgleichsFlaeche" WHERE "gid" = ' + str(gid)
        bp_ausglFlae_query = QtSql.QSqlQuery(self.db)
        bp_ausglFlae_query.prepare(bp_ausglFlae_sql)
        bp_ausglFlae_query.exec_()
        ausglFlae = []
        if bp_ausglFlae_query.isActive():
            if bp_ausglFlae_query.size() != 0:
                while bp_ausglFlae_query.next():
                    ausglFlae.append([bp_ausglFlae_query.value(0), bp_ausglFlae_query.value(1),bp_ausglFlae_query.value(2), bp_ausglFlae_query.value(3), bp_ausglFlae_query.value(4)])
        return ausglFlae
    # Massnahmen
    def abf_ausglFlae_mas(self, gid):
        bp_ausglFlaeMas_sql = 'SELECT * FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_AusgleichsFlaeche_massnahme" as mas'\
            'JOIN "XP_Basisobjekte"."XP_SPEMassnahmenDaten" as spe'\
            'on (mas."massnahme"= spe."id")'\
            'WHERE mas."BP_AusgleichsFlaeche_gid" =' + str(gid)
        bp_ausglFlaeMas_query = QtSql.QSqlQuery(self.db)
        bp_ausglFlaeMas_query.prepare(bp_ausglFlaeMas_sql)
        bp_ausglFlaeMas_query.exec_()
        ausglFlaeMas = []
        if bp_ausglFlaeMas_query.isActive():
            if bp_ausglFlaeMas_query.size() != 0:
                while bp_ausglFlaeMas_query.next():
                    ausglFlaeMas.append([bp_ausglFlaeMas_query.value(3), bp_ausglFlaeMas_query.value(4), bp_ausglFlaeMas_query.value(5)])
        return ausglFlaeMas

    # BP_AnpflanzungBindungErhaltung
    def abf_anpfBindErh(self, gid):
        bp_anpfBindErh_sql = 'SELECT * FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_AnpflanzungBindungErhaltung" WHERE "gid" = ' + str(gid)
        bp_anpfBindErh_query = QtSql.QSqlQuery(self.db)
        bp_anpfBindErh_query.prepare(bp_anpfBindErh_sql)
        bp_anpfBindErh_query.exec_()
        anpfBindErh = []
        if bp_anpfBindErh_query.isActive():
            if bp_anpfBindErh_query.size() != 0:
                while bp_anpfBindErh_query.next():
                    anpfBindErh.append([bp_anpfBindErh_query.value(1), bp_anpfBindErh_query.value(2),
                    bp_anpfBindErh_query.value(3), bp_anpfBindErh_query.value(4), bp_anpfBindErh_query.value(5), 
                    bp_anpfBindErh_query.value(6)])     
        return anpfBindErh
    # BP_AnpflanzungBindungErhaltung Gegenstand
    def abf_anpfBindErh_geg(self, gid):
        bp_aBErhGeg_sql = 'SELECT gegenstand FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_AnpflanzungBindungErhaltung_gegenstand" WHERE "BP_AnpflanzungBindungErhaltung_gid" = ' + str(gid)
        bp_aBErhGeg_query = QtSql.QSqlQuery(self.db)
        bp_aBErhGeg_query.prepare(bp_aBErhGeg_sql)
        bp_aBErhGeg_query.exec_()
        aBErhGeg = []
        if bp_aBErhGeg_query.isActive():
            if bp_aBErhGeg_query.size() != 0:
                while bp_aBErhGeg_query.next():
                    aBErhGeg.append(bp_aBErhGeg_query.value(0))     
        return aBErhGeg

    # Abfrage BP_SchutzPflegeEntwicklungsMassnahme
    def abf_schPfEntw(self, gid):
        bp_schPfEntw_sql = 'SELECT * FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_SchutzPflegeEntwicklungsMassnahme" WHERE "gid" = ' + str(gid)
        bp_schPfEntw_query = QtSql.QSqlQuery(self.db)
        bp_schPfEntw_query.prepare(bp_schPfEntw_sql)
        bp_schPfEntw_query.exec_()
        schPfEntw = []
        if bp_schPfEntw_query.isActive():
            if bp_schPfEntw_query.size() != 0:
                while bp_schPfEntw_query.next():
                    schPfEntw.append([bp_schPfEntw_query.value(1), bp_schPfEntw_query.value(2),bp_schPfEntw_query.value(3), 
                    bp_schPfEntw_query.value(4), bp_schPfEntw_query.value(5)])     
        return schPfEntw
    # Massnahmen
    def abf_schPfEntw_mas(self, gid):
        bp_schPfEntwMas_sql = 'SELECT * FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_SchutzPflegeEntwicklungsMassnahme_massnahme" as mas'\
            'JOIN "XP_Basisobjekte"."XP_SPEMassnahmenDaten" as spe'\
            'on (mas."massnahme"= spe."id")'\
            'WHERE mas."BP_SchutzPflegeEntwicklungsMassnahme_gid" =' + str(gid)
        bp_schPfEntwMas_query = QtSql.QSqlQuery(self.db)
        bp_schPfEntwMas_query.prepare(bp_schPfEntwMas_sql)
        bp_schPfEntwMas_query.exec_()
        schPfEntwMas = []
        if bp_schPfEntwMas_query.isActive():
            if bp_schPfEntwMas_query.size() != 0:
                while bp_schPfEntwMas_query.next():
                    schPfEntwMas.append([bp_schPfEntwMas_query.value(3), bp_schPfEntwMas_query.value(4), bp_schPfEntwMas_query.value(5)])
        return schPfEntwMas
    
    # BP_SchutzPflegeEntwicklungsFlaeche
    def abf_speFlae(self, gid):
        bp_speFlae_sql = 'SELECT ST_AsGeoJSON("position"), "ziel", "sonstZiel", "istAusgleich", "refMassnahmenText", "refLandschaftsplan" FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_SchutzPflegeEntwicklungsFlaeche" WHERE "gid" = ' + str(gid)
        bp_speFlae_query = QtSql.QSqlQuery(self.db)
        bp_speFlae_query.prepare(bp_speFlae_sql)
        bp_speFlae_query.exec_()
        speFlae = []
        if bp_speFlae_query.isActive():
            if bp_speFlae_query.size() != 0:
                while bp_speFlae_query.next():
                    speFlae.append([bp_speFlae_query.value(0), bp_speFlae_query.value(1),bp_speFlae_query.value(2), 
                    bp_speFlae_query.value(3), bp_speFlae_query.value(4), bp_speFlae_query.value(5)])
        return speFlae
    # Massnahmen
    def abf_speFlae_mas(self, gid):
        bp_speFlaeMas_sql = 'SELECT * FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_SchutzPflegeEntwicklungsFlaeche_massnahme" as mas'\
            'JOIN "XP_Basisobjekte"."XP_SPEMassnahmenDaten" as spe'\
            'on (mas."massnahme"= spe."id")'\
            'WHERE mas."BP_SchutzPflegeEntwicklungsFlaeche_gid" =' + str(gid)
        bp_speFlaeMas_query = QtSql.QSqlQuery(self.db)
        bp_speFlaeMas_query.prepare(bp_speFlaeMas_sql)
        bp_speFlaeMas_query.exec_()
        speFlaewMas = []
        if bp_speFlaeMas_query.isActive():
            if bp_speFlaeMas_query.size() != 0:
                while bp_speFlaeMas_query.next():
                    speFlaewMas.append([bp_speFlaeMas_query.value(3), bp_speFlaeMas_query.value(4), bp_speFlaeMas_query.value(5)])
        return speFlaewMas

    # BP_AusgleichsMassnahme
    def abf_ausglFlMas(self, gid):
        bp_ausglFlMas_sql = 'SELECT * FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_AusgleichsMassnahme" WHERE "gid" = ' + str(gid)
        bp_ausglFlMas_query = QtSql.QSqlQuery(self.db)
        bp_ausglFlMas_query.prepare(bp_ausglFlMas_sql)
        bp_ausglFlMas_query.exec_()
        ausglFlMas = []
        if bp_ausglFlMas_query.isActive():
            if bp_ausglFlMas_query.size() != 0:
                while bp_ausglFlMas_query.next():
                    ausglFlMas.append([bp_ausglFlMas_query.value(1), bp_ausglFlMas_query.value(2),bp_ausglFlMas_query.value(3), 
                    bp_ausglFlMas_query.value(4)])     
        return ausglFlMas
    # Massnahmen
    def abf_ausglFlMas_mas(self, gid):
        bp_ausglFlMas_mas_sql = 'SELECT * FROM "BP_Naturschutz_Landschaftsbild_Naturhaushalt"."BP_AusgleichsMassnahme_massnahme" as mas'\
            'JOIN "XP_Basisobjekte"."XP_SPEMassnahmenDaten" as spe'\
            'on (mas."massnahme"= spe."id")'\
            'WHERE mas."BP_AusgleichsMassnahme_gid" =' + str(gid)
        bp_ausglFlMas_mas_query = QtSql.QSqlQuery(self.db)
        bp_ausglFlMas_mas_query.prepare(bp_ausglFlMas_mas_sql)
        bp_ausglFlMas_mas_query.exec_()
        ausglFlMas_mas = []
        if bp_ausglFlMas_mas_query.isActive():
            if bp_ausglFlMas_mas_query.size() != 0:
                while bp_ausglFlMas_mas_query.next():
                    ausglFlMas_mas.append([bp_ausglFlMas_mas_query.value(3),bp_ausglFlMas_mas_query.value(4), bp_ausglFlMas_mas_query.value(5)])
        return ausglFlMas_mas
    
    # Abfrage BP_EmissionskontingentLaerm
    def abf_laermKonti(self, id):
        bp_laermKonti_sql = 'SELECT * FROM "BP_Laerm"."BP_EmissionskontingentLaerm" WHERE "id" = ' + str(id)
        bp_laermKonti_query = QtSql.QSqlQuery(self.db)
        bp_laermKonti_query.prepare(bp_laermKonti_sql)
        bp_laermKonti_query.exec_()
        ekwertTag, ekwertNacht, erlaeuterung ="","",""
        if bp_laermKonti_query.isActive():
            if bp_laermKonti_query.size() != 0:
                while bp_laermKonti_query.next():
                    ekwertTag=bp_laermKonti_query.value(1)
                    ekwertNacht=bp_laermKonti_query.value(2)
                    erlaeuterung=bp_laermKonti_query.value(3)
        return [ekwertTag, ekwertNacht, erlaeuterung]

    # BP_EmissionskontingentLaermGebiet
    def abf_larmKonGebi(self, gid):
        bp_laermKonGeb_sql = 'SELECT * FROM "BP_Basisobjekte"."BP_Objekt_laermkontingentGebiet" as obj\
            JOIN "BP_Laerm"."BP_EmissionskontingentLaermGebiet" as emKoLaeGeb\
                ON(obj."laermkontingentGebiet"=emKoLaeGeb."id")\
                    WHERE "BP_Objekt_gid" = ' + str(gid)
        bp_laermKonGeb_query = QtSql.QSqlQuery(self.db)
        bp_laermKonGeb_query.prepare(bp_laermKonGeb_sql)
        bp_laermKonGeb_query.exec_()
        laermKonGeb = []
        if bp_laermKonGeb_query.isActive():
            if bp_laermKonGeb_query.size() != 0:
                while bp_laermKonGeb_query.next():
                    laermKonGeb.append(bp_laermKonGeb_query.value(1))
        return laermKonGeb

    # BP_ZusatzkontingentLaerm
    def abf_zusKonti(self, gid):
        bp_zusKonti_sql = 'SELECT ST_AsGeoJSON("position"),"bezeichnung" FROM "BP_Laerm"."BP_ZusatzkontingentLaerm" WHERE "gid" = ' + str(gid)
        bp_zusKonti_query = QtSql.QSqlQuery(self.db)
        bp_zusKonti_query.prepare(bp_zusKonti_sql)
        bp_zusKonti_query.exec_()
        zusKonti = []
        if bp_zusKonti_query.isActive():
            if bp_zusKonti_query.size() != 0:
                while bp_zusKonti_query.next():
                    zusKonti.append([bp_zusKonti_query.value(0), bp_zusKonti_query.value(1)])
        return zusKonti
    # BP_Richtungssektor
    def abf_richtSekt(self, gid):
        bp_zusKontiRich_sql = 'SELECT * FROM "BP_Laerm"."BP_ZusatzkontingentLaerm_richtungssektor" as obj\
            JOIN "BP_Laerm"."BP_Richtungssektor" as richSek\
                ON (obj."richtungssektor"=richSek."id")\
                    WHERE obj."BP_ZusatzkontingentLaerm_gid" = ' + str(gid)
        bp_zusKontiRich_query = QtSql.QSqlQuery(self.db)
        bp_zusKontiRich_query.prepare(bp_zusKontiRich_sql)
        bp_zusKontiRich_query.exec_()
        richSek = []
        if bp_zusKontiRich_query.isActive():
            if bp_zusKontiRich_query.size() != 0:
                while bp_zusKontiRich_query.next():
                    richSek.append([bp_zusKontiRich_query.value(3), bp_zusKontiRich_query.value(4), bp_zusKontiRich_query.value(5),bp_zusKontiRich_query.value(6)])
        return richSek
     
    # BP_ZusatzkontingentLaermFlaeche
    def abf_zusKontiFlae(self, gid):
        bp_zusKontiF_sql = 'SELECT ST_AsGeoJSON(zlf."position"),zlf."bezeichnung", zlf."richtungssektor", zlf."gid", zlf."flaechenschluss" FROM "BP_Basisobjekte"."BP_Objekt_zusatzkontingentFlaeche" as obj \
            JOIN "BP_Laerm"."BP_ZusatzkontingentLaermFlaeche" as zlf\
            on (obj."zusatzkontingentFlaeche" = zlf."gid") \
            WHERE obj."BP_Objekt_gid" = ' + str(gid)
        bp_zusKontiF_query = QtSql.QSqlQuery(self.db)
        bp_zusKontiF_query.prepare(bp_zusKontiF_sql)
        bp_zusKontiF_query.exec_()
        zusKontiF =[]
        if bp_zusKontiF_query.isActive():
            if bp_zusKontiF_query.size() != 0:
                while bp_zusKontiF_query.next():
                    zusKontiF.append([bp_zusKontiF_query.value(0), bp_zusKontiF_query.value(1), bp_zusKontiF_query.value(2), bp_zusKontiF_query.value(3), bp_zusKontiF_query.value(4)])
        return zusKontiF
    # BP_Richtungssektor --> BP_ZusatzkontingentLaermFlaeche
    def abf_richtSekt_zKF(self, gid):
        bp_zusKontiRich_sql = 'SELECT * FROM "BP_Laerm"."BP_Richtungssektor" WHERE "id" = ' + str(gid)
        bp_zusKontiRich_query = QtSql.QSqlQuery(self.db)
        bp_zusKontiRich_query.prepare(bp_zusKontiRich_sql)
        bp_zusKontiRich_query.exec_()
        richSek = []
        if bp_zusKontiRich_query.isActive():
            if bp_zusKontiRich_query.size() != 0:
                while bp_zusKontiRich_query.next():
                    richSek.append([bp_zusKontiRich_query.value(1), bp_zusKontiRich_query.value(2), bp_zusKontiRich_query.value(3),bp_zusKontiRich_query.value(4)])
        return richSek

    # BP_RichtungssektorGrenze
    def abf_richSekGre(self, gid):
        bp_richSekGre_sql = 'SELECT ST_AsGeoJSON(position), winkel FROM "BP_Laerm"."BP_RichtungssektorGrenze" WHERE "id" = ' + str(gid)
        bp_richSekGre_query = QtSql.QSqlQuery(self.db)
        bp_richSekGre_query.prepare(bp_richSekGre_sql)
        bp_richSekGre_query.exec_()
        richSekGre = []
        if bp_richSekGre_query.isActive():
            if bp_richSekGre_query.size() != 0:
                while bp_richSekGre_query.next():
                    richSekGre.append([bp_richSekGre_query.value(0), bp_richSekGre_query.value(1)])
        return richSekGre
    
    ###################
    # BP_BaugebietsTeilFlaeche
    def abf_bauGebTF(self, gid):
        bp_bgtf_sql = 'SELECT ST_AsGeoJSON("position"), *  FROM "BP_Bebauung"."BP_BaugebietsTeilFlaeche" WHERE gid = '+ str(gid)
        bp_bgtf_query  = QtSql.QSqlQuery(self.db)
        bp_bgtf_query.prepare(bp_bgtf_sql)
        bp_bgtf_query.exec_()
        bgtf = []
        if bp_bgtf_query.isActive():
            if bp_bgtf_query.size() != 0:
                while bp_bgtf_query.next():
                    bgtf.append([bp_bgtf_query.value(0), bp_bgtf_query.value(3), bp_bgtf_query.value(4), bp_bgtf_query.value(5), bp_bgtf_query.value(6), bp_bgtf_query.value(7), bp_bgtf_query.value(8), bp_bgtf_query.value(9)])
        return bgtf
    
    ######################
    # BP_Dachgestaltung
    def abf_dachGest(self, gid_Obj):
        bp_dachGest_sql= 'SELECT * FROM "BP_Bebauung"."BP_GestaltungBaugebiet_dachgestaltung" as gestBaug\
            JOIN "BP_Bebauung"."BP_Dachgestaltung" as dachGe\
                ON (gestBaug."dachgestaltung" = dachGe."id")\
                    WHERE gestBaug."BP_GestaltungBaugebiet_gid" = '+ str(gid_Obj)
        bp_dachGest_query = QtSql.QSqlQuery(self.db)
        bp_dachGest_query.prepare(bp_dachGest_sql)
        bp_dachGest_query.exec_()
        dachGest =[]
        if bp_dachGest_query.isActive():
            if bp_dachGest_query.size() != 0:
                while bp_dachGest_query.next():
                    dachGest.append([bp_dachGest_query.value(3), bp_dachGest_query.value(4), bp_dachGest_query.value(5), 
                    bp_dachGest_query.value(6), bp_dachGest_query.value(7), bp_dachGest_query.value(8)])
        return dachGest
    
    # BP_GestaltungBaugebiet
    def abf_gestBaugebiet(self, gid_Obj):
        bp_gestB_sql= 'SELECT * FROM "BP_Bebauung"."BP_GestaltungBaugebiet" WHERE gid = '+ str(gid_Obj)
        bp_gestB_query = QtSql.QSqlQuery(self.db)
        bp_gestB_query.prepare(bp_gestB_sql)
        bp_gestB_query.exec_()
        gestB =[]
        if bp_gestB_query.isActive():
            if bp_gestB_query.size() != 0:
                while bp_gestB_query.next():
                    gestB.append([bp_gestB_query.value(1), bp_gestB_query.value(2), bp_gestB_query.value(3), bp_gestB_query.value(4), bp_gestB_query.value(5)])
        return gestB


    # BP_Dachform
    def abf_dachForm(self, gid_Obj):
        bp_dachF_sql= 'SELECT "dachform" FROM "BP_Bebauung"."BP_GestaltungBaugebiet_dachform" WHERE "BP_GestaltungBaugebiet_gid" = '+ str(gid_Obj)
        bp_dachF_query = QtSql.QSqlQuery(self.db)
        bp_dachF_query.prepare(bp_dachF_sql)
        bp_dachF_query.exec_()
        dachform = "NULL"
        if bp_dachF_query.isActive():
            if bp_dachF_query.size() != 0:
                while bp_dachF_query.next():
                    dachform = bp_dachF_query.value(0)           
        return dachform

    def abf_detDachF(self, gid_Obj):
        bp_detDachF_sql= 'SELECT detDachF."Bezeichner" FROM "BP_Bebauung"."BP_GestaltungBaugebiet_detaillierteDachform" as gestBaug\
            JOIN "BP_Bebauung"."BP_DetailDachform" as detDachF\
                ON (gestBaug."detaillierteDachform" = detDachF."Code")\
                    WHERE gestBaug."BP_GestaltungBaugebiet_gid" = '+ str(gid_Obj)
        bp_detDachF_query = QtSql.QSqlQuery(self.db)
        bp_detDachF_query.prepare(bp_detDachF_sql)
        bp_detDachF_query.exec_()
        detDachF = "NULL"
        if bp_detDachF_query.isActive():
            if bp_detDachF_query.size() != 0:
                while bp_detDachF_query.next():
                    detDachF = bp_detDachF_query.value(0)           
        return detDachF
    
    # BP_FestsetzungenBaugebiet
    def abf_festBaug(self, gid):
        bp_bestBaug_sql = 'SELECT * FROM "BP_Bebauung"."BP_FestsetzungenBaugebiet" WHERE "gid" = '+str(gid)
        bp_bestBaug_query = QtSql.QSqlQuery(self.db)
        bp_bestBaug_query.prepare(bp_bestBaug_sql)
        bp_bestBaug_query.exec_()
        if bp_bestBaug_query.isActive():
            if bp_bestBaug_query.size() != 0:
                while bp_bestBaug_query.next():
                    MaxZahlWoh = bp_bestBaug_query.value(1)
                    Fmin = bp_bestBaug_query.value(2)
                    Fmax = bp_bestBaug_query.value(3)
                    Bmin = bp_bestBaug_query.value(4)
                    Bmax = bp_bestBaug_query.value(5)
                    Tmin = bp_bestBaug_query.value(6)
                    Tmax = bp_bestBaug_query.value(7)
                    GFZmin = bp_bestBaug_query.value(8)
                    GFZmax = bp_bestBaug_query.value(9)
                    gfz = bp_bestBaug_query.value(10)
                    GFZ_Ausn = bp_bestBaug_query.value(11)
                    GFmin = bp_bestBaug_query.value(12)
                    GFmax = bp_bestBaug_query.value(13)
                    gf = bp_bestBaug_query.value(14)
                    GF_Ausn = bp_bestBaug_query.value(15)
                    bmz = bp_bestBaug_query.value(16)
                    BMZ_Ausn = bp_bestBaug_query.value(17)
                    bm = bp_bestBaug_query.value(18)
                    BM_Ausn = bp_bestBaug_query.value(19)
                    GRZmin = bp_bestBaug_query.value(20)
                    GRZmax = bp_bestBaug_query.value(21)
                    grz = bp_bestBaug_query.value(22)
                    GRZ_Ausn = bp_bestBaug_query.value(23)
                    GRmin = bp_bestBaug_query.value(24)
                    GRmax = bp_bestBaug_query.value(25)
                    gr = bp_bestBaug_query.value(26)
                    GR_Ausn = bp_bestBaug_query.value(27)
                    Zmin = bp_bestBaug_query.value(28)
                    Zmax = bp_bestBaug_query.value(29)
                    Zzwingend = bp_bestBaug_query.value(30)
                    z = bp_bestBaug_query.value(31)
                    Z_Ausn = bp_bestBaug_query.value(32)
                    Z_Staffel = bp_bestBaug_query.value(33)
                    Z_Dach = bp_bestBaug_query.value(34)
                    ZUmin = bp_bestBaug_query.value(35)
                    ZUmax = bp_bestBaug_query.value(36)
                    ZUzwingend = bp_bestBaug_query.value(37)
                    zu = bp_bestBaug_query.value(38)
                    ZU_Ausn = bp_bestBaug_query.value(39)          
        return [MaxZahlWoh, Fmin, Fmax, Bmin, Bmax, Tmin, Tmax, GFZmin, GFZmax, gfz, GFZ_Ausn,GFmin, GFmax, gf, GF_Ausn, bmz,
        BMZ_Ausn, bm, BM_Ausn, GRZmin, GRZmax, grz, GRZ_Ausn, GRmin, GRmax, gr,GR_Ausn, Zmin, Zmax, Zzwingend, z, Z_Ausn, 
        Z_Staffel, Z_Dach, ZUmin, ZUmax, ZUzwingend, zu, ZU_Ausn]

    def abf_zusFest(self, gid):
        bp_zusFest_sql = 'SELECT * FROM "BP_Bebauung"."BP_ZusaetzlicheFestsetzungen" WHERE "gid" = '+str(gid)
        bp_zusFest_query = QtSql.QSqlQuery(self.db)
        bp_zusFest_query.prepare(bp_zusFest_sql)
        bp_zusFest_query.exec_()
        zusFest =[]
        if bp_zusFest_query.isActive():
            if bp_zusFest_query.size() != 0:
                while bp_zusFest_query.next():
                    zusFest.append([bp_zusFest_query.value(1), bp_zusFest_query.value(2), bp_zusFest_query.value(3),
                    bp_zusFest_query.value(4), bp_zusFest_query.value(5), bp_zusFest_query.value(6), bp_zusFest_query.value(7)])
        return zusFest

    # BP_BaugebietsTeilFlaeche_sondernutzung
    def abf_sondNutz(self, gid):
        bp_sondNutz_sql = 'SELECT * FROM "BP_Bebauung"."BP_BaugebietsTeilFlaeche_sondernutzung" WHERE "BP_BaugebietsTeilFlaeche_gid" = '+str(gid)
        bp_sondNutz_query = QtSql.QSqlQuery(self.db)
        bp_sondNutz_query.prepare(bp_sondNutz_sql)
        bp_sondNutz_query.exec_()
        sondernutzung = "NULL"
        if bp_sondNutz_query.isActive():
            if bp_sondNutz_query.size() != 0:
                while bp_sondNutz_query.next():
                    sondernutzung = bp_sondNutz_query.value(1)
        return sondernutzung           
    
    # BP_BaugebietBauweise
    def abf_baugBauw(self, gid):
        bp_baugBauw_sql = 'SELECT * FROM "BP_Bebauung"."BP_BaugebietBauweise" WHERE "gid" = '+str(gid)
        bp_baugBauw_query = QtSql.QSqlQuery(self.db)
        bp_baugBauw_query.prepare(bp_baugBauw_sql)
        bp_baugBauw_query.exec_()
        baugBauw=[]
        if bp_baugBauw_query.isActive():
            if bp_baugBauw_query.size() != 0:
                while bp_baugBauw_query.next():
                    baugBauw.append([bp_baugBauw_query.value(1), bp_baugBauw_query.value(2), bp_baugBauw_query.value(3),
                    bp_baugBauw_query.value(4), bp_baugBauw_query.value(5), bp_baugBauw_query.value(6), bp_baugBauw_query.value(7)])
        return baugBauw

    
    def abf_refGebQuerSch(self, gid):
        bp_refGebQuerSch_sql = 'SELECT * FROM "BP_Bebauung"."BP_BaugebietBauweise_refGebauedequerschnitt" WHERE "BP_BaugebietBauweise_gid" = '+str(gid)
        bp_refGebQuerSch_quer = QtSql.QSqlQuery(self.db)
        bp_refGebQuerSch_quer.prepare(bp_refGebQuerSch_sql)
        bp_refGebQuerSch_quer.exec_()
        extRef = []
        if bp_refGebQuerSch_quer.isActive():
            if bp_refGebQuerSch_quer.size() != 0:
                while bp_refGebQuerSch_quer.next():
                    extRef.append(self.abf_externRef(bp_refGebQuerSch_quer.value(1)))
        return extRef

    ### BP_StrassenVerkehrsFlaeche
    # GID 
    def abf_strVerkFlae_ID(self, berID):
        bp_strVerk_sql = 'SELECT verk."gid" FROM "XP_Basisobjekte"."XP_Objekt_gehoertZuBereich" as obj\
            JOIN "BP_Verkehr"."BP_StrassenVerkehrsFlaeche" as verk\
                ON(obj."XP_Objekt_gid" = verk."gid")\
                    WHERE obj."gehoertZuBereich" = '+ str (berID)
        bp_strVerk_query = QtSql.QSqlQuery(self.db)
        bp_strVerk_query.prepare(bp_strVerk_sql)
        bp_strVerk_query.exec_()
        gid_Ver=[]
        if bp_strVerk_query.isActive():
            if bp_strVerk_query.size() != 0:
                while bp_strVerk_query.next():
                    gid_Ver.append(bp_strVerk_query.value(0))
        return gid_Ver
    
    # BP_StrassenVerkehrsFlaeche
    def abf_strVerkF(self, gid):
        bp_strVerkF_sql = 'SELECT ST_AsGeoJSON("position"), flaechenschluss, nutzungsform FROM "BP_Verkehr"."BP_StrassenVerkehrsFlaeche" WHERE gid = '+ str(gid)
        bp_strVerkF_query  = QtSql.QSqlQuery(self.db)
        bp_strVerkF_query.prepare(bp_strVerkF_sql)
        bp_strVerkF_query.exec_()
        strVerkF = []
        if bp_strVerkF_query.isActive():
            if bp_strVerkF_query.size() != 0:
                while bp_strVerkF_query.next():
                    strVerkF.append([bp_strVerkF_query.value(0), bp_strVerkF_query.value(1), bp_strVerkF_query.value(2)])
        return strVerkF

    #BP_StrassenbegrenzungsLinie
    def abf_strbegrLin(self, gid):
        bp_strVerkL_sql = 'SELECT ST_AsGML("position"), bautiefe FROM "BP_Verkehr"."BP_StrassenVerkehrsFlaeche_begrenzungsLinie" as obj\
            JOIN "BP_Verkehr"."BP_StrassenbegrenzungsLinie" as strBegLin\
                ON(obj."begrenzungsLinie"= strBegLin."gid")\
                    WHERE obj."BP_StrassenVerkehrsFlaeche_gid" = '+ str(gid)
        bp_strVerkL_query  = QtSql.QSqlQuery(self.db)
        bp_strVerkL_query.prepare(bp_strVerkL_sql)
        bp_strVerkL_query.exec_()
        strVerkF = []
        if bp_strVerkL_query.isActive():
            if bp_strVerkL_query.size() != 0:
                while bp_strVerkL_query.next():
                    strVerkF.append([bp_strVerkL_query.value(0), bp_strVerkL_query.value(1)])
        return strVerkF

    # Abfrage XP_AbstraktesPraesentationsobjekt
    def abf_abstPrOb(self, ber_id):
        bp_abstPrOb_sql = 'SELECT * FROM "XP_Praesentationsobjekte"."XP_AbstraktesPraesentationsobjekt" WHERE "gehoertZuBereich" = '+ str(ber_id)
        bp_abstPrOb_query  = QtSql.QSqlQuery(self.db)
        bp_abstPrOb_query.prepare(bp_abstPrOb_sql)
        bp_abstPrOb_query.exec_()
        abstPrOb = []
        if bp_abstPrOb_query.isActive():
            if bp_abstPrOb_query.size() != 0:
                while bp_abstPrOb_query.next():
                    abstPrOb.append([bp_abstPrOb_query.value(0), bp_abstPrOb_query.value(1), bp_abstPrOb_query.value(2), bp_abstPrOb_query.value(3), bp_abstPrOb_query.value(4)])
        return abstPrOb
    
    # XP_Praesentationsobjekte Darstellung
    def abf_apoDarst(self, gid):
        bp_apoDarst_sql = 'SELECT * FROM "XP_Praesentationsobjekte"."XP_APObjekt_dientZurDarstellungVon" WHERE "XP_APObjekt_gid" = '+ str(gid)
        bp_apoDarst_query  = QtSql.QSqlQuery(self.db)
        bp_apoDarst_query.prepare(bp_apoDarst_sql)
        bp_apoDarst_query.exec_()
        apoDarst = []
        if bp_apoDarst_query.isActive():
            if bp_apoDarst_query.size() != 0:
                while bp_apoDarst_query.next():
                    apoDarst.append([ bp_apoDarst_query.value(1), bp_apoDarst_query.value(2), bp_apoDarst_query.value(3)])
        return apoDarst
    
    # XP_Praesentationsobjekte GML:ID XP_Bereich
    def abf_gmlIDBereich_APO(self, gid):
        bp_gmlIDBer_sql = 'SELECT gml_id FROM "XP_Basisobjekte"."XP_Bereich" WHERE gid = '+ str(gid)
        bp_gmlIDBer_query  = QtSql.QSqlQuery(self.db)
        bp_gmlIDBer_query.prepare(bp_gmlIDBer_sql)
        bp_gmlIDBer_query.exec_()
        gmlIDBer = ""
        if bp_gmlIDBer_query.isActive():
            if bp_gmlIDBer_query.size() != 0:
                while bp_gmlIDBer_query.next():
                    gmlIDBer = bp_gmlIDBer_query.value(0)
        return gmlIDBer

    # XP_Praesentationsobjekte dientZurDarstellungVon
    def abf_ref_XPobj(self, gid):
        bp_ref_XPobj_sql = 'SELECT gml_id FROM "XP_Basisobjekte"."XP_Objekt" WHERE gid = '+ str(gid)
        bp_ref_XPobj_query  = QtSql.QSqlQuery(self.db)
        bp_ref_XPobj_query.prepare(bp_ref_XPobj_sql)
        bp_ref_XPobj_query.exec_()
        ref_XPobj = ""
        if bp_ref_XPobj_query.isActive():
            if bp_ref_XPobj_query.size() != 0:
                while bp_ref_XPobj_query.next():
                    ref_XPobj = bp_ref_XPobj_query.value(0)
        return ref_XPobj

    ### Abschnitt zum Schreiben der GML ###

    # Kleinstes Recht (boundedBy) um Objket
    def exp_boundBy(self, tab, koor_loCorner, koor_upCorner):
        boundBy = tab * str("\t") + "<gml:boundedBy>\n"
        boundBy += (tab+1) * str("\t") +'<gml:Envelope srsName="'+self.epsg+'">\n'
        boundBy += (tab+2) * str("\t") + "<gml:lowerCorner>"+koor_loCorner+"</gml:lowerCorner>\n"
        boundBy += (tab+2) * str("\t") + "<gml:upperCorner>"+koor_upCorner+"</gml:upperCorner>\n"
        boundBy += (tab+1) * str("\t") + "</gml:Envelope>\n" 
        boundBy += tab * str("\t") + "</gml:boundedBy>\n"
        return boundBy

    # XP_Plan
    def exp_XP_plan_gml(self, xp_plan, aendListe, wGeaeVon, rGeltungB, verfMerk, tex, begAbschnitt, extRef, spezExRef):
        xp_plan_gml = ""
        xp_plan_gml += '\t\t\t<xplan:name>'+ self.params["plangebiet"] +'</xplan:name>\n'
        if str(xp_plan[0]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:nummer>'+xp_plan[0]+'</xplan:nummer>\n'
        if str(xp_plan[1]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:internalId>'+ xp_plan[1] +'</xplan:internalId>\n'
        if str(xp_plan[2]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:beschreibung>'+ xp_plan[2] +'</xplan:beschreibung>\n'
        if str(xp_plan[3]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:kommentar>'+ xp_plan[3] +'</xplan:kommentar>\n'
        if str(xp_plan[4]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:technHerstellDatum>'+ xp_plan[4].toString(Qt.ISODate) +'</xplan:technHerstellDatum>\n'
        if str(xp_plan[5]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:genehmigungsDatum>'+ xp_plan[5].toString(Qt.ISODate) +'</xplan:genehmigungsDatum>\n'
        if str(xp_plan[6]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:untergangsDatum>'+ xp_plan[6].toString(Qt.ISODate) +'</xplan:untergangsDatum>\n'
        # Abfrage aendert für XP_Plan
        tab = 4
        if len(aendListe) > 0 :
            for aList in aendListe:
                xp_plan_gml += '\t\t\t<xplan:aendert>\n'
                xp_plan_gml += self.exp_verbundenerPlan(tab, aList)
                xp_plan_gml +='\t\t\t</xplan:aendert>\n'
        # Abfrage wurdeGeaendertVon für XP_Plan
        if len(wGeaeVon) > 0 :
            for wgvList in wGeaeVon:
                xp_plan_gml += '\t\t\t<xplan:wurdeGeaendertVon>\n'
                xp_plan_gml += self.exp_verbundenerPlan(tab, wgvList)
                xp_plan_gml +='\t\t\t</xplan:wurdeGeaendertVon>\n'

        if str(xp_plan[7]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:erstellungsMassstab>'+ str(xp_plan[7]) +'</xplan:erstellungsMassstab>\n'
        if str(xp_plan[8]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:bezugshoehe uom="m">'+ str(xp_plan[8]) +'</xplan:bezugshoehe>\n'
        if str(xp_plan[9]) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:technischerPlanersteller>'+ str(xp_plan[9]) +'</xplan:technischerPlanersteller>\n'
        
        # Abfrage räumlicher Gestaltungsbereich
        if str(rGeltungB) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:raeumlicherGeltungsbereich>\n'
            xp_plan_gml += self.exp_gmlGeometrie(tab, rGeltungB)
            xp_plan_gml += '\t\t\t</xplan:raeumlicherGeltungsbereich>\n' 
        
        # verfahrensMerkmale
        if len(verfMerk)>0:
            for vM in verfMerk:
                xp_plan_gml += '\t\t\t<xplan:verfahrensMerkmale>\n'
                xp_plan_gml += self.exp_verfahrenMerkmal(tab, vM)
                xp_plan_gml += '\t\t\t</xplan:verfahrensMerkmale>\n'

        # hatGenerAttribut
        
        # XP_SpezExterneReferenz
        self.debug("Z. 1341: " + str(spezExRef))
        if str(spezExRef) != "NULL":
            xp_plan_gml += '\t\t\t<xplan:externeReferenz>\n'
            xp_plan_gml += self.exp_spezExtRef(tab, extRef, spezExRef)
            xp_plan_gml += '\t\t\t</xplan:externeReferenz>\n'

        # texte
        if len(tex)>0:
            for t in tex:
                xp_plan_gml += '\t\t\t<xplan:texte>\n'
                xp_plan_gml += self.exp_Xp_texAB(tab, t)
                xp_plan_gml += '\t\t\t</xplan:texte>\n'

        # XP_Plan begruendungsTexte
        if len(begAbschnitt)>0:
            for bAb in begAbschnitt:
                xp_plan_gml += '\t\t\t<xplan:begruendungsTexte>\n'
                xp_plan_gml += self.exp_begAbschnitt(tab, bAb)
                xp_plan_gml += '\t\t\t</xplan:begruendungsTexte>\n'

        return xp_plan_gml
    
    # XP_SpezExterneReferenz
    def exp_spezExtRef(self, tab, extR, spER):
        self.debug('Z. 1355: ' + str(spER))
        spezER = tab * str("\t") +'<xplan:XP_SpezExterneReferenz>\n'
        if len(extR) > 0:
            for e in extR:
                spezER += self.exp_extRef(tab+1, e)
        spezER += (tab+1) * str("\t") + '<xplan:typ>'+ str(spER) + '</xplan:typ>\n'
        spezER += tab * str("\t") +'</xplan:XP_SpezExterneReferenz>\n'

        return spezER

    # GML-Auszug zu XPlan Gebiet
    def exp_plangebietGML(self, koor_loCorner, koor_upCorner):
        # Abfragen für die Attribute der Datenbank 
        # Abfrage XP_Plan
        xp_plan = self.abf_xpPlan()
        aendListe = self.abf_aendertPlan()
        wGeaeVon = self.abf_wgvPlan()
        rGeltungB = self.abf_raeumlGeltPlan()
        verfMerk = self.abf_verfMerkPlan()
        tex = self.abf_XP_texAb(self.gid)
        begAbschnitt = self.abf_begAbsch()
        spezExRef = self.abf_spezExRef(self.gid)
        if spezExRef[0] != "NULL":
            extRef = self.abf_externRef(spezExRef[0])

        # Abfrage BP_Plan
        bp_Plan = self.abf_bpPlan()
        gemeinde = self.abf_gemeinde()
        planaufGem = self.abf_planaufGemeinde()
        planArt = self.abf_planArt()
        self.abf_bereichGMLID() # Hier werden globale Variablen definiert

        # Anfang-Tag BP_Plan
        self.gmlID_plan = xp_plan[11]
        planGebiet = '\t<gml:featureMember>\n'
        planGebiet += '\t\t<xplan:BP_Plan gml:id="GML_'+ self.gmlID_plan +'">\n'
        tab = 3
        planGebiet += self.exp_boundBy(tab, koor_loCorner, koor_upCorner) 

        # XP_Plan
        planGebiet += self.exp_XP_plan_gml(xp_plan, aendListe, wGeaeVon, rGeltungB, verfMerk, tex, begAbschnitt, extRef, spezExRef[1])
        
        # BP_Plan
        # BP_Gemeinde
        tab = 4
        if len(gemeinde)>0:
            for gem in gemeinde:
                planGebiet += '\t\t\t<xplan:gemeinde>\n'
                planGebiet += self.exp_XPgemeinde_gml(tab, gem)
                planGebiet += '\t\t\t</xplan:gemeinde>\n'
        # BP_planaufstellendeGemeinde
        if len(planaufGem)>0:
            for plangem in planaufGem:
                planGebiet += '\t\t\t<xplan:planaufstellendeGemeinde>\n'
                planGebiet += self.exp_XPgemeinde_gml(tab, plangem)
                planGebiet += '\t\t\t</xplan:planaufstellendeGemeinde>\n'
        # Plangeber
        if str(bp_Plan[0])!="NULL":
            plaGeb = self.abf_plangeber(bp_Plan[0])
            planGebiet += '\t\t\t<xplan:plangeber>\n'
            planGebiet += self.exp_XPplangeber_gml(tab, plaGeb)
            planGebiet += '\t\t\t</xplan:plangeber>\n'
        ##############################################################################################################################################
        # Planart ####################################################################################################################################
        # 
        if len(planArt)>0:
            for pA in planArt:
                planGebiet += '\t\t\t<xplan:planArt>'+ str(pA) +'</xplan:planArt>\n'
        #############################################################################################################################################
        # sonstPlanArt
        if str(bp_Plan[1])!="NULL":
            soPlanArt = self.abf_sonstPlanArt(bp_Plan[1])
            planGebiet += '\t\t\t<xplan:sonstPlanArt>'+ soPlanArt +'</xplan:sonstPlanArt>\n'
        # verfahren
        if str(bp_Plan[2])!="NULL":
            planGebiet += '\t\t\t<xplan:verfahren>'+ str(bp_Plan[2]) +'</xplan:verfahren>\n'
        # rechtsstand
        if str(bp_Plan[3])!="NULL":
            planGebiet += '\t\t\t<xplan:rechtsstand>'+ str(bp_Plan[3]) +'</xplan:rechtsstand>\n'
        # status
        if str(bp_Plan[4])!="NULL":
            planGebiet += '\t\t\t<xplan:status>'+ bp_Plan[4] +'</xplan:status>\n'
        # hoehenbezug
        if str(bp_Plan[5])!="NULL":
            planGebiet += '\t\t\t<xplan:hoehenbezug>'+ bp_Plan[5] +'</xplan:hoehenbezug>\n'
        # aenderungenBisDatum
        if str(bp_Plan[6])!="NULL":
            planGebiet += '\t\t\t<xplan:aenderungenBisDatum>'+ bp_Plan[6].toString(Qt.ISODate) +'</xplan:aenderungenBisDatum>\n'
        # aufstellungsbeschlussDatum
        if str(bp_Plan[7])!="NULL":
            planGebiet += '\t\t\t<xplan:aufstellungsbeschlussDatum>'+ bp_Plan[7].toString(Qt.ISODate) +'</xplan:aufstellungsbeschlussDatum>\n'
        # veraenderungssperreDatum
        if str(bp_Plan[8])!="NULL":
            planGebiet += '\t\t\t<xplan:veraenderungssperreDatum>'+ bp_Plan[8].toString(Qt.ISODate) +'</xplan:veraenderungssperreDatum>\n'
        
        # auslegungsStartDatum
        if str(bp_Plan[9])!="NULL" and str(bp_Plan[9])!="{"+"}":
            eingabe = bp_Plan[9].replace("{","[")
            eingabe = eingabe.replace("}","]")
            planGebiet += '\t\t\t<xplan:auslegungsStartDatum>'+ eingabe +'</xplan:auslegungsStartDatum>\n'
        # auslegungsEndDatum
        if str(bp_Plan[10])!="NULL" and str(bp_Plan[10])!="{"+"}":
            eingabe = bp_Plan[10].replace("{","[")
            eingabe = eingabe.replace("}","]")
            planGebiet += '\t\t\t<xplan:auslegungsEndDatum>'+ eingabe +'</xplan:auslegungsEndDatum>\n'
        # traegerbeteiligungsStartDatum
        if str(bp_Plan[11])!="NULL" and str(bp_Plan[11])!="{"+"}":
            eingabe = bp_Plan[11].replace("{","[")
            eingabe = eingabe.replace("}","]")
            planGebiet += '\t\t\t<xplan:traegerbeteiligungsStartDatum>'+ eingabe +'</xplan:traegerbeteiligungsStartDatum>\n'
        # traegerbeteiligungsEndDatum
        if str(bp_Plan[12])!="NULL" and str(bp_Plan[12])!="{"+"}":
            eingabe = bp_Plan[12].replace("{","[")
            eingabe = eingabe.replace("}","]")
            planGebiet += '\t\t\t<xplan:traegerbeteiligungsEndDatum>'+ eingabe +'</xplan:traegerbeteiligungsEndDatum>\n'
        
        # satzungsbeschlussDatum
        if str(bp_Plan[13])!="NULL":
            planGebiet += '\t\t\t<xplan:satzungsbeschlussDatum>'+ bp_Plan[13].toString(Qt.ISODate) +'</xplan:satzungsbeschlussDatum>\n'
        # rechtsverordnungsDatum
        if str(bp_Plan[14])!="NULL":
            planGebiet += '\t\t\t<xplan:rechtsverordnungsDatum>'+ bp_Plan[14].toString(Qt.ISODate) +'</xplan:rechtsverordnungsDatum>\n'
        # inkrafttretensDatum
        if str(bp_Plan[15])!="NULL":
            planGebiet += '\t\t\t<xplan:inkrafttretensDatum>'+ bp_Plan[15].toString(Qt.ISODate) +'</xplan:inkrafttretensDatum>\n'
        # ausfertigungsDatum
        if str(bp_Plan[16])!="NULL":
            planGebiet += '\t\t\t<xplan:ausfertigungsDatum>'+ bp_Plan[16].toString(Qt.ISODate) +'</xplan:ausfertigungsDatum>\n'
        # veraenderungssperre
        if str(bp_Plan[17])!="NULL":
            planGebiet += '\t\t\t<xplan:veraenderungssperre>'+ str(bp_Plan[17]) +'</xplan:veraenderungssperre>\n'
        # staedtebaulicherVertrag
        if str(bp_Plan[18])!="NULL":
            planGebiet += '\t\t\t<xplan:staedtebaulicherVertrag>'+ str(bp_Plan[18]) +'</xplan:staedtebaulicherVertrag>\n'
        # erschliessungsVertrag
        if str(bp_Plan[19])!="NULL":
            planGebiet += '\t\t\t<xplan:erschliessungsVertrag>'+ str(bp_Plan[19]) +'</xplan:erschliessungsVertrag>\n'
        # durchfuehrungsVertrag
        if str(bp_Plan[20])!="NULL":
            planGebiet += '\t\t\t<xplan:durchfuehrungsVertrag>'+ str(bp_Plan[20]) +'</xplan:durchfuehrungsVertrag>\n'
        # gruenordnungsplan
        if str(bp_Plan[21])!="NULL":
            planGebiet += '\t\t\t<xplan:gruenordnungsplan>'+ str(bp_Plan[21]) +'</xplan:gruenordnungsplan>\n'
        # versionBauNVODatum
        if str(bp_Plan[22])!="NULL":
            planGebiet += '\t\t\t<xplan:versionBauNVODatum>'+ bp_Plan[22].toString(Qt.ISODate) +'</xplan:versionBauNVODatum>\n'
        # versionBauNVOText
        if str(bp_Plan[23])!="NULL":
            planGebiet += '\t\t\t<xplan:versionBauNVOText>'+ bp_Plan[23] +'</xplan:versionBauNVOText>\n'
        # versionBauGBDatum
        if str(bp_Plan[24])!="NULL":
            planGebiet += '\t\t\t<xplan:versionBauGBDatum>'+ bp_Plan[24].toString(Qt.ISODate) +'</xplan:versionBauGBDatum>\n'
        # versionBauGBText
        if str(bp_Plan[25])!="NULL":
            planGebiet += '\t\t\t<xplan:versionBauGBText>'+ bp_Plan[25] +'</xplan:versionBauGBText>\n'
        # versionSonstRechtsgrundlageDatum
        if str(bp_Plan[26])!="NULL":
            planGebiet += '\t\t\t<xplan:versionSonstRechtsgrundlageDatum>'+ bp_Plan[26].toString(Qt.ISODate) +'</xplan:versionSonstRechtsgrundlageDatum>\n'
        # versionBauGBText
        if str(bp_Plan[27])!="NULL":
            planGebiet += '\t\t\t<xplan:versionSonstRechtsgrundlageText>'+ bp_Plan[27] +'</xplan:versionSonstRechtsgrundlageText>\n'

        # Bereich über gehoertZuPlan
        if len(self.gmlID_bereiche)>0:
            for bGMLID in self.gmlID_bereiche:
                planGebiet += '\t\t\t<xplan:bereich xlink:href="#GML_'+ bGMLID +'" />\n'

        # Ende des Plangebiets
        planGebiet += '\t\t</xplan:BP_Plan>\n'
        planGebiet += '\t</gml:featureMember>\n'
        return planGebiet

    # Klasse XP_VerbundenerPlan
    def exp_verbundenerPlan(self, tab, aList):
        verbPlan = tab * str("\t") +"<xplan:XP_VerbundenerPlan>\n"
        if str(aList[0]) != "NULL": 
            verbPlan += (tab+1) * str("\t") +"<xplan:planName>" + str(aList[0]) + "</xplan:planName>\n"
        if str(aList[1]) != "NULL": 
            verbPlan += (tab+1) * str("\t") +"<xplan:rechtscharakter>" + str(aList[1]) + "</xplan:rechtscharakter>\n"
        if str(aList[2]) != "NULL": 
            verbPlan += (tab+1) * str("\t") +"<xplan:nummer>" + str(aList[2]) + "</xplan:nummer>\n"
        if str(aList[3]) != "NULL": 
            verbPlan += (tab+1) * str("\t") +"<xplan:verbundenerPlan>" + str(aList[3]) + "</xplan:verbundenerPlan>\n"
        verbPlan += tab * str("\t") +"</xplan:XP_VerbundenerPlan>\n"
        return verbPlan

    # Klasse XP_VerfahrensMerkmal
    def exp_verfahrenMerkmal(self, tab, verMerk):
        verM = tab * str("\t") +"<xplan:XP_VerfahrensMerkmal>\n"
        if str(verMerk[0]) != "NULL": 
            verM += (tab+1) * str("\t") +"<xplan:vermerk>" + str(verMerk[0]) + "</xplan:vermerk>\n"
        if str(verMerk[1]) != "NULL": 
            verM += (tab+1) * str("\t") +"<xplan:datum>" + verMerk[1].toString(Qt.ISODate) + "</xplan:datum>\n"
        if str(verMerk[2]) != "NULL": 
            verM += (tab+1) * str("\t") +"<xplan:signatur>" + str(verMerk[2]) + "</xplan:signatur>\n"
        if str(verMerk[3]) != "NULL": 
            verM += (tab+1) * str("\t") +"<xplan:signiert>" + str(verMerk[3]) + "</xplan:signiert>\n"
        verM += tab * str("\t") +"</xplan:XP_VerfahrensMerkmal>\n"
        return verM

    # Klasse XP_TextAbschnitt
    def exp_Xp_texAB(self, tab, anf_tex):
        texte = tab * str("\t") +"<xplan:XP_TextAbschnitt>\n"
        if str(anf_tex[0]) !="NULL":
            texte+= (tab+1) * str("\t") +"<xplan:schluessel>"+ anf_tex[0] +"</xplan:schluessel>\n"
        if str(anf_tex[1]) !="NULL":
            texte+= (tab+1) * str("\t") +"<xplan:gesetzlicheGrundlage>"+ anf_tex[1] +"</xplan:gesetzlicheGrundlage>\n"
        if str(anf_tex[2]) !="NULL":
            texte+= (tab+1) * str("\t") +"<xplan:text>"+ anf_tex[2] +"</xplan:text>\n"
        if str(anf_tex[3]) !="NULL":
            eRef = self.abf_externRef(anf_tex[3])
            if len(eRef)>0:
                for e in eRef:
                    texte+= (tab+1) * str("\t") +"<xplan:refText>\n"
                    texte += self.exp_extRef(tab+2, e)
                    texte+= (tab+1) * str("\t") +"</xplan:refText>\n"
        texte += tab * str("\t") +"</xplan:XP_TextAbschnitt>\n"
        return texte

    # Klasse XP_ExterneReferenz
    def exp_extRef(self, tab, extRef):
        exRef = tab * str("\t") +"<xplan:XP_ExterneReferenz>\n"
        if str(extRef[0]) != "NULL":
            exRef +=(tab+1) * str("\t") + "<xplan:georefURL>"+ extRef[0]+ "</xplan:georefURL>\n"
        if str(extRef[1]) != "NULL":
            exRef +=(tab+1) * str("\t") + "<xplan:georefMimeType>"+ extRef[1]+ "</xplan:georefMimeType>\n"
        if str(extRef[2]) != "NULL":
            exRef +=(tab+1) * str("\t") + "<xplan:art>"+ extRef[2]+ "</xplan:art>\n"
        if str(extRef[3]) != "NULL":
            exRef +=(tab+1) * str("\t") + "<xplan:informationssystemURL>"+ extRef[3]+ "</xplan:informationssystemURL>\n"
        if str(extRef[4]) != "NULL":
            exRef +=(tab+1) * str("\t") + "<xplan:referenzName>"+ extRef[4]+ "</xplan:referenzName>\n"
        if str(extRef[5]) != "NULL":
            exRef +=(tab+1) * str("\t") + "<xplan:referenzURL>"+ extRef[5]+ "</xplan:referenzURL>\n"
        if str(extRef[6]) != "NULL":
            exRef +=(tab+1) * str("\t") + "<xplan:referenzMimeType>"+ extRef[6]+ "</xplan:referenzMimeType>\n"
        if str(extRef[7]) != "NULL":
            exRef +=(tab+1) * str("\t") + "<xplan:beschreibung>"+ extRef[7]+ "</xplan:beschreibung>\n"
        if str(extRef[8]) != "NULL":
            exRef +=(tab+1) * str("\t") + "<xplan:datum>"+ extRef[8].toString(Qt.ISODate)+ "</xplan:datum>\n"
        exRef += tab * str("\t") +"</xplan:XP_ExterneReferenz>\n"
        return exRef

    # Klasse XP_BegruendungAbschnitt
    def exp_begAbschnitt(self, tab, begAbschnitt):
        begAbsch = tab * str("\t") +"<xplan:XP_BegruendungAbschnitt>\n"
        if str(begAbschnitt[0]) !="NULL":
            begAbsch+= (tab+1) * str("\t") +"<xplan:schluessel>"+ begAbschnitt[0] +"</xplan:schluessel>\n"
        if str(begAbschnitt[1]) !="NULL":
            begAbsch+= (tab+1) * str("\t") +"<xplan:text>"+ begAbschnitt[1] +"</xplan:text>\n"
        if str(begAbschnitt[2]) !="NULL":
            eRef = self.abf_externRef(begAbschnitt[2])
            if len(eRef)>0:
                for e in eRef:
                    begAbsch+= (tab+1) * str("\t") +"<xplan:refText>\n"
                    begAbsch += self.exp_extRef(tab+2, e)
                    begAbsch+= (tab+1) * str("\t") +"</xplan:refText>\n"
        begAbsch += tab * str("\t") +"</xplan:XP_BegruendungAbschnitt>\n"
        return begAbsch

    # Klasse XP_Gemeinde
    def exp_XPgemeinde_gml(self, tab, abf_gem):
        gem = tab * str("\t") +"<xplan:XP_Gemeinde>\n"
        if str(abf_gem[0])!="NULL":
            gem += (tab+1) * str("\t") +"<xplan:ags>"+ str(abf_gem[0]) +"</xplan:ags>\n"
        if str(abf_gem[1])!="NULL":
            gem += (tab+1) * str("\t") +"<xplan:rs>"+ str(abf_gem[1]) +"</xplan:rs>\n"
        if str(abf_gem[2])!="NULL":
            gem += (tab+1) * str("\t") +"<xplan:gemeindeName>"+ abf_gem[2] +"</xplan:gemeindeName>\n"
        if str(abf_gem[3])!="NULL":
            gem += (tab+1) * str("\t") +"<xplan:ortsteilName>"+ abf_gem[3] +"</xplan:ortsteilName>\n"
        gem += tab * str("\t") +"</xplan:XP_Gemeinde>\n"
        return gem

    # Klasse XP_Plangeber
    def exp_XPplangeber_gml(self, tab, plaGeber):
        planGeb = tab * str("\t") +"<xplan:XP_Plangeber>\n"
        if str(plaGeber[0]) != "NULL":
            planGeb += (tab+1) * str("\t") +"<xplan:name>"+ plaGeber[0] +"</xplan:name>\n"
        if str(plaGeber[1]) != "NULL":
            planGeb += (tab+1) * str("\t") +"<xplan:kennziffer>"+ str(plaGeber[1]) +"</xplan:kennziffer>\n"
        planGeb += tab * str("\t") +"</xplan:XP_Plangeber>\n"
        return planGeb

    # XP_Bereich
    def exp_xp_Bereich_gml(self, tab, xp_bereich, geltungsbereich, refScan, bereich_obj, bereich_prObj):
        xp_ber = ""
        if str(xp_bereich[0]) != "NULL":
            xp_ber += '\t\t\t<xplan:nummer>'+ str(xp_bereich[0]) +'</xplan:nummer>\n'
        if str(xp_bereich[1]) != "NULL":
            xp_ber += '\t\t\t<xplan:name>'+ str(xp_bereich[1]) +'</xplan:name>\n'
        if str(xp_bereich[2]) != "NULL":
            xp_ber += '\t\t\t<xplan:bedeutung>'+ str(xp_bereich[2]) +'</xplan:bedeutung>\n'
        if str(xp_bereich[3]) != "NULL":
            xp_ber += '\t\t\t<xplan:detaillierteBedeutung>'+ str(xp_bereich[3]) +'</xplan:detaillierteBedeutung>\n'
        if str(xp_bereich[4]) != "NULL":
            xp_ber += '\t\t\t<xplan:erstellungsMassstab>'+ str(xp_bereich[4]) +'</xplan:erstellungsMassstab>\n'
        # Geltungsbereich
    
        if str(geltungsbereich) != "NULL":
            xp_ber += '\t\t\t<xplan:geltungsbereich>\n'
            xp_ber += self.exp_gmlGeometrie(tab, geltungsbereich)
            xp_ber +='\t\t\t</xplan:geltungsbereich>\n'
        
        # refScan
        if len(refScan) > 0:
            for rS in refScan:
                xp_ber += '\t\t\t<xplan:refScan>\n'
                xp_ber += self.exp_extRef(tab, rS)
                xp_ber +='\t\t\t</xplan:refScan>\n'

        #  XP_rasterBasis
       
        
        # Planinhalte über XP_Objekt gehoertZuObjekt
        if len(bereich_obj)>0:
            for objGMLID in bereich_obj:
                xp_ber += '\t\t\t<xplan:planinhalt xlink:href="#GML_'+ objGMLID +'" />\n'
        
        # Präsentationsobjekte über XP_AbstraktesPraesentationsobjekt
        if len(bereich_prObj) > 0:
            for prOb in bereich_prObj:
                xp_ber += '\t\t\t<xplan:praesentationsobjekt xlink:href="#GML_'+ prOb +'" />\n'
        return xp_ber
    
    ### GML-Auszug für BP_Bereich
    def exp_bereichgebietGML(self, berGid, i):
        # Abfragen an die DB
        upKo, lowKo=self.abf_bereichBBy(berGid)
        
        xp_bereich = self.abf_xpBereich(berGid)
        geltungsbereich = self.abf_geltBereich(berGid)
        refScan = self.abf_refScanBer(berGid)
        bereich_obj = self.abf_ObjektGMLID(berGid)
        bereich_prObj = self.abf_prObjektGMLID(berGid)
        # Abfrage der Attribute BP_Bereich
        bp_bereich = self.abf_bpBereich(berGid)

        # Öffnen
        bereich = '\t<gml:featureMember>\n'
        bereich += '\t\t<xplan:BP_Bereich gml:id="GML_'+ self.gmlID_bereiche[i] +'">\n'
        # BoundBy Bereich
        tab = 3
        bereich += self.exp_boundBy(tab, upKo, lowKo)

        ### XP_Bereich ###
        # Abfrage der Attribute XP_Bereich
        tab = 4
        bereich += self.exp_xp_Bereich_gml(tab, xp_bereich, geltungsbereich, refScan, bereich_obj, bereich_prObj)

         ### BP_Bereich ###
        if str(bp_bereich[0]) != "NULL":
            bereich += '\t\t\t<xplan:versionBauNVODatum>'+ bp_bereich[0].toString(Qt.ISODate) +'</xplan:versionBauNVODatum>\n'
        if str(bp_bereich[1]) != "NULL":
            bereich += '\t\t\t<xplan:versionBauNVOText>'+ str(bp_bereich[1]) +'</xplan:versionBauNVOText>\n'
        if str(bp_bereich[2]) != "NULL":
            bereich += '\t\t\t<xplan:versionBauGBDatum>'+ bp_bereich[2].toString(Qt.ISODate) +'</xplan:versionBauGBDatum>\n'
        if str(bp_bereich[3]) != "NULL":
            bereich += '\t\t\t<xplan:versionBauGBText>'+ str(bp_bereich[3]) +'</xplan:versionBauGBText>\n'
        if str(bp_bereich[4]) != "NULL":
            bereich += '\t\t\t<xplan:versionSonstRechtsgrundlageDatum>'+ bp_bereich[4].toString(Qt.ISODate) +'</xplan:versionSonstRechtsgrundlageDatum>\n'
        if str(bp_bereich[5]) != "NULL":
            bereich += '\t\t\t<xplan:versionSonstRechtsgrundlageText>'+ str(bp_bereich[5]) +'</xplan:versionSonstRechtsgrundlageText>\n'

        bereich += '\t\t\t<xplan:gehoertZuPlan xlink:href="#GML_'+ self.gmlID_plan + '" />\n'
        # Schließen
        bereich += '\t\t</xplan:BP_Bereich>\n'
        bereich += '\t</gml:featureMember>\n'

        return bereich

    ### XP_Objekt
    def exp_XPobj_GML(self, tab, xp_obj, xp_obj_hoe, xp_obj_extRef, xp_gehoertZuBereich, xp_dargDurch, xp_begrAbschnitt):
        xp_Obj_gml=""
        # XP_Objekt
        if str(xp_obj[0])!="NULL":
            xp_Obj_gml += '\t\t\t<xplan:uuid>'+str(xp_obj[0]) +'</xplan:uuid>\n'
        if str(xp_obj[1])!="NULL":
            xp_Obj_gml += '\t\t\t<xplan:text>'+str(xp_obj[1]) +'</xplan:text>\n'
        if str(xp_obj[2])!="NULL":
            xp_Obj_gml += '\t\t\t<xplan:rechtsstand>'+str(xp_obj[2]) +'</xplan:rechtsstand>\n'
        if str(xp_obj[3])!="NULL":
            xp_Obj_gml += '\t\t\t<xplan:gesetzlicheGrundlage>'+str(xp_obj[3]) +'</xplan:gesetzlicheGrundlage>\n'
        if str(xp_obj[4])!="NULL":
            xp_Obj_gml += '\t\t\t<xplan:gliederung1>'+str(xp_obj[4]) +'</xplan:gliederung1>\n'
        if str(xp_obj[5])!="NULL":
            xp_Obj_gml += '\t\t\t<xplan:gliederung2>'+str(xp_obj[5]) +'</xplan:gliederung2>\n'
        if str(xp_obj[6])!="NULL":
            xp_Obj_gml += '\t\t\t<xplan:ebene>'+str(xp_obj[6]) +'</xplan:ebene>\n'
        
        # XP_GenerAttribut
        
        # hoehenangabe
        if len(xp_obj_hoe)>0:
            for hoA in xp_obj_hoe:
                xp_Obj_gml += '\t\t\t<xplan:hoehenangabe>\n'
                xp_Obj_gml += self.exp_hoehenangabe(tab, hoA)
                xp_Obj_gml += '\t\t\t</xplan:hoehenangabe>\n'
        # ExterneReferenz
        if len(xp_obj_extRef)>0:
            for exR in xp_obj_extRef:
                xp_Obj_gml += '\t\t\t<xplan:externeReferenz>\n'
                xp_Obj_gml += self.exp_extRef(tab, exR)
                xp_Obj_gml += '\t\t\t</xplan:externeReferenz>\n'
        # gehoertZuBereich und wirdDargestelltDurch
        if str(xp_gehoertZuBereich) != "NULL":
            xp_Obj_gml += '\t\t\t<xplan:gehoertZuBereich xlink:href="#GML_'+ str(xp_gehoertZuBereich) + '" />\n'
        if len(xp_dargDurch)>0:
            for darg in xp_dargDurch:
                xp_Obj_gml += '\t\t\t<xplan:wirdDargestelltDurch xlink:href="#GML_'+ darg + '" />\n'
        # refBegruendungInhalt
        if len(xp_begrAbschnitt)>0:
            for bAbsch in xp_begrAbschnitt:
                xp_Obj_gml += '\t\t\t<xplan:refBegruendungInhalt>\n'
                xp_Obj_gml +=  self.exp_begAbschnitt(tab, bAbsch)
                xp_Obj_gml += '\t\t\t</xplan:refBegruendungInhalt>\n'
        # startBedingung
        if str(xp_obj[7]) != "NULL":
            xp_Obj_gml +='\t\t\t<xplan:startBedingung>\n'
            xp_Obj_gml += self.exp_wirkBedingung(tab, self.abf_wirkBed(xp_obj[7]))
            xp_Obj_gml += '\t\t\t</xplan:startBedingung>\n'
        # endeBedingung
        if str(xp_obj[8]) != "NULL":
            xp_Obj_gml += '\t\t\t<xplan:endeBedingung>\n'
            xp_Obj_gml += self.exp_wirkBedingung(tab, self.abf_wirkBed(xp_obj[8]))
            xp_Obj_gml += '\t\t\t</xplan:endeBedingung>\n'
        # aufschrift
        if str(xp_obj[10]) != "NULL":
            xp_Obj_gml += '\t\t\t<xplan:aufschrift>'+str(xp_obj[10]) +'</xplan:aufschrift>\n'
        return xp_Obj_gml

    ### BP_Objekt
    def exp_BPobj_GML(self, tab, bp_obj, bp_refText,xp_refTex, bp_ausglFlae, bp_ausglFlae_mas, bp_anpfBindErh, bp_anpfBindErh_geg, bp_schPfEntw, bp_schPfEntw_mas, bp_speFlae, bp_speFlae_mas, bp_ausglFlMas, bp_ausglFlMas_mas, bp_larmKonGebi, bp_zusKo,bp_zusKo_bpObj, bp_richtSekt, bp_zusKonFlae, bp_zusKonFlae_bp_obj ,bp_richSekGre, laermK):
        bp_obj_gml=""
        if str(bp_obj[0]) != "NULL":
            bp_obj_gml += '\t\t\t<xplan:rechtscharakter>'+str(bp_obj[0]) +'</xplan:rechtscharakter>\n'
        # refTextInhalt
        if len(bp_refText)>0:
            for refT in bp_refText:
                bp_obj_gml +=self.exp_BP_textAbsch(tab, refT, xp_refTex)
                
        # wirdAusgeglichenDurchFlaeche
        if len(bp_ausglFlae)>0:
            i = 0
            for ausg in bp_ausglFlae:
                bp_obj_gml += '\t\t\t<xplan:wirdAusgeglichenDurchFlaeche>\n'
                bp_obj_gml += self.exp_ausglFlaeche(tab, ausg, bp_ausglFlae_mas)
                bp_obj_gml += '\t\t\t</xplan:wirdAusgeglichenDurchFlaeche>\n'
                i+=1
        # wirdAusgeglichenDurchABE
        if len(bp_anpfBindErh)>0:
            i = 0
            for aBE in bp_anpfBindErh:
                bp_obj_gml += '\t\t\t<xplan:wirdAusgeglichenDurchABE>\n'
                bp_obj_gml += self.exp_anpfBindErh(tab, aBE, bp_anpfBindErh_geg, i)
                bp_obj_gml += '\t\t\t</xplan:wirdAusgeglichenDurchABE>\n'
                i+=1
        # wirdAusgeglichenDurchSPEMassnahme 
        if len(bp_schPfEntw)>0:
            i=0
            for spe in bp_schPfEntw:
                bp_obj_gml += '\t\t\t<xplan:wirdAusgeglichenDurchSPEMassnahme>\n'
                bp_obj_gml += self.exp_schPfEntw(tab, spe, bp_schPfEntw_mas)
                bp_obj_gml += '\t\t\t</xplan:wirdAusgeglichenDurchSPEMassnahme>\n'
                i+=1
        
        # wirdAusgeglichenDurchSPEFlaeche
        if len(bp_speFlae)>0:
            i = 0
            for speF in bp_speFlae:
                bp_obj_gml += '\t\t\t<xplan:wirdAusgeglichenDurchMassnahme>\n'
                bp_obj_gml += self.exp_speFlae(tab, speF, bp_speFlae_mas)
                bp_obj_gml += '\t\t\t</xplan:wirdAusgeglichenDurchMassnahme>\n'
                i+=1
        # wirdAusgeglichenDurchMassnahme
        if len(bp_ausglFlMas)>0:
            i = 0
            for agFMa in bp_ausglFlMas:
                bp_obj_gml += '\t\t\t<xplan:wirdAusgeglichenDurchSPEFlaeche>\n'
                bp_obj_gml += self.exp_ausglFlMas(tab, agFMa, bp_ausglFlMas_mas)
                bp_obj_gml += '\t\t\t</xplan:wirdAusgeglichenDurchSPEFlaeche>\n'
                i+=1
        # laermkontingent
        if str(bp_obj[1]) != "NULL":
            bp_obj_gml += '\t\t\t<xplan:laermkontingent>\n'
            bp_obj_gml += self.exp_laermKonti(tab, laermK)
            bp_obj_gml += '\t\t\t</xplan:laermkontingent>\n'
        # laermkontingentGebiet
        if len(bp_larmKonGebi)>0:
            for lKG in bp_larmKonGebi:
                bp_obj_gml += '\t\t\t<xplan:laermkontingentGebiet>\n'
                bp_obj_gml += self.exp_laermKontiGeb(tab, lKG)
                bp_obj_gml += '\t\t\t</xplan:laermkontingentGebiet>\n'
        # zusatzkontingent
        if str(bp_obj[2]) != "NULL":
            bp_obj_gml += '\t\t\t<xplan:zusatzkontingent>\n'
            bp_obj_gml += self.exp_zuKonti(tab, bp_zusKo, bp_richtSekt, bp_zusKo_bpObj)
            bp_obj_gml += '\t\t\t</xplan:zusatzkontingent>\n'
        # zusatzkontingentFlaeche
        if len(bp_zusKonFlae)>0:
            bp_obj_gml += '\t\t\t<xplan:zusatzkontingentFlaeche>\n'
            bp_obj_gml += self.exp_zuKontiFlae(tab, bp_zusKonFlae, bp_zusKonFlae_bp_obj)
            bp_obj_gml += '\t\t\t</xplan:zusatzkontingentFlaeche>\n'
        # richtungssektorGrenze
        '''if len(bp_richSekGre)>0:
            for riSekGre in bp_richSekGre:
                bp_obj_gml += '\t\t\t<xplan:richtungssektorGrenze>\n'
                bp_obj_gml += self.exp_riSekGre(tab, riSekGre)
                bp_obj_gml += '\t\t\t</xplan:richtungssektorGrenze>\n' '''
        return bp_obj_gml
    
    # BP_TextAbschnitt
    def exp_BP_textAbsch(self, tab, texAbsch, xp_texAbsch):
        bp_texAbsch = tab * str("\t") +'<xplan:BP_TextAbschnitt>'
        bp_texAbsch += self.exp_Xp_texAB(tab, xp_texAbsch)
        bp_texAbsch += (tab +1) * str("\t") +'<xplan:rechtscharakter>'+ texAbsch +'</xplan:rechtscharakter>'
        bp_texAbsch += tab * str("\t") +'</xplan:BP_TextAbschnitt>'
        return bp_texAbsch

    # Klasse BP_Flaechenobjekt
    def exp_BP_flae_GML(self, bp_bgtf):
        tab = 4
        bp_flae_gml = ""
        if len(bp_bgtf)>0 and str(bp_bgtf[0][0])!="NULL":
            bp_flae_gml += "\t\t\t<xplan:position>\n"
            bp_flae_gml += self.exp_gmlGeometrie(tab, bp_bgtf[0][0]) # --> GML_Geometrie exp_gmlGeometrie
            bp_flae_gml += "\t\t\t</xplan:position>\n"
        if len(bp_bgtf)>0 and str(bp_bgtf[0][1])!="NULL":
            bp_flae_gml +="\t\t\t<xplan:flaechenschluss>"+ str(bp_bgtf[0][1]) +"</xplan:flaechenschluss>\n"
        
        return bp_flae_gml

    # BP_FestsetzungenBaugebiet
    def exp_BP_festseBaugebiet_gml(self, bp_festBaug):
        bp_festBG =""
        if str(bp_festBaug[0])!="NULL":
            bp_festBG += '\t\t\t<xplan:MaxZahlWohnungen>'+str(bp_festBaug[0]) +'</xplan:MaxZahlWohnungen>\n'
        if str(bp_festBaug[1])!="NULL":
            bp_festBG += '\t\t\t<xplan:Fmin uom="m2">'+str(bp_festBaug[1]) +'</xplan:Fmin>\n'
        if str(bp_festBaug[2])!="NULL":
            bp_festBG += '\t\t\t<xplan:Fmax uom="m2">'+str(bp_festBaug[2]) +'</xplan:Fmax>\n'
        if str(bp_festBaug[3])!="NULL":
            bp_festBG += '\t\t\t<xplan:Bmin uom="m">'+str(bp_festBaug[3]) +'</xplan:Bmin>\n'
        if str(bp_festBaug[4])!="NULL":
            bp_festBG += '\t\t\t<xplan:Bmax uom="m">'+str(bp_festBaug[4]) +'</xplan:Bmax>\n'
        if str(bp_festBaug[5])!="NULL":
            bp_festBG += '\t\t\t<xplan:Tmin uom="m">'+str(bp_festBaug[5]) +'</xplan:Tmin>\n'
        if str(bp_festBaug[6])!="NULL":
            bp_festBG += '\t\t\t<xplan:Tmax uom="m">'+str(bp_festBaug[6]) +'</xplan:Tmax>\n'
        if str(bp_festBaug[7])!="NULL":
            bp_festBG += '\t\t\t<xplan:GFZmin>'+str(bp_festBaug[7]) +'</xplan:GFZmin>\n'
        if str(bp_festBaug[8])!="NULL":
            bp_festBG += '\t\t\t<xplan:GFZmax>'+str(bp_festBaug[8]) +'</xplan:GFZmax>\n'
        if str(bp_festBaug[9])!="NULL":
            bp_festBG += '\t\t\t<xplan:GFZ>'+str(bp_festBaug[9]) +'</xplan:GFZ>\n'
        if str(bp_festBaug[10])!="NULL":
            bp_festBG += '\t\t\t<xplan:GFZ_Ausn>'+str(bp_festBaug[10]) +'</xplan:GFZ_Ausn>\n'
        if str(bp_festBaug[11])!="NULL":
            bp_festBG += '\t\t\t<xplan:GFmin uom="m2">'+str(bp_festBaug[11]) +'</xplan:GFmin>\n'
        if str(bp_festBaug[12])!="NULL":
            bp_festBG += '\t\t\t<xplan:GFmax uom="m2">'+str(bp_festBaug[12]) +'</xplan:GFmax>\n'
        if str(bp_festBaug[13])!="NULL":
            bp_festBG += '\t\t\t<xplan:GF uom="m2">'+str(bp_festBaug[13]) +'</xplan:GF>\n'
        if str(bp_festBaug[14])!="NULL":
            bp_festBG += '\t\t\t<xplan:GF_Ausn uom="m2">'+str(bp_festBaug[14]) +'</xplan:GF_Ausn>\n'
        if str(bp_festBaug[15])!="NULL":
            bp_festBG += '\t\t\t<xplan:BMZ>'+str(bp_festBaug[15]) +'</xplan:BMZ>\n'
        if str(bp_festBaug[16])!="NULL":
            bp_festBG += '\t\t\t<xplan:BMZ_Ausn>'+str(bp_festBaug[16]) +'</xplan:BMZ_Ausn>\n'
        if str(bp_festBaug[17])!="NULL":
            bp_festBG += '\t\t\t<xplan:BM uom="m3">'+str(bp_festBaug[17]) +'</xplan:BM>\n'
        if str(bp_festBaug[18])!="NULL":
            bp_festBG += '\t\t\t<xplan:BM_Ausn uom="m3">'+str(bp_festBaug[18]) +'</xplan:BM_Ausn>\n'
        if str(bp_festBaug[19])!="NULL":
            bp_festBG += '\t\t\t<xplan:GRZmin>'+str(bp_festBaug[19]) +'</xplan:GRZmin>\n'
        if str(bp_festBaug[20])!="NULL":
            bp_festBG += '\t\t\t<xplan:GRZmax>'+str(bp_festBaug[20]) +'</xplan:GRZmax>\n'
        if str(bp_festBaug[21])!="NULL":
            bp_festBG += '\t\t\t<xplan:GRZ>'+str(bp_festBaug[21]) +'</xplan:GRZ>\n'
        if str(bp_festBaug[22])!="NULL":
            bp_festBG += '\t\t\t<xplan:GRZ_Ausn>'+str(bp_festBaug[22]) +'</xplan:GRZ_Ausn>\n'
        if str(bp_festBaug[23])!="NULL":
            bp_festBG += '\t\t\t<xplan:GRmin uom="m2">'+str(bp_festBaug[23]) +'</xplan:GRmin>\n'
        if str(bp_festBaug[24])!="NULL":
            bp_festBG += '\t\t\t<xplan:GRmax uom="m2">'+str(bp_festBaug[24]) +'</xplan:GRmax>\n'
        if str(bp_festBaug[25])!="NULL":
            bp_festBG += '\t\t\t<xplan:GR uom="m2">'+str(bp_festBaug[25]) +'</xplan:GR>\n'
        if str(bp_festBaug[26])!="NULL":
            bp_festBG += '\t\t\t<xplan:GR_Ausn uom="m2">'+str(bp_festBaug[26]) +'</xplan:GR_Ausn>\n'
        if str(bp_festBaug[27])!="NULL":
            bp_festBG += '\t\t\t<xplan:Zmin>'+str(bp_festBaug[27]) +'</xplan:Zmin>\n'
        if str(bp_festBaug[28])!="NULL":
            bp_festBG += '\t\t\t<xplan:Zmax>'+str(bp_festBaug[28]) +'</xplan:Zmax>\n'
        if str(bp_festBaug[29])!="NULL":
            bp_festBG += '\t\t\t<xplan:Zzwingend>'+str(bp_festBaug[29]) +'</xplan:Zzwingend>\n'
        if str(bp_festBaug[30])!="NULL":
            bp_festBG += '\t\t\t<xplan:Z>'+str(bp_festBaug[30]) +'</xplan:Z>\n'
        if str(bp_festBaug[31])!="NULL":
            bp_festBG += '\t\t\t<xplan:Z_Ausn>'+str(bp_festBaug[31]) +'</xplan:Z_Ausn>\n'
        if str(bp_festBaug[32])!="NULL":
            bp_festBG += '\t\t\t<xplan:Z_Staffel>'+str(bp_festBaug[32]) +'</xplan:Z_Staffel>\n'
        if str(bp_festBaug[33])!="NULL":
            bp_festBG += '\t\t\t<xplan:Z_Dach>'+str(bp_festBaug[33]) +'</xplan:Z_Dach>\n'
        if str(bp_festBaug[34])!="NULL":
            bp_festBG += '\t\t\t<xplan:ZUmin>'+str(bp_festBaug[34]) +'</xplan:ZUmin>\n'
        if str(bp_festBaug[35])!="NULL":
            bp_festBG += '\t\t\t<xplan:ZUmax>'+str(bp_festBaug[35]) +'</xplan:ZUmax>\n'
        if str(bp_festBaug[36])!="NULL":
            bp_festBG += '\t\t\t<xplan:ZUzwingend>'+str(bp_festBaug[36]) +'</xplan:ZUzwingend>\n'
        if str(bp_festBaug[37])!="NULL":
            bp_festBG += '\t\t\t<xplan:ZU>'+str(bp_festBaug[37]) +'</xplan:ZU>\n'
        if str(bp_festBaug[38])!="NULL":
            bp_festBG += '\t\t\t<xplan:ZU_Ausn>'+str(bp_festBaug[38]) +'</xplan:ZU_Ausn>\n'
        return bp_festBG

    ### GML-Auszug für BP_BaugebietsTeilFlaeche
    def exp_bgtfObj_GML(self, gid_Obj):
        # Abfrage der Attribute
        xp_obj = self.abf_xpObj(gid_Obj)
        xp_obj_hoe = self.abf_xpObjHoean(gid_Obj)
        xp_obj_extRef = self.abf_externRef(gid_Obj)
        xp_gehoertZuBereich = self.abf_gmlIDBereich_bgtfObj(gid_Obj)
        xp_dargDurch = self.abf_gmlIDPraes_bgtfObj(gid_Obj)
        xp_begrAbschnitt =  self.abf_begrAbsch(gid_Obj)

        bp_obj = self.abf_bpObj(gid_Obj)
        bp_refText = self.abf_refTextIn(gid_Obj)
        xp_refTex = self.abf_XP_texAb(gid_Obj)
        bp_ausglFlae = self.abf_ausglFlae(gid_Obj)
        bp_ausglFlae_mas = self.abf_ausglFlae_mas(gid_Obj)
        bp_anpfBindErh = self.abf_anpfBindErh(gid_Obj)
        bp_anpfBindErh_geg = self.abf_anpfBindErh_geg(gid_Obj)
        bp_schPfEntw = self.abf_schPfEntw(gid_Obj)
        bp_schPfEntw_mas = self.abf_schPfEntw_mas(gid_Obj)
        bp_speFlae = self.abf_speFlae(gid_Obj)
        bp_speFlae_mas = self.abf_speFlae_mas(gid_Obj)
        bp_ausglFlMas = self.abf_ausglFlMas(gid_Obj)
        bp_ausglFlMas_mas = self.abf_ausglFlMas_mas(gid_Obj)
        bp_larmKonGebi = self.abf_larmKonGebi(gid_Obj)
        bp_laermK = self. abf_laermKonti(bp_obj[1])
        bp_zusKo = self.abf_zusKonti(bp_obj[2])
        bp_zusKo_bpObj = self.abf_bpObj(bp_obj[2])
        bp_richtSekt = self.abf_richtSekt(bp_obj[2])
        bp_zusKonFlae = self.abf_zusKontiFlae(gid_Obj)
        bp_zusKonFlae_bp_obj = []
        if len(bp_zusKonFlae)>0:
            bp_zusKonFlae_bp_obj = self.abf_bpObj(bp_zusKonFlae[0][3])
        bp_richSekGre = self.abf_richSekGre(gid_Obj)

        bp_bgtf = self.abf_bauGebTF(gid_Obj)

        bp_dachGest = self.abf_dachGest(gid_Obj)
        bp_gestBaugebiet = self.abf_gestBaugebiet(gid_Obj)
        bp_dachform = self.abf_dachForm(gid_Obj)
        bp_detDachF = self.abf_detDachF(gid_Obj)

        bp_festBaug = self.abf_festBaug(gid_Obj)
        bp_zusFest = self.abf_zusFest(gid_Obj)
        bp_sondNutz = self.abf_sondNutz(gid_Obj)

        bp_baugBauw = self.abf_baugBauw(gid_Obj)
        bp_refGebQuerSch = self. abf_refGebQuerSch(gid_Obj)

        # Schreiben des GML-Abschnitts 
        tab = 4

        bgtfObj = '\t<gml:featureMember>\n'
        bgtfObj += '\t\t<xplan:BP_BaugebietsTeilFlaeche gml:id="GML_'+ xp_obj[9] +'">\n'

        # XP_Objekt
        bgtfObj += self.exp_XPobj_GML(tab, xp_obj, xp_obj_hoe, xp_obj_extRef, xp_gehoertZuBereich, xp_dargDurch, xp_begrAbschnitt)

        # BP_Objekt
        bgtfObj += self.exp_BPobj_GML(tab, bp_obj, bp_refText,xp_refTex, bp_ausglFlae, bp_ausglFlae_mas, bp_anpfBindErh, bp_anpfBindErh_geg, bp_schPfEntw, bp_schPfEntw_mas, bp_speFlae, bp_speFlae_mas, bp_ausglFlMas, bp_ausglFlMas_mas, bp_larmKonGebi, bp_zusKo, bp_zusKo_bpObj, bp_richtSekt, bp_zusKonFlae, bp_zusKonFlae_bp_obj ,bp_richSekGre, bp_laermK)
        
        # BP_Flaechenobjekt
        bgtfObj += self.exp_BP_flae_GML(bp_bgtf)

        ######
        # BP_BaugebietsTeilFlaeche
        if len(bp_dachGest)>0:
            bgtfObj += '\t\t\t<xplan:dachgestaltung>\n'
            bgtfObj += self.exp_dachGe(tab, bp_dachGest)
            bgtfObj += '\t\t\t</xplan:dachgestaltung>\n'
        
        if len(bp_gestBaugebiet)>0 and str(bp_gestBaugebiet[0][0])!="NULL":
            bgtfObj += '\t\t\t<xplan:DNmin uom="grad">'+str(bp_gestBaugebiet[0][0]) +'</xplan:DNmin>\n'
        if len(bp_gestBaugebiet)>0 and str(bp_gestBaugebiet[0][1])!="NULL":
            bgtfObj += '\t\t\t<xplan:DNmax uom="grad">'+str(bp_gestBaugebiet[0][1]) +'</xplan:DNmax>\n'
        if len(bp_gestBaugebiet)>0 and str(bp_gestBaugebiet[0][2])!="NULL":
            bgtfObj += '\t\t\t<xplan:DN uom="grad">'+str(bp_gestBaugebiet[0][2]) +'</xplan:DN>\n'
        if len(bp_gestBaugebiet)>0 and str(bp_gestBaugebiet[0][3])!="NULL":
            bgtfObj += '\t\t\t<xplan:DNZwingend uom="grad">'+str(bp_gestBaugebiet[0][3]) +'</xplan:DNZwingend>\n'
        if len(bp_gestBaugebiet)>0 and str(bp_gestBaugebiet[0][4])!="NULL":
            bgtfObj += '\t\t\t<xplan:FR uom="grad">'+str(bp_gestBaugebiet[0][4]) +'</xplan:FR>\n'
        # dachform
        if str(bp_dachform)!="NULL":
            bgtfObj += '\t\t\t<xplan:dachform>'+str(bp_dachform) +'</xplan:dachform>\n'
        # detaillierteDachform 
        if str(bp_detDachF)!="NULL":
            bgtfObj += '\t\t\t<xplan:detaillierteDachform>'+str(bp_detDachF) +'</xplan:detaillierteDachform>\n'
        
        # abweichungText --> BP_TextAbschnitt nicht gefunden in DB

        # BP_FestsetzungenBaugebiet
        bgtfObj += self.exp_BP_festseBaugebiet_gml(bp_festBaug)
        
        # BP_ZusaetzlicheFestsetzungen
        if len(bp_zusFest)>0 and str(bp_zusFest[0][0]) != "NULL":
            bgtfObj += '\t\t\t<xplan:wohnnutzungEGStrasse>'+str(bp_zusFest[0][0]) +'</xplan:wohnnutzungEGStrasse>\n'
        if len(bp_zusFest)>0 and str(bp_zusFest[0][1]) != "NULL":
            bgtfObj += '\t\t\t<xplan:ZWohn>'+str(bp_zusFest[0][1]) +'</xplan:ZWohn>\n'
        if len(bp_zusFest)>0 and str(bp_zusFest[0][2]) != "NULL":
            bgtfObj += '\t\t\t<xplan:GFAntWohnen>'+str(bp_zusFest[0][2]) +'</xplan:GFAntWohnen>\n'
        if len(bp_zusFest)>0 and str(bp_zusFest[0][3]) != "NULL":
            bgtfObj += '\t\t\t<xplan:GFWohnen uom="m2">'+str(bp_zusFest[0][3]) +'</xplan:GFWohnen>\n'
        if len(bp_zusFest)>0 and str(bp_zusFest[0][4]) != "NULL":
            bgtfObj += '\t\t\t<xplan:GFAntGewerbe>'+str(bp_zusFest[0][4]) +'</xplan:GFAntGewerbe>\n'
        if len(bp_zusFest)>0 and str(bp_zusFest[0][5]) != "NULL":
            bgtfObj += '\t\t\t<xplan:GFGewerbe uom="m2">'+str(bp_zusFest[0][5]) +'</xplan:GFGewerbe>\n'
        if len(bp_zusFest)>0 and str(bp_zusFest[0][6]) != "NULL":
            bgtfObj += '\t\t\t<xplan:VF uom="m2">'+str(bp_zusFest[0][6]) +'</xplan:VF>\n'
        
        # BP_BaugebietsTeilFlaeche
        if len(bp_bgtf)>0 and str(bp_bgtf[0][2])!="NULL":
            bgtfObj += '\t\t\t<xplan:allgArtDerBaulNutzung>'+str(bp_bgtf[0][2]) +'</xplan:allgArtDerBaulNutzung>\n'
        if len(bp_bgtf)>0 and str(bp_bgtf[0][3])!="NULL":
            bgtfObj += '\t\t\t<xplan:besondereArtDerBaulNutzung>'+str(bp_bgtf[0][3]) +'</xplan:besondereArtDerBaulNutzung>\n'
        # Sondernutzung
        if str(bp_sondNutz)!= "NULL":
            bgtfObj += '\t\t\t<xplan:sondernutzung>'+ str(bp_sondNutz) +'</xplan:sondernutzung>\n'

        if len(bp_bgtf)>0 and str(bp_bgtf[0][4])!="NULL":
            bgtfObj += '\t\t\t<xplan:detaillierteArtDerBaulNutzung>'+str(bp_bgtf[0][4]) +'</xplan:detaillierteArtDerBaulNutzung>\n'
        if len(bp_bgtf)>0 and str(bp_bgtf[0][5])!="NULL":
            bgtfObj += '\t\t\t<xplan:nutzungText>'+str(bp_bgtf[0][5]) +'</xplan:nutzungText>\n'
        if len(bp_bgtf)>0 and str(bp_bgtf[0][6])!="NULL":
            bgtfObj += '\t\t\t<xplan:abweichungBauNVO>'+str(bp_bgtf[0][6]) +'</xplan:abweichungBauNVO>\n'
        
        # BP_BaugebietBauweise
        if len(bp_baugBauw)>0 and str(bp_baugBauw[0][0])!="NULL":
            bgtfObj += '\t\t\t<xplan:bauweise>'+str(bp_baugBauw[0][0]) +'</xplan:bauweise>\n'
        if len(bp_baugBauw)>0 and str(bp_baugBauw[0][1])!="NULL":
            bgtfObj += '\t\t\t<xplan:abweichendeBauweise>'+str(bp_baugBauw[0][1]) +'</xplan:abweichendeBauweise>\n'
        if len(bp_baugBauw)>0 and str(bp_baugBauw[0][2])!="NULL":
            bgtfObj += '\t\t\t<xplan:vertikaleDifferenzierung>'+str(bp_baugBauw[0][2]) +'</xplan:vertikaleDifferenzierung>\n'
        if len(bp_baugBauw)>0 and str(bp_baugBauw[0][3])!="NULL":
            bgtfObj += '\t\t\t<xplan:bebauungsArt>'+str(bp_baugBauw[0][3]) +'</xplan:bebauungsArt>\n'
        if len(bp_baugBauw)>0 and str(bp_baugBauw[0][4])!="NULL":
            bgtfObj += '\t\t\t<xplan:bebauungVordereGrenze>'+str(bp_baugBauw[0][4]) +'</xplan:bebauungVordereGrenze>\n'
        if len(bp_baugBauw)>0 and str(bp_baugBauw[0][5])!="NULL":
            bgtfObj += '\t\t\t<xplan:bebauungRueckwaertigeGrenze>'+str(bp_baugBauw[0][5]) +'</xplan:bebauungRueckwaertigeGrenze>\n'
        if len(bp_baugBauw)>0 and str(bp_baugBauw[0][6])!="NULL":
            bgtfObj += '\t\t\t<xplan:bebauungSeitlicheGrenze>'+str(bp_baugBauw[0][6]) +'</xplan:bebauungSeitlicheGrenze>\n'

        # refGebaeudequerschnitt
        if len(bp_refGebQuerSch)>0:
            for refEx in bp_refGebQuerSch:
                bgtfObj += '\t\t\t<xplan:refGebaeudequerschnitt>\n'
                bgtfObj += self.exp_extRef(tab, refEx)
                bgtfObj += '<\t\t\t/xplan:refGebaeudequerschnitt>\n'

        if len(bp_bgtf)>0 and str(bp_bgtf[0][7])!="NULL":
            bgtfObj += '\t\t\t<xplan:zugunstenVon>'+str(bp_bgtf[0][7]) +'</xplan:zugunstenVon>\n'

        # Ende des Abschnitts
        bgtfObj += '\t\t</xplan:BP_BaugebietsTeilFlaeche>\n'
        bgtfObj += '\t</gml:featureMember>\n'

        return bgtfObj

    # BP_Dachgestaltung
    def exp_dachGe(self, tab, dG):
        dachGe = tab * str("\t") +"<xplan:BP_Dachgestaltung>\n"
        if str(dG[0])!="NULL":
            dachGe += (tab+1) * str("\t") +'<xplan:DNmin uom="grad">'+ str(dG[0]) +"</xplan:DNmin>\n"
        if str(dG[1])!="NULL":
            dachGe += (tab+1) * str("\t") +'<xplan:DNmax uom="grad">'+ str(dG[1]) +"</xplan:DNmax>\n"
        if str(dG[2])!="NULL":
            dachGe += (tab+1) * str("\t") +'<xplan:DN uom="grad">'+ str(dG[2]) +"</xplan:DN>\n"
        if str(dG[3])!="NULL":
            dachGe += (tab+1) * str("\t") +'<xplan:DNzwingend uom="grad">'+ str(dG[3]) +"</xplan:DNzwingend>\n"
        if str(dG[4])!="NULL":
            dachGe += (tab+1) * str("\t") +"<xplan:dachform>"+ str(dG[4]) +"</xplan:dachform>\n"
        if str(dG[5])!="NULL":
            dachGe += (tab+1) * str("\t") +"<xplan:detaillierteDachform>"+ str(dG[5]) +"</xplan:detaillierteDachform>\n"
        dachGe += tab * str("\t") +"</xplan:BP_Dachgestaltung>\n"

    # XP_Hoehenangabe
    def exp_hoehenangabe(self,tab, xp_obj_hoe):
        hoeAng = tab * str("\t") +"<xplan:XP_Hoehenangabe>\n"
        if str(xp_obj_hoe[0])!= "NULL":
            hoeAng +=(tab+1) * str("\t") +"<xplan:abweichenderHoehenbezug>"+ str(xp_obj_hoe[0]) +"</xplan:abweichenderHoehenbezug>\n"
        if str(xp_obj_hoe[1])!= "NULL":
            hoeAng +=(tab+1) * str("\t") +"<xplan:hoehenbezug>"+ str(xp_obj_hoe[1]) +"</xplan:hoehenbezug>\n"
        if str(xp_obj_hoe[2])!= "NULL":
            hoeAng +=(tab+1) * str("\t") +"<xplan:abweichenderBezugspunkt>"+ str(xp_obj_hoe[2]) +"</xplan:abweichenderBezugspunkt>\n"
        if str(xp_obj_hoe[3])!= "NULL":
            hoeAng +=(tab+1) * str("\t") +"<xplan:bezugspunkt>"+ str(xp_obj_hoe[3]) +"</xplan:bezugspunkt>\n"
        if str(xp_obj_hoe[4])!= "NULL":
            hoeAng +=(tab+1) * str("\t") +'<xplan:hMin uom="m">'+ str(xp_obj_hoe[4]) +"</xplan:hMin>\n"
        if str(xp_obj_hoe[5])!= "NULL":
            hoeAng +=(tab+1) * str("\t") +'<xplan:hMax uom="m">'+ str(xp_obj_hoe[5]) +"</xplan:hMax>\n"
        if str(xp_obj_hoe[6])!= "NULL":
            hoeAng +=(tab+1) * str("\t") +'<xplan:hZwingend uom="m">'+ str(xp_obj_hoe[6]) +"</xplan:hZwingend>\n"
        if str(xp_obj_hoe[7])!= "NULL":
            hoeAng +=(tab+1) * str("\t") +'<xplan:h uom="m">'+ str(xp_obj_hoe[7]) +"</xplan:h>\n"
        hoeAng += tab * str("\t") +"</xplan:XP_Hoehenangabe>\n"
        return hoeAng
    
    # Klasse XP_WirksamkeitBedingung
    def exp_wirkBedingung(self, tab, wBed):
        wB = tab * str("\t") +"<xplan:XP_WirksamkeitBedingung>\n"
        if str(wBed[0])!= "NULL":
            wB +=(tab+1) * str("\t") +"<xplan:bedingung>"+ str(wBed[0]) +"</xplan:bedingung>\n"
        if str(wBed[1])!= "NULL":
            wB +=(tab+1) * str("\t") +"<xplan:datumAbsolut>"+ wBed[1].toString(Qt.ISODate) +"</xplan:datumAbsolut>\n"
        if str(wBed[2])!= "NULL":
            wB +=(tab+1) * str("\t") +"<xplan:datumRelativ>"+ wBed[2].toString(Qt.ISODate) +"</xplan:datumRelativ>\n"
        wB += tab * str("\t") +"</xplan:XP_WirksamkeitBedingung>\n"
        return wB

    # BP_AusgleichsFlaeche
    def exp_ausglFlaeche(self, tab, aFlae, ausglFlae_mas):
        ausFlae = tab * str("\t") +"<xplan:BP_AusgleichsFlaeche>\n"
        if str(aFlae[0][0])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:position>\n"
            ausFlae += self.exp_gmlGeometrie(tab+3, aFlae[0][0]) # --> GML_Geometrie exp_gmlGeometrie
            ausFlae += (tab+1) * str("\t") +"</xplan:position>\n"
        if str(aFlae[0][1])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:ziel>"+ str(aFlae[0][1]) +"</xplan:ziel>\n"
        if str(aFlae[0][2])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:sonstZiel>"+ str(aFlae[0][2]) +"</xplan:sonstZiel>\n"
        # XP_SPEMassnahmenDaten
        if len(ausglFlae_mas)>0:
            for mas in ausglFlae_mas:
                ausFlae += (tab+1) * str("\t") +"<xplan:massnahme>\n"
                ausFlae += self.exp_XP_SPEMasD(tab+1, mas)
                ausFlae += (tab+1) * str("\t") +"</xplan:massnahme>\n"
        if str(aFlae[3])!= "NULL":
            eRef= self.abf_externRef(aFlae[3])
            if len(eRef)>0:
                for e in eRef:
                    ausFlae += (tab+1) * str("\t") +"<xplan:refMassnahmenText>\n"
                    ausFlae += self.exp_extRef(tab, e)
                    ausFlae += (tab+1) * str("\t") +"</xplan:refMassnahmenText>\n"
        if str(aFlae[4])!= "NULL":
            eRef= self.abf_externRef(aFlae[4])
            if len(eRef)>0:
                for e in eRef:
                    ausFlae += (tab+1) * str("\t") +"<xplan:refLandschaftsplan>\n"
                    ausFlae += self.exp_extRef(tab, e)
                    ausFlae += (tab+1) * str("\t") +"</xplan:refLandschaftsplan>\n"
        ausFlae += tab * str("\t") +"</xplan:BP_AusgleichsFlaeche>\n"
        return ausFlae

    # BP_AnpflanzungBindungErhaltung
    def exp_anpfBindErh(self, tab, anBiEr, geg, i):
        ausFlae = tab * str("\t") +"<xplan:BP_AnpflanzungBindungErhaltung>\n"
        if str(anBiEr[0])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:massnahme>"+ str(anBiEr[0]) +"</xplan:massnahme>\n"
        if str(geg[i])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:gegenstand>"+ str(geg[i]) +"</xplan:gegenstand>\n"
        if str(anBiEr[1])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:kronendurchmesser>"+ str(anBiEr[1]) +"</xplan:kronendurchmesser>\n"
        if str(anBiEr[2])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:pflanztiefe>"+ str(anBiEr[2]) +"</xplan:pflanztiefe>\n"
        if str(anBiEr[3])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:istAusgleich>"+ str(anBiEr[3]) +"</xplan:istAusgleich>\n"
        if str(anBiEr[4])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:baumArt>"+ str(anBiEr[4]) +"</xplan:baumArt>\n"
        if str(anBiEr[5])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:mindesthoehe>"+ str(anBiEr[5]) +"</xplan:mindesthoehe>\n"
        if str(anBiEr[6])!= "NULL":
            ausFlae += (tab+1) * str("\t") +"<xplan:anzahl>"+ str(anBiEr[6]) +"</xplan:anzahl>\n"
        ausFlae += tab * str("\t") +"</xplan:BP_AnpflanzungBindungErhaltung>\n"

    # BP_SchutzPflegeEntwicklungsMassnahme
    def exp_schPfEntw(self, tab, spe, spe_mas):
        schPfEntw = tab * str("\t") +"<xplan:BP_SchutzPflegeEntwicklungsMassnahme>\n"
        if str(spe[0])!= "NULL":
            schPfEntw += (tab+1) * str("\t") +"<xplan:ziel>"+ str(spe[0]) +"</xplan:ziel>\n"
        if str(spe[1])!= "NULL":
            schPfEntw += (tab+1) * str("\t") + "<xplan:sonstZiel>"+ str(spe[1]) + "</xplan:sonstZiel>\n"
        # XP_SPEMassnahmenDaten 
        if len(spe_mas)>0:
            for mas in spe_mas:
                schPfEntw += (tab+1) * str("\t") +"<xplan:massnahme>\n"
                schPfEntw += self.exp_XP_SPEMasD(tab+1, mas)
                schPfEntw += (tab+1) * str("\t") +"</xplan:massnahme>\n"
        if str(spe[2])!= "NULL":
            schPfEntw += (tab+1) * str("\t") +"<xplan:istAusgleich>"+ str(spe[2]) +"</xplan:istAusgleich>\n"
        if str(spe[3])!= "NULL":
            eRef= self.abf_externRef(spe[3])
            if len(eRef)>0:
                for e in eRef:
                    schPfEntw += (tab+1) * str("\t") +"<xplan:refMassnahmenText>\n"
                    schPfEntw += self.exp_extRef(tab, e)
                    schPfEntw += (tab+1) * str("\t") +"</xplan:refMassnahmenText>\n"
        if str(spe[4])!= "NULL":
            eRef= self.abf_externRef(spe[4])
            if len(eRef)>0:
                for e in eRef:
                    schPfEntw += (tab+1) * str("\t") +"<xplan:refLandschaftsplan>\n"
                    schPfEntw += self.exp_extRef(tab, e)
                    schPfEntw += (tab+1) * str("\t") +"</xplan:refLandschaftsplan>\n"
        schPfEntw += tab * str("\t") +"</xplan:BP_SchutzPflegeEntwicklungsMassnahme>\n"
        return schPfEntw

    # XP_SPEMassnahmenDaten
    def exp_XP_SPEMasD(self, tab, mas):
        speM = tab * str("\t") +"<xplan:XP_SPEMassnahmenDaten>\n"
        speM += (tab+1) * str("\t") +"<xplan:klassifizMassnahme>"+ str(mas[0]) +"</xplan:klassifizMassnahme>\n"
        speM += (tab+1) * str("\t") +"<xplan:massnahmeText>"+ str(mas[1]) +"</xplan:massnahmeText>\n"
        speM += (tab+1) * str("\t") +"<xplan:massnahmeKuerzel>"+ str(mas[2]) +"</xplan:massnahmeKuerzel>\n"
        speM += tab * str("\t") +"<xplan:XP_SPEMassnahmenDaten>\n"
        return speM

    # BP_SchutzPflegeEntwicklungsFlaeche
    def exp_speFlae(self, tab, speF, speF_mas):
        speFlae = tab * str("\t") +"<xplan:BP_SchutzPflegeEntwicklungsFlaeche>\n"
        if str(speF[0][0])!= "NULL":
            speFlae += (tab+1) * str("\t") +"<xplan:position>\n"
            speFlae += self.exp_gmlGeometrie(tab+2, speF[0][0]) # --> GML_Geometrie exp_gmlGeometrie
            speFlae += (tab+1) * str("\t") +"</xplan:position>\n"
        if str(speF[0][1])!= "NULL":
            speFlae += (tab+1) * str("\t") +"<xplan:ziel>"+ str(speF[0][1]) +"</xplan:ziel>\n"
        if str(speF[0][2])!= "NULL":
            speFlae += (tab+1) * str("\t") +"<xplan:sonstZiel>"+ str(speF[0][2]) +"</xplan:sonstZiel>\n"
        # XP_SPEMassnahmenDaten 
        if len(speF_mas)>0:
            for mas in speF_mas:
                speFlae += (tab+1) * str("\t") +"<xplan:massnahme>\n"
                speFlae += self.exp_XP_SPEMasD(tab+1, mas)
                speFlae += (tab+1) * str("\t") +"</xplan:massnahme>\n"
        if str(speF[3])!= "NULL":
            speFlae += (tab+1) * str("\t") +"<xplan:istAusgleich>"+ str(speF[3]) +"</xplan:istAusgleich>\n"
        if str(speF[4])!= "NULL":
            eRef= self.abf_externRef(speF[4])
            if len(eRef)>0:
                for e in eRef:
                    speFlae += (tab+1) * str("\t") +"<xplan:refMassnahmenText>\n"
                    speFlae += self.exp_extRef(tab, e)
                    speFlae += (tab+1) * str("\t") +"</xplan:refMassnahmenText>\n"
        if str(speF[5])!= "NULL":
            eRef= self.abf_externRef(speF[4])
            if len(eRef)>0:
                for e in eRef:
                    speFlae += (tab+1) * str("\t") +"<xplan:refLandschaftsplan>\n"
                    speFlae += self.exp_extRef(tab, e)
                    speFlae += (tab+1) * str("\t") +"</xplan:refLandschaftsplan>\n"
        speFlae += tab * str("\t") +"</xplan:BP_SchutzPflegeEntwicklungsFlaeche>\n"
        return speFlae

    # BP_AusgleichsMassnahme
    def exp_ausglFlMas(self, tab, ausgF, ausgF_mas):
        ausgFlae = tab * str("\t") +"<xplan:BP_AusgleichsMassnahme>\n"
        # XP_Objekt
        # BP_Objekt
        if str(ausgF[0])!= "NULL":
            ausgFlae += (tab+1) * str("\t") +"<xplan:ziel>"+ str(ausgF[0]) +"</xplan:ziel>\n"
        if str(ausgF[1])!= "NULL":
            ausgFlae += (tab+1) * str("\t") +"<xplan:sonstZiel>"+ str(ausgF[1]) +"</xplan:sonstZiel>\n"
        # XP_SPEMassnahmenDaten 
        if len(ausgF_mas)>0:
            for mas in ausgF_mas:
                ausgFlae += (tab+1) * str("\t") +"<xplan:massnahme>\n"
                ausgFlae += self.exp_XP_SPEMasD(tab+1, mas)
                ausgFlae += (tab+1) * str("\t") +"</xplan:massnahme>\n"
        if str(ausgF[2])!= "NULL":
            eRef= self.abf_externRef(ausgF[2])
            if len(eRef)>0:
                for e in eRef:
                    ausgFlae += (tab+1) * str("\t") +"<xplan:refMassnahmenText>\n"
                    ausgFlae += self.exp_extRef(tab, e)
                    ausgFlae += (tab+1) * str("\t") +"</xplan:refMassnahmenText>\n"
        if str(ausgF[3])!= "NULL":
            eRef= self.abf_externRef(ausgF[3])
            if len(eRef)>0:
                for e in eRef:
                    ausgFlae += (tab+1) * str("\t") +"<xplan:refLandschaftsplan>\n"
                    ausgFlae += self.exp_extRef(tab, e)
                    ausgFlae += (tab+1) * str("\t") +"</xplan:refLandschaftsplan>\n"
        ausgFlae += tab * str("\t") +"</xplan:BP_AusgleichsMassnahme>\n"
        return ausgFlae

    # BP_EmissionskontingentLaerm
    def exp_laermKonti(self, tab, laermKo):
        lKon = tab * str("\t") +"<xplan:BP_EmissionskontingentLaerm>\n"
        if str(laermKo[0]) != "NULL":
            lKon += (tab+1) * str("\t") +"<xplan:ekwertTag>"+ str(laermKo[0]) +"</xplan:ekwertTag>\n"
        if str(laermKo[1]) != "NULL":
            lKon += (tab+1) * str("\t") +"<xplan:ekwertNacht>"+ str(laermKo[1]) +"</xplan:ekwertNacht>\n"
        if str(laermKo[2]) != "NULL":
            lKon += (tab+1) * str("\t") +"<xplan:erlaeuterung>"+ str(laermKo[2]) +"</xplan:erlaeuterung>\n"
        lKon += tab * str("\t") +"</xplan:BP_EmissionskontingentLaerm>\n"
        return lKon
    
    #  BP_EmissionskontingentLaermGebiet
    def exp_laermKontiGeb(self, tab, laekonGeb):
        lkonGe = tab * str("\t") +"<xplan:BP_EmissionskontingentLaermGebiet>\n"
        lkonGe += (tab+1) * str("\t") +"<xplan:gebietsbezeichnung>"+ str(laekonGeb) +"</xplan:gebietsbezeichnung>\n"
        lkonGe += tab * str("\t") +"</xplan:BP_EmissionskontingentLaermGebiet>\n"
        return lkonGe

    # BP_ZusatzkontingentLaerm
    def exp_zuKonti(self, tab, zuK, richSek, bp_obj):
        zuKon = tab * str("\t") +"<xplan:BP_ZusatzkontingentLaerm>\n"
        # XP_Objekt
        # BP_Objekt
        if str(bp_obj[0]) != "NULL":
            zuKon += (tab+1) * str("\t") +'<xplan:rechtscharakter>'+str(bp_obj[0]) +'</xplan:rechtscharakter>\n'
        if str(zuK[0][0]) != "NULL":
            zuKon += (tab+1) * str("\t") +"<xplan:position>\n"
            zuKon += self.exp_gmlGeometrie(tab+2, zuK[0][0]) # --> GML_Geometrie exp_gmlGeometrie
            zuKon += (tab+1) * str("\t") +"</xplan:position>\n"
        if str(zuK[0][1]) != "NULL":
            zuKon +=(tab+1) * str("\t") +"<xplan:bezeichnung>"+ str(zuK[0][1]) +"</xplan:bezeichnung>\n"
        if len(richSek)>0:
            for rS in richSek:
                zuKon += (tab+1) * str("\t") +"<xplan:richtungssektor>\n"
                zuKon += self.exp_RichtSekt(tab+2, rS) 
                zuKon += (tab+1) * str("\t") +"</xplan:richtungssektor>\n"
        zuKon += tab * str("\t") +"</xplan:BP_ZusatzkontingentLaerm>\n"
        return zuKon

    # BP_Richtungssektor
    def exp_RichtSekt(self, tab, rS):
        richSek = tab * str("\t") +"<xplan:BP_Richtungssektor>\n"
        if str(rS[0])!= "NULL":
            richSek += (tab+1) * str("\t") +'<xplan:winkelAnfang uom="grad">'+ str(rS[0]) +"</xplan:winkelAnfang>\n"
        if str(rS[1])!= "NULL":
            richSek += (tab+1) * str("\t") +'<xplan:winkelEnde uom="grad">'+ str(rS[1]) +"</xplan:winkelEnde>\n"
        if str(rS[2])!= "None":
            richSek += (tab+1) * str("\t") +'<xplan:zkWertTag uom="db">'+ str(rS[2]) +"</xplan:zkWertTag>\n"
        if str(rS[3])!= "None":
            richSek += (tab+1) * str("\t") +'<xplan:zkWertNacht uom="db">'+ str(rS[3]) +"</xplan:zkWertNacht>\n"
        richSek += tab * str("\t") +"</xplan:BP_Richtungssektor>\n"
        return richSek
    
    # BP_ZusatzkontingentLaermFlaeche
    def exp_zuKontiFlae(self, tab, zuKonFl, bp_obj):
        zuKonF = tab * str("\t") +"<xplan:BP_ZusatzkontingentLaermFlaeche>\n"
        # BP_Objekt
        if str(bp_obj[0]) != "NULL":
            zuKonF += (tab+1) * str("\t") +'<xplan:rechtscharakter>'+str(bp_obj[0]) +'</xplan:rechtscharakter>\n'
        if str(zuKonFl[0][0]) != "NULL":
            zuKonF += (tab+1) * str("\t") +"<xplan:position>\n"
            zuKonF += self.exp_gmlGeometrie(tab+2, zuKonFl[0][0]) # --> GML_Geometrie exp_gmlGeometrie
            zuKonF += (tab+1) * str("\t") +"</xplan:position>\n"
        if str(zuKonFl[0][4])!= "NULL":
            zuKonF += (tab+1) * str("\t") + "<xplan:flaechenschluss>"+ str(zuKonFl[0][4]) +"</xplan:flaechenschluss>\n"
        if str(zuKonFl[0][1]) != "NULL":
            zuKonF += (tab+1) * str("\t") + "<xplan:bezeichnung>"+ str(zuKonFl[0][1]) +"</xplan:bezeichnung>\n"
        if str(zuKonFl[0][2]) != "NULL":
            richSek = self.abf_richtSekt_zKF(zuKonFl[0][2])
            for rS in richSek:
                zuKonF += (tab+1) * str("\t") +"<xplan:richtungssektor>\n"
                zuKonF += self.exp_RichtSekt(tab+2, rS)
                zuKonF += (tab+1) * str("\t") +"</xplan:richtungssektor>\n"
        zuKonF += tab * str("\t") +"</xplan:BP_ZusatzkontingentLaermFlaeche>\n"
        return zuKonF
    
    # BP_RichtungssektorGrenze !!!!bearbeiten!!!
    def exp_riSekGre(self, tab, riSekGre):
        rsG = tab * str("\t") +"<xplan:BP_RichtungssektorGrenze>\n"
        if str(riSekGre[0]) != "NULL":
            rsG += (tab+1) * str("\t") +"<xplan:position>\n"
            rsG += (tab+2) * str("\t") +str(riSekGre[0]) + "\n" # --> GML_Geometrie exp_gmlGeometrie
            # rsG += self.exp_gmlGeometrie(tab+3, riSekGre[0])
            rsG += (tab+1) * str("\t") +"</xplan:position>\n"
        if str(riSekGre[1]) != "NULL":
            rsG +=(tab+1) * str("\t") +"<xplan:winkel>"+ str(riSekGre[1]) +"</xplan:winkel>\n"
        rsG += tab * str("\t") +"</xplan:BP_RichtungssektorGrenze>\n"
        return rsG

    ### GML-Auszug für BP_StrassenVerkehrsFlaeche
    def exp_strVerkFlae_GML(self, gid_Obj):
        # Abfrage der Attribute
        xp_obj = self.abf_xpObj(gid_Obj)
        xp_obj_hoe = self.abf_xpObjHoean(gid_Obj)
        xp_obj_extRef = self.abf_externRef(gid_Obj)
        xp_gehoertZuBereich = self.abf_gmlIDBereich_bgtfObj(gid_Obj)
        xp_dargDurch = self.abf_gmlIDPraes_bgtfObj(gid_Obj)
        xp_begrAbschnitt =  self.abf_begrAbsch(gid_Obj)

        bp_obj = self.abf_bpObj(gid_Obj)
        bp_refText = self.abf_refTextIn(gid_Obj)
        xp_refTex = self.abf_XP_texAb(gid_Obj)
        bp_ausglFlae = self.abf_ausglFlae(gid_Obj)
        bp_ausglFlae_mas = self.abf_ausglFlae_mas(gid_Obj)
        bp_anpfBindErh = self.abf_anpfBindErh(gid_Obj)
        bp_anpfBindErh_geg = self.abf_anpfBindErh_geg(gid_Obj)
        bp_schPfEntw = self.abf_schPfEntw(gid_Obj)
        bp_schPfEntw_mas = self.abf_schPfEntw_mas(gid_Obj)
        bp_speFlae = self.abf_speFlae(gid_Obj)
        bp_speFlae_mas = self.abf_speFlae_mas(gid_Obj)
        bp_ausglFlMas = self.abf_ausglFlMas(gid_Obj)
        bp_ausglFlMas_mas = self.abf_ausglFlMas_mas(gid_Obj)
        bp_larmKonGebi = self.abf_larmKonGebi(gid_Obj)
        bp_laermK = self. abf_laermKonti(bp_obj[1])
        bp_zusKo = self.abf_zusKonti(bp_obj[2])
        bp_zusKo_bpObj = self.abf_bpObj(bp_obj[2])
        bp_richtSekt = self.abf_richtSekt(bp_obj[2])
        bp_zusKonFlae = self.abf_zusKontiFlae(gid_Obj)
        bp_zusKonFlae_bp_obj = []
        if len(bp_zusKonFlae)>0:
            bp_zusKonFlae_bp_obj = self.abf_bpObj(bp_zusKonFlae[0][3])
        bp_richSekGre = self.abf_richSekGre(gid_Obj)

        bp_festBaug=self.abf_festBaug(gid_Obj)

        bp_strVerkFlae = self.abf_strVerkF(gid_Obj)
        bp_strbegrLin = self.abf_strbegrLin(gid_Obj)

        # Schreiben des GML-Abschnitts 
        tab = 4
        strVerkF = '\t<gml:featureMember>\n'
        strVerkF += '\t\t<xplan:BP_StrassenVerkehrsFlaeche gml:id="GML_'+ xp_obj[9] +'">\n'

        # XP_Objekt
        strVerkF += self.exp_XPobj_GML(tab, xp_obj, xp_obj_hoe, xp_obj_extRef, xp_gehoertZuBereich, xp_dargDurch, xp_begrAbschnitt)

        # BP_Objekt 
        strVerkF += self.exp_BPobj_GML(tab, bp_obj, bp_refText,xp_refTex, bp_ausglFlae, bp_ausglFlae_mas, bp_anpfBindErh, bp_anpfBindErh_geg, bp_schPfEntw, bp_schPfEntw_mas, bp_speFlae, bp_speFlae_mas, bp_ausglFlMas, bp_ausglFlMas_mas, bp_larmKonGebi, bp_zusKo, bp_zusKo_bpObj, bp_richtSekt, bp_zusKonFlae, bp_zusKonFlae_bp_obj ,bp_richSekGre, bp_laermK)

        # BP_Flaechenobjekt
        strVerkF += self.exp_BP_flae_GML(bp_strVerkFlae)
        
        ###
        # BP_FestsetzungenBaugebiet
        strVerkF += self.exp_BP_festseBaugebiet_gml(bp_festBaug)

        if len(bp_strVerkFlae)>0 and str(bp_strVerkFlae[0][2])!="NULL":
            strVerkF +="\t\t\t<xplan:nutzungsform>"+ str(bp_strVerkFlae[0][2]) +"</xplan:nutzungsform>\n"
        # begrenzungslinie
        '''if len(bp_strbegrLin)>0:
            for strBL in bp_strbegrLin:
                strVerkF += '\t\t\t<xplan:begrenzungslinie>\n'
                strVerkF += self.exp_strbegrLin(tab, strBL)
                strVerkF += '\t\t\t</xplan:begrenzungslinie>\n' '''
        # Ende des Abschnitts
        strVerkF += '\t\t</xplan:BP_StrassenVerkehrsFlaeche>\n'
        strVerkF += '\t</gml:featureMember>\n' 
        return strVerkF

    # BP_StrassenbegrenzungsLinie !!!!!bearbeiten!!!!!!
    def exp_strbegrLin(self, tab, strBeLi):
        st = tab * str("\t") +"<xplan:BP_StrassenbegrenzungsLinie>\n"
        if str(strBeLi[0]) != "NULL":
            st += (tab+1) * str("\t") +"<xplan:position>\n"
            st += (tab+2) * str("\t") + str(strBeLi[0]) + "\n" # --> GML_Geometrie exp_gmlGeometrie
            # st += self.exp_gmlGeometrie(tab+3, strBeLi[0])
            st += (tab+1) * str("\t") +"</xplan:position>\n"
        if str(strBeLi[1]) != "NULL":
            st +=(tab+1) * str("\t") +"<xplan:bautiefe>"+ str(strBeLi[1]) +"</xplan:bautiefe>\n"
        st += tab * str("\t") +"</xplan:BP_StrassenbegrenzungsLinie>\n"
        return st
    
    # XP_AbstraktesPraesentationsobjekt
    def exp_APO(self, apo):

        # Abfragen Daten
        apo_Dar = self.abf_apoDarst(apo[0])
        gml_id = self.abf_gmlIDBereich_APO(apo[4])
        ref_XPobj = self.abf_ref_XPobj(apo_Dar[0])
         # GML-Daten
        apo = '\t<gml:featureMember>\n'
        apo += '\t\t<xplan:XP_AbstraktesPraesentationsobjekt>\n'

        if str(apo[1])!="NULL":
            apo += '\t\t\t<xplan:stylesheetId>'+ str(apo[1]) +'</xplan:stylesheetId>'
        if str(apo[2])!="NULL":
            apo += '\t\t\t<xplan:darstellungsprioritaet>'+ str(apo[2]) +'</xplan:darstellungsprioritaet>'
        if str(apo_Dar[1])!="NULL":
            apo += '\t\t\t<xplan:art>'+ str(apo_Dar[1]) +'</xplan:art>'
        if str(apo_Dar[2])!="NULL":
            apo += '\t\t\t<xplan:index>'+ str(apo_Dar[2]) +'</xplan:index>'
        if str(gml_id)!="NULL":
            apo +='\t\t\t<xplan:gehoertZuBereich xlink:href="#GML_'+ str(gml_id) + '" />\n'
        if str(ref_XPobj)!="NULL":
            apo +='\t\t\t<xplan:dientZurDarstellungVon xlink:href="#GML_'+ str(ref_XPobj) + '" />\n'

        apo += '\t\t</xplan:XP_AbstraktesPraesentationsobjekt>\n'
        apo += '\t</gml:featureMember>\n'
        return apo

    # GML-Geometrien Ausgabe
    def exp_gmlGeometrie(self, tab, geom):
        # Bestandteile der Geometrie für die GML-Daten aus der GeoJSON Filtern
        geom_json = json.loads(geom)
        geom_bestand = self.geom_Best(geom_json)
        gml_geom = ""
        # GML-Geometrie Point
        if geom_bestand[0] == "Point":
            gml_geom = tab * str("\t") +'<gml:'+geom_bestand[0] + ' srsName="'+ self.epsg +'" gml:id="GML_'+ str(uuid.uuid1()) +'">\n'
            gml_geom += (tab+1) * str("\t") + '<gml:pos>'+ geom_bestand[6] +'</gml:pos>\n'
            gml_geom += tab * str("\t") + '</gml:Point>\n'
        # GML-Geometrie Linie
        
        # GML-Geometrie Polygon
        elif geom_bestand[0] == "Polygon":
            gml_geom = tab * str("\t") +'<gml:'+geom_bestand[0] + ' srsName="'+ self.epsg +'" gml:id="GML_'+ str(uuid.uuid1()) +'">\n'
            gml_geom += (tab+1) * str("\t") +'<gml:exterior>\n'
            gml_geom += (tab+2) * str("\t") +'<gml:LinearRing>\n'
            gml_geom += (tab+2) * str("\t") + '<gml:posList srsDimension="' + str(geom_bestand[1]) +'" count="'+ str(geom_bestand[3]) +'">'+ geom_bestand[2] +'</gml:posList>\n'
            gml_geom += (tab+2) * str("\t") +'</gml:LinearRing>\n'
            gml_geom += (tab+1) * str("\t") +'</gml:exterior>\n'
            # Sind Innenhüllen vorhanden?
            if len(geom_bestand[4]) > 0:
                for ior, ior_anz in zip(geom_bestand[4], geom_bestand[5]):
                    gml_geom += (tab+1) * str("\t") +'<gml:exterior>\n'
                    gml_geom += (tab+2) * str("\t") +'<gml:LinearRing>\n'
                    gml_geom += (tab+2) * str("\t") + '<gml:posList srsDimension="' + str(geom_bestand[1]) +'" count="'+ str(ior_anz) +'">'+ ior +'</gml:posList>\n'
                    gml_geom += (tab+2) * str("\t") +'</gml:LinearRing>\n'
                    gml_geom += (tab+1) * str("\t") +'</gml:exterior>\n'
            gml_geom += tab * str("\t") +'</gml:'+geom_bestand[0] +'>\n'
        
        return gml_geom
    
    # Bestandteile aus der Geometrie für GML aus GeoJSON ausarbeiten
    def geom_Best(self, geom):
        geotyp = ""
        dim = 0
        exterior = ""
        ex_len = ""
        interior = []
        in_len = []
        pointKoor = ""

        # Bestimmung des Geometrie-Typs
        if geom["type"]=="MultiPolygon" or geom["type"]=="Polygon":
            geotyp = "Polygon"
            dim = len(geom["coordinates"][0][0][0])
            # Geometrie-Koordinaten Außenhülle
            # Hier könnten auch noch mehrere Polygone vorliegen / Fall wird nicht betrachtet
            for poly in geom["coordinates"]:
                for koorList in poly:
                    # Länge mit übergeben!!!
                    ex_len= len(koorList)
                    
                    for koor in koorList:
                        exterior_koor = ""
                        for einzKo in koor:
                            exterior_koor += str(einzKo) + " "
                        exterior = exterior_koor + exterior
                # Abfrage der innernen Hüllen
                
                if len(poly) > 1:
                    i = 1
                    while len(poly) > i:
                        in_len.append(str(len(poly[i])))
                        koor_in = ""
                        for koor in poly[i]:
                            ior_ko = ""
                            for einzKoor in koor:
                                ior_ko += str(einzKoor) + " "
                            koor_in = ior_ko + koor_in
                        interior.append(koor_in)
                        i += 1
        if geom["type"]=="MultiPoint" or geom["type"]=="Point":
            geotyp = "Point"
            pointKoor = str(geom["coordinates"][0][0]) + " " + str(geom["coordinates"][0][1])

        return [geotyp, dim, exterior, ex_len, interior, in_len, pointKoor]
    
    

    # Hilfsfunktion zum Debuggen
    def debug(self, msg):
        qgis.core.QgsMessageLog.logMessage("Debug" + "\n" + msg,  "XPlanung")
    
    def showQueryError(self, query):
        self.tools.showQueryError(query)
