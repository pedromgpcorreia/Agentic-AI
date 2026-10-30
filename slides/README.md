# Slides (tasks 1-6)

Abrir `deck.html` num browser (precisa dos ficheiros em `assets/`). As notas de cada slide estão no `<aside>` de `src/slides/*.html`.

| Ficheiro | Conteúdo |
|---|---|
| `src/` | Slides, um ficheiro por slide, e índice (`deck.json`) |
| `assets/` | Gráficos e animação |
| `make_charts.py` | Gera os gráficos a partir de `data/` e `results/` |
| `make_animation.py` | Gera a animação de uma corrida |
| `build_deck.py` | Gera `deck.html` |
| `check_numbers.py` | Recalcula os números dos slides e confirma que estão no texto |

Comandos a partir da raiz do repositório: `python slides/check_numbers.py`, `python slides/build_deck.py`.
