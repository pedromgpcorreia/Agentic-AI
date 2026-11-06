"""Builds the project report (Word, LNCS template) from the results of the analysis.

Usage (from the repository root):  python report/build_report.py
Requires: python-docx, and report/template_lncs.docx (the course template).
"""
import copy
import json
import os
import re
from decimal import ROUND_HALF_UP, Decimal

import docx
import pandas as pd
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = f"{ROOT}/report/template_lncs.docx"
OUT = f"{ROOT}/report/Report_Consumer_Choice.docx"
FIG = f"{ROOT}/results/figures"
TAB = f"{ROOT}/results/tables"
S = json.load(open(f"{TAB}/summary.json"))
TEXT_W = 122  # mm, LNCS printing area

doc = docx.Document(TEMPLATE)
body = doc.element.body
for el in list(body):
    if el.tag != qn("w:sectPr"):
        body.remove(el)
KEEP = os.environ.get("KEEP", "1") == "1"
counters = {"table": 0, "fig": 0, "listing": 0}


# ---------------------------------------------------------------- helpers
def add_runs(par, text, size=None):
    """Minimal inline markup: *italic*, `code`, **bold**, ^sup^, ~sub~."""
    for tok in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\^[^^]+\^|~[^~]+~)", text):
        if not tok:
            continue
        if tok.startswith("**"):
            r = par.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith("*"):
            r = par.add_run(tok[1:-1]); r.italic = True
        elif tok.startswith("`"):
            r = par.add_run(tok[1:-1]); r.font.name = "Courier New"
            r.font.size = Pt(size - 1 if size else 8.5)
            r._element.rPr.rFonts.set(qn("w:hAnsi"), "Courier New")
        elif tok.startswith("^"):
            r = par.add_run(tok[1:-1]); r.font.superscript = True
        elif tok.startswith("~"):
            r = par.add_run(tok[1:-1]); r.font.subscript = True
        else:
            r = par.add_run(tok)
        if size and not tok.startswith("`"):
            r.font.size = Pt(size)
    return par


_after_heading = [True]


def P(text, style=None):
    style = style or ("p1a" if _after_heading[0] else "Normal")
    _after_heading[0] = False
    return add_runs(doc.add_paragraph(style=style), text)


def H1(text):
    _after_heading[0] = True
    doc.add_paragraph(text, style="heading1")


def H2(text):
    _after_heading[0] = True
    doc.add_paragraph(text, style="heading2")


def H3(title, text):
    """Run-in heading (LNCS 3rd level): bold title followed by text."""
    p = doc.add_paragraph(style="heading3")
    r = p.add_run(title + " "); r.bold = True
    add_runs(p, text)
    for rr in p.runs[1:]:
        rr.bold = False
    _after_heading[0] = False
    return p


def bullets(items):
    for it in items:
        p = doc.add_paragraph(style="Normal")
        p.paragraph_format.left_indent = Mm(5)
        p.paragraph_format.first_line_indent = Mm(-3.5)
        add_runs(p, "• " + it)


def caption(kind, text):
    counters[kind] += 1
    n = counters[kind]
    label = {"table": "Table", "fig": "Fig.", "listing": "Listing"}[kind]
    style = "table title" if kind == "table" else "figure legend"
    p = doc.add_paragraph(style=style)
    p.paragraph_format.keep_with_next = (kind == "table")
    r = p.add_run(f"{label} {n}. "); r.bold = True
    add_runs(p, text)
    return n


def set_cell_border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders"); tcPr.append(b)
    for edge, val in kw.items():
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), str(val)); e.set(qn("w:color"), "000000")
        b.append(e)


def table(cap, header, rows, widths, size=7.5, align=None):
    """LNCS-style table: caption above, rules at top, below header and at bottom."""
    caption("table", cap)
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tblPr = t._tbl.tblPr
    for i, row in enumerate([header] + rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.width = Mm(widths[j])
            p = c.paragraphs[0]
            p.style = doc.styles["Normal"]
            pf = p.paragraph_format
            pf.first_line_indent = Mm(0); pf.space_before = Pt(1); pf.space_after = Pt(1)
            pf.line_spacing = 1.0
            pf.keep_with_next = i < len(rows)       # keep the table on one page
            if align and align[j] == "r":
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_runs(p, str(val), size=size)
            if i == 0:
                for rr in p.runs:
                    rr.bold = True
            if i == 0:
                set_cell_border(c, top=8, bottom=4)
            if i == len(rows):
                set_cell_border(c, bottom=8)
    for j, w in enumerate(widths):
        for cell in t.columns[j].cells:
            cell.width = Mm(w)
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(Mm(w).twips)))
    tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(int(Mm(sum(widths)).twips))); tw.set(qn("w:type"), "dxa")
    old = tblPr.find(qn("w:tblW"))
    if old is not None:
        tblPr.remove(old)
    tblPr.append(tw)
    order = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
             "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders",
             "shd", "tblLayout", "tblCellMar", "tblLook"]
    kids = sorted(list(tblPr), key=lambda e: order.index(e.tag.split("}")[1])
                  if e.tag.split("}")[1] in order else len(order))
    for k in kids:
        tblPr.remove(k)
        tblPr.append(k)
    doc.add_paragraph(style="Normal").paragraph_format.space_after = Pt(0)
    return t


def span(file, start, end):
    """Line numbers (1-based) from the first line containing `start`
    to the first following line containing `end`."""
    lines = open(f"{ROOT}/{file}").read().splitlines()
    a = next(i for i, l in enumerate(lines) if start in l)
    b = next(i for i in range(a, len(lines)) if end in lines[i])
    return (a + 1, b + 1)


def listing(file, segments, cap):
    """Code excerpt from the repository with its original line numbers."""
    lines = open(f"{ROOT}/{file}").read().splitlines()
    segments = [span(file, *seg) if isinstance(seg[0], str) else seg
                for seg in segments]
    p = doc.add_paragraph(style="programcode")
    p.paragraph_format.keep_together = KEEP
    # common indentation removed so that code inside classes fits the printing area
    shown = [lines[n - 1] for a, b in segments for n in range(a, b + 1) if lines[n - 1].strip()]
    cut = min(len(x) - len(x.lstrip()) for x in shown)
    first = True
    for k, (a, b) in enumerate(segments):
        if k:
            p.add_run().add_break(); p.add_run("   ...")
        for n in range(a, b + 1):
            if not first:
                p.add_run().add_break()
            first = False
            r = p.add_run(f"{n:>3}  {lines[n - 1][cut:]}")
            r.font.size = Pt(7)
            r.font.name = "Courier New"
            r._element.rPr.rFonts.set(qn("w:hAnsi"), "Courier New")
            r._element.rPr.rFonts.set(qn("w:cs"), "Courier New")
    rng = ", ".join(f"{a}–{b}" for a, b in segments)
    caption("listing", f"{cap} (`{file}`, lines {rng}).")


def figure(path, cap, width=TEXT_W):
    p = doc.add_paragraph(style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Mm(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Mm(width))
    caption("fig", cap)


def half_up(x, d):
    """Round half up on the decimal value (0.5065 -> 0.507), not on its binary approximation."""
    return str(Decimal(repr(round(float(x), 9))).quantize(Decimal(1).scaleb(-d), ROUND_HALF_UP))


def f2(x):
    return half_up(x, 2)


def f3(x):
    return half_up(x, 3)


# ---------------------------------------------------------------- numbers
B = S["baseline"]
Bo, Bb, Bc = B["Orange market share"], B["Blue market share"], B["Consumer clustering"]
OUTC = S["baseline_outcomes"]
HZ = {r["tick"]: r for r in S["baseline_horizon"]}
CI100, CIALL = S["ci_halfwidth_at_100_runs"], S["ci_halfwidth_at_all_runs"]
SN = {r["norm_influence"]: r for r in S["sensitivity_norm_influence"]}
SQ = {r["quality_blue"]: r for r in S["sensitivity_quality_blue"]}
SE = {r["exploration"]: r for r in S["sensitivity_exploration"]}
RUNS = OUTC["runs"]

# ---------------------------------------------------------------- numbers, new model (tasks 3 to 6)
PR = f"{ROOT}/results/pricing"
SC = pd.read_csv(f"{PR}/tables/scenarios.csv").set_index("scenario")
PA = pd.read_csv(f"{PR}/tables/paired_vs_fixed_1.00.csv").set_index("scenario")
RP = pd.read_csv(f"{PR}/runs.csv")
SER = pd.read_csv(f"{PR}/series.csv.gz")
FX = SER[SER.scenario == "fixed_1.00"].set_index("month")
NE = SER[SER.scenario == "no_entry"].set_index("month")
BAND = "bandit_e0.10_a0.2"
LOG = pd.read_csv(f"{PR}/bandit_log.csv.gz")
LATE = LOG[(LOG.scenario == BAND) & (LOG.month > 72)]           # years 6 to 10 after the entry
SENS = pd.read_csv(f"{ROOT}/results/sensitivity/tables/summary.csv").set_index("variant")
OPS = ("MEO", "NOS", "Vodafone")
N_P = int(SC.loc["fixed_1.00", "n"])
N_S = int(SENS.loc["base", "seeds"])
ANACOM = {19: 2.8, 25: 3.0, 28: 3.2}                             # DIGI/NOWO share (%)
CAL = {m: FX.share_DIGI[m] * 100 for m in ANACOM}
RMSE = (sum((CAL[m] - v) ** 2 for m, v in ANACOM.items()) / len(ANACOM)) ** 0.5
LIST_PCT = {o: (LATE[LATE.operator == o].new_arm == 1.0).mean() * 100 for o in OPS}
LIST_GREEDY = (LATE[~LATE.explored].new_arm == 1.0).mean() * 100
MULT =json.load(open(f"{PR}/tables/summary.json"))["bandit_sensitivity"]["mean_multiplier"]
DIGI_END = RP[RP.scenario == "fixed_1.00"].share_DIGI_end * 100


def sg(x, d=1):
    """Signed value with a typographic minus sign."""
    return f"{x:+.{d}f}".replace("-", "−")


def dp(s, who="incumbents"):
    r = PA.loc[s]
    return r[f"dprofit_{who}_pct"], r[f"dprofit_{who}_lo"], r[f"dprofit_{who}_hi"]


def dps(s, who="incumbents"):
    m, lo, hi = dp(s, who)
    return f"{sg(m)}% (95% CI {sg(lo)} to {sg(hi)})"


def dpc(s, who="incumbents"):
    m, lo, hi = dp(s, who)
    return f"{sg(m)}% ({sg(lo)} to {sg(hi)})"


def nt(k=1):
    """Number of the next table (tables are numbered as they are added)."""
    return counters["table"] + k


def ds(s):
    """DIGI share in year 10 (%, mean of the last 12 months)."""
    return SC.loc[s, "share_DIGI_end"] * 100


ALL_SOLO = [SENS[f"solo_{o}_pct"] for o in OPS]
SENS_V = SENS.drop(index="base")

# ================================================================ front matter
doc.add_paragraph("Consumer Choice and the Entry of DIGI: An Agent-Based Model of the "
                  "Portuguese Market of Bundled Services with Learning Incumbents",
                  style="title")
doc.add_paragraph("[Author 1], [Author 2], [Author 3], [Author 4]", style="author")
doc.add_paragraph("[Institution], [Programme]", style="authorinfo")
doc.add_paragraph("{[student1], [student2], [student3], [student4]}@[domain]", style="email")

ab = doc.add_paragraph(style="abstract")
r = ab.add_run("Abstract."); r.bold = True
add_runs(ab, " This report analyses the Consumer Choice model, an agent-based model in which "
         "consumers choose between products under the influence of habits, information from "
         "friends and social norms, and adapts it to the entry of DIGI into the Portuguese "
         "market of bundled services. The baseline was implemented in Python with Mesa 3 and "
         f"replicated {RUNS} times. Clustering reaches {f2(Bc['mean'])} and the final market "
         f"share varies widely between runs (standard deviation {f2(Bo['sd'])}). The new model "
         "has four operators, prices, loyalty contracts with legal exit penalties, a quality "
         "measure built from complaints and a changing population. It is calibrated to the "
         f"market shares published by ANACOM and reproduces the slow growth of DIGI (RMSE "
         f"{RMSE:.2f} percentage points). The three incumbents then learn their prices with an "
         "ε-greedy multi-armed bandit. Each incumbent would gain by cutting its price alone, but "
         f"joint profit falls by {abs(dp('fixed_0.90')[0]):.1f}% if all cut by 10%, a prisoner’s "
         "dilemma. The learning incumbents return to the list price in most decisions and lose "
         f"only {abs(dp(BAND)[0]):.1f}% of joint profit. A sensitivity analysis that changes "
         "six assumptions one at a time, in nine variants, confirms both conclusions.")
kw = doc.add_paragraph(style="abstract")
r = kw.add_run("Keywords:"); r.bold = True
kw.add_run(" Agent-based modelling, Consumer behaviour, Social influence, Telecommunications, "
           "Reinforcement learning, Mesa.")

# ================================================================ 1 Introduction
H1("1   Introduction")
P("This report covers the six tasks of Project 1 of the course Multi-Agent Systems and "
  "Simulation of Organizations. The tasks are to analyse a model and define a baseline, to run "
  "it many times to obtain reliable statistics, to fit it to a real situation, to support the "
  "new model with scientific articles, to extend it with agent learning, and to run, analyse "
  "and discuss the new model.")
P("The chosen model is Consumer Choice [1], from the NetLogo Models Library [2]. It derives "
  "from a basic model by M. A. Janssen and from earlier work on habits and social processes in "
  "market dynamics [3]. It simulates "
  "a market with two competing products whose quality can change. Consumers are linked in a "
  "social network and choose a product according to three mechanisms: habit, informative "
  "social influence (learning about quality from friends) and normative social influence "
  "(using the same product as the majority of friends) [4]. The model shows how these "
  "mechanisms produce clusters of consumption, tipping points and social lock-in, a situation "
  "in which a product of lower quality keeps its market because it is the norm [5].")
P("The real case is the entry of DIGI into the Portuguese market of bundled services in "
  "November 2024. DIGI sells fibre and television for about half the price of MEO, NOS and "
  "Vodafone, with a commitment of 3 months instead of 24. Even so, its share, together with "
  "NOWO, which it acquired, grew only from 2.6% to 3.2% in about 18 months [8]. The new model "
  "asks why a much cheaper operator grows so slowly, and how the incumbents should respond on "
  "price. Habit, social influence and loyalty contracts are the mechanisms that can explain "
  "the first question, and the Consumer Choice model already contains the first two.")
P("Both models were implemented in Python with the Mesa 3 framework [6]. The baseline follows "
  "the NetLogo code rule by rule. Section 2 describes it along the lines of the ODD protocol "
  "[7] and Section 3 presents the baseline experiments. Section 4 describes the new model, its "
  "data, its calibration and the learning incumbents. Section 5 presents the results of the "
  "new model and its sensitivity analysis, and Section 6 concludes. The code, data and figures "
  "are available in the project repository.")

# ================================================================ 2 Model
H1("2   Model Description")
H2("2.1   Purpose and Entities")
P("The purpose of the model is to explain how habits and social influence shape the market "
  "shares of two products, and why consumers may fail to adopt a product of higher quality. "
  "The model contains one type of agent, the consumer. The social network and the products are "
  "not agents (Table 1).")
table("Entities of the model.",
      ["Entity", "Represents", "Role in the model"],
      [["Consumer (100)", "A person who buys one of two products",
        "The only agent type. It chooses a product, learns about quality and influences its friends"],
       ["Link (≈250)", "A friendship",
        "Channel through which information and norms are transmitted. The network is fixed during a run"],
       ["Product: orange (0) and blue (1)", "Two competing brands",
        "Defined by global parameters (`quality_orange`, `quality_blue`) that can be changed during a run"]],
      [30, 34, 58])
P("Time is discrete. In each tick all consumers first execute the consumption decision and "
  "then update their utilities. Within each phase the consumers are activated in random order "
  "(Listing 1). The outputs are recorded at the end of each tick.")
listing("consumer_choice/model.py", [("def step(self)", "datacollector.collect(self)")], "Schedule of one tick")

H2("2.2   State Variables of the Consumer")
P("Each consumer holds five state variables (Table 2, Listing 2), and a position used only to "
  "build the network (Sect. 2.3). The variable `satisfaction` links "
  "product quality to habit: it is the probability that the consumer keeps its current "
  "product without considering the alternative. The variable `personal_experience` is the "
  "memory of the consumer. It is updated only for the product in use and may therefore become "
  "outdated when the quality of the other product changes.")
table("State variables of the consumer.",
      ["Variable", "Values", "Role", "Consequence"],
      [["`choice`", "0 (orange) or 1 (blue)", "Product in use",
        "Counts for the market share. It is what friends observe when they compute the norm"],
       ["`satisfaction`", "log10(1 + 9q) of the product in use", "Probability of keeping the product (habit)",
        "With q = 0.5 it equals 0.74. Higher quality produces stronger habits and less attention to the alternative"],
       ["`personal_experience`", "Remembered quality of each product, initially [0, 0]",
        "Memory of the consumer", "A product never used is valued at 0, and a change in the quality of the unused product is not perceived"],
       ["`utilities`", "Total utility of each product", "Basis of the choice when the consumer neither keeps nor explores",
        "Combines norm and product utility (Sect. 2.4)"],
       ["`friends`", "List of linked consumers", "Social network of the consumer",
        "Source of information and of the norm"]],
      [32, 27, 27, 36])
listing("consumer_choice/model.py", [("class Consumer(", "self.friends = []")], "Consumer state variables")

H2("2.3   Social Network")
P("Each consumer is placed at a random position in a 51 × 51 space. Links are created one at "
  "a time: a random consumer is linked to the nearest consumer to which it is not yet linked, "
  "until the number of links equals `avg_connections` × `num_consumers` / 2 (250 in the "
  "baseline). The position is used only for this purpose (Listing 3). Because links connect "
  "nearby consumers, the network is local: friends of a consumer tend to be friends of each "
  "other. This property favours the formation of clusters of consumers that use the same "
  "product.")
listing("consumer_choice/model.py", [("def build_network", "links += 1")], "Construction of the social network")

H2("2.4   Actions of the Consumer")
H3("Consumption Decision.", "In each tick the consumer applies three rules in sequence "
   "(Listing 4). First, with probability equal to `satisfaction`, it keeps the current product "
   "(habit). Second, if it did not keep the product, it switches to the other product with "
   "probability `exploration`. Third, if it neither kept nor explored, it chooses the product "
   "with the higher utility. If both utilities are equal, it keeps the current product. "
   "Satisfaction is then recomputed for the product in use. In the baseline the probability "
   "of exploring in a given tick is (1 − 0.74) × 0.01 ≈ 0.003.")
listing("consumer_choice/model.py", [("def consume(self)", "self.satisfaction = self.model.satisfaction(self.choice)"), ("def satisfaction(self, choice)", "return math.log10")], "Consumption decision and satisfaction")
H3("Utility Update.", "After the consumption phase, each consumer computes the utility of "
   "each product (Listing 5) in four steps: (1) the experience of the product in use is set to "
   "its current quality, (2) with probability `information_exchange`, and only if at least one "
   "friend uses the product, the consumer receives the current quality of that product, "
   "(3) the norm-based utility is the share of friends who use the product, and (4) the total "
   "utility is")
p = doc.add_paragraph(style="Normal"); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_runs(p, "*U* = *w* · *N* + (1 − *w*) · (*E* + *I*) / 2 ,")
P("where *w* is `norm_influence`, *N* the share of friends using the product, *E* the "
  "remembered quality and *I* the quality reported by friends (0 if no information was "
  "received). Without information from friends, the product utility is half of the "
  "remembered quality. As a result, information exchange favours the product that friends "
  "already use, in the same direction as the norm.")
listing("consumer_choice/model.py", [("def update_utilities", "(1 - m.norm_influence) * prod_util)")], "Utility update")
P("Table 3 summarises the actions and their consequences.")
table("Actions of the consumer, in the order in which they are executed.",
      ["Action", "When", "Consequence"],
      [["Keep the product (habit)", "With probability `satisfaction`",
        "No change. The consumer does not consider the alternative, so improvements of the other product are not perceived"],
       ["Explore", "If not kept, with probability `exploration`",
        "Switches to the other product and learns its actual quality in the next update. It is the only way to discover an improvement of a product that no friend uses"],
       ["Choose by utility", "If neither kept nor explored, and utilities differ",
        "Selects the product with the higher utility. In a tie it keeps the current product"],
       ["Update experience", "Every tick, for the product in use", "Memory of that product equals its current quality"],
       ["Ask friends", "For each product, with probability `information_exchange`, if a friend uses it",
        "Receives the current quality. Reinforces the product used by friends"],
       ["Observe the norm", "Every tick", "Pulls utility towards the local majority. Produces clusters and can produce lock-in"]],
      [28, 38, 56])
P("Taken together, habit slows down change, exploration is the only source of new "
  "information about an unused product, and information exchange and the norm reinforce the "
  "product that is already used by friends. These mechanisms produce the three patterns "
  "described by the authors of the model: clustering of consumption, amplification of small "
  "differences in quality and social lock-in [1].")

H2("2.5   Global Parameters and Baseline")
P("The model has eight parameters (Listing 6). The baseline uses the default values of the "
  "original model file (Table 4).")
listing("consumer_choice/model.py", [("def __init__(self, num_consumers", "self.quality = [quality_orange")], "Model parameters and their baseline values")
table("Global parameters, baseline values and role. The last column summarises the effect "
      "measured in Sect. 3.3. Parameters marked “not tested” were kept at the baseline value.",
      ["Parameter", "Baseline", "Role", "Effect of increasing the value"],
      [["`num_consumers`", "100", "Size of the market", "Not tested"],
       ["`avg_connections`", "5", "Average number of friends", "Not tested"],
       ["`initial_pct_orange`", "50", "Initial share of orange consumers", "Not tested"],
       ["`norm_influence`", "0.15", "Weight of the norm against product utility",
        f"From 0 to 0.1, mean clustering rises from {f2(SN[0.0]['clustering_mean'])} to {f2(SN[0.1]['clustering_mean'])}. Above 0.1 it changes little"],
       ["`information_exchange`", "0.05", "Probability of learning from friends", "Not tested"],
       ["`exploration`", "0.01", "Probability of trying the other product",
        f"At 0.2, mean clustering falls to {f2(SE[0.2]['clustering_mean'])} and the dispersion of market shares decreases"],
       ["`quality_orange`", "0.5", "Quality of the orange product", "Not tested (reference value)"],
       ["`quality_blue`", "0.5", "Quality of the blue product",
        f"A difference of 0.05 gives the better product {round((1 - SQ[0.55]['orange_mean']) * 100)}–{round(SQ[0.45]['orange_mean'] * 100)}% of the market (mean)"]],
      [33, 15, 31, 43])

H2("2.6   Model Outputs")
P("The original model reports two plots: the market shares of the two products and the "
  "clustering of consumers. The implementation records the same three quantities at every "
  "tick with a Mesa `DataCollector` (Listing 7, Table 5). The analysis in Section 3 uses only "
  "these outputs.")
listing("consumer_choice/model.py", [("self.datacollector = mesa.DataCollector", "self.datacollector.collect(self)"), ("def count_choice", "return total / self.num_consumers")], "Model outputs")
table("Outputs of the model.",
      ["Output", "Definition", "Interpretation"],
      [["Orange consumers", "Number of consumers with `choice` = 0", "Market share of the orange product (out of 100)"],
       ["Blue consumers", "Number of consumers with `choice` = 1", "Market share of the blue product (out of 100)"],
       ["Clustering", "Mean, over consumers, of the share of friends that use the same product",
        "1: all friends use the same product. ≈0.5: choices independent of friends"]],
      [27, 50, 45])

H2("2.7   Notes on the Implementation")
P("Three differences between the description in the Info tab of the original model and its "
  "code were found. The implementation follows the code:")
bullets(["The Info tab states a default `exploration` of 0.05, but the model file uses 0.01.",
         "The Info tab states that friends may share outdated information. In the code, a friend "
         "always reports the current quality of the product.",
         "The Info tab states that less satisfied consumers seek more information. In the code, "
         "the probability of information exchange does not depend on satisfaction. Satisfaction "
         "only determines whether the utilities are used in the decision."])

# ================================================================ 3 Results
H1("3   Baseline Simulation and Statistical Analysis")
H2("3.1   Experimental Setup")
P(f"The baseline was replicated {RUNS} times with different random seeds (0 to {RUNS - 1}), "
  "for 2000 ticks each, with the outputs recorded at every tick. The statistics are reported "
  "at tick 1000, and ticks 1500 and 2000 are used to check the horizon. For the sensitivity "
  "analysis, three parameters were varied one at a time, with 100 replications per value and "
  "1000 ticks per run (Table 6). The same 100 seeds were used for every value of a parameter "
  "(common random numbers), so that differences between values are not due to different "
  "random draws. The experiments use the Mesa `batch_run` function (Listing 8).")
table("Experimental design.",
      ["Experiment", "Parameter values", "Runs per value", "Ticks"],
      [["Baseline", "Table 4", str(RUNS), "2000"],
       ["Norm", "`norm_influence` = 0, 0.1, …, 1.0", "100", "1000"],
       ["Quality", "`quality_blue` = 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7", "100", "1000"],
       ["Exploration", "`exploration` = 0, 0.01, 0.05, 0.1, 0.2", "100", "1000"]],
      [22, 62, 20, 18])
listing("experiments/run_experiments.py", [("BASELINE = dict(", "quality_orange=0.5, quality_blue=0.5)"), ("results = batch_run(", "display_progress=False)")], "Baseline values and batch run")
P("For each output we report the mean, the standard deviation (SD), the 95% confidence "
  "interval of the mean (Student’s *t*), the median and the 5th and 95th percentiles "
  "(P5, P95). Market shares are expressed as fractions of the 100 consumers.")
H3("Number of Runs.", "Figure 2 shows the mean of each output at tick 1000 as a function of the "
   f"number of runs. With 100 runs, the half-width of the 95% confidence interval is "
   f"{f3(CI100['orange_share'])} for the orange share and {f3(CI100['clustering'])} for "
   f"clustering. With {RUNS} runs it is {f3(CIALL['orange_share'])} and "
   f"{f3(CIALL['clustering'])}. The market share requires more runs than clustering because "
   "its variance between runs is "
   f"about {round((Bo['sd'] / Bc['sd']) ** 2)} times larger. We therefore use "
   f"{RUNS} runs for the baseline and 100 runs per value in the sensitivity analysis, where "
   "the differences between parameter values are larger than this precision.")
H3("Horizon.", "Table 8 shows the outputs at several ticks. Mean clustering increases by "
   f"{f3(HZ[1000]['clustering_mean'] - HZ[500]['clustering_mean'])} between ticks 500 and 1000 and by "
   f"{f3(HZ[2000]['clustering_mean'] - HZ[1000]['clustering_mean'])} between ticks 1000 and 2000. "
   "The SD of the orange share keeps increasing "
   f"({f2(HZ[500]['orange_share_sd'])}, {f2(HZ[1000]['orange_share_sd'])}, {f2(HZ[2000]['orange_share_sd'])} "
   "at ticks 500, 1000 and 2000). The model does not reach a stationary distribution of market "
   "shares within 2000 ticks: individual markets continue to move away from the initial "
   "50/50 split. Tick 1000 is used as the reference horizon because the change of mean "
   "clustering after it is small and the shares have already separated. Statistics at a later "
   "tick would show a larger dispersion of shares, and this must be considered when the extended "
   "model is compared with the baseline.")

H2("3.2   Baseline Results")
P(f"Table 7 reports the statistics of the three outputs at tick 1000 over the {RUNS} runs, and "
  "Fig. 1 shows their evolution.")
table(f"Baseline outputs at tick 1000 ({RUNS} runs).",
      ["Output", "Mean", "SD", "95% CI", "Median", "P5", "P95"],
      [[name, f3(x["mean"]), f3(x["sd"]), f"{f3(x['ci95_low'])}–{f3(x['ci95_high'])}",
        f3(x["median"]), f2(x["p5"]), f2(x["p95"])]
       for name, x in [("Orange market share", Bo), ("Blue market share", Bb), ("Clustering", Bc)]],
      [30, 12, 12, 24, 14, 15, 15], align="lrrrrrr")
figure(f"{FIG}/fig1_baseline.png",
       "Baseline. (a) Orange market share in three runs (the 5th, 50th and 95th percentile of the "
       f"final share). (b) Mean clustering and mean orange share over {RUNS} runs, with the "
       "band between P5 and P95. (c) Distribution of the orange share at tick 1000.")
P("Three results characterise the baseline:")
bullets([f"*Each market becomes segmented.* Mean clustering rises from {f2(HZ[0]['clustering_mean'])} "
         f"at tick 0 to {f2(Bc['mean'])} at tick 1000 (95% CI {f3(Bc['ci95_low'])}–{f3(Bc['ci95_high'])}). "
         f"On average, {round(Bc['mean'] * 100)}% of the friends of a consumer use the same "
         "product. The variation between runs is small (SD "
         f"{f3(Bc['sd'])}), so this result does not depend on the random seed.",
         f"*The market outcome is not predictable.* The mean orange share is {f2(Bo['mean'])}, as "
         "expected from the symmetry of the baseline (equal qualities and initial shares), but "
         f"the SD between runs is {f2(Bo['sd'])}. In 90% of the runs the orange share lies between "
         f"{f2(Bo['p5'])} and {f2(Bo['p95'])}. Orange holds the majority in {OUTC['pct_runs_orange_majority']:.1f}% "
         f"of the runs and blue in {OUTC['pct_runs_blue_majority']:.1f}% (ties: {OUTC['pct_runs_tie']:.1f}%). Only "
         f"{OUTC['pct_runs_share_between_40_60']:.0f}% of the runs end with shares between 0.40 and 0.60, and "
         f"{OUTC['pct_runs_one_product_ge_90pct']:.1f}% end with one product at 90% or more.",
         "*The mean share is not informative, the dispersion is.* With identical products, "
         "the result of a run depends on early random events that are amplified by the norm and "
         "by information exchange. The relevant statistic for the baseline is therefore the "
         "distribution of shares (Fig. 1c), not its mean."])
table("Mean and SD of the outputs over time (baseline).",
      ["Tick", "Clustering (mean)", "Clustering (SD)", "Orange share (mean)", "Orange share (SD)"],
      [[str(t), f3(HZ[t]["clustering_mean"]), f3(HZ[t]["clustering_sd"]),
        f3(HZ[t]["orange_share_mean"]), f3(HZ[t]["orange_share_sd"])] for t in [0, 100, 250, 500, 750, 1000, 1500, 2000]],
      [14, 27, 27, 27, 27], align="lrrrr")
figure(f"{FIG}/fig2_number_of_runs.png",
       "Mean of the outputs at tick 1000 as a function of the number of runs, with the 95% "
       "confidence interval. (a) Orange market share. (b) Clustering.")

H2("3.3   Sensitivity Analysis")
P("The sensitivity analysis varies one parameter at a time, with all other parameters at "
  "the baseline. Figures 3 to 5 show the distribution of the orange share and the mean "
  "clustering at tick 1000, and Tables 9 to 11 report the statistics.")
H3("Social Norm.", f"Without norm (`norm_influence` = 0), mean clustering is "
   f"{f2(SN[0.0]['clustering_mean'])}, close to the value of independent choices, and the orange "
   f"share stays near 0.5 (SD {f2(SN[0.0]['orange_sd'])}). With `norm_influence` = 0.1, mean "
   f"clustering is {f2(SN[0.1]['clustering_mean'])} and the SD of the orange share is "
   f"{f2(SN[0.1]['orange_sd'])}. Above 0.1 both values change little (clustering between "
   f"{f2(min(SN[v]['clustering_mean'] for v in SN if v > 0))} and "
   f"{f2(max(SN[v]['clustering_mean'] for v in SN if v > 0))}). The effect of the norm is a "
   "threshold, not a gradual effect. The reason is visible in the utility function. With "
   "both qualities equal to *q*, the product utility of a consumer can only take the values 0, "
   "*q*/2 and *q*, so the difference between the two products is either 0 or at least *q*/2. "
   "The norm can reverse a non-zero difference only if *w* / (1 − *w*) > *q*/2, that is, "
   "*w* > *q* / (2 + *q*) = 0.2 for *q* = 0.5. For *w* ≤ 0.2 the norm acts only when the product "
   "utilities are equal. This explains why the results "
   "for *w* = 0.1 and *w* = 0.2 are identical under common random numbers (Table 9), and why "
   "a small positive norm is sufficient to coordinate the choices of friends.")
figure(f"{FIG}/fig3_sensitivity_norm_influence.png",
       "Effect of `norm_influence` (100 runs per value). (a) Distribution of the orange share "
       "at tick 1000. (b) Mean clustering at tick 1000 with 95% confidence interval.")
table("Outputs at tick 1000 as a function of `norm_influence` (100 runs per value).",
      ["`norm_influence`", "Orange share (mean)", "Orange share (SD)", "Clustering (mean)", "Clustering 95% CI"],
      [[f"{v:g}", f3(r["orange_mean"]), f3(r["orange_sd"]), f3(r["clustering_mean"]),
        f"{f3(r['clustering_ci95_low'])}–{f3(r['clustering_ci95_high'])}"] for v, r in sorted(SN.items())],
      [26, 24, 22, 23, 27], align="lrrrr")
H3("Product Quality.", "With `quality_orange` fixed at 0.5, a small difference in quality "
   f"determines the market. With `quality_blue` = 0.45, the mean orange share is "
   f"{f2(SQ[0.45]['orange_mean'])}. With 0.55, it is {f2(SQ[0.55]['orange_mean'])}, which gives blue a "
   f"mean share of {f2(1 - SQ[0.55]['orange_mean'])}. With a difference of 0.1 or more, the better product "
   f"holds at least {min(SQ[0.4]['orange_mean'], 1 - SQ[0.6]['orange_mean']) * 100:.1f}% of the market "
   "in the mean. Mean clustering is higher when qualities differ "
   f"({f2(SQ[0.3]['clustering_mean'])} at 0.3 and {f2(SQ[0.7]['clustering_mean'])} at 0.7) than when they are "
   f"equal ({f2(SQ[0.5]['clustering_mean'])}), because most consumers then use the same product. "
   "The dispersion of the outcome is largest when the products are equal (SD "
   f"{f2(SQ[0.5]['orange_sd'])}) and falls to {f3(max(SQ[v]['orange_sd'] for v in (0.3, 0.4, 0.6, 0.7)))} or less when the difference "
   "is 0.1 or more.")
figure(f"{FIG}/fig4_sensitivity_quality_blue.png",
       "Effect of `quality_blue`, with `quality_orange` = 0.5 (100 runs per value). (a) "
       "Distribution of the orange share at tick 1000. (b) Mean clustering at tick 1000 with "
       "95% confidence interval.")
table("Outputs at tick 1000 as a function of `quality_blue` (`quality_orange` = 0.5, 100 runs per value).",
      ["`quality_blue`", "Orange share (mean)", "Orange share (SD)", "Clustering (mean)", "Clustering 95% CI"],
      [[f"{v:g}", f3(r["orange_mean"]), f3(r["orange_sd"]), f3(r["clustering_mean"]),
        f"{f3(r['clustering_ci95_low'])}–{f3(r['clustering_ci95_high'])}"] for v, r in sorted(SQ.items())],
      [26, 24, 22, 23, 27], align="lrrrr")
H3("Exploration.", "Mean clustering decreases as exploration increases, from "
   f"{f2(SE[0.01]['clustering_mean'])} at 0.01 to {f2(SE[0.05]['clustering_mean'])} at 0.05 and "
   f"{f2(SE[0.2]['clustering_mean'])} at 0.2, because random switches break the agreement between "
   "friends. The dispersion of the orange share is not monotonic: its SD is "
   f"{f2(SE[0.0]['orange_sd'])} without exploration, {f2(SE[0.05]['orange_sd'])} at 0.05 and "
   f"{f2(SE[0.2]['orange_sd'])} at 0.2. A possible interpretation is that, without exploration, few consumers change product and "
   "the shares move slowly. Moderate exploration increases the number of changes and lets "
   "clusters grow, and high exploration randomises choices and keeps the shares close to 0.5.")
figure(f"{FIG}/fig5_sensitivity_exploration.png",
       "Effect of `exploration` (100 runs per value). (a) Distribution of the orange share at "
       "tick 1000. (b) Mean clustering at tick 1000 with 95% confidence interval.")
table("Outputs at tick 1000 as a function of `exploration` (100 runs per value).",
      ["`exploration`", "Orange share (mean)", "Orange share (SD)", "Clustering (mean)", "Clustering 95% CI"],
      [[f"{v:g}", f3(r["orange_mean"]), f3(r["orange_sd"]), f3(r["clustering_mean"]),
        f"{f3(r['clustering_ci95_low'])}–{f3(r['clustering_ci95_high'])}"] for v, r in sorted(SE.items())],
      [26, 24, 22, 23, 27], align="lrrrr")

H2("3.4   Summary of Findings")
P("The baseline and the sensitivity analysis lead to four conclusions that will serve as "
  "reference for the extended model:")
bullets([f"Social influence segments the market. All tested positive values of `norm_influence` "
         f"(0.1 to 1.0) lead to a mean clustering of about "
         f"{f2(Bc['mean'])}. Without norm, clustering stays at {f2(SN[0.0]['clustering_mean'])}.",
         "With equal products, the outcome of a market is path dependent: the same rules produce "
         f"markets dominated by either product (SD of the share {f2(Bo['sd'])}). The baseline must be "
         "described by the distribution of outcomes, not by the mean.",
         "Small differences in quality are amplified: a difference of 0.05 gives the better "
         f"product about {round((1 - SQ[0.55]['orange_mean']) * 100)}–{round(SQ[0.45]['orange_mean'] * 100)}% of the market.",
         "Exploration is the only mechanism that brings new information into a cluster. It reduces "
         "clustering but also determines how fast markets can change."])

# ================================================================ 4 New model
H1("4   The New Model: DIGI’s Entry into the Portuguese Market")
H2("4.1   Problem and Data")
P("In the third quarter of 2024 the market of bundled services was shared by MEO (41.8%), NOS "
  "(35.0%), Vodafone (20.6%) and NOWO (2.6%) [8]. DIGI bought NOWO and started selling in "
  "November 2024 at €22 per month for fibre and television, with a commitment of 3 months "
  "[10]. The main offers of the incumbents cost €40.50 to €42.49 with contracts of 24 months "
  "[9]. In the first quarter of 2026, 16 months after the entry, DIGI and NOWO together held "
  "3.2% [8]. The incumbents kept the prices of their main brands almost unchanged [9]. A cheaper operator was "
  "therefore not enough to move the market quickly. NOWO already charged much less than "
  "the incumbents before the entry (€26.35 [11]) and held only 2.6%.")
P("The new model is used to answer two questions. Which mechanisms explain the slow growth "
  "of a much cheaper operator? And what is the best price response of the incumbents when "
  f"each of them learns from its own profit? Table {nt()} summarises the data used for each "
  "operator.")
table("Operators in the model. Shares: ANACOM, third quarter of 2024 [8]. Prices of fibre and "
      "television with VAT [9,10,11]. Complaints per thousand customers in 2025 [8]. Quality "
      "is derived from the complaints (Sect. 4.2).",
      ["Operator", "Initial share", "Price", "Contract", "Complaints", "Quality"],
      [["MEO", "41.8%", "€42.49", "24 months", "4.0", "0.848"],
       ["NOS", "35.0%", "€42.49", "24 months", "6.2", "0.784"],
       ["Vodafone", "20.6%", "€40.50", "24 months", "7.7", "0.776"],
       ["NOWO, before the entry", "2.6%", "€26.35", "24 months", "18.7", "0.572"],
       ["DIGI, from month 12", "NOWO’s customers", "€22.00", "3 months", "18.7", "0.572 to 0.756"]],
      [32, 20, 16, 18, 17, 19], align="lrrrrr")

H2("4.2   From the Baseline to the New Model")
P("The decision rule of the baseline is kept: each month a consumer keeps its operator by "
  "habit with probability equal to its satisfaction, otherwise explores another operator with "
  "probability `exploration`, otherwise chooses the operator with the highest utility. The "
  "network, the memory of quality and the information from friends are also unchanged. With "
  "two operators and all extensions switched off, the new model reproduces the baseline "
  f"exactly, with the same random draws. Table {nt()} lists what changes. One tick is one month.")
table("Correspondence between the original model and the new model.",
      ["Original model", "New model"],
      [["2 products", "4 operators. NOWO becomes DIGI at month 12 (November 2024) and keeps its customers"],
       ["Fixed quality", "Quality from complaints. DIGI improves during its first 18 months"],
       ["No price", "Price in the product utility, with a weight taken from a choice experiment [12]"],
       ["Habit", "Habit and loyalty contracts with the legal penalty for early exit [13]"],
       ["No renewal", "At the end of a contract the consumer decides again. If it stays, it may accept a renewal discount"],
       ["100 consumers, fixed", "At least 1000 households. 0.5% leave each month and new households join"],
       ["Fixed products", "The three incumbents learn their prices after the entry (Sect. 4.4)"]],
      [34, 88])
H3("Utility with Price.", "The utility of operator *k* for a consumer is")
p = doc.add_paragraph(style="Normal"); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_runs(p, "*U*~k~ = *w* · *N*~k~ + (1 − *w*) · [ (*E*~k~ + *I*~k~) / 2 − *θ* · *p*~k~ ] + *β*~k~ ,")
P("where the first terms are those of the baseline, *p*~k~ is the price the consumer pays (the "
  "contract price for its own operator, the current price for the others) and *β*~k~ is a "
  "brand constant (Listing 9). The price weight *θ* is not free. Confraria et al. [12] "
  "estimate with a discrete choice experiment that Portuguese consumers value one unit of "
  "market share as much as €10.22 per month. Imposing the same ratio between the norm and the "
  "price gives *θ* = *w* / ((1 − *w*) · 10.22), which is 0.0109 per euro for *w* = 0.10.")
listing("consumer_choice/telecom.py",
        [("price = self.contract_price if option", "+ m.brand_constant[option])")],
        "Utility with price and brand constant")
H3("Quality from Complaints.", "The model needs a quality between 0 and 1, and ANACOM "
   "publishes complaints per thousand customers [8]. With *r* the ratio of an operator’s "
   "complaints to the mean of the incumbents, quality is *q* = 0.80 − *κ* ln *r*, with "
   "*κ* = 0.20. Doubling the complaints therefore always lowers quality by the same amount. "
   "The value of *κ* is a modelling choice and is tested in Sect. 5.4. The complaints of DIGI "
   "fell from 3.1 to 1.25 times the incumbents’ mean in about 18 months while its share barely "
   "changed, so its quality rises linearly with the time since entry, from 0.572 to 0.756.")
H3("Contracts.", "A consumer who chooses an operator signs a contract at the current price "
   "and pays that price until the contract ends. Before the end it can leave only if the "
   "savings cover the legal penalty, which is 50% of the remaining fees in the first year and "
   "30% in the second [13] (Listing 10). A scenario with full lock-in is also tested. When the "
   "contract ends, the consumer decides as in any other month and can leave without penalty. "
   "If it stays, the operator offers a renewal discount of 10% for a new contract of 24 months. "
   "The consumer accepts if the discount is at least its own cost of being committed. This cost "
   "comes from the same choice experiment [12], which values a shorter commitment at about "
   "€0.22 per month of commitment, so about €5.25 per month for 24 months. Each consumer draws "
   "its cost uniformly between 50% and 150% of this value. DIGI offers no renewal discount.")
listing("consumer_choice/telecom.py", [("def can_leave", "return savings - penalty > 0")],
        "Early exit from a contract")
H3("Population.", "The number of bundle subscribers grows about 1% per year [8]. Each month "
   "0.5% of the households leave and slightly more join, with a minimum of 1000. A new "
   "household links to its nearest neighbours, chooses by utility with what its friends tell "
   "it and signs a contract with the chosen operator. New households are an important channel "
   "for DIGI, because they choose before any contract binds them. The exit rate is not observed and is tested in Sect. 5.4.")

H2("4.3   Calibration and Validation")
P("Seven values were fixed from data or from the literature: the initial shares, the prices, "
  "the contract lengths, the qualities, the price weight, the commitment cost and the legal "
  "penalties. The main assumptions without data are that 70% of the households start under "
  "contract, that the renewal discount is 10% and that 0.5% of the households leave each "
  "month. The remaining "
  "values were calibrated in two steps.")
bullets(["*Before the entry.* Without brand constants the norm favours the largest operator "
         "and the shares drift. Constants were calibrated so that, without DIGI, the shares stay "
         "at the ANACOM values (MEO is the reference, NOS +0.0307, Vodafone +0.0161, NOWO and "
         "DIGI −0.0820). The share of initial contracts that already carry the renewal discount "
         "(48%) was set to its own long run value, so that the average price paid does not drift.",
         "*After the entry.* A grid over the norm weight *w* ∈ {0.08, 0.10, 0.12} and the "
         "exploration rate ∈ {0.005, 0.01, 0.02, 0.03}, with 24 runs per point, minimised the "
         "error against the DIGI shares at months 19, 25 and 28. The point *w* = 0.10 and "
         "exploration 0.02 was kept. It is the second best point (RMSE 0.15 against 0.12) but "
         "keeps the norm weight *w* = 0.10 of the earlier calibration and gives more switching "
         "between operators (2.7% of the households per year against 2.1%), which the model "
         "otherwise underestimates (Sect. 6.3)."])
P(f"With the final values and {N_P} runs, the model gives DIGI {CAL[19]:.1f}%, {CAL[25]:.1f}% and "
  f"{CAL[28]:.1f}% at months 19, 25 and 28, against 2.8%, 3.0% and 3.2% in the data (RMSE "
  f"{RMSE:.2f} percentage points, Fig. 6). At month 28 the incumbents hold "
  f"{FX.share_MEO[28] * 100:.1f}%, {FX.share_NOS[28] * 100:.1f}% and "
  f"{FX.share_Vodafone[28] * 100:.1f}%, against 41.5%, 34.9% and 20.3%. The model therefore "
  "reproduces the main fact: half the price is not enough for fast growth, because most "
  "households are under contract, keep their operator by habit and follow their friends. "
  "Two limitations remain. The model has fewer switches at the end of a contract than the "
  "survey of Confraria et al. suggests, so DIGI grows through a narrower channel than in "
  "reality. Without the entry, MEO also loses share slowly "
  f"({FX.share_MEO[0] * 100:.1f}% at month 0, {NE.share_MEO[132] * 100:.1f}% at month 132). "
  "This drift is common to all scenarios, which are always compared with each other under "
  "the same random numbers.")
figure(f"{PR}/figures/digi_share.png",
       f"Share of NOWO and DIGI (mean of {N_P} runs) with the ANACOM data, and its evolution "
       "over 10 years under fixed list prices, learned prices, a common cut to 0.90 and no "
       "entry. Data exist only up to month 28.")

H2("4.4   Learning Incumbents")
P("From the month of the entry, MEO, NOS and Vodafone learn their prices as independent "
  "agents (task 5). Each one uses an ε-greedy multi-armed bandit [14]. Every 3 months it "
  "chooses a price multiplier from {1.00, 0.95, 0.90, 0.85, 0.80} of its list price. The "
  "lowest price, €34 for MEO and NOS, stays above the unit cost. The reward is the profit of "
  "the quarter, the sum over its customers of the price paid minus the unit cost. The unit "
  "cost is 60% of the list price, a margin of 40% close to the 2024 EBITDA margins of NOS "
  "(45.3%) and MEO (35.8%). With probability ε = 0.1 the incumbent tries a random price, "
  "otherwise it chooses the price with the highest value. After each quarter it updates the "
  "value of the price it used:")
p = doc.add_paragraph(style="Normal"); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_runs(p, "*Q*(*a*) ← *Q*(*a*) + *α* · [ *R* − *Q*(*a*) ] ,   *α* = 0.2 .")
P("A constant step *α* gives more weight to recent quarters, which suits a market that keeps "
  "changing as DIGI grows and the rivals learn. In the first quarter after the entry the "
  "incumbent keeps the list price. It then tries each other price once, in random order, and "
  "the first reward of each price becomes its value (Listing 11). An incumbent "
  "sees only its own profit. It does not observe the prices of its rivals and cannot "
  "communicate with them. DIGI keeps its price of €22. The bandit draws from its own random "
  "generator, so the consumers receive exactly the same random numbers as in the scenarios "
  "with fixed prices.")
listing("consumer_choice/learning.py", [("reward = self.acc[k]", "explored = False")],
        "Update and choice of the bandit")

H2("4.5   Experimental Design")
P(f"Each scenario was run {N_P} times for 132 months, 12 before the entry and 10 years after "
  "it, with the same seeds in every scenario (common random numbers). Profit is summed over "
  "the 10 years after the entry and compared with the scenario where all incumbents keep the "
  "list price. Differences are computed seed by seed (paired comparison) and reported with "
  f"95% confidence intervals. The scenarios are listed in Table {nt()}. The 10 year values compare "
  "scenarios under the same assumptions. They are not forecasts, because the data cover only "
  "the first 30 months.")
table("Scenarios of the new model.",
      ["Scenario", "Prices of the incumbents after the entry", "Question"],
      [["No entry", "List prices, NOWO stays", "What does the entry cost?"],
       ["All at list price", "×1.00 (reference)", "Reference"],
       ["Common cuts", "All three at ×0.95, 0.90, 0.85 or 0.80", "Does matching DIGI pay?"],
       ["Solo cuts", "One incumbent at ×0.90 or 0.80, the others at list price",
        "Is the list price a best response?"],
       ["Learned prices", "Bandit, decisions every 3, 6 or 12 months", "What do learning agents do?"],
       ["Bandit parameters", "ε ∈ {0.05, 0.10, 0.20} × α ∈ {0.1, 0.2, 0.4}", "Do ε and α matter?"]],
      [27, 55, 40])

# ================================================================ 5 Results
H1("5   Results of the New Model")
H2("5.1   The Entry and Common Price Cuts")
P(f"The entry costs the incumbents about a tenth of their profit. Without DIGI they would earn "
  f"{dp('no_entry')[0]:.1f}% more (95% CI {dp('no_entry')[1]:.1f} to {dp('no_entry')[2]:.1f}) than with DIGI and list prices (Table {nt()}). With list prices DIGI "
  f"reaches {ds('fixed_1.00'):.1f}% in year 10. Matching DIGI on price slows it down: if all "
  f"incumbents cut to ×0.90, DIGI stays at {ds('fixed_0.90'):.1f}%. But every common cut costs "
  f"more than it saves, from {sg(dp('fixed_0.95')[0])}% at ×0.95 to {sg(dp('fixed_0.80')[0])}% "
  "at ×0.80. The customers kept by the cut do not compensate for the lower margin on all "
  "the others.")
rows = []
for s, lab in [("no_entry", "No entry"), ("fixed_1.00", "All at list price"),
               (BAND, "Learned, every 3 months"), ("bandit_p6", "Learned, every 6 months"),
               ("bandit_p12", "Learned, every 12 months"), ("fixed_0.95", "All at ×0.95"),
               ("fixed_0.90", "All at ×0.90"), ("fixed_0.85", "All at ×0.85"),
               ("fixed_0.80", "All at ×0.80")]:
    m, lo, hi = dp(s)
    ci_ = "reference" if s == "fixed_1.00" else f"{sg(lo)} to {sg(hi)}"
    rows.append([lab, "0.0" if s == "fixed_1.00" else sg(m), ci_,
                 "n/a" if s == "no_entry" else f"{ds(s):.1f}",
                 f"{SC.loc[s, 'avg_price_paid_end']:.2f}"])
table(f"Joint profit of the incumbents over 10 years after the entry, in % against all at list "
      f"price (paired by seed, {N_P} runs), mean share of DIGI in year 10 and average price paid in "
      "year 10.",
      ["Scenario", "Profit (%)", "95% CI", "DIGI (%)", "Price (€)"],
      rows, [38, 18, 30, 17, 19], align="lrrrr")

H2("5.2   Cutting Alone: a Prisoner’s Dilemma")
P(f"Table {nt()} shows the profit of each incumbent when it alone cuts its price to ×0.90 and when "
  "all three do. Each incumbent gains by cutting alone, by "
  f"{sg(dp('solo_MEO_0.90', 'MEO')[0])}% (MEO), {sg(dp('solo_NOS_0.90', 'NOS')[0])}% (NOS) and "
  f"{sg(dp('solo_Vodafone_0.90', 'Vodafone')[0])}% (Vodafone), and all three confidence "
  "intervals exclude zero. The gain comes from the rivals’ customers, so joint profit still "
  f"falls by {abs(dp('solo_Vodafone_0.90')[0]):.1f}% to {abs(dp('solo_MEO_0.90')[0]):.1f}%. When "
  "all three cut, each one loses. This is a prisoner’s dilemma: the list price is not an "
  "equilibrium, but among the symmetric prices tested it gives the highest joint profit. The "
  "result depends on the size of the cut. A deeper solo cut, to ×0.80, loses money for MEO "
  f"({sg(dp('solo_MEO_0.80', 'MEO')[0])}%) and NOS ({sg(dp('solo_NOS_0.80', 'NOS')[0])}%) and "
  f"still pays for Vodafone ({sg(dp('solo_Vodafone_0.80', 'Vodafone')[0])}%), the incumbent "
  "with the smallest base of customers.")
table("Own profit of each incumbent over 10 years, in % against all at list price (95% CI).",
      ["Incumbent", "Cuts alone to ×0.90", "All cut to ×0.90"],
      [[o, dpc(f"solo_{o}_0.90", o), dpc("fixed_0.90", o)] for o in OPS],
      [26, 48, 48], align="lrr")

H2("5.3   Learned Prices")
P(f"The learning incumbents do not start a price war (Fig. 7). During the first 15 months "
  "after the entry each one tries every price once, and the mean price falls by 10% to 15%. "
  f"After that they return close to the list price, with a mean multiplier of "
  f"{MULT[BAND]:.2f}. In years 6 to 10 the list price is chosen in {LIST_PCT['MEO']:.0f}% (MEO), "
  f"{LIST_PCT['NOS']:.0f}% (NOS) and {LIST_PCT['Vodafone']:.0f}% (Vodafone) of the decisions. "
  f"Most of the remaining decisions are the random exploration: when the incumbents do not "
  f"explore, they choose the list price {LIST_GREEDY:.0f}% of the time. Joint profit is only "
  f"{abs(dp(BAND)[0]):.1f}% lower than with list prices (95% CI {abs(dp(BAND)[2]):.1f} to "
  f"{abs(dp(BAND)[1]):.1f}), much better than any common cut, and DIGI "
  f"reaches {ds(BAND):.1f}% in year 10.")
figure(f"{PR}/figures/learned_prices.png",
       f"Learned prices (ε = 0.1, α = 0.2, {N_P} runs). Left: mean price divided by the list "
       "price. Right: share of each price in the decisions of years 6 to 10.")
P("This outcome is not learned collusion. Calvano et al. [15] show that Q-learning agents "
  "that observe each other’s prices can learn to keep prices high and to punish deviations. "
  "Our bandits cannot see their rivals, so they cannot reward or punish them. Our "
  "explanation is the short reward. A price cut lowers the margin at once, while the "
  "customers it wins arrive slowly, because most households are under contracts of 24 months. "
  "A customer won by a cut also keeps paying in later quarters, and that profit is credited "
  "to whichever price is active then, often the list price. Judged on three months of profit, "
  "a cut therefore looks worse than it is. The real incumbents also kept the prices of their "
  "main brands almost unchanged after the entry, although they compete with cheaper secondary brands, which "
  "the model does not include.")
P(f"Two checks support this reading. First, the result does not depend on ε and α. Across the "
  f"nine combinations of ε ∈ {{0.05, 0.10, 0.20}} and α ∈ {{0.1, 0.2, 0.4}} joint profit "
  f"stays between {sg(max(PA.loc[[i for i in PA.index if i.startswith('bandit_e')], 'dprofit_incumbents_pct']))}% "
  f"and {sg(min(PA.loc[[i for i in PA.index if i.startswith('bandit_e')], 'dprofit_incumbents_pct']))}% "
  "and the mean multiplier between "
  f"{min(v for k, v in MULT.items() if k.startswith('bandit_e')):.2f} and "
  f"{max(v for k, v in MULT.items() if k.startswith('bandit_e')):.2f}. The learning rate barely "
  "matters, and more exploration costs more only because it forces more random cuts. Second, "
  "with a longer decision period the bandits cut more often, as expected if a short reward "
  "hides part of the value of a cut. With decisions every 6 and 12 months the mean multiplier "
  f"falls to {MULT['bandit_p6']:.2f} and {MULT['bandit_p12']:.2f}, but joint profit also falls, "
  f"by {abs(dp('bandit_p6')[0]):.1f}% and {abs(dp('bandit_p12')[0]):.1f}%. Each price is then held "
  "longer and the bandit has fewer decisions to learn from. We did not isolate which of these "
  "effects dominates, so this check is consistent with our explanation but does not prove it.")

H2("5.4   Sensitivity Analysis")
P(f"Six assumptions without direct data were changed one at a time, in nine variants and without recalibration "
  f"(task 6). For each variant the list price scenario, the three solo cuts to ×0.90 and the "
  f"bandit were run {N_S} times with common random numbers (Fig. 8, Table {nt()}). Because of the "
  f"smaller number of runs, the base row differs slightly from the results above.")
figure(f"{ROOT}/results/sensitivity/figures/sensitivity.png",
       f"Sensitivity of the two conclusions ({N_S} runs per scenario, 95% CI). Left: own profit "
       "of an incumbent that alone cuts to ×0.90. Right: joint profit with learned prices and "
       "mean price multiplier.")
srows = []
for v, r_ in SENS.iterrows():
    srows.append([r_["label"].replace(" %", "%"), sg(r_["solo_MEO_pct"]), sg(r_["solo_NOS_pct"]),
                  sg(r_["solo_Vodafone_pct"]), sg(r_["bandit_joint_pct"]),
                  f"{r_['digi_m28_pct']:.1f}", f"{r_['digi_10y_list_pct']:.1f}"])
table(f"Sensitivity analysis ({N_S} runs per scenario). Own profit of a solo cut to ×0.90 and "
      "joint profit with learned prices, in % against all at list price. DIGI share at month 28 "
      "(ANACOM: 3.2%) and in year 10 with list prices.",
      ["Variant", "MEO solo", "NOS solo", "Vod. solo", "Learned", "DIGI m28", "DIGI y10"],
      srows, [34, 14, 14, 14, 15, 15, 16], align="lrrrrrr")
P("Both conclusions hold in all nine changes:")
bullets([f"*A solo cut pays for at least one incumbent.* NOS gains between "
         f"{sg(SENS_V.solo_NOS_pct.min())}% and {sg(SENS_V.solo_NOS_pct.max())}% and Vodafone "
         f"between {sg(SENS_V.solo_Vodafone_pct.min())}% and {sg(SENS_V.solo_Vodafone_pct.max())}%. "
         f"The only cut that does not pay is MEO’s with *κ* = 0.30 "
         f"({sg(SENS.loc['kappa_0.30', 'solo_MEO_pct'])}%). A larger *κ* widens the quality gaps, "
         "and MEO, which has the best quality, already holds its customers.",
         f"*Learned prices stay near the list price.* The mean multiplier stays between "
         f"{SENS.bandit_multiplier.min():.2f} and {SENS.bandit_multiplier.max():.2f} and joint "
         f"profit between {sg(SENS_V.bandit_joint_pct.max())}% and {sg(SENS_V.bandit_joint_pct.min())}%. "
         "With exits of 1% per month and with a margin of 60% the confidence interval includes zero.",
         "*Cuts pay more when more customers are free.* More exits bring more new households "
         "without a contract, and a higher margin makes each extra customer worth more. Both "
         "make solo cuts more profitable."])
P(f"The long run share of DIGI is not robust. With list prices it ranges from "
  f"{SENS.digi_10y_list_pct.min():.1f}% to {SENS.digi_10y_list_pct.max():.1f}% in year 10 across "
  "the variants. Without recalibration some variants also move away from the data at month 28 "
  f"({SENS.loc['kappa_0.10', 'digi_m28_pct']:.2f}% with *κ* = 0.10 and "
  f"{SENS.loc['kappa_0.30', 'digi_m28_pct']:.2f}% with *κ* = 0.30, against 3.2%). The analysis "
  "therefore tests the robustness of the conclusions, not the fit. The direction of the results "
  "is robust, but the exact share of DIGI in 10 years should not be read as a forecast.")

H2("5.5   Comparison with the Baseline")
IND = {m: sum(FX[f"share_{o}"][m] ** 2 for o in OPS + ("DIGI",)) for m in (0, 132)}
P(f"The new model keeps the main property of the baseline. Outcomes vary between runs with the "
  f"same parameters: with list prices DIGI ends year 10 between {DIGI_END.min():.1f}% and "
  f"{DIGI_END.max():.1f}% (standard deviation {DIGI_END.std():.1f} points over {N_P} runs). "
  "As in the baseline, the distribution of outcomes matters, which is why every comparison is "
  "paired by seed. The norm also still groups friends. At month 0 clustering is "
  f"{FX.clustering[0]:.2f}, about the value expected if friends chose independently with the "
  f"observed shares ({IND[0]:.2f}). By month 132 it rises to {FX.clustering[132]:.2f}, while "
  f"independent choices with the shares of that month would give only {IND[132]:.2f}. "
  f"Clustering stays below the {f2(Bc['mean'])} of the baseline because the market has four "
  "operators, contracts delay switching, households keep joining and leaving, and the horizon "
  "is 132 months instead of 1000 ticks. Habit and the norm, which in the baseline produced "
  "lock-in, now explain why a much cheaper operator grows slowly.")

# ================================================================ 6 Conclusions
H1("6   Conclusions")
H2("6.1   The New Model")
bullets(["*Contracts, habit and friends slow a cheap rival.* The model reproduces the slow growth "
         f"of DIGI (RMSE {RMSE:.2f} points in the first 16 months after the entry) with the decision rule of the "
         "baseline, prices and legal contracts. Price alone does not move a market where most "
         "households are committed and follow their friends.",
         "*The list price is not an equilibrium.* Each incumbent gains by cutting its price "
         "alone, but all lose if all cut. Matching DIGI on price slows it down but costs much "
         "more than it saves.",
         "*Simple learners stay near the list price.* Bandits that see only their own quarterly "
         f"profit return to the list price in most decisions and lose only {abs(dp(BAND)[0]):.1f}% "
         "of joint profit. This happens without communication and without observing the "
         "rivals, and agrees with the observed behaviour of the incumbents. The reason in the "
         "model is the short reward horizon against contracts of 24 months, not collusion.",
         "*Both conclusions are robust* to nine changes of the assumptions without data. The "
         "share of DIGI in 10 years is not, and is not a forecast."])
H2("6.2   The Project as a Whole")
P("Starting from a model of two abstract products, the project produced a model of a real "
  "market that is calibrated to public data and supported by a choice experiment, the law on "
  "contracts and the literature on learning and pricing. The decision rule of the original "
  "model was kept and remains testable, because the new model reproduces the baseline when "
  "the extensions are switched off. Three lessons stand out. First, statistics over many runs "
  "were needed at every stage, because single runs of both models can be very different. "
  "Second, paired comparisons with common random numbers made small differences between "
  "scenarios measurable. The first version of the bandit used the random generator of the "
  "consumers and broke this pairing until it was given its own generator. Third, the learning "
  "design matters: the first version tried the prices always in the same order and made the "
  "lower prices look worse than they were. Both errors were corrected and the results above "
  "use the corrected version.")
H2("6.3   Limitations and Future Work")
bullets(["The model has fewer switches at the end of a contract than the survey data suggest, and "
         "without the entry the shares drift slowly.",
         "Several values have no direct data (the initial share under contract, the renewal "
         "discount, the exit rate and the mapping from complaints to quality). They were tested "
         "in the sensitivity analysis, one at a time, so interactions between them are not known.",
         "The incumbents can only change the price of one offer. In reality they answered DIGI "
         "with cheaper secondary brands, and DIGI keeps a fixed price.",
         "The bandit has no state and a reward of one quarter. A learner that values future "
         "profit, such as Q-learning with the rivals’ prices as state [15], could test whether "
         "the result changes when the incumbents can see each other."])

# ================================================================ References
H1("References")
refs = [
    "Jager, W., Wang, S.: NetLogo Consumer Choice model. Center for Connected Learning and "
    "Computer-Based Modeling, Northwestern University, Evanston, IL (2024). "
    "http://ccl.northwestern.edu/netlogo/models/ConsumerChoice",
    "Wilensky, U.: NetLogo. Center for Connected Learning and Computer-Based Modeling, "
    "Northwestern University, Evanston, IL (1999). http://ccl.northwestern.edu/netlogo/",
    "Janssen, M.A., Jager, W.: Fashions, Habits and Changing Preferences: Simulation of "
    "Psychological Factors Affecting Market Dynamics. Journal of Economic Psychology 22(6), "
    "745–772 (2001)",
    "Cialdini, R.B., Goldstein, N.J.: Social Influence: Compliance and Conformity. Annual "
    "Review of Psychology 55, 591–621 (2004)",
    "Nyborg, K., et al.: Social Norms as Solutions. Science 354(6308), 42–43 (2016)",
    "ter Hoeven, E., Kwakkel, J., Hess, V., Pike, T., Wang, B., Rht, Kazil, J.: Mesa 3: "
    "Agent-Based Modeling with Python in 2025. Journal of Open Source Software 10(107), 7668 "
    "(2025). https://doi.org/10.21105/joss.07668",
    "Grimm, V., et al.: The ODD Protocol for Describing Agent-Based and Other Simulation "
    "Models: A Second Update to Improve Clarity, Replication, and Structural Realism. Journal "
    "of Artificial Societies and Social Simulation 23(2), 7 (2020)",
    "ANACOM: Statistical information on bundled services (third quarter of 2024 to first "
    "quarter of 2026) and on complaints (2025 and second quarter of 2026). Autoridade Nacional "
    "de Comunicações, Lisbon",
    "CNN Portugal, DECO PROteste: Barometer of telecommunications prices (October 2025)",
    "Observador: DIGI prices and conditions at launch in Portugal (4 November 2024)",
    "ANACOM: O Sector das Comunicações 2024, Table 20. Autoridade Nacional de Comunicações, "
    "Lisbon (2025)",
    "Confraria, J., Ribeiro, T., Vasconcelos, H.: Analysis of Consumer Preferences for Mobile "
    "Telecom Plans Using a Discrete Choice Experiment. Telecommunications Policy 41(3), "
    "157–169 (2017). https://doi.org/10.1016/j.telpol.2016.12.009",
    "Lei n.º 16/2022, de 16 de agosto: Lei das Comunicações Eletrónicas. Diário da República",
    "Sutton, R.S., Barto, A.G.: Reinforcement Learning: An Introduction, 2nd edn. MIT Press, "
    "Cambridge, MA (2018)",
    "Calvano, E., Calzolari, G., Denicolò, V., Pastorello, S.: Artificial Intelligence, "
    "Algorithmic Pricing, and Collusion. American Economic Review 110(10), 3267–3297 (2020). "
    "https://doi.org/10.1257/aer.20190623",
]
for i, ref in enumerate(refs, 1):
    p = doc.add_paragraph(style="reference")
    p.add_run(f"{i}.\t{ref}")

doc.save(OUT)

# remove the template's sample comments and footnotes (no longer referenced)
import shutil, zipfile, tempfile  # noqa: E402
tmp = tempfile.mktemp(suffix=".docx")
with zipfile.ZipFile(OUT) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/comments.xml":
            data = re.sub(rb"<w:comment\b.*?</w:comment>", b"", data, flags=re.S)
        elif item.filename == "word/numbering.xml":
            # schema order inside <w:lvl>: numFmt before pStyle (template converted from .doc)
            data = re.sub(rb"(<w:pStyle [^>]*/>)(<w:numFmt [^>]*/>)", rb"\2\1", data)
        elif item.filename == "word/footnotes.xml":
            data = re.sub(rb'<w:footnote (?:(?!w:type=)[^>])*>.*?</w:footnote>', b"", data, flags=re.S)
        zout.writestr(item, data)
shutil.move(tmp, OUT)
print("saved", OUT, counters)
