# Change Log

## [Änderungen seither](https://github.com/bstroebl/xplanplugin/compare/v4.0.0...develop)

### Fixed
- Lies QSettings plattformunabhängig
- Ergänze SVG-Pfad auch wenn er leer ist oder nur ein Element hat
- QGIS3-api Anpassungen

# [4.0.0 - 2019-04-08](https://github.com/bstroebl/xplanplugin/compare/v3.0.0...v4.0.0)

### Added
- Füge Tutorials und Workshopmaterial hinzu

### Changed
- Update Plugin auf QGIS3

### Fixed
- Passe Erzeugung der Nutzungsschablone an geänderte Datenstruktur an
- Berechne raeumlichenGeltungsbereich über gid statt fid
- Berücksichtige, dass Bereiche keine Geometrie brauchen

# [3.0.0 - 2018-08-23](https://github.com/bstroebl/xplanplugin/compare/v2.0.0...v3.0.0)

### Added
- Importfunktion für XPlanGML-Dateien
- Bearbeite XP_ExterneReferenz mit eigenem Dialog

### Fixed
- Verbessere Bereichsmanger: verhindere Einfrieren beim Starten, wenn kein aktiver Bereich gewählt wird.
- Ermögliche automatische Bereichszuordnung auch bei aktivem Filter
- Passe Erzeugen einer externenReferenz an XPlan 5.0 an

# 2.1.0 - 2018-06-07

### Added
- Bereichsmanager: Dialog, mit dem der aktive Bereich verwaltet werden kann. Weiterhin können Bereichsfilter auf Layer angewendet oder entfernt werden.

### Fixed
- Setze korrekten Filter beim Laden von Bereichen
- Lösche Bereichsauswahl falls Dialog erneut geöffnet wird
- Ordne Präsentationsobjekte einem Bereich zu
- Filtere auch Präsentationsobjekte nach aktivem Bereich

# 2.0.0 - 2018-03-20

### Added
- Lade Standardstil ohne Nachfrage, wenn er der einzige Stil ist
- Implementiere XPlan 5.0 (passe an geänderte Datenbankstrukturen an)
- Erhalte Zustand des Bereichsauswahldialogs

### Fixed
- Nutze authcfg (falls eingestellt) zum Laden von Objektklassen
- Ordne neue Objekte bereits geladener Layer dem aktiven Bereich zu
- Fange Relationsnamen mit Umlauten o.ä. ab
- ordne neue Features automatische den aktiven Bereichen zu

# 1.2.0 - 2017-08-11

### Added
- Nutzungsschablone wird über einen Dialog definiert und durch Klick in eine BP_BaugebietsTeilFlaeche erzeugt
- Weise Präsentationsobjekte beim Digitalisieren dem aktiven Bereich zu
- Deaktiviere Menüpunkt "Aktive Bereiche löschen", wenn kein Bereich aktiv ist
- Prüfe beim Initialisieren, ob es sich um einen XP-Layer und nicht um einen _qv-View handelt
- Lese den Typ (Punkt/Linie/Fläche) der Objektart aus dem Objekte-View eines Fachschemas aus
- Lade das Bereichsobjekt selbst mit bei "Bereich laden"
- Ermögliche die Bearbeitung der Stylesheetparameter aus QGIS heraus
- Empfehle Neustart nach Wechsel der DB
- Lade Flächenschlussobjekte als unterstes in den Bereich
- Ermögliche Bereichsfilter auf beliebiege Objektklassen
- Neue SVG-Dateien

### Changed
- Modularisiere Erzeugung der Bereichsfilter

### Fixed
- Bereichszuordnung von Objekten auf neue Bereichsnamen angepasst
- Stelle Auswahl sicher, dass eine Auswahl exisitert
- Stelle sicher, dass Geometrien hinzugefügt wurden
- Gebe Nutzerausgaben aus, bei Bereichszuordnung
- Beseitige Laufzeitfehler
- Ermögliche Bereichszuordnung auch für Punktobjekte
- Entlade SO-Menü beim Entladen des Plugins

# 1.1.0 - 2017-02-27

### Added
- Laden eines Bereichs: Lädt auch nachrichtliche und Präsentationsobjekte und wendet passenden Stil an

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

