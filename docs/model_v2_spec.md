# Especificação do modelo novo (v2): entrada da DIGI no mercado português de pacotes

Documento interno para o grupo validar antes da implementação (fases 2 a 4).
O relatório final será escrito em inglês a partir deste documento.

Estado: **rascunho para validação**, 29/10/2026 (revisto às 17h com as decisões do grupo; ver secção 11).

---

## 1. Pergunta do trabalho

Como evoluem as quotas de mercado quando uma operadora low-cost (DIGI) entra num mercado de pacotes
dominado por três incumbentes com contratos de fidelização, e qual a melhor resposta de preço dos
incumbentes (tarefa 5: aprendizagem por reforço)?

Facto a explicar (dados ANACOM): a DIGI/NOWO passou de 2,6% (3T2024) para 3,2% (1T2026), +0,6 p.p.
em ~18 meses, apesar de cobrar cerca de metade do preço. Os incumbentes quase não mexeram nas quotas
nem nos preços das marcas principais.

---

## 2. Decisões tomadas pelo grupo

| Tema | Decisão |
|---|---|
| Estrutura de decisão | A do Consumer Choice: hábito → exploração → utilidade. Acrescenta-se preço e contratos |
| Unidade de tempo | 1 tick = 1 mês |
| Fidelização | Saída antecipada com penalização legal (Lei 16/2022); opção de bloqueio total como cenário |
| População | Variável, com mínimo de 1000 agentes |
| DIGI | Herda a base da NOWO no momento da entrada |
| Qualidade | A partir das reclamações por mil clientes (ANACOM). Incumbentes constantes; DIGI melhora com o tempo |
| Preços antes da DIGI | Fixos e alinhados (conluio tácito). O reforço começa na entrada da DIGI |
| Implementação | Python/Mesa, módulo novo; o baseline (tarefas 1 e 2) fica intacto |

---

## 3. O que se mantém do baseline

- Consumidores numa rede social de vizinhos mais próximos (regra igual à do baseline).
- Decisão mensal em três passos: (1) fica por hábito com probabilidade `satisfação = log10(1 + 9q)`;
  (2) senão, experimenta outra operadora com probabilidade `exploration`; (3) senão, escolhe a de maior utilidade.
- Utilidade = norma (partilha de amigos que usam a operadora) + utilidade de produto (experiência própria + informação dos amigos).
- Memória: o consumidor só conhece a qualidade das operadoras que usou ou de que os amigos falaram.
  Uma melhoria de qualidade numa operadora que ninguém à volta usa não é percebida.
- Outputs do baseline: quotas por operadora e clustering.

---

## 4. O que muda

### 4.1 Operadoras

| Operadora | Quota inicial (3T2024) | Preço (fibra + TV, com IVA) | Contrato | Qualidade q |
|---|---|---|---|---|
| MEO | 41,8% | €42,49 | 24 meses | 0,848 |
| NOS | 35,0% | €42,49 | 24 meses | 0,784 |
| Vodafone | 20,6% | €40,50 | 24 meses | 0,776 |
| NOWO (até à entrada) | 2,6% | €26,35 | 24 meses | 0,572 |
| DIGI (a partir da entrada) | herda a NOWO | €22,00 | 3 meses | 0,572 → 0,756 |

Fontes: quotas ANACOM (pacotes de serviços, 3T2024); preços barómetro CNN Portugal/DECO PROteste
(outubro 2025; a NOS estava a €42,49 antes de baixar €2 com corte de velocidade); DIGI €10 fibra 1 Gbps
+ €12 TV e compromisso de 3 meses (Observador, 04/11/2024); NOWO €26,35: ANACOM, *O Sector das Comunicações 2024*,
Tabela 20 (mensalidade mínima BLF+TVS, dezembro de 2024, com IVA, contratos de 24 meses).

Nota sobre as marcas low-cost: na mesma Tabela 20, a mensalidade mínima de internet + TV dos incumbentes,
incluindo as marcas Uzo, Woo e oteuamigo, já era €25 (MEO, NOS) e €22 (Vodafone) em dezembro de 2024, contra €22 da DIGI.
O modelo usa o preço da marca principal (onde está a maioria dos clientes) e trata o nível ~€25 como o limite
inferior das ações de preço do reforço (secção 7).

Nota: a receita média por cliente (ANACOM) não é usada como preço, porque reflete a mistura de pacotes
(a NOS vende mais 4/5P) e não o preço de um serviço igual. Serve para validação.

### 4.2 Qualidade a partir das reclamações

Reclamações por mil clientes (ANACOM): 2025 — MEO 4,0, NOS 6,2, Vodafone 7,7, DIGI/NOWO 18,7;
2T2026 — MEO 1,6, NOS 2,0, Vodafone 1,7, DIGI 2,2.

Como os períodos não são comparáveis em valor absoluto (ano vs trimestre), usa-se a razão face à
média dos incumbentes, r. Mapeamento (pressuposto):

    q = 0,80 − κ · ln(r),   κ = 0,20

- Incumbentes: média de r nos dois períodos → MEO 0,848; NOS 0,784; Vodafone 0,776.
- DIGI: r = 3,13 em 2025 → q = 0,572 na entrada; r = 1,25 no 2T2026 → q = 0,756.
  Sobe linearmente de 0,572 (entrada) até 0,756 (entrada + 18 meses) e fica constante.
- NOWO: valor do grupo DIGI/NOWO em 2025 (0,572).
- Análise de sensibilidade: κ = 0,10 e 0,30.

A qualidade da DIGI depende do tempo desde a entrada e não da quota: os dados mostram queda das
reclamações sem crescimento relevante de quota.

### 4.3 Utilidade com preço

Para cada operadora k:

    U_k = w · N_k + (1 − w) · [ (E_k + I_k)/2 − θ · p_k ]

- N_k: fração de amigos que usam k (norma, como no baseline).
- E_k: qualidade lembrada; I_k: qualidade transmitida por amigos (como no baseline).
- p_k: preço pago (contrato em vigor) ou preço atual da operadora.
- w = `norm_influence` (calibrar; ponto de partida 0,15).
- θ obtido de Confraria et al. (2017), Tabela 4: o preço vale −0,074 por €/mês e a quota de mercado
  (40% vs 15%) vale +0,189. A razão dá ~€10,2 por unidade de quota. Impondo a mesma razão entre norma e
  preço: θ = w / ((1 − w) · 10,22). Com w = 0,15, θ = 0,0173 por euro (€20 de diferença ≈ 0,35 de utilidade de produto).
- Pressuposto a declarar: Confraria mede a quota nacional no móvel; aqui aplica-se à quota entre amigos nos pacotes fixos.

### 4.4 Contratos e penalização

- Ao escolher uma operadora, o consumidor assina um contrato: 24 meses (incumbentes, NOWO) ou 3 meses (DIGI),
  ao preço em vigor nesse mês. Paga esse preço até ao fim do contrato.
- Com contrato em curso, só pode mudar se R·(p_atual − p_nova) − penalização > 0, com R = meses em falta e
  penalização = 50% (1.º ano) ou 30% (2.º ano) das mensalidades em falta (Lei 16/2022).
  No cenário "bloqueio total" não pode mudar.
- Fim do contrato: o consumidor passa pela decisão normal do mês (hábito → exploração → utilidade), sem
  penalização, e pode mudar de operadora. Se mudar, assina contrato com a nova operadora.
- Se ficar na mesma operadora, esta oferece um desconto de refidelização δ = 10% sobre o preço atual em troca
  de um novo contrato de 24 meses. O consumidor aceita se o desconto for maior do que o seu custo de ficar preso:
  aceita se δ·p ≥ c_j. Se não aceitar, fica sem fidelização (paga o preço atual e pode sair em qualquer mês).
- Custo de compromisso c_j (Confraria et al., 2017): €1,31/mês para reduzir o compromisso de 12 para 6 meses,
  ou seja ~€0,22 por mês de compromisso. Para 24 meses: c = €5,25/mês em média. Heterogeneidade entre consumidores:
  c_j uniforme entre 50% e 150% da média (€2,6–7,9), fixo para cada consumidor.
- A DIGI não tem refidelização: após os 3 meses iniciais o cliente fica livre.
- No início, uma fração φ dos consumidores está fidelizada, com meses decorridos uniformes entre 0 e 23.
  **φ = 0,7 (pressuposto; sem dado público encontrado).**

### 4.5 Entrada da DIGI

- Tick de entrada T = 12 (t = 0 corresponde a novembro de 2023; T = novembro de 2024).
- Os clientes da NOWO passam a clientes da DIGI, mantendo o contrato e o preço até ao fim; depois pagam o preço DIGI.
- A informação sobre a DIGI espalha-se pelos mecanismos do baseline: clientes da DIGI (ex-NOWO e novos)
  transmitem a qualidade aos amigos, e a exploração leva consumidores a experimentá-la.

### 4.6 População

- Saída mensal: d = 0,5% dos consumidores (decisão do grupo; justificação na secção 11; sensibilidade 0,3–1%).
- Entrada mensal: b = d + 0,083%, para um crescimento líquido de ~1%/ano (subscritores de pacotes 4,7 → 4,8 milhões, ANACOM).
- Mínimo: se a população ficar abaixo de 1000, entram consumidores até repor o mínimo.
- Quem entra: sem contrato, posição aleatória, ligado aos `avg_connections` consumidores mais próximos
  (assim a rede não se desfaz). Escolhe pela utilidade, com o que os amigos lhe transmitem.
- Cada agente representa ~4700 subscritores (4,7 milhões / 1000).

### 4.7 Preços dos incumbentes

- Antes da entrada: fixos (tabela 4.1). Representa o conluio tácito observado (preços quase iguais).
- Depois da entrada: tarefa 5 (secção 7). No modelo sem aprendizagem (fase 3), os preços ficam fixos,
  com cenários para cada nível de preço.

---

## 5. Ordem das operações em cada mês

1. Entradas e saídas de consumidores (mínimo 1000).
2. Entrada da DIGI (se t = T) e atualização da qualidade da DIGI.
3. Decisão de consumo (hábito → exploração → utilidade), com a restrição do contrato.
4. Atualização das utilidades (experiência, informação dos amigos, norma, preço).
5. Contratos: descontar um mês; fim de contrato → renovação com probabilidade ρ.
6. Operadoras: preços (fixos, ou bandit a cada 3 meses após a entrada).
7. Registo dos outputs.

---

## 6. Calibração e validação

**Alvos (ANACOM):**

| Momento | Mês do modelo | DIGI/NOWO | MEO / NOS / Vodafone |
|---|---|---|---|
| 3T2024 (antes) | 10 | 2,6% | 41,8 / 35,0 / 20,6 |
| 2T2025 | 19 | 2,8% | 41,7 / 34,9 / 20,5 |
| 4T2025 | 25 | 3,0% | 41,6 / 34,9 / 20,4 |
| 1T2026 | 28 | 3,2% | 41,5 / 34,9 / 20,3 |

**Procedimento:**
1. Aquecimento de 12 meses sem DIGI: as quotas têm de ficar estáveis (±0,5 p.p.). Se houver deriva,
   acrescentar constantes de marca por operadora calibradas neste período (prática habitual em modelos de escolha).
2. Grelha sobre `norm_influence` e `exploration` (e `information_exchange` se necessário), 30 corridas por
   ponto, minimizando o erro quadrático face aos alvos da DIGI.
3. Resultado aceitável: DIGI a 3,2% ± 0,5 p.p. no mês 28.

**Outputs registados todos os meses:** quotas por operadora, clustering, número de mudanças, preço médio
pago, % de consumidores fidelizados, receita e margem por operadora, qualidade da DIGI, população.

---

## 7. Tarefa 5: aprendizagem por reforço (resumo; detalhe na fase 4)

- Agentes que aprendem: MEO, NOS e Vodafone. A DIGI mantém o preço.
- Início: no mês da entrada da DIGI. Decisão de 3 em 3 meses.
- Ações: preço = preço base × {1,00; 0,95; 0,90; 0,85; 0,80}.
- Recompensa: margem do trimestre = Σ (preço do contrato − custo unitário) dos clientes, menos custo fixo.
  Custo unitário = 60% do preço base (margem de 40%, a partir das margens EBITDA de 2024: NOS 45,3%, MEO 35,8%;
  sensibilidade 40% e 60%; ver secção 11).
  A recompensa é a margem e não a receita, por ser o objetivo das empresas.
- Método: bandit ε-greedy com passo constante (α = 0,2; ε = 0,1), valores iniciais na escala das recompensas (Sutton & Barto, 2018).
- Referência de comparação: os cenários de preço fixo da fase 3.
- Validação qualitativa: na realidade os incumbentes não baixaram os preços das marcas principais e responderam com
  marcas low-cost (Uzo, Woo, Amigo, a €25 no barómetro de outubro 2025).
- Discussão: três operadoras a aprender ao mesmo tempo tornam o problema não estacionário; a literatura mostra que
  algoritmos de aprendizagem podem convergir para preços de conluio (Calvano et al., 2020).
- Cenário opcional: aprendizagem também antes da entrada, para testar se o conluio se mantém.

---

## 8. Implementação

- Módulo novo `consumer_choice/telecom.py` (classe `TelecomMarketModel`). `model.py` (baseline) não muda.
- Teste de segurança: com 2 operadoras, sem preços, contratos nem demografia, o modelo novo reproduz o baseline com as mesmas seeds.
- Testes: população ≥ 1000; contadores de contrato; exemplos de cálculo da penalização; soma das quotas = 100%.
- Experiências em `experiments/`, resultados em `results/v2/`. Um commit por fase.

---

## 9. Pressupostos ainda em aberto

| Pressuposto | Valor | Estado |
|---|---|---|
| Fidelizados no início (φ) | 70% | Ponto de partida, não alvo: a percentagem evolui com as decisões dos consumidores (secção 11.15). Sem dado público; aceite pelo Pedro em 29/10; sensibilidade 50–90% |
| Desconto de refidelização (δ) | 10% | Decisão do Pedro (29/10, 19:22), depois de testado 17,8%; secções 11.8 e 11.15 |
| Heterogeneidade do custo de compromisso | ±50% | Pressuposto; o desvio estimado por Confraria et al. não é significativo |

---

## 10. Referências (corrigidas, formato LNCS)

1. Jager, W., Wang, S.: NetLogo Consumer Choice model. CCL, Northwestern University (2024)
2. Wilensky, U.: NetLogo. CCL, Northwestern University (1999)
3. Janssen, M.A., Jager, W.: Fashions, Habits and Changing Preferences: Simulation of Psychological Factors Affecting Market Dynamics. J. Econ. Psychol. 22(6), 745–772 (2001)
4. Cialdini, R.B., Goldstein, N.J.: Social Influence: Compliance and Conformity. Annu. Rev. Psychol. 55, 591–621 (2004)
5. Nyborg, K., et al.: Social Norms as Solutions. Science 354(6308), 42–43 (2016)
6. ter Hoeven, E., et al.: Mesa 3: Agent-Based Modeling with Python in 2025. J. Open Source Softw. 10(107), 7668 (2025)
7. Grimm, V., et al.: The ODD Protocol for Describing Agent-Based and Other Simulation Models: A Second Update. JASSS 23(2), 7 (2020)
8. Confraria, J., Ribeiro, T., Vasconcelos, H.: Analysis of Consumer Preferences for Mobile Telecom Plans Using a Discrete Choice Experiment. Telecommun. Policy 41(3), 157–169 (2017). https://doi.org/10.1016/j.telpol.2016.12.009
9. Wang, R., Wang, Z.: Consumer Choice Models with Endogenous Network Effects. Manag. Sci. (2017). https://doi.org/10.1287/mnsc.2016.2520
10. Griffin, M., Lyons, S., Mohan, G., Joseph, M., Mac Domhnaill, C., Evans, J.: Intra-Operator Mobile Plan Switching: Evidence from Linked Survey and Billing Microdata. Telecommun. Policy 46, 102343 (2022)
11. Twomey, P., Cadman, R.: Agent-Based Modelling of Customer Behaviour in the Telecoms and Media Markets. info 4(1) (2002)
12. Mittal, A., Huang, W., Krejci, C.C.: Consumer-Adoption Modeling of Distributed Solar Using an Agent-Based Approach. In: CSS 2017. ACM (2017). https://doi.org/10.1145/3145574.3145602
13. Vanderlynden, J., Mathieu, P., Warlop, R.: Agent-Based Modeling of Context Effects in Consumer Choice. In: ECAI 2025, pp. 3622–3629. IOS Press (2025). https://doi.org/10.3233/FAIA251239
14. Vimaladhevi, N., Thaiyalnayaki, M.: Analyzing the Influence of Reference Groups on Consumer Brand Connectivity through Behavioral Modeling. In: GTSS 2026. IEEE (2026). https://doi.org/10.1109/GTSS68743.2026.11679887
15. Sturley, C.E.: A Proof of Concept Agent-Based Model of Consumer Store Choice Behaviour. MSc dissertation, University of Leeds (2016)
16. Sutton, R.S., Barto, A.G.: Reinforcement Learning: An Introduction, 2nd edn. MIT Press (2018)
17. Calvano, E., Calzolari, G., Denicolò, V., Pastorello, S.: Artificial Intelligence, Algorithmic Pricing, and Collusion. Am. Econ. Rev. 110(10), 3267–3297 (2020). https://doi.org/10.1257/aer.20190623

Fontes de dados: ANACOM (pacotes de serviços 1T2024, 3T2024, 2T2025, 4T2025, 1T2026; reclamações 2025 e 2T2026);
barómetro CNN Portugal/DECO PROteste (outubro 2025); DECO PROteste (penalizações, Lei 16/2022); Observador (preços DIGI, 2024).

Notas sobre o documento do Zé: o Wang & Wang foi publicado em 2017 (o DOI correto é …2520); no Griffin, os 54% referem-se
a mudanças de tarifário dentro da mesma operadora que aumentaram o sobrecusto face ao melhor plano, sem atribuição a
vieses; Venables & Bilge (1998) falta na lista de referências; Campos et al. (2013) não é citado no texto.

---

## 11. Registo de decisões e justificações

### 11.1 Preço da NOWO: €26,35
Mensalidade mínima de internet fixa + TV da NOWO em dezembro de 2024, com IVA, para contratos de 24 meses
(ANACOM, *O Sector das Comunicações 2024*, Tabela 20). É a única fonte oficial encontrada com o preço da NOWO
no mesmo tipo de oferta que as restantes operadoras.

### 11.2 Saída mensal de consumidores: d = 0,5%
- Dado: o número de subscritores de pacotes cresce ~1%/ano (ANACOM: 4,7 → 4,8 milhões). Isto fixa o saldo
  (entradas − saídas), mas não os valores brutos.
- Decisão: saídas de 0,5%/mês (~6%/ano) e entradas de ~0,58%/mês (~7%/ano).
- Justificação: valor intermédio que gera rotação suficiente para haver consumidores novos sem contrato
  (um canal de entrada da DIGI), sem dominar a dinâmica dos contratos de 24 meses.
- Como não há dado, o efeito é testado com d = 0,3% e 1%; as conclusões são reportadas com essa amplitude.

### 11.3 Qualidade a partir das reclamações: q = 0,80 − κ·ln(r), κ = 0,20
- O modelo precisa de uma qualidade entre 0 e 1; os dados são reclamações por mil clientes (ANACOM).
- r é a razão face à média dos incumbentes, o que permite comparar períodos com escalas diferentes (ano vs trimestre).
- Forma logarítmica: duplicar as reclamações reduz sempre a qualidade na mesma quantidade (0,14 com κ = 0,20).
- O valor 0,80 para o incumbente médio e κ = 0,20 são escolhas de modelação, não estimativas. Por isso o
  modelo corre também com κ = 0,10 e 0,30, e o relatório indica se as conclusões mudam.
- Resultado com κ = 0,20: MEO 0,848; NOS 0,784; Vodafone 0,776; DIGI 0,572 na entrada e 0,756 após 18 meses.

### 11.4 Qualidade da DIGI dependente do tempo
As reclamações da DIGI passaram de 3,1× para 1,25× a média dos incumbentes em ~18 meses, enquanto a quota
quase não mudou (+0,6 p.p.). A qualidade sobe com o tempo desde a entrada, e não com a quota.

### 11.5 Margem dos incumbentes: 40%
- Margens EBITDA de 2024: NOS 45,3% (EBITDA €767,6 M / receitas €1 696,3 M); MEO 35,8% (EBITDA €994 M /
  receitas €2 775 M). Média ponderada pelas receitas: 39,4%. A Vodafone Portugal deixou de publicar contas separadas.
- A margem EBITDA inclui custos fixos, por isso subestima a margem por cliente adicional. Com uma margem por cliente
  maior, baixar preços custa menos; por isso testa-se também 60%.
- A recompensa do reforço é a margem e não a receita: com 40% de margem, uma descida de 10% no preço reduz o lucro
  por cliente em 25% e exige ~33% mais clientes para compensar.

### 11.6 Fim do contrato e refidelização (decidido em 29/10)
- Decisão: no fim do contrato o consumidor decide como em qualquer outro mês e pode mudar sem penalização.
  A refidelização deixa de ser uma probabilidade fixa e passa a ser uma escolha do consumidor.
- Regra: se ficar, a operadora oferece um desconto δ = 10% por um novo contrato de 24 meses; o consumidor aceita
  se δ·p ≥ c_j, sendo c_j o seu custo de ficar preso.
- Justificação do custo c_j: Confraria et al. (2017, Tabela 4) estimam que os consumidores pagam €1,31/mês para
  reduzir o compromisso de 12 para 6 meses (≈ €0,22 por mês de compromisso). Para 24 meses, c ≈ €5,25/mês.
  Pressuposto: o custo cresce linearmente com a duração e é igual em euros para pacotes fixos.
- Justificação de δ = 10%: valor de referência que gera uma taxa de refidelização intermédia (com o preço da MEO,
  €4,25 de desconto; aceitam os consumidores com c_j abaixo desse valor, cerca de 30%). Testa-se δ = 5%, 15% e 20%.
- Verificação: Confraria et al. estimam que ~86% dos contratos móveis que terminam ficam na mesma operadora
  (13,6% saem). No modelo, a percentagem de consumidores que muda de operadora no fim do contrato deve ser da mesma ordem.

### 11.7 Confirmação de que a NOWO já era barata antes da DIGI
Tabela do idealista (janeiro 2024, pacotes com telemóvel): NOWO €30/mês (€20 nos primeiros 12 meses), NOS €60,99,
MEO €66,99, Vodafone €67,50. Na Tabela 20 da ANACOM (dezembro 2024): pacote 4P NOWO €36,25 contra ~€56 dos incumbentes.
A NOWO cobrava cerca de metade dos incumbentes e tinha apenas 2,6% de quota: o preço baixo, só por si, não garante
quota. Este facto reforça os mecanismos do modelo (hábito, norma, contratos e qualidade).

### 11.8 Desconto de refidelização calibrado: δ = 17,8% (em vez de 10%) — SUBSTITUÍDA pela 11.15
- Problema: com δ = 10% só os consumidores com custo de compromisso abaixo de €4,25 aceitam a refidelização.
  A percentagem de fidelizados desce de 70% para ~35% em dois anos, o que contradiz o valor inicial φ = 70%.
- Decisão: δ é calibrado para que a percentagem de fidelizados se mantenha em ~70% no mercado sem DIGI
  (`calibration/calibrate_pre_entry.py`). Resultado: δ = 0,178 (€7,56 de desconto no preço da MEO).
- Justificação: φ e δ não são independentes; fixar os dois sem dados cria uma incoerência. Mantém-se φ (valor de
  partida do grupo) e δ passa a ser consequência. Os descontos de fidelização observados nos tarifários
  (ex.: NOWO €20 nos primeiros 12 meses contra €30 depois, idealista 2024) são da mesma ordem ou superiores.
- Estado: confirmado pelo Pedro em 29/10 e **revertido pelo Pedro no mesmo dia (19:22)**: ver secção 11.15. Os resultados com δ = 17,8% ficam em `results/pricing_delta178/` e no commit e395505.

### 11.9 Constantes de marca (ASC) por operadora
- Sem constantes, o modelo não mantém as quotas observadas antes da entrada da DIGI (a norma favorece a maior
  operadora). Constantes por alternativa são prática habitual em modelos de escolha discreta.
- São calibradas para que, sem DIGI, as quotas médias fiquem nas da ANACOM (3T2024). MEO é a referência (0).
- Valores finais (para w = 0,10): NOS +0,0280; Vodafone +0,0168; NOWO/DIGI −0,0837.
- A constante da posição 3 passa da NOWO para a DIGI. Pressuposto: a DIGI herda a posição de marca da NOWO;
  a diferença entre as duas é captada pelo preço e pela qualidade.

### 11.10 Peso da norma (w) e exploração (ε)
- Grelha grossa: w ∈ {0,10; 0,15; 0,25; 0,40} × ε ∈ {0,0025; 0,005; 0,01; 0,02}. Com w ≥ 0,25 a DIGI chega a 11–25%,
  porque o peso do preço θ está ligado a w (secção 4). Com w = 0,15 a DIGI cresce demasiado depressa.
- Grelha fina: w ∈ {0,08; 0,10; 0,12; 0,13} × ε ∈ {0,01; 0,02; 0,03; 0,05}, 24 corridas por ponto.
  Melhor ponto: w = 0,10, ε = 0,02 (DIGI 2,76 / 3,06 / 3,38% nos meses 19 / 25 / 28; RMSE 0,11 p.p.).
  Resultados em `results/v2/calibration_entry.csv` e `calibration_entry_fine.csv`.
- Depois da correção da secção 11.11, ε passa para 0,03 (RMSE 0,18 p.p. com 48 corridas; 0,02 dá 0,36 p.p.;
  0,025 dá 0,23 p.p.). DIGI: 2,53 / 2,85 / 3,14%, dentro do critério de aceitação (3,2% ± 0,5 p.p. no mês 28).
- Conjunto final em `consumer_choice/calibrated.py`: w = 0,10; ε = 0,03; δ = 0,178; ρ = 0,78; ASC acima.

### 11.11 Contratos iniciais com preço de refidelização: ρ = 78% (com δ = 17,8%; com δ = 10%, ρ = 48%, secção 11.15)
- Problema: no início todos os fidelizados pagavam o preço de tabela. Como 78% dos contratos assinados em regime
  são refidelizações com desconto, o preço médio pago caía de €41,6 para €37,4 em 36 meses. Esta queda é um
  artefacto da inicialização e enviesaria a recompensa das operadoras que aprendem (o lucro cairia mesmo sem
  mudança de preço).
- Decisão: 78% dos contratos iniciais têm o preço com desconto. O valor é o ponto fixo do modelo: a proporção de
  refidelizações entre os contratos assinados nos meses 24–72 (`calibration/calibrate_long.py`).
- Resultado: preço médio pago estável (€37,6 no mês 0 e no mês 12; €37,0 no mês 72). Referência: ARPU de pacotes
  da ANACOM no 1T2026, €39,59.

### 11.12 Limitações encontradas na calibração
- **Deriva lenta das quotas sem DIGI.** Em 72 meses a MEO passa de 42,5% para 46%, a NOS de 34% para 31% e a NOWO
  de 2,6% para 1,5%; a percentagem de fidelizados sobe de 69% para 78%. A causa é o reforço da norma (a maior
  operadora atrai mais). Tentou-se calibrar as constantes para o longo prazo (`calibrate_long.py`), mas o
  processo oscilou entre MEO e NOS: o equilíbrio de longo prazo é muito sensível à diferença entre as constantes.
  Decisão: manter a calibração de curto prazo (válida para o período com dados, meses 0–30) e comparar todos os
  cenários com o contrafactual sem DIGI e com os mesmos números aleatórios. A deriva é comum a todos os cenários.
- **Mudanças no fim do contrato.** No modelo ~0,6–1% dos consumidores mudam de operadora no fim do contrato; Confraria
  et al. estimam 13,6% (rede móvel, 2014). A rotação anual do modelo é ~2–3%. O modelo subestima a mobilidade; a
  entrada da DIGI é lenta no modelo como na realidade, mas por um canal de mudança mais estreito. Fica como limitação.

### 11.13 Desenho da aprendizagem (tarefa 5)
- Braços de preço: ×{1,00; 0,95; 0,90; 0,85; 0,80} do preço de lista (plano acordado). O braço mais baixo (€34 para
  MEO/NOS) fica acima do custo unitário (60% do preço de lista), por isso nenhum braço dá prejuízo por cliente.
- Decisão de 3 em 3 meses: as operadoras não mudam preços todos os meses; com contratos de 24 meses o efeito de uma
  mudança de preço só aparece nos clientes novos, renovações e sem contrato.
- Valores iniciais: o lucro do primeiro trimestre com o preço de lista, para todos os braços. Como o lucro cai com
  a entrada da DIGI, os braços ainda não testados ficam acima do braço atual: isto obriga a experimentar todos os
  braços no início (valores iniciais otimistas, Sutton & Barto, 2018, sec. 2.6).
- Passo constante α (e não média simples): o ambiente não é estacionário (as outras operadoras também aprendem e a
  qualidade da DIGI melhora).
- Horizonte: 120 meses depois da entrada (40 decisões). Resultados lidos a 5 e a 10 anos.
- Cenários de referência com os mesmos números aleatórios: sem DIGI; os três incumbentes a ×1,00 … ×0,80;
  um incumbente sozinho a ×0,90 ou ×0,80 (testa se manter o preço de lista é a melhor resposta).
- Sensibilidade: ε ∈ {0,05; 0,10; 0,20} × α ∈ {0,1; 0,2; 0,4}; 30 corridas por cenário.

### 11.14 Resultados das fases 3 e 4 (30 corridas por cenário, mesmos números aleatórios)
Lucro acumulado nos 10 anos depois da entrada; diferenças em % face a "todos ao preço de lista" (pareadas por seed).
Ficheiros: `results/pricing/tables/` e `results/pricing/figures/`.
- **Contrafactual sem DIGI:** lucro conjunto dos incumbentes +9,4%. A entrada custa ~9% do lucro com preços fixos.
- **Descidas comuns:** todos a 0,95 → −9,3%; 0,90 → −18,7%; 0,80 → −44,0%. Travam a DIGI (quota a 10 anos de 18,7%
  com preços de lista para 6,3% a 0,90 e 0,7% a 0,80), mas não compensam em lucro.
- **Descida unilateral (melhor resposta):** NOS sozinha a 0,90 → +26,5% de lucro para a NOS; Vodafone sozinha a 0,90 → +29,3%;
  MEO sozinha a 0,90 → −0,9%. Manter o preço de lista não é um equilíbrio para a NOS nem para a Vodafone: há incentivo
  a desviar (dilema do prisioneiro). A MEO, líder, não ganha com a descida.
- **Preços aprendidos (bandit, ε = 0,1, α = 0,2):** multiplicador médio 0,95; nos anos 6–10 o preço de lista é escolhido em 77% (MEO),
  63% (NOS) e 68% (Vodafone) das decisões. Lucro conjunto −6,0% face ao preço de lista, acima de qualquer descida comum ≥ 5%.
  Quota da DIGI a 10 anos: 10,6%.
- **Sensibilidade:** com as nove combinações (ε, α) o lucro conjunto fica entre −3,2% e −9,3% e o multiplicador médio
  entre 0,94 e 0,97. Um α maior (esquece mais depressa) leva a preços mais altos e mais lucro. As conclusões não
  dependem da escolha de (ε, α).
- **Interpretação:** os algoritmos não comunicam, mas acabam perto do preço de lista: os ensaios de descida coincidem
  com a perda de lucro causada pela entrada, e a punição implícita (os outros também descem) torna as descidas pouco
  rentáveis. É compatível com Calvano et al. (2020) e com o comportamento observado: os incumbentes não baixaram as
  marcas principais e responderam com marcas low-cost.
- **Cuidado na leitura:** o horizonte de 10 anos ultrapassa o período com dados (30 meses); os valores de longo prazo
  são comparações entre cenários e não previsões.

### 11.15 Reversão para δ = 10% (decisão do Pedro, 29/10, 19:22)
- **Decisão:** o desconto de refidelização volta a 10%. Os 70% de fidelizados são apenas o ponto de partida; a
  percentagem de fidelizados não é um alvo da calibração e evolui com as decisões dos consumidores.
- **Justificação (Pedro):** o objetivo do modelo é perceber se os consumidores mudam de operadora em função da
  informação que têm, da rede de amigos, do preço e da qualidade, e não forçar que fiquem. Calibrar δ para manter
  70% de fidelizados impunha ao modelo um resultado que devia ser consequência do comportamento dos consumidores.
- **Consequência no modelo sem DIGI:** os fidelizados descem de 70% para ~37% em 2 anos e estabilizam em ~40%.
  O preço médio pago fica em ~€40,6–40,9 (ARPU de pacotes da ANACOM no 1T2026: €39,59; com δ = 17,8% era €37,1).
- **Recalibração (todos os outros valores mantêm a lógica das secções 11.9–11.11):**
  - ρ = 0,48 (ponto fixo com δ = 10%: proporção de refidelizações entre os contratos assinados nos meses 24–72).
  - Grelha w ∈ {0,08; 0,10; 0,12} × ε ∈ {0,005; 0,01; 0,02; 0,03}, 24 corridas por ponto
    (`calibration/calibrate_entry.py delta10`, resultados em `results/v2/calibration_entry_delta10.csv`).
    Melhor: (0,12; 0,005) com RMSE 0,12 p.p.; segundo: (0,10; 0,02) com 0,15 p.p.
    Escolhe-se (0,10; 0,02): mantém w = 0,10 e dá uma rotação anual mais próxima dos dados (2,7% contra 2,1%).
  - Constantes de marca: NOS +0,0307; Vodafone +0,0161; NOWO/DIGI −0,0820.
  - Validação com 48 corridas: DIGI 2,53 / 2,96 / 3,37% nos meses 19 / 25 / 28 (ANACOM 2,8 / 3,0 / 3,2); RMSE 0,18 p.p.
- **Efeito secundário:** sem DIGI, a deriva das quotas quase desaparece (MEO 41,3% → 40,9% e NOS 35,3% → 35,3%
  em 60 meses; com δ = 17,8% a MEO ganhava ~3,5 p.p.). A NOWO continua a perder quota sem a entrada (2,8% → 1,5%).
  A limitação da secção 11.12 sobre a deriva fica muito reduzida.

### 11.16 Resultados das fases 3 e 4 com δ = 10% (substituem os da secção 11.14)
Mesmo desenho da 11.14 (30 corridas por cenário, mesmos números aleatórios, lucro acumulado em 10 anos).
Os resultados com δ = 17,8% estão em `results/pricing_delta178/`.
- Contrafactual sem DIGI: lucro conjunto +11,4% face a "todos ao preço de lista".
- Descidas comuns: ×0,95 → −9,1%; ×0,90 → −17,5%; ×0,85 → −28,4%; ×0,80 → −41,2%.
  Quota da DIGI a 10 anos: 22,6% (lista), 16,7%, 7,9%, 1,9%, 0,8%.
- Descida unilateral a ×0,90: MEO +14,9%, NOS +19,3%, Vodafone +36,2% de lucro próprio. Com δ = 10% os três têm
  incentivo a desviar (com 17,8% a MEO não tinha): dilema do prisioneiro completo.
- Bandit (ε = 0,1, α = 0,2): lucro conjunto −3,2%; multiplicador médio 0,97; preço de lista escolhido em 75% (MEO),
  76% (NOS) e 78% (Vodafone) das decisões dos anos 6–10; DIGI a 10 anos 15,7%.
- Sensibilidade (9 combinações de ε e α): lucro conjunto entre −1,6% e −5,6%; multiplicador médio entre 0,96 e 0,98.
- As conclusões qualitativas da 11.14 mantêm-se e ficam mais fortes.
