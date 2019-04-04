#/***************************************************************************
# xplanung
#                             -------------------
# begin                : 2012-03-01
# copyright            : (C) 2012 by Bernhard Stroebl, KIJ/DV
# email                : bernhard.stroebl@jena.de
#
#/***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# ***************************************************************************/

# Makefile for a PyQGIS plugin

PLUGINNAME = xplanung

PY_FILES = XPlan.py XPlanDialog.py __init__.py HandleDb.py XPTools.py XPImport.py

EXTRAS = tools/icons/logo_xplanung.png metadata.txt license.txt

DIRS = schema svg

UI_FILES = Ui_Bereichsauswahl.ui Ui_conf.ui Ui_ObjektartLaden.ui Ui_Stilauswahl.ui Ui_Nutzungsschablone.ui Ui_Bereichsmanager.ui Ui_Referenzmanager.ui Ui_Import.ui

QGISDIR=.local/share/QGIS/QGIS3/profiles/default

default: deploy

deploy:
	@echo
	@echo "------------------------------------------"
	@echo "Deploying plugin to your .qgis3 directory."
	@echo "------------------------------------------"
	# The deploy  target only works on unix like operating system where
	# the Python plugin directory is located at:
	# $HOME/$(QGISDIR)/python/plugins
	mkdir -p $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)
	cp -vf $(PY_FILES) $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)
	cp -vf $(EXTRAS) $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)
	cp -vfr $(DIRS) $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)

# The dclean target removes compiled python files from plugin directory
dclean:
	find $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME) -iname "*.pyc" -delete

# The derase deletes deployed plugin
derase:
	@echo
	@echo "-------------------------"
	@echo "Removing deployed plugin."
	@echo "-------------------------"
	rm -Rf $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)

# The zip target deploys the plugin and creates a zip file with the deployed
# content. You can then upload the zip file on http://plugins.qgis.org
zip: deploy dclean
	rm -f $(PLUGINNAME).zip
	cd $(HOME)/$(QGISDIR)/python/plugins; zip -9r $(CURDIR)/$(PLUGINNAME).zip $(PLUGINNAME)

# Create a zip package of the plugin named $(PLUGINNAME).zip.
# This requires use of git (your plugin development directory must be a
# git repository).
# To use, pass a valid commit or tag as follows:
#   make package VERSION=Version_0.3.2
package:
		rm -f $(PLUGINNAME).zip
		git archive --prefix=$(PLUGINNAME)/ -o $(PLUGINNAME).zip $(VERSION)
		echo "Created package: $(PLUGINNAME).zip"

