# Market Opportunity Analyst

Proyecto CrewAI independiente que analiza una idea de producto dentro de un territorio y genera un informe de mercado con competidores, modelos de negocio, ranking explicable y oportunidades por validar.

## El informe incluye

- Delimitación del mercado y supuestos inferidos a partir de la idea y el territorio.
- Competidores directos, indirectos y sustitutos, con presencia geográfica, público objetivo, propuesta de valor, estrategia de adquisición, monetización, precios públicos y señales de tracción.
- Ranking comparable con criterios y pesos explícitos. El score mide relevancia competitiva para el producto y territorio analizados; no pretende ser cuota de mercado ni valoración de empresa.
- Áreas de oportunidad expresadas como hipótesis, con evidencia, segmento, propuesta inicial, forma de monetización, riesgos y experimento de validación.
- URLs, editor, tipo de fuente y fecha de consulta. Estimaciones e inferencias deben quedar etiquetadas; no se inventan descargas, ventas, ingresos o cuotas.
- Informe Markdown y datos JSON para reutilizar el análisis.

El proyecto no modifica archivos externos. La cobertura de las fuentes públicas puede variar por país, tienda de aplicaciones y disponibilidad de datos privados. Un ranking de fuentes públicas no sustituye una investigación primaria con usuarios.

## Configuración

Requiere Python 3.10–3.13 y `uv`. El modelo y la búsqueda son servicios separados:

- `OPENAI_API_KEY` (o la clave del proveedor que configures) para los agentes. El modelo por defecto es `openai/gpt-4o-mini`; `CREWAI_MODEL` permite cambiarlo.
- `SERPER_API_KEY` para búsquedas web y de noticias con ubicación/idioma. Consulta [Serper](https://serper.dev/) para la disponibilidad y condiciones actuales de sus créditos.

```powershell
cd market_opportunity_analyst
uv sync
$env:OPENAI_API_KEY = "..."
$env:SERPER_API_KEY = "..."
```

## Ejecutar un análisis

```powershell
uv run market-opportunity-analyst --idea "Servicio de transporte tipo taxi" --territory "México"
```

Se pueden agregar condiciones como ciudad, segmento objetivo, presupuesto, tipo de cliente o modelo de negocio:

```powershell
uv run market-opportunity-analyst --idea "Servicio de transporte tipo taxi" --territory "Ciudad de México" --constraints "B2C, bajo costo inicial, sin flota propia"
```

Si no proporcionas segmento o presupuesto, el analista propondrá supuestos explícitos y preguntas pendientes. Los informes se guardan en `output/`.

## Metodología del ranking

Cada competidor se puntúa de 1 a 5 en seis criterios. El código calcula el total de forma determinista: `score = sum(puntuación / 5 × peso)`, con un resultado de 0 a 100.

| Criterio | Peso |
|---|---:|
| Presencia y disponibilidad en el territorio | 25 % |
| Coincidencia del cliente objetivo | 20 % |
| Coincidencia del problema y la solución | 25 % |
| Alcance y señales públicas de tracción | 15 % |
| Fortaleza y diferenciación de la oferta | 10 % |
| Calidad de la evidencia pública | 5 % |

El ranking ordena la cercanía competitiva relativa, no el tamaño real del mercado. Las puntuaciones deben incluir una explicación y referencias; si faltan pruebas, el informe debe indicarlo y bajar la confianza.
