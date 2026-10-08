# quelonio -- structure spec (data input for recetas/asset_spec.py)

Every value is copied from DungeonParty-A/game/docs/art/_references/turtle/_synthesis.md
(lines 195-242, "ESTRUCTURA -- plano, angulo y limite por parte movil"); the line
of the source row is in the Limite or Angulo cell as [s:LINE]. `tail` has NO row on
purpose: the synthesis has no structural data for it, so the gate reports it as
not researched instead of letting it be invented.

## STRUCTURE

| Parte | Plano | Angulo | Limite |
|---|---|---|---|
| humerus_L | horizontal, sale hacia AFUERA del caparazon [s:212] | pitch -13 a -2 deg al apoyar; yaw +40 deg adelante-afuera [s:214,218] | la abertura anterior limita la retraccion: puente carapacho-plastron [s:232] |
| humerus_R | horizontal, sale hacia AFUERA del caparazon [s:212] | pitch -13 a -2 deg al apoyar; yaw +40 deg adelante-afuera [s:214,218] | la abertura anterior limita la retraccion: puente carapacho-plastron [s:232] |
| forearm_L | vertical, baja al suelo [s:213] | codo 62-74 deg sobre la horizontal en protraccion, 147-149 deg en retraccion [s:215] | el codo debe quedar FUERA del borde del caparazon (CREATION_PROTOCOL 2d) |
| forearm_R | vertical, baja al suelo [s:213] | codo 62-74 deg sobre la horizontal en protraccion, 147-149 deg en retraccion [s:215] | el codo debe quedar FUERA del borde del caparazon (CREATION_PROTOCOL 2d) |
| neck | vertical, S en el plano sagital (criptodiro) [s:241] | se pliega en S, no se escala [s:195] | el caparazon es hueso: el cuello se retrae dentro, no deforma el caparazon |
| head | vertical (retraccion del cuello) [s:241] | cuña con hocico preorbital angulado, NO esfera [s:240] | linea de mandibula marcada, boca como corte horizontal [s:242] |
