# Design Tokens

Die aktive v1-UI nutzt CSS Custom Properties.

## Dateien

- `ui/src/shared/styles/tokens/base.css`: Basis-Tokens und Accessibility-/Density-Overrides
- `ui/src/shared/styles/tokens/theme-*.css`: thematische Varianten
- `ui/src/shared/styles/tokens/aelunor-premium.css`: Dark-Fantasy-Premium-Palette, Wallpaper-URLs, Oberflaechen, Borders, Shadows
- `ui/src/shared/styles/aelunor-premium-layout.css`: aktueller Premium-Layout-Chrome fuer Hub/Play

## Referenzrichtung

- Dunkle, cinematic Hintergruende
- Goldene Linien und dezente magische Akzente
- Pergament-/Buchflaechen fuer Story
- Rechte Kontextspalte fuer Party/Weltstatus
- Klare, nicht ueberladene Controls

## Regeln

- Neue Farben zuerst als Token einfuehren.
- Keine einmaligen Hex-Werte in Komponenten, wenn ein Token existiert.
- Responsive Layouts mit Grid/Flex und stabilen Min/Max-Werten.
- Lesbarkeit vor Atmosphaere.
