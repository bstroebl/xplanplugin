# Change Log

## [Unreleased](https://gitlab.jena.de/Fachschale/XPlanung/compare/v1.0.0...develop)

# 1.0.0 - 2016-06-22
### Added
- Laden einer Objektart: zusätzlich zur PostGIS-Tabelle als editierbarem Layer wird optional ein View zur Darstellung geladen; er enthält alle benötigten joins. Der editierbare Layer enthält aus Performancegründen keine Joins mehr. Joins mussten zuletzt mit *Memory cache* ausgeführt werden, damit QGIS nicht mehr einfriert, weil ewig auf DB-Abfragen gewartet wurde. Der Darstellungslayer symbolisiert stets nach dem aktuellen Wert.
- Neuer Stil *einfarbig* zur Darstellung des editierbaren Layers (wird dort per default eingestellt), andere Stile sind verfügbar (insbesondere zur Bearbeitung derselben), ihre Anwendung auf den editierbaren Layer ergibt jedoch i.d.R. keinen Sinn.
- Modellbereich Regionalplan_Kernmodell ansprechbar
- Die SVG-Dateien sind nun Bestandteil des Plugins, der QGIS-SVG-Pfad wird entsprechend ergänzt.

### Changed
- Elterntabellen werden beim Darstellugnslayer nur gejoint, wenn eines ihrer Felder für die Darstellung benötigt wird.
- Ausgaben an den Nutzer werden mit einheitlichen Methoden über die MessageBar ausgegeben.
- Debug-Ausgaben werden über QgsMessageLog ausgegeben.
- Der Layername ist nun nur noch der Tabellenname.

# 0.5.0 - 2016-02-25
### Added
- Funktion getBereichInPlan: gebe gids der Bereiche eines Plans zurück
- Ermögliche gespeicherte Authentifizierung (ab QGIS 2.12) zur Verbindung mit der XPlan-Datenbank

### Changed
- Funktion getLayerInBereich: gebe Layer für mehrere Bereiche zurück
- Auswahldialog: Klassen umstrukturiert
- Speichern von Layerstilen fragt nun explizit, ob der bestehende Stil überschrieben werden soll

### Fixed
- Zeige Schema und Tabelle in Fehlermeldung
- Initialisiere Plugin vor Speichern eines Stils

## 0.4.0 - 2015-11-9
### Added
- Menüpunkt BPlan: Geltungsbereich eines Plans aus seinen Bereichen errechnen
- Menüpunkt XPlanung: Eine externe Referenz anlegen
- Tool, um einen Iterator über die Features eines Layers (falls eine Selektion exisitert nur über diese) zu erhalten
- Tool, um einen Layer für schema.table zu erhalten, falls er nicht im Projekt ist, wird er geladen

### Changed
- Tool joinLayer verbindet optional nur bestimmte Felder

