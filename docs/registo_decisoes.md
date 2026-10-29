# Registo de decisões — Projeto 1 (Consumer Choice / DIGI)

29/10/2026 · Pedro Correia

Cópia do documento partilhado em Claude (versão viva: https://claude.ai/artifact/Wag7H62YWC979XeRerM3B9).

## Para que serve

Este documento regista todas as decisões que levaram do baseline do Consumer Choice ao modelo atual do mercado português de pacotes com a entrada da DIGI (tarefas 3 a 5). Cada decisão indica quem a tomou, a justificação e como a reverter.

- **Quem decidiu.** "Pedro" = decisão tomada pelo Pedro na sessão de trabalho de 29/10. "Reunião" = ponto da lista da reunião do grupo. "Proposta técnica, aceite" = proposta feita durante o trabalho e aceite pelo Pedro. "Proposta técnica, por validar" = escolha de calibração ou de implementação que o grupo ainda não confirmou.
- **Como reverter.** Quase todas as decisões são um parâmetro de `TelecomMarketModel` ou de `calibrated.py`. A coluna "Como reverter" indica o parâmetro e o valor alternativo.
- **Documento de referência técnica.** A especificação completa, com as contas, está em `docs/model_v2_spec.md` (secção 11 = registo de decisões). Este documento é o resumo para o grupo.

## Baseline, protótipo do Zé e modelo atual

O modelo atual mantém a regra de decisão do baseline (hábito → exploração → utilidade) e aproveita do protótipo do Zé o cenário, a penalização legal e a ideia do bandit. O protótipo substituía a regra do baseline por um logit com quotas de mercado; essa mudança não foi adotada, para que as tarefas 1–2 continuem a ser a base do trabalho.

| Elemento | Baseline (tarefas 1–2) | Protótipo do Zé (NetLogo) | Modelo atual (Mesa) |
| --- | --- | --- | --- |
| Ferramenta | Mesa e NetLogo | NetLogo | Mesa (`telecom.py`) |
| Tempo | 1 tick abstrato | 1 tick = 1 dia | 1 tick = 1 mês |
| Produtos | 2 (laranja, azul) | MEO, NOS, Vodafone, DIGI | MEO, NOS, Vodafone, NOWO → DIGI no mês 12 |
| Quotas iniciais | 50/50 | 38 / 31 / 31 / 0 | ANACOM 3T2024: 41,8 / 35,0 / 20,6 / 2,6 |
| Regra de decisão | hábito → exploração → utilidade | 5%/dia avaliam; logit com ruído Gumbel | igual ao baseline |
| Influência social | norma dos amigos + informação dos amigos | quota nacional (efeito de rede) + notoriedade da DIGI | igual ao baseline |
| Preço | não existe | na utilidade, sensibilidade individual | na utilidade, peso ligado à norma (Confraria et al., 2017) |
| Qualidade | parâmetro fixo | fixa; DIGI sobe com a quota | reclamações ANACOM; DIGI sobe com o tempo desde a entrada |
| Contratos | não existem | 24 meses (DIGI 3); penalização Lei 16/2022 | igual, + refidelização com desconto decidida pelo consumidor |
| População | 100, fixa | mortes por idade, substituídas 1 para 1 | saídas 0,5%/mês, crescimento 1%/ano, mínimo 1000 |
| Operadoras antes da DIGI | — | já aprendem preços | preços fixos (conluio tácito) |
| Aprendizagem (tarefa 5) | — | bandit ε-greedy, braços €41,99–€26,99, recompensa = receita | bandit ε-greedy, braços ×1,00–×0,80, recompensa = margem, desde a entrada da DIGI |
| Calibração com dados | — | não | quotas da DIGI nos meses 19 / 25 / 28 (erro 0,18 p.p.) |
| Teste de regressão | — | — | reproduz o baseline exatamente com 2 produtos |

## Registo de decisões

Foram tomadas 22 decisões de modelação; todas estão fechadas. Ordem: estrutura, mercado, contratos, população, tarefa 5.

| # | Decisão | Quem | Justificação | Como reverter |
| --- | --- | --- | --- | --- |
| D1 | Implementar só em Python Mesa; NetLogo abandonado | Pedro | Um único código para testar, calibrar e correr milhares de simulações | — |
| D2 | Relatório em inglês, tom formal; tarefas 1–2 e relatório do GitHub ficam como estão | Pedro | Coerência com o que já foi entregue ao grupo | — |
| D3 | Manter a regra do Consumer Choice (hábito → exploração → utilidade) e acrescentar preço e contratos; não usar o logit do protótipo | Pedro | As tarefas 1–2 continuam a ser a base; com 2 produtos o modelo novo reproduz o baseline exatamente (teste automático) | Reescrever `consume` e `update_utilities` |
| D4 | 1 tick = 1 mês | Pedro | Dados ANACOM trimestrais, contratos e preços mensais; 1 dia exigia 30× mais passos | — |
| D5 | 4 operadoras; a NOWO passa a DIGI no mês 12 (set. 2025) | Reunião + Pedro | A DIGI comprou a NOWO; a ANACOM reporta DIGI/NOWO numa só linha. Dados verificados | `entry_tick=None` (sem DIGI) |
| D6 | Quotas iniciais da ANACOM, 3T2024: 41,8 / 35,0 / 20,6 / 2,6% | Reunião | Último trimestre antes da entrada | `initial_shares` |
| D7 | Preço da NOWO €26,35 | Proposta técnica, aceite | ANACOM, *O Sector das Comunicações 2024*, Tabela 20: única fonte oficial com o mesmo tipo de oferta | `prices` |
| D8 | Antes da DIGI os preços são fixos (conluio tácito) | Pedro | Os preços das marcas principais quase não mudaram entre 2024 e 2025 | `BanditPricePolicy(learn_before_entry=True)` |
| D9 | Peso do preço ligado ao peso da norma: θ = w / ((1−w) · 10,22) | Proposta técnica, aceite | Confraria et al. (2017), Tabela 4: o rácio preço/quota estimado em Portugal | `price_weight` |
| D10 | Qualidade a partir das reclamações ANACOM: q = 0,80 − κ·ln(r), κ = 0,20 | Reunião (qualidade) + Pedro (κ, com registo) | Dado oficial e comparável entre operadoras; κ é escolha de modelação, testada com 0,10 e 0,30 | `qualities` |
| D11 | Incumbentes com qualidade constante; a DIGI melhora com o tempo (0,572 → 0,756 em 18 meses) | Pedro | As reclamações da DIGI caíram de 3,1× para 1,25× a média sem a quota subir; no protótipo subia com a quota | `digi_quality_end`, `digi_maturation` |
| D12 | Fidelização de 24 meses (DIGI 3) com penalização da Lei 16/2022; alternativa com bloqueio total | Reunião + Pedro | Regra legal em vigor | `exit_rule="lock"` |
| D13 | No fim do contrato o consumidor decide: pode mudar sem custo ou aceitar refidelização com desconto | Pedro | Uma probabilidade fixa de renovação não depende do preço nem da concorrência | `contracts=False` |
| D14 | Desconto de refidelização δ = 17,8% (proposta inicial 10%) | Proposta técnica, confirmada pelo Pedro (29/10) | Com 10% os fidelizados caem de 70% para 35%; 17,8% mantém os 70% | `renewal_discount=0.10` |
| D15 | 70% dos clientes fidelizados no início | Proposta técnica, aceite pelo Pedro (29/10) | Não há dado público; testado entre 50% e 90% | `initial_contracted` |
| D16 | População variável com mínimo de 1000 consumidores | Reunião + Pedro | Entram famílias novas sem contrato, um canal de entrada da DIGI | `demography=False` |
| D17 | Saídas 0,5%/mês; crescimento líquido 1%/ano | Proposta técnica, aceite (com registo) | ANACOM: 4,7 → 4,8 milhões de subscritores; testado com 0,3% e 1% | `exit_rate` |
| D18 | Margem por cliente de 40% | Pedro (pediu a pesquisa) | EBITDA 2024: NOS 45,3%, MEO 35,8% (média ponderada 39,4%); testado com 60% | `margin` |
| D19 | Recompensa da aprendizagem = margem, não receita | Pedro | É o objetivo das empresas; com receita, baixar preços parece sempre melhor | `TelecomMarketModel.profit` |
| D20 | A aprendizagem começa na entrada da DIGI e só nos incumbentes; a DIGI mantém €22 | Pedro | A pergunta é como os incumbentes reagem à entrada | `learn_before_entry` |
| D21 | Bandit ε-greedy: ε = 0,1, α = 0,2, decisão de 3 em 3 meses, braços ×{1,00; 0,95; 0,90; 0,85; 0,80} | Proposta técnica, aceite (plano de 29/10) | α e período iguais ao protótipo; braços relativos ao preço de cada operadora; o mais baixo fica acima do custo | `BanditPricePolicy(...)` |
| D22 | Comparar o bandit com cenários de preço fixo e com o cenário sem DIGI, com os mesmos números aleatórios | Proposta técnica, aceite (plano de 29/10) | Isola o efeito da aprendizagem do ruído da simulação | — |

## Valores calibrados

Com os valores abaixo, a quota da DIGI no modelo é 2,5 / 2,9 / 3,1% nos meses 19 / 25 / 28, contra 2,8 / 3,0 / 3,2% da ANACOM (erro médio 0,18 p.p., 48 corridas). Todos são propostas técnicas obtidas por calibração; estão em `consumer_choice/calibrated.py`.

| Parâmetro | Valor | Como foi obtido |
| --- | --- | --- |
| Peso da norma (w) | 0,10 | Grelha de 32 combinações (w, ε) contra a trajetória da DIGI. Com w ≥ 0,25 a DIGI chega a 11–25%, porque o peso do preço depende de w (D9) |
| Exploração (ε) | 0,03 | Melhor valor depois da correção de ρ (0,02 dá erro de 0,36 p.p.; 0,03 dá 0,18 p.p.) |
| Desconto de refidelização (δ) | 0,178 | Mantém 70% de fidelizados no mercado sem DIGI (D14) |
| Contratos iniciais já refidelizados (ρ) | 78% | Proporção de refidelizações entre os contratos assinados no longo prazo. Sem isto o preço médio pago caía de €41,6 para €37,4 por um artefacto de arranque, e esse artefacto enviesava a recompensa da aprendizagem |
| Constantes de marca (NOS / Vodafone / NOWO-DIGI; MEO = 0) | +0,028 / +0,017 / −0,084 | Sem elas a norma faz crescer a maior operadora e as quotas afastam-se das da ANACOM antes da entrada. A DIGI herda a constante da NOWO |

O preço médio pago no modelo fica em €37,6; o ARPU de pacotes da ANACOM no 1T2026 é €39,59.

## Resultados da tarefa 5

Quando aprendem os preços, os incumbentes acabam perto do preço de lista sem comunicarem entre si, embora baixar sozinho seja rentável para a NOS e para a Vodafone. Valores: 30 corridas por cenário, lucro acumulado em 10 anos após a entrada, comparado com "todos ao preço de lista".

| Cenário | Lucro conjunto dos incumbentes | Quota da DIGI a 10 anos |
| --- | --- | --- |
| Sem DIGI (contrafactual) | +9,4% | — |
| Todos ao preço de lista | referência | 18,7% |
| Preços aprendidos (bandit, ε = 0,1, α = 0,2) | −6,0% | 10,6% |
| Todos a ×0,95 | −9,3% | 13,5% |
| Todos a ×0,90 | −18,7% | 6,3% |
| Todos a ×0,85 | −30,0% | 1,2% |
| Todos a ×0,80 | −44,0% | 0,7% |

- **Baixar sozinho compensa.** A NOS sozinha a ×0,90 ganha +26,5% de lucro e a Vodafone +29,3%; a MEO perde 0,9%. Manter o preço de lista não é um equilíbrio: é um dilema do prisioneiro.
- **O bandit volta ao preço de lista.** Nos anos 6–10, o preço de lista é escolhido em 77% (MEO), 63% (NOS) e 68% (Vodafone) das decisões. O multiplicador médio é 0,95.
- **Robusto aos parâmetros do bandit.** Nas 9 combinações de ε ∈ {0,05; 0,10; 0,20} e α ∈ {0,1; 0,2; 0,4}, o lucro conjunto fica entre −3% e −9% e o multiplicador médio entre 0,94 e 0,97.
- **Leitura.** É o resultado de Calvano et al. (2020): algoritmos independentes chegam a preços acima do competitivo. Coincide com o observado: os incumbentes não baixaram as marcas principais e responderam com marcas low-cost (Uzo, Woo, Amigo).

Figuras em `results/pricing/figures/`: quota da DIGI, preços aprendidos, lucro por cenário.

## Limitações e pendências

Há três limitações conhecidas, todas documentadas na especificação, e duas tarefas por fazer.

- **Deriva lenta sem DIGI.** Em 6 anos a MEO ganha cerca de 3,5 p.p. e a NOS perde o mesmo, por reforço da norma. Calibrar para o longo prazo não convergiu (oscilou entre MEO e NOS). Por isso todos os cenários são comparados entre si com os mesmos números aleatórios.
- **Pouca mudança no fim do contrato.** No modelo cerca de 1% muda de operadora no fim do contrato; Confraria et al. estimam 13,6% (rede móvel, 2014). O modelo subestima a mobilidade.
- **Horizonte longo.** Os 10 anos vão além dos 30 meses com dados; os valores servem para comparar cenários, não são previsões.

- [x] Desconto de refidelização de 17,8% (D14): confirmado pelo Pedro em 29/10
- [x] 70% de fidelizados no início (D15): aceite pelo Pedro em 29/10
- [ ] Correr as análises de sensibilidade combinadas: κ 0,10/0,30; saídas 0,3–1%; fidelizados 50–90%; δ; bloqueio vs penalização; margem 60%
- [ ] Escrever as secções 3–5 do relatório em inglês

## Onde está cada coisa

Tudo está no repositório `Projeto1_baseline`. O baseline (`consumer_choice/model.py`) não foi alterado.

| Ficheiro | Conteúdo |
| --- | --- |
| `docs/registo_decisoes.md` | Este documento |
| `docs/model_v2_spec.md` | Especificação completa; secção 11 = registo técnico das decisões |
| `consumer_choice/telecom.py` | Modelo atual (consumidores e mercado) |
| `consumer_choice/calibrated.py` | Valores calibrados |
| `consumer_choice/learning.py` | Preços fixos e bandit (tarefa 5) |
| `tests/test_telecom.py` | Testes: regressão contra o baseline, penalizações, renovação, políticas de preço |
| `calibration/` | Scripts de calibração; resultados em `results/v2/` |
| `experiments/run_pricing.py` | Cenários de preço e bandit; resultados em `results/pricing/` |
| `analysis/analyze_pricing.py` | Tabelas e figuras da tarefa 5 |
| `visualization/live.py` | Janela ao vivo, ao estilo do NetLogo |
