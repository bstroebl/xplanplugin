This QGIS plugin allows interaction between QGIS and the [XPlan-PostGIS project](https://github.com/bstroebl/xplanPostGIS). XPlanung is a German standard for spatial planning data. It thus addresses German speaking users, all further information is therefore given in German.

# Einführung
XPlanung ist ein Standard für den Datenaustausch von Bauleitplänen, Raumordnungsplänen und Landschaftsplänen. Weitere Informationen gibt es auf der [Homepage des XPlanungsprojekts](http://www.xplanungwiki.de). Das xplanung-QGIS-Plugin ermöglicht die Bearbeitung und Anzeige von Daten, die in einer xplan-PostGIS-Datenbank liegen. Dieses Repository enthält die _Quelldateien_ des Plugins, nicht das Plugin selbst.

# Voraussetzungen
## Datenbank
Es muß eine PostGIS-Datenbank vorhanden sein, in die Schemas des [XPlan-PostGIS-Projektes](https://github.com/bstroebl/xplanPostGIS)) eingeladen wurden. 

## Plugin DataDrivenInputMask
Zur Anzeige und zum Editieren von Sachdaten ist das Plugin [DataDrivenInputMask](http://plugins.qgis.org/plugins/DataDrivenInputMask/) aus dem offiziellen Plugin Repository zu installieren.

# Installation
Um aus den Quelldateien ein lauffähiges Plugin zu erzeugen, sind die ui-Dateien zu kompilieren (dafür muß `pyuic4` installiert sein) und die zum Plugin gehörenden Dateien in ein Verzeichnis zu verschieben, in dem QGIS nach Plugins sucht.
## Installation mit make
Ist `make` installiert, können beide Schritte mit `make deploy` ausgeführt werden.
## Händische Installation
Alternativ können die *.ui-Dateien mit `pyuic4` selbst kompiliert werden. Sodann müssen alle zum Plugin gehörenden Dateien in ein Unterverzeichnis des Verzeichnisses verschoben werden, in dem QGIS nach Plugins sucht. Dies ist üblicherweise (für QGIS2) `$HOME/.qgis2/python/plugins`.
