⚠️ REGLAS ESTRICTAS DE DESARROLLO (ANTI-CONFLICTOS) ⚠️
INSTRUCCIONES CORE PARA EL AGENTE DE IA:
A partir de este momento, operarás bajo las siguientes reglas inquebrantables de arquitectura y limpieza de código. Si no puedes cumplir una, detente y pide aclaración.

1. Modularidad Extrema (Cero Monolitos):

NUNCA escribas componentes gigantes en un solo archivo.

Separa la lógica de negocio (Custom Hooks, llamadas a la API, formateo de datos) de la interfaz de usuario (Componentes visuales).

Un componente = Un archivo. Si un archivo supera las 150 líneas, divídelo lógicamente en subcomponentes.

2. Inmutabilidad del Contrato de Datos:

El JSON estructurado (response_id, narrative, render_type, chart_config, raw_data) es sagrado.

NUNCA alteres el nombre de estas claves ni asumas que vendrán datos diferentes. Todo tu código frontend debe diseñarse para consumir exactamente esta estructura.

Todo tu código backend debe diseñarse para escupir exactamente esta estructura.

3. Prohibido Alucinar Dependencias:

Cíñete estrictamente al stack tecnológico definido (Next.js App Router, Tailwind CSS, Recharts, Lucide-react para Front / Python, FastAPI, Pydantic para Back).

NUNCA inventes librerías que no he solicitado ni uses paquetes obsoletos. Si necesitas una librería extra para resolver el problema, pregúntame primero antes de integrarla en el código.

4. Cambios Incrementales (No destructivos):

Cuando te pida modificar un componente existente, NUNCA reescribas todo el archivo a menos que sea estrictamente necesario.

Entrégame solo las funciones o bloques de código que cambiaron, indicando claramente dónde debo insertarlos (ej: "Reemplaza la función X en la línea Y").

No elimines comentarios existentes ni variables que no estén relacionadas con tu tarea actual.

5. Manejo de Errores y "Fail-Safes":

Todo componente que reciba datos externos debe tener un estado de carga (isLoading) y un manejo de errores (isError).

Si el render_type del JSON viene vacío o con un formato no reconocido, el DynamicRenderer debe tener un fallback (por defecto, renderizar solo el texto narrativo) en lugar de quebrar la aplicación (evitar Pantalla Blanca de la Mue