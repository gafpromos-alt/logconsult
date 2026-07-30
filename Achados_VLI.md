# Achados — Base Interna VLI (P&L por fluxo)

**CONFIDENCIAL — USO RESTRITO AOS SÓCIOS** · Gerado em 2026-07-11 19:05

> Lógica proprietária (Hypothesis Generator em SQL). Nunca vai ao cliente — só a conclusão.

## 1. Retrato VLI 2024 (Real)
- Receita total: **R$ 10.79 bi** · Margem (IND-MRG): **R$ 7.13 bi (66%)** · Volume: 42.6 bi TKU.
- Composição: frete R$ 6.2 bi · manobra R$ 2.0 bi · serviços acessórios R$ 155 mi. **Acessórias/manobra = 20% da receita** (pool menos regulado que o frete → alvo de negociação).

## 2. A própria VLI planeja expandir margem (2024 → 2026)
| Panorama | Receita | Margem % |
|---|---:|---:|
| 2024 - Real | R$ 10.8 bi | 66% |
| 2025 - Real | R$ 10.9 bi | 63% |
| 2026 - Tendência 6+6_Aceite v18 | R$ 10.8 bi | 76% |

> Com receita ~estável, a margem sobe de 66% para ~89% no orçamento 2026 — a VLI embute ganho de margem. **Cautela metodológica:** a definição de custo pode variar entre panoramas (o orçamento pode sub-alocar custo); confirmar antes de usar o número de 89% em negociação.

## 3. Margem por corredor VLI (2024) — onde a VLI mais lucra
| Corredor | Receita | Margem % | Leitura |
|---|---:|---:|---|
| Centro-Norte | R$ 3,166 mi | 77% | corredor exportador cativo → alavanca alta |
| Centro-Leste | R$ 2,698 mi | 50% | margem intermediária |
| Centro-Sudeste | R$ 1,328 mi | 10% | competição rodoviária → pouca folga |

## 4. Clientes-alvo LogConsult — margem que a VLI faz (2024)
Ordenado por margem %. Margem alta + acessórias altas = maior espaço de renegociação.

| Cliente | Receita VLI | Margem VLI % | Acessórias % |
|---|---:|---:|---:|
| Nova Agri | R$ 158 mi | 94% | 36% |
| Cenibra | R$ 141 mi | 86% | 36% |
| Agrex | R$ 170 mi | 76% | 35% |
| Cargill | R$ 951 mi | 75% | 23% |
| Bunge | R$ 502 mi | 74% | 19% |
| Selecta | R$ 105 mi | 72% | 30% |
| Caramuru | R$ 86 mi | 71% | 9% |
| Vibra Energia | R$ 210 mi | 70% | 21% |
| Cmoc | R$ 134 mi | 66% | 17% |
| Gerdau | R$ 360 mi | 56% | 32% |
| Mosaic | R$ 686 mi | 46% | 15% |

## 5. Radar de originação — alta receita e alta margem (2024)
Clientes onde a VLI fatura muito **e** lucra muito: originação prioritária.

| Cliente | Receita VLI | Margem VLI % |
|---|---:|---:|
| ADM | R$ 1,041 mi | 74% |
| Cargill | R$ 951 mi | 75% |
| Usiminas | R$ 857 mi | 63% |
| Bunge | R$ 502 mi | 74% |
| Suzano | R$ 295 mi | 84% |
| Cofco graos | R$ 251 mi | 73% |
| CBA | R$ 236 mi | 78% |
| Copersucar | R$ 229 mi | 68% |
| CSN | R$ 218 mi | 78% |
| Vibra Energia | R$ 210 mi | 70% |
| Tereos | R$ 207 mi | 64% |
| ALZ | R$ 202 mi | 92% |
| CHS | R$ 179 mi | 79% |
| Agrex | R$ 170 mi | 76% |
| Nova Agri | R$ 158 mi | 94% |

---
*Reproduzir:* `python3 analises.py` · Fonte: `logconsult.db` (tabela `vli_pnl`, panorama 2024 Real).