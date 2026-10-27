# Checklist de entrega — Grupo 4 · Propagación de Fake News

Mantenido por Ernesto (P4, integración del documento). Actualizar en cada checkpoint y avisar en el grupo
qué falta y de quién. Estados: ⬜ pendiente · 🟨 borrador · ✅ listo · 🔒 revisado por otra persona.

Última actualización: mar 27 oct 2026 (CP0/CP1).

## 1. Secciones del documento (orden del PDF final)

| # | Exigido por el curso | Archivo (`docs/informe/`) | Dueño | Estado | Notas |
|---|---|---|---|---|---|
| 01 | Descripción del problema | `01_problema.md` | Camila | ⬜ | Cita Vosoughi et al. (2018) |
| 02 | Análisis (pregunta, hipótesis H1–H5) | `02_analisis.md` | Camila | ⬜ | |
| 03 | Propuesta de solución (y por qué SEIR-D + ABM) | `03_propuesta.md` | Juan Francisco | ⬜ | |
| 04a | Descripción de la solución: modelo ODE y R0 | `04a_modelo_ode.md` | Camila | ⬜ | |
| 04b | Descripción de la solución: ABM, redes y Monte Carlo | `04b_abm_redes.md` | Marinés | ⬜ | |
| 04c | Descripción de la solución: intervenciones | `04c_intervenciones.md` | Juan Francisco | ⬜ | |
| 04d | Descripción de la solución: dashboard | `04d_dashboard.md` | Ernesto | 🟨 | Faltan capturas con datos finales (CP3) |
| 05 | Herramientas aplicadas (prompts de IA, evolución, comprensión) | `05_herramientas.md` | Marinés | ⬜ | Compila `docs/prompts/PROMPTS_*.md` de los 4 |
| 06a | Resultados y métricas (E1, E3–E7) | `06a_resultados.md` | Juan Francisco | ⬜ | Todo número sale de `results/*.csv` |
| 06b | Validación (V1–V4) | `06b_validacion.md` | Camila | ⬜ | V4 la aporta Marinés |
| 07 | Conclusión | `07_conclusion.md` | Ernesto | 🟨 | Esqueleto; veredictos H1–H5 cuando estén 06a/06b |
| 08 | Bibliografía (APA, verificada) | `08_bibliografia.md` | Ernesto | ⬜ | Une los `refs_<nombre>.md` de los 4 |

## 2. Insumos que Ernesto necesita de los demás

| Insumo | De quién | Para | Estado |
|---|---|---|---|
| `refs_camila.md` | Camila | 08 | ⬜ |
| `refs_marines.md` | Marinés | 08 | 🟨 en la rama `p2-marines-abm` (falta merge) |
| `refs_juanfran.md` | Juan Francisco | 08 | ⬜ |
| `refs_ernesto.md` | Ernesto | 08 | 🟨 una referencia marcada `[VERIFICAR]` |
| `slides_camila.md` (slides 2, 4, 6) | Camila | deck | ⬜ pedir el sáb 31 |
| `slides_marines.md` (slides 5, 7) | Marinés | deck | ⬜ pedir el sáb 31 |
| `slides_juanfran.md` (slides 3, 8, 9) | Juan Francisco | deck | ⬜ pedir el sáb 31 |
| `results/E1…E7_*.csv`, `figures/fig_*.png` | Juan Francisco | dashboard, 07, slides | ⬜ |
| `ode_model.simulate_ode` en `main` | Camila | dashboard (curva ODE) | ⬜ |
| `abm`, `networks` en `main` | Marinés | dashboard (Simulador, Estructura de la red) | 🟨 en la rama `p2-marines-abm` |

## 3. Entregables

| Entregable | Pts | Dueño | Fecha | Estado |
|---|---|---|---|---|
| Entrega parcial (descripción + captura del correo de aprobación) | 3 | Camila | vie 30 oct (subir jue 29) | ⬜ |
| Documento PDF `Informe_Grupo4_FakeNews.pdf` | 5 | Ernesto (ensambla) | lun 2 nov | ⬜ |
| Repositorio público con todo el código | 1 | Marinés | lun 2 nov | ⬜ |
| Video (solución, implementación, hallazgos) | 1 | Juan Francisco | lun 2 nov | ⬜ |
| Slides (máx. 10) `presentacion.pdf` | 5 | Ernesto | lun 2 nov | ⬜ |
| Presentación en clase (ensayo cronometrado con los 4) | 10 | todos | según catedrático | ⬜ |

## 4. Verificación final del PDF (CP4, antes del congelamiento dom 1 nov 22:00)

- [ ] Portada, índice, numeración de páginas, pies de figura y estilo uniforme.
- [ ] Secciones en el orden 01, 02, 03, 04a–d, 05, 06a–b, 07, 08.
- [ ] Cada número del documento coincide con `results/*.csv` (revisar tabla por tabla).
- [ ] Cada figura existe en `figures/` y se reproduce con el código del repo.
- [ ] Ninguna figura ni número viene de datos de demostración (`fakenews.mock`).
- [ ] La sección 05 incluye prompts relevantes, cuáles funcionaron, cuáles fallaron y por qué.
- [ ] Toda referencia está verificada; no queda ninguna marca `[VERIFICAR]`.
- [ ] Link al repositorio público y link al video.
- [ ] Hipótesis H1–H5 evaluadas en 07 con evidencia de `results/`.
- [ ] Limitaciones y trabajo futuro declarados.

## 5. Subida a Canvas (lun 2 nov; confirmar la hora límite en Canvas)

- [ ] PDF del documento + link al repo.
- [ ] PDF de la presentación.
