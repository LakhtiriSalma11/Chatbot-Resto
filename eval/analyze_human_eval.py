"""Agrège les résultats de l'évaluation humaine (reports/human_eval_results.csv).

    python -m eval.analyze_human_eval [--csv chemin.csv]
"""
import argparse
import sys

import pandas as pd

from src import config as C

RATINGS = ["fluency", "coherence", "efficiency"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(C.REPORTS_DIR / "human_eval_results.csv"))
    args = ap.parse_args(argv)

    try:
        df = pd.read_csv(args.csv)
    except FileNotFoundError:
        sys.exit(f"Fichier introuvable : {args.csv}\nCopie eval/human_eval_template.csv vers reports/human_eval_results.csv "
                 "et ajoute une ligne par conversation (voir eval/human_eval.md).")
    if df.empty:
        sys.exit("Le fichier de résultats est vide : ajoute au moins une ligne.")

    for c in RATINGS:
        if not df[c].between(1, 5).all():
            sys.exit(f"Colonne {c} : les notes doivent être comprises entre 1 et 5.")

    lines = [f"# Résultats de l'évaluation humaine\n",
             f"- Conversations : **{len(df)}**  |  Testeurs : **{df['tester_id'].nunique()}**",
             f"- Taux de réussite de la tâche : **{df['task_completed'].mean():.0%}**",
             f"- Nombre moyen de tours : **{df['n_turns'].mean():.1f}**\n",
             "| Critère | Moyenne (/5) | Écart-type |", "|---|---|---|"]
    for c in RATINGS:
        lines.append(f"| {c} | {df[c].mean():.2f} | {df[c].std(ddof=0):.2f} |")

    lines += ["\n## Par scénario\n", "| Scénario | n | Réussite | Fluidité | Cohérence | Efficacité | Tours |", "|---|---|---|---|---|---|---|"]
    for sid, g in df.groupby("scenario_id"):
        lines.append(f"| {sid} | {len(g)} | {g['task_completed'].mean():.0%} | {g['fluency'].mean():.2f} | "
                     f"{g['coherence'].mean():.2f} | {g['efficiency'].mean():.2f} | {g['n_turns'].mean():.1f} |")

    bad = df[(df["task_completed"] == 0) & df["comments"].notna()]
    if len(bad):
        lines += ["\n## Échecs commentés\n"] + [f"- ({r.tester_id}, {r.scenario_id}) {r.comments}" for r in bad.itertuples()]

    out = "\n".join(lines)
    print(out)
    (C.REPORTS_DIR / "human_eval_summary.md").write_text(out + "\n", encoding="utf-8")
    print(f"\n-> {C.REPORTS_DIR / 'human_eval_summary.md'}")


if __name__ == "__main__":
    main()
