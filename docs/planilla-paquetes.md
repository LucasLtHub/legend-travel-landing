# Cómo completar la planilla de paquetes

La planilla es el archivo **`data/paquetes-completar.csv`**. Tiene una fila por cada paquete que está publicado en la web. Sirve para sumar los datos que hoy faltan: precios por base, hoteles, vuelos, datos del crucero y la foto de portada.

## Abrirla

- Hacé doble clic en el archivo y se abre en Excel.
- Cada columna es un dato. La primera fila tiene el nombre de cada columna.
- Las columnas **id** y **titulo** sirven para saber qué paquete es cada fila. **No cambies el id.**

## La regla más importante

**Si no tenés un dato, dejá la celda vacía.**

- No escribas "a confirmar", "consultar", "-" ni nada parecido. La planilla los rechaza.
- Una celda vacía nunca borra lo que ya está cargado: el dato anterior queda como estaba.
- En la web solo se muestra lo que está completo. Si un paquete no tiene hoteles, la sección de hoteles directamente no aparece.

## Qué va en cada columna

### Precios

Los precios son **por persona** y se escriben **solo con números**, sin puntos ni signos.

| Columna | Qué poner | Ejemplo |
|---|---|---|
| moneda | USD, ARS o EUR | USD |
| precio_single | Precio para una persona sola en la habitación | 3660 |
| precio_doble | Precio por persona en habitación doble | 2490 |
| precio_triple | Precio por persona en habitación triple | 2350 |
| precio_cuadruple | Precio por persona en habitación cuádruple | 2300 |

- El precio grande que se ve en la web es siempre el **doble**, con la leyenda "por persona en base doble". Si un paquete no tiene precio doble, no se puede destacar como corresponde: avisá para cargarlo.
- Si dejás vacía una base, esa fila no aparece en la tabla de precios del paquete.

**Cruceros.** En los cruceros el precio depende de la cabina. Por eso hay hasta 4 cabinas: cabina1, cabina2, cabina3 y cabina4. Cada una tiene estas columnas:

- **cabina1_tipo:** el tipo de cabina, por ejemplo "Interna", "Externa" o "Con balcón".
- **cabina1_precio_single**, **cabina1_precio_doble**, **cabina1_precio_triple** y **cabina1_precio_cuadruple:** el precio de esa cabina en cada base.

Cargá primero la cabina más económica. En los paquetes que no son cruceros, las columnas de cabina quedan vacías.

### Hoteles

Hay lugar para 12 hoteles por paquete: hotel1, hotel2, y así hasta hotel12. Cada uno tiene:

| Columna | Qué poner | Ejemplo |
|---|---|---|
| hotel1_ciudad | Ciudad o zona del hotel | Bariloche |
| hotel1_nombre | Nombre del hotel | Huinid Pioneros Hotel |
| hotel1_categoria | Estrellas: el número solo, o "4 Sup" si es superior | 4 |
| hotel1_noches | Cuántas noches se duerme ahí, solo el número | 3 |
| hotel1_regimen | Régimen de comidas en ese hotel | All Inclusive |
| hotel1_habitacion | Tipo de habitación | Habitación estándar |
| hotel1_web | Página oficial del hotel, completa | https://www.hotel.com |
| hotel1_foto_credito | De quién es la foto del hotel o quién la cedió. Sin este dato la foto no se muestra. Ver `docs/fotos-hoteles.md` | HM Hotels |

- Cargá los hoteles en el orden del viaje.
- Si un hotel tiene datos, tiene que tener nombre.
- La página web tiene que empezar con https://. Copiala desde la barra del navegador.

### Vuelos

Hay lugar para 4 vuelos: vuelo1, vuelo2, vuelo3 y vuelo4. Cada uno tiene:

| Columna | Qué poner | Ejemplo |
|---|---|---|
| vuelo1_aerolinea | Aerolínea | LATAM |
| vuelo1_ruta | Tramo | Buenos Aires – Punta Cana |
| vuelo1_clase | Clase | Económica |
| vuelo1_fecha | Fecha del vuelo | 15/01/2027 |
| vuelo1_horario | Horario de salida y llegada | 08:40 – 16:10 |
| vuelo1_numero | Número de vuelo | LA 8126 |
| vuelo1_equipaje | Equipaje incluido | 1 valija de 23 kg + equipaje de mano |

### Crucero (solo para cruceros)

| Columna | Qué poner | Ejemplo |
|---|---|---|
| crucero_naviera | Compañía del crucero | Costa Cruceros |
| crucero_barco | Nombre del barco | Costa Diadema |
| crucero_cabina | Tipos de cabina disponibles | Interna, externa o con balcón |
| crucero_bebidas | "Sí", "No" o el detalle | En almuerzo y cena |
| crucero_propinas | "Sí", "No" o el detalle | Sí |
| crucero_wifi | "Sí", "No" o el detalle | No |
| crucero_asistencia | Asistencia al viajero: "Sí", "No" o el nombre | Universal Assistance |
| crucero_web | Página oficial de la naviera, completa | https://www.naviera.com |

"Sí" se muestra en la web como "Incluido", y "No" como "No incluido".

### Regiones secundarias
Columna `regiones_extra` (opcional, separadas por coma): regiones donde el paquete también tiene que aparecer en la madre y en los relacionados, además de la suya. Ejemplo: Egipto & Jordania es de África y lleva `medio-oriente`. La región principal no cambia (URL, etiqueta y chips siguen igual).

### Sigla del operador
Columna `operador_sigla`: dos letras (KM = King Midas, JT = Julia Tours, CC = Cuarto Continente, PI = Piamonte).
Sirve para la planilla de revisión y para saber de dónde salió cada paquete.
Es interna, como `operador` y `ref`: el operador nunca se muestra al cliente (ni en la página, ni en las cards, ni en el schema, ni en llms).

### Foto de portada

En **foto_portada** va la foto grande de arriba de la página del paquete. Puede ser:

- la ubicación de una foto que ya está en la carpeta del sitio, por ejemplo `assets/img/pexels/2868242-1800.jpg`;
- una dirección web completa de la foto.

En los cruceros, lo ideal es la foto oficial del barco. Si la dejás vacía, se usa la foto que el paquete ya tiene.

## Guardar

En Excel, usá **Archivo → Guardar** y, si pregunta, elegí **mantener el formato CSV**. No lo guardes como .xlsx.

## Pasar la planilla a la web

Esto lo hace quien mantiene la web:

1. `python planilla-paquetes.py importar --probar` revisa la planilla sin guardar nada. Muestra qué cambiaría y qué errores hay.
2. Si hay errores, se corrigen en la planilla y se vuelve al paso 1. Mientras haya un error, no se guarda nada.
3. `python planilla-paquetes.py importar` guarda los datos. Antes guarda una copia del archivo anterior en `data/respaldos/`.
4. `python build-paquetes.py` regenera las páginas.

Para empezar una planilla nueva con lo que ya está cargado: `python planilla-paquetes.py exportar`. **Ojo:** reemplaza la planilla actual.

La planilla y la carpeta `data/` no se publican en la web.
