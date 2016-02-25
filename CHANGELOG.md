# Change Log

## [Unreleased](https://gitlab.jena.de/Fachschale/XPlanung/compare/master...develop)

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

