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
 This script initializes the plugin, making it known to QGIS.
"""
def name():
  return u"FS XPlanung"
def description():
  return u"Fachschale für XPlanung"
def version():
  return "Version 0.1"
def qgisMinimumVersion():
  return "1.6"
def classFactory(iface):
  from XPlan import XPlan
  return XPlan(iface, 'xplanung')
def icon(): # new QGIS 1.7
    return "tools/icons/logo_xplanung.png"

