Rol: Actúa como un Desarrollador Frontend Senior experto en React, Next.js, Tailwind CSS y arquitecturas escalables.

Objetivo: Construir "Synapse UI", una interfaz de Data Storytelling para un producto Enterprise. No es un chat genérico; es un "Dynamic UI Renderer" que interpreta un JSON estricto del backend para renderizar texto, gráficos y tablas dinámicamente.

Stack Estricto: Next.js (App Router), Tailwind CSS (modo oscuro por defecto, estilo corporativo/financiero), recharts para visualización de datos, y lucide-react para iconografía.

Contrato de Datos (El Payload):
Tu frontend debe esperar y procesar exactamente esta estructura JSON que vendrá del backend:

JSON
{
  "response_id": "req_123",
  "narrative": "El ROAS de octubre cayó un 15% debido a ineficiencias en Paid Social. Aquí el desglose:", 
  "render_type": "chart", 
  "chart_config": {
    "type": "bar",
    "x_axis": ["Semana 1", "Semana 2", "Semana 3"],
    "y_axis": [2.5, 3.1, 1.8],
    "metrics_label": "ROAS"
  },
  "raw_data": [{"semana": "Semana 1", "roas": 2.5}, {"semana": "Semana 2", "roas": 3.1}, {"semana": "Semana 3", "roas": 1.8}]
}
(Nota: render_type puede ser "text", "chart", o "table").

Arquitectura Requerida:

useSynapseQuery (Custom Hook): Maneja el estado de la conexión. Expone una función askSynapse(query). Debe incluir un estado isLoading robusto.

SynapseChatLayout: Contenedor principal. Mientras isLoading sea true, MUESTRA un "Skeleton Loader" sofisticado (simulando que se está construyendo un gráfico), no un simple spinner.

DynamicRenderer (Core): Recibe el JSON. Muestra siempre la narrative primero. Luego lee render_type:

Si es "chart" -> Renderiza un <ChartModule /> usando recharts (haz que sea responsivo).

Si es "table" -> Renderiza un <TableModule /> limpio y corporativo.

ActionToolbar: Debajo de cada respuesta, agrega botones sutiles de Lucide (Descargar CSV, Exportar PDF). Por ahora solo haz un console.log en sus eventos onClick.

Genera el código modularizado, tipado (si usas TypeScript) y listo para ser conectado a una API real.