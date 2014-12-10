#/***************************************************************************
# radwege
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

PY_FILES = XPlan.py XPlanDialog.py __init__.py HandleDb.py XPTools.py

EXTRAS = tools/icons/logo_xplanung.png

METADATA = metadata.txt

UI_FILES = Ui_Bereichsauswahl.py Ui_conf.py

#RESOURCE_FILES = tools/resources_rc.py

default: compile

#compile: $(UI_FILES) $(RESOURCE_FILES)
compile: $(UI_FILES)

#%_rc.py : %.qrc
#	pyrcc4 -o $@  $<

%.py : %.ui
	pyuic4 -o $@ $<

# The deploy target only works on unix like operating system where
# the Python plugin directory is located at:
# $HOME/.qgis/python/plugins
deploy: compile
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)/tools
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)/tools/icons
	cp -vf $(PY_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(METADATA) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	#cp -vf $(RESOURCE_FILES) $(HOME)/.qgis/python/plugins/$(PLUGINNAME)/tools
	cp -vf $(EXTRAS) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)/tools/icons

# The dclean target removes compiled python files from plugin directory
dclean:
	find $(HOME)/.qgis2/python/plugins/$(PLUGINNAME) -iname "*.pyc" -delete

# The zip target deploys the plugin and creates a zip file with the deployed
# content. You can then upload the zip file on http://plugins.qgis.org
zip: deploy dclean
	rm -f $(PLUGINNAME).zip
	cd $(HOME)/.qgis2/python/plugins; zip -9r $(CURDIR)/$(PLUGINNAME).zip $(PLUGINNAME)

# Create a zip package of the plugin named $(PLUGINNAME).zip.
# This requires use of git (your plugin development directory must be a
# git repository).
# To use, pass a valid commit or tag as follows:
#   make package VERSION=Version_0.3.2
package: compile
		rm -f $(PLUGINNAME).zip
		git archive --prefix=$(PLUGINNAME)/ -o $(PLUGINNAME).zip $(VERSION)
		echo "Created package: $(PLUGINNAME).zip"

