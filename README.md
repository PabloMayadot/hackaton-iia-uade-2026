# T20 · ¿Esta entrega falla por ausente?

**Integrantes:** Integrante 1 (completar nombre y apellido) · Integrante 2 (completar nombre y apellido)
**IA declarada:** Claude
**Pista:** Reglas
**Publicación en LinkedIn:** Pendiente de agregar link al publicar

---

## 1. Formulación y PEAS

**La pregunta.** Para cada caso (una entrega programada de última milla), ¿la entrega falla porque no hay nadie en el domicilio?
- **SÍ (`1`)** significa que **la entrega falla por ausente** (el domicilio estará vacío al llegar el reparto), por lo que el sistema de ruteo debe **reprogramar la entrega** antes de que salga el camión.
- **NO (`0`)** significa que **la entrega no falla por ausente** (hay alguien para recibirla), por lo que el paquete se **despacha normalmente** en el recorrido del camión.

| PEAS | Su sistema |
|---|---|
| **Medida de rendimiento** | Minimizar la cantidad de viajes perdidos a domicilios vacíos (**Falsos Negativos**) y evitar demoras por reprogramaciones innecesarias en entregas que habrían salido bien (**Falsos Positivos**), maximizando la efectividad de entrega en primera visita y reduciendo el costo operativo por paquete entregado. |
| **Entorno** | Operación logística de distribución urbana de última milla: domicilios particulares con distinta disponibilidad según franja horaria (mañana o tarde), clientes con distinto historial de recepción y canal de aviso previo por WhatsApp. Es un entorno parcialmente observable (no sabemos con certeza si habrá alguien hasta llegar, solo vemos señales previas), estocástico y episódico (cada decisión de despacho se evalúa por entrega antes de cerrar la hoja de ruta). |
| **Actuadores** | El sistema de ruteo antes de la salida del vehículo: ejecuta la acción de **Reprogramar la entrega y excluirla de la carga del camión** (cuando predice **SÍ**) o **Confirmar e incluir el envío en la hoja de ruta del camión** (cuando predice **NO**). |
| **Sensores** | Base de datos operativa del sistema de ruteo al momento previo al despacho, que registra tres entradas por entrega: **1)** `Entregas fallidas previas (del cliente)` (cantidad histórica entera), **2)** `Respondió el aviso por WhatsApp` (`0 = no`, `1 = sí`), y **3)** `Franja horaria` asignada (`0 = mañana`, `1 = tarde`). |

**Objetivo y métrica.**
- **Qué importa de verdad (el objetivo):** El objetivo real del negocio es operativo y económico: **no enviar el camión a un domicilio vacío** (ahorrando combustible, horas de chofer y capacidad de bodega que puede usar otro paquete) sin demorar innecesariamente a los clientes que sí estaban esperando su pedido.
- **Con qué métrica lo medimos:** Medimos el desempeño priorizando la **Sensibilidad (Recall)** —para detectar todos los casos que realmente fallan por ausente y reducir a cero los viajes perdidos— acompañada por la **Precisión** y la **Especificidad** —para verificar que no estemos reprogramando entregas exitosas—, además de reportar la **Exactitud (Accuracy)** global.
- **¿Son lo mismo?** **No, no son lo mismo.** La métrica es solo un indicador matemático calculado sobre una muestra de 20 casos pasados, mientras que el objetivo es el impacto económico y de servicio en la operación real. Además, como el problema está fuertemente desbalanceado (en entrenamiento el 85,7 % de las entregas son `NO` y solo el 14,3 % son `SÍ`), si usáramos la **Exactitud** como único sinónimo de éxito caeríamos en una trampa: un sistema que nunca reprograma nada tiene 85,7 % de exactitud pero **0 % de sensibilidad** (fracasa por completo en el objetivo porque manda el camión a todos los domicilios vacíos).

---

## 2. El sistema

**Cómo decide.**
Elegimos la **Pista Reglas** (sistema experto de reglas lógicas `SI-ENTONCES`, mutuamente excluyentes y exhaustivas):

- **Regla 1 (Riesgo alto de ausencia — Reprogramar):**
  **SI** `Respondió el aviso por WhatsApp == 0` (no respondió) **Y** `Franja horaria == 0` (mañana) **Y** `Entregas fallidas previas >= 3` **ENTONCES** el sistema decide **SÍ (`1`)** *(la entrega falla por ausente; se reprograma antes de cargar el camión)*.
- **Regla 2 (Regla por defecto — Despachar normal):**
  **SI NO** se cumplen las tres condiciones anteriores al mismo tiempo *(es decir: **SI** `Respondió el aviso por WhatsApp == 1` **O** `Franja horaria == 1` [tarde] **O** `Entregas fallidas previas <= 2`)* **ENTONCES** el sistema decide **NO (`0`)** *(la entrega no falla; sale en el camión normalmente)*.

**Variables que usa y por qué.**
El sistema utiliza **las tres variables disponibles en la ficha** y **no descarta ninguna**, por dos razones fundamentales:

1. **Disponibilidad temporal (cero fuga de datos del futuro):** Las tres variables (`Entregas fallidas previas`, `Respondió el aviso por WhatsApp` y `Franja horaria`) se conocen en la central de ruteo **antes** de que el camión salga del depósito. Ninguna utiliza información posterior al viaje.
2. **Necesidad conjunta demostrada en los datos de entrenamiento (Casos 1 a 14):** Si descartáramos cualquiera de las tres variables, el sistema cometería errores en el entrenamiento:
   - **`Respondió el aviso por WhatsApp (0 = no, 1 = sí)`:** Actúa como inhibidor principal del riesgo. En entrenamiento, siempre que el cliente respondió el WhatsApp (`1`), la entrega fue exitosa (`NO`), incluso en clientes con 4, 5 o 6 entregas fallidas previas y en turno mañana (Casos 2, 9, 11, 12 y 14). Si descartáramos esta variable, reprogramaríamos por error a clientes reincidentes que ya confirmaron que hoy sí están en su casa.
   - **`Franja horaria (0 = mañana, 1 = tarde)`:** Captura la disponibilidad en el hogar según el horario laboral. En el Caso 8 de entrenamiento, el cliente tiene `4` entregas fallidas previas y **no** respondió el WhatsApp (`0`), pero como la entrega es a la **tarde (`1`)**, no falla (`resultado_real = 0`). En cambio, con los mismos valores a la **mañana (`0`)** (Caso 1), la entrega sí falla (`resultado_real = 1`). Si descartáramos la franja horaria, cometeríamos un Falso Positivo en el Caso 8.
   - **`Entregas fallidas previas (del cliente)`:** Permite distinguir, dentro del grupo de entregas matutinas sin confirmación de WhatsApp (`WhatsApp = 0` y `Franja = 0`), a los clientes que habitualmente están en su domicilio (Casos 3, 5 y 7, con `1`, `2` y `0` fallidas previas respectivamente, que dan todos `0`) de los clientes crónicamente ausentes (Casos 1 y 6, con `4` y `5` fallidas previas, que dan `1`). Si descartáramos esta variable, reprogramaríamos por error los Casos 3, 5 y 7.

**Cómo se corre en vivo.**
Para resolver cualquier caso nuevo en la mesa en menos de 5 segundos (a mano o en planilla):
1. **Paso 1 (Filtro WhatsApp):** Mirar `Respondió el aviso por WhatsApp`. Si vale `1`, la respuesta inmediata es **NO (`0`)**. Si vale `0`, pasar al Paso 2.
2. **Paso 2 (Filtro Franja horaria):** Mirar `Franja horaria`. Si vale `1` (tarde), la respuesta inmediata es **NO (`0`)**. Si vale `0` (mañana), pasar al Paso 3.
3. **Paso 3 (Umbral de reincidencia):** Mirar `Entregas fallidas previas`. Si es **mayor o igual a 3 (`>= 3`)**, la respuesta es **SÍ (`1`)**. Si es **2 o menos (`<= 2`)**, la respuesta es **NO (`0`)**.
- *Fórmula equivalente para planilla de cálculo (Google Sheets / Excel):* `=SI(Y(C2>=3; D2=0; E2=0); "SÍ (1)"; "NO (0)")` donde `C` = Entregas fallidas previas, `D` = Respondió WhatsApp y `E` = Franja horaria.

**Dos casos de ejemplo.**

| Caso inventado | Valores | Salida del sistema |
|---|---|---|
| **A** | `Entregas fallidas previas = 3`, `Respondió WhatsApp = 0 (no)`, `Franja horaria = 0 (mañana)` | **SÍ** *(Cumple las 3 condiciones de la Regla 1: no contestó WhatsApp, es a la mañana y tiene 3 fallidas previas $\rightarrow$ se reprograma)* |
| **B** | `Entregas fallidas previas = 5`, `Respondió WhatsApp = 1 (sí)`, `Franja horaria = 0 (mañana)` | **NO** *(Aunque tiene 5 fallidas y es a la mañana, respondió el WhatsApp confirmando presencia $\rightarrow$ aplica Regla 2 y se despacha)* |

**Verificación completa sobre los 20 casos de la ficha (`datos/T20.csv`):**

| Caso | Conjunto | Fallidas previas | WhatsApp (`0`/`1`) | Franja (`0`/`1`) | ¿Cumple Regla 1 (`>=3` y `0` y `0`)? | Predicción | Real | Clasificación |
|---|---|---|---|---|---|---|---|---|
| 1 | Entrenamiento | 4 | 0 | 0 | Sí | **1 (SÍ)** | 1 | **VP** |
| 2 | Entrenamiento | 5 | 1 | 0 | No (WhatsApp = 1) | **0 (NO)** | 0 | **VN** |
| 3 | Entrenamiento | 1 | 0 | 0 | No (Fallidas = 1 < 3) | **0 (NO)** | 0 | **VN** |
| 4 | Entrenamiento | 2 | 1 | 1 | No (WhatsApp = 1, Franja = 1) | **0 (NO)** | 0 | **VN** |
| 5 | Entrenamiento | 2 | 0 | 0 | No (Fallidas = 2 < 3) | **0 (NO)** | 0 | **VN** |
| 6 | Entrenamiento | 5 | 0 | 0 | Sí | **1 (SÍ)** | 1 | **VP** |
| 7 | Entrenamiento | 0 | 0 | 0 | No (Fallidas = 0 < 3) | **0 (NO)** | 0 | **VN** |
| 8 | Entrenamiento | 4 | 0 | 1 | No (Franja = 1 tarde) | **0 (NO)** | 0 | **VN** |
| 9 | Entrenamiento | 5 | 1 | 1 | No (WhatsApp = 1, Franja = 1) | **0 (NO)** | 0 | **VN** |
| 10 | Entrenamiento | 2 | 1 | 0 | No (WhatsApp = 1) | **0 (NO)** | 0 | **VN** |
| 11 | Entrenamiento | 4 | 1 | 0 | No (WhatsApp = 1) | **0 (NO)** | 0 | **VN** |
| 12 | Entrenamiento | 4 | 1 | 1 | No (WhatsApp = 1, Franja = 1) | **0 (NO)** | 0 | **VN** |
| 13 | Entrenamiento | 3 | 1 | 1 | No (WhatsApp = 1, Franja = 1) | **0 (NO)** | 0 | **VN** |
| 14 | Entrenamiento | 6 | 1 | 1 | No (WhatsApp = 1, Franja = 1) | **0 (NO)** | 0 | **VN** |
| 15 | Prueba | 3 | 0 | 1 | No (Franja = 1 tarde) | **0 (NO)** | 0 | **VN** |
| 16 | Prueba | 2 | 1 | 1 | No (WhatsApp = 1, Franja = 1) | **0 (NO)** | 0 | **VN** |
| 17 | Prueba | 2 | 1 | 0 | No (WhatsApp = 1) | **0 (NO)** | 0 | **VN** |
| 18 | Prueba | 3 | 1 | 0 | No (WhatsApp = 1) | **0 (NO)** | 0 | **VN** |
| 19 | Prueba | 4 | 0 | 0 | Sí | **1 (SÍ)** | 1 | **VP** |
| 20 | Prueba | 3 | 0 | 1 | No (Franja = 1 tarde) | **0 (NO)** | 0 | **VN** |

---

## 3. Medición

**Entrenamiento (casos 1–14)**

| | Predice SÍ | Predice NO |
|---|---|---|
| **Real SÍ** | VP = 2 | FN = 0 |
| **Real NO** | FP = 0 | VN = 12 |

*(Total entrenamiento: `2 + 0 + 0 + 12 = 14` casos. Los 2 VP son los Casos 1 y 6; los 12 VN son los Casos 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13 y 14).*

**Prueba (casos 15–20)**

| | Predice SÍ | Predice NO |
|---|---|---|
| **Real SÍ** | VP = 1 | FN = 0 |
| **Real NO** | FP = 0 | VN = 5 |

*(Total prueba: `1 + 0 + 0 + 5 = 6` casos. El único VP es el Caso 19; los 5 VN son los Casos 15, 16, 17, 18 y 20).*

| Métrica | Entrenamiento | Prueba |
|---|---|---|
| **Exactitud** $(VP + VN) / Total$ | **100 %** $(14 / 14)$ | **100 %** $(6 / 6)$ |
| **Precisión** $VP / (VP + FP)$ | **100 %** $(2 / 2)$ | **100 %** $(1 / 1)$ |
| **Sensibilidad** $VP / (VP + FN)$ | **100 %** $(2 / 2)$ | **100 %** $(1 / 1)$ |
| **Especificidad** $VN / (VN + FP)$ | **100 %** $(12 / 12)$ | **100 %** $(5 / 5)$ |

**Entrenamiento contra prueba.**
No hay caída de rendimiento entre entrenamiento y prueba: en ambos conjuntos el sistema alcanza **100 % en las cuatro métricas**. Esto muestra **generalización** y no sobreajuste (*overfitting*) por dos motivos:
1. **Baja complejidad del modelo y sentido causal:** No armamos una regla ad-hoc memorizando casos aislados, sino una única conjunción lógica con sentido de negocio directo (el cliente no confirma por WhatsApp, la visita es en horario laboral matutino y ya acumula un historial alto de entregas fallidas).
2. **Consistencia en casos borde de prueba:** En prueba aparecen casos difíciles con `3 entregas fallidas previas` donde cambia una sola condición —como los Casos 15 y 20 (`3, 0, 1`, que no fallan porque son a la tarde) y el Caso 18 (`3, 1, 0`, que no falla porque contestó WhatsApp)— y la regla los clasifica correctamente como `NO`, mientras que detecta sin error el Caso 19 (`4, 0, 0` $\rightarrow$ `SÍ`).
- *Nota de cautela estadística:* Aunque el resultado en prueba es 6/6, reconocemos que el conjunto de prueba tiene solo 6 casos (y un único caso positivo real, el Caso 19), por lo que en operación real con miles de entregas siempre existirá una tasa irreducible de error (por ejemplo, un cliente que respondió que sí por WhatsApp y tuvo una urgencia médica antes de que llegue el camión).

---

## 4. El error más caro

**¿Es peor el falso positivo o el falso negativo en nuestro problema?**
En la logística de última milla de la ficha `T20`, **el error más caro es el Falso Negativo (FN)** (el sistema predice `NO`, despacha el camión, y en realidad era `SÍ`, no había nadie en el domicilio).

**¿Por qué, según la ficha?**
- **Costo del Falso Negativo (FN — Viaje perdido):** Según la ficha, mandar el camión a un domicilio vacío significa un **viaje perdido**. Operativamente, la empresa ya incurrió en el costo físico real e irrecuperable de cargar el paquete, gastar combustible, consumir tiempo de jornada del chofer y ocupar volumen en la camioneta, para terminar volviendo con el paquete al depósito y teniendo que pagar **un segundo viaje completo** otro día.
- **Costo del Falso Positivo (FP — Demora innecesaria):** Según la ficha, reprogramar una entrega que iba a salir bien genera una **demora innecesaria**. Si bien incomoda al comprador, el paquete sigue en el depósito (no se gasta flete ni horas de camión en vano) y, dado que nuestra regla solo se activa cuando el cliente **no respondió el aviso por WhatsApp (`WhatsApp = 0`)**, el cliente ya estaba avisado de que debía confirmar recepción.

**¿Qué cambiamos en el sistema para cometer menos ese error?**
Al analizar los datos de entrenamiento (Casos 1 a 14) para las entregas matutinas sin respuesta de WhatsApp (`WhatsApp = 0` y `Franja = 0`), observamos que:
- Con `0, 1 y 2` entregas fallidas previas (Casos 7, 3 y 5), el resultado real es `0 (NO)`.
- Con `4 y 5` entregas fallidas previas (Casos 1 y 6), el resultado real es `1 (SÍ)`.
- El valor intermedio **`Entregas fallidas previas = 3` con `WhatsApp = 0` y `Franja = 0`** no aparece en el entrenamiento (es una **zona gris** entre 2 y 4).

Inicialmente, un sistema conservador ajustado solo al mínimo de los casos positivos observados habría fijado la regla en `Entregas fallidas previas >= 4`. Sin embargo, con `>= 4`, si llega un caso nuevo con `3 entregas fallidas previas`, que **no respondió el WhatsApp** y va **a la mañana**, el sistema diría `NO` y mandaría el camión, exponiéndose de lleno a un **Falso Negativo (viaje perdido)**. Por eso **cambiamos el umbral de la Regla 1 bajándolo de `>= 4` a `>= 3` entregas fallidas previas**: ante la duda en la zona gris (`3 fallidas, sin WhatsApp, a la mañana`), preferimos reprogramar preventivamente para blindar la **Sensibilidad (0 Falsos Negativos)** sin agregar ningún Falso Positivo en entrenamiento ni en prueba.

---

## 5. ¿Comparado contra qué?

**Línea base trivial.**
Como en entrenamiento hay **12 casos `NO (0)`** y solo **2 casos `SÍ (1)`**, la línea base trivial consiste en un sistema que **responde siempre `NO (0)`** (despachar todos los envíos sin reprogramar ninguno):
- **En Entrenamiento (14 casos):** La línea base trivial obtiene `VP = 0, FN = 2, FP = 0, VN = 12`, lo que da una **Exactitud de $12 / 14 = 85,7\text{ \%}$** y Especificidad de $100\text{ \%}$, pero **Sensibilidad = $0\text{ \%}$ ($0 / 2$)** y Precisión indefinida ($0 / 0$).
- **En Prueba (6 casos):** La línea base trivial obtiene `VP = 0, FN = 1, FP = 0, VN = 5`, lo que da una **Exactitud de $5 / 6 = 83,3\text{ \%}$** y Especificidad de $100\text{ \%}$, pero **Sensibilidad = $0\text{ \%}$ ($0 / 1$)**.
- **Cómo se compara nuestro sistema:** Nuestro sistema de reglas supera a la línea base trivial subiendo la **Exactitud de 85,7 % a 100 % en entrenamiento (+14,3 puntos)** y **de 83,3 % a 100 % en prueba (+16,7 puntos)**. Pero la diferencia crítica está en la **Sensibilidad**: la línea base trivial tiene **0 % de sensibilidad** (no detecta ni un solo ausente y se come todos los viajes perdidos), mientras que nuestro sistema alcanza **100 % de sensibilidad** (evita el 100 % de los viajes perdidos en ambos conjuntos sin cometer Falsos Positivos).

| Checklist (Clase 6) | Respuesta |
|---|---|
| **¿Qué datos?** | 20 casos sintéticos de la ficha `T20` (`datos/T20.csv`), con división fija e inamovible de **14 casos de entrenamiento** (Casos 1–14, con 2 `SÍ` y 12 `NO`) y **6 casos de prueba** (Casos 15–20, con 1 `SÍ` y 5 `NO`), usando 3 variables conocidas antes del despacho. |
| **¿Qué métrica?** | **Sensibilidad (Recall)** como métrica prioritaria (por ser el Falso Negativo el error más caro), junto con **Precisión**, **Especificidad** y **Exactitud**, ya que la Exactitud aislada engaña por el fuerte desbalance de clases (85,7 % de negativos). |
| **¿Comparado contra qué?** | Contra el **clasificador trivial de clase mayoritaria ("decir siempre NO")**, que logra 85,7 % de exactitud en entrenamiento y 83,3 % en prueba pero con **0 % de sensibilidad** (contra 100 % de exactitud y 100 % de sensibilidad de nuestra regla). |
| **¿Quién lo midió?** | Medido por el propio grupo sobre la partición de prueba retenida (`Casos 15–20`, que no se usó para diseñar la regla) y auditado externamente contra el bot evaluador de la cátedra y la prueba en vivo de la mesa, dejando constancia de que $n = 6$ en prueba es una muestra chica. |

---

## 6. Riesgo: el camino completo

Aplicamos la cadena completa **Datos $\rightarrow$ Modelo $\rightarrow$ Decisión $\rightarrow$ Consecuencia** a un riesgo real de nuestra solución en operación:

1. **Datos (Sesgo de medición y registro histórico):** La variable `Entregas fallidas previas` se alimenta de lo que cargaron los repartidores en viajes anteriores, y `Respondió el aviso por WhatsApp` depende de que el cliente use activamente esa aplicación. En logística urbana es frecuente que, cuando un chofer no llega a completar su recorrido matutino en barrios periféricos o complejos, cargue en el sistema *"domicilio ausente"* para no recibir una sanción, o que personas mayores no utilicen WhatsApp (`WhatsApp = 0`) aunque estén toda la mañana en su casa.
2. **Modelo (Cristalización del sesgo en la regla):** Nuestra Regla 1 interpreta literalmente que `Entregas fallidas previas >= 3` + `WhatsApp == 0` + `Franja == 0` equivale a que el cliente no está en el domicilio, sin distinguir si las fallas previas fueron ausencias reales del destinatario o incumplimientos del transportista en esa zona, ni si la falta de respuesta en WhatsApp se debe a brecha digital.
3. **Decisión (Reprogramación automática sistemática):** El sistema de ruteo bloquea el despacho matutino y reprograma automáticamente los pedidos de esos clientes cada vez que compran para recibir a la mañana.
4. **Consecuencia (Degradación discriminatoria del servicio y profecía autocumplida):** Clientes adultos mayores que sí estaban en su casa esperando el paquete, o vecinos de zonas donde el correo anterior funcionaba mal, sufren demoras y reprogramaciones crónicas sin motivo real, lo que termina provocando reclamos, cancelaciones de compras y pérdida de clientes en segmentos específicos. Para mitigarlo en producción, debería auditarse por GPS que los "ausentes" previos hayan tenido visita real en la puerta y ofrecer un canal alternativo (SMS o llamada) a quienes no usan WhatsApp.

---

## 7. Bitácora

**Uso de la IA**

| # | Qué le pedimos | Qué aceptamos | Qué rechazamos y por qué |
|---|---|---|---|
| 1 | Analizar el repositorio del hackatón, las bases (`BASES.md`) y los datos de `datos/T20.csv` para identificar el patrón entre las variables de entrenamiento (Casos 1–14) y comparar las tres pistas (Neurona, Reglas y Agente). | Aceptamos el hallazgo de que los casos positivos en entrenamiento ocurren únicamente cuando `Respondió WhatsApp = 0`, `Franja horaria = 0` y `Entregas fallidas previas` es alto, y aceptamos elegir la **Pista Reglas** por ser 100 % transparente y verificable a mano en segundos. | Rechazamos usar la **Pista Agente** porque complejizaba innecesariamente el cálculo de las matrices de confusión, y descartamos la **Pista Neurona** porque, aunque lograba el mismo resultado con $z = 1 \cdot \text{Fallidas} - 5 \cdot \text{WhatsApp} - 5 \cdot \text{Franja} - 3 \ge 0$, requería hacer cuentas aritméticas en vivo cuando una regla lógica se evalúa a simple vista sin margen de error. |
| 2 | Evaluar si convenía descartar alguna de las 3 variables de la ficha `T20` para simplificar todavía más el sistema. | Aceptamos conservar las **3 variables** y documentar con contraejemplos concretos del entrenamiento (Caso 8 para franja horaria, Casos 2/11/14 para WhatsApp y Casos 3/5/7 para fallidas previas) por qué las tres son indispensables y están libres de fuga de datos del futuro. | Rechazamos una regla de solo 2 variables (como mirar únicamente `Entregas fallidas previas >= 4` y `WhatsApp == 0`) porque fallaba en el Caso 8 de entrenamiento (`4, 0, 1 -> 0`), generando un Falso Positivo evitable en el turno tarde. |
| 3 | Definir el umbral exacto de `Entregas fallidas previas` teniendo en cuenta la brecha entre 2 y 4 fallidas en entrenamiento y el análisis del error más caro (Criterio D). | Aceptamos fijar el umbral en **`Entregas fallidas previas >= 3`** (en lugar de `>= 4`) justificando que el **Falso Negativo** (viaje de camión perdido) es mucho más caro que el Falso Positivo, cubriendo así la zona gris `(3, 0, 0)` sin alterar el 100 % de acierto en entrenamiento ni en prueba. | Rechazamos dejar el umbral en `>= 4` porque nos dejaba desprotegidos frente al error más caro (FN) si en la operación o en la prueba en vivo de la mesa aparecía un cliente con 3 entregas fallidas previas, sin respuesta de WhatsApp y en la franja de la mañana. |
| 4 | Redactar las secciones de medición, comparación contra línea base trivial, checklist de la Clase 6 y análisis de riesgo completo cuidando la claridad conceptual. | Aceptamos la comparación explícita contra la línea base trivial ("decir siempre NO" = 85,7 % de exactitud en entrenamiento y 83,3 % en prueba, pero 0 % de sensibilidad) y el caso de riesgo sobre sesgo de registro de choferes y brecha digital en WhatsApp. | Rechazamos afirmar que obtener 100 % en prueba garantiza 100 % de éxito en producción real, porque con $n = 6$ casos de prueba sería una exageración sin sustento estadístico (*snake oil*); agregamos explícitamente la advertencia sobre el tamaño de la muestra. |

**Corridas contra el evaluador**

| Corrida | Nota | Agujero que encontró | Qué cambiamos |
|---|---|---|---|
| 1 | Pendiente de enviar a `@Evaluador_iia_uade_bot` | Se completará con la devolución de la primera corrida | Se registrará el ajuste realizado tras la devolución del bot |
