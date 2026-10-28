# Évaluation humaine du chatbot — protocole et grille

Objectif (livrable du projet) : mesurer **fluidité**, **cohérence** et **efficacité de complétion de la tâche**
avec de vrais utilisateurs. Les scripts automatiques (`eval/evaluate_*.py`) ne remplacent pas ce test.

## 1. Préparer
- 5 à 10 testeurs (camarades, famille). Ils n'ont pas vu le code.
- Lancer l'interface : `streamlit run app_streamlit.py`
- **Les testeurs notent directement dans l'app** (encadré « 📝 Évaluation humaine », sous la conversation) : chaque envoi ajoute une ligne à `reports/human_eval_results.csv` (n_turns est compté automatiquement).
- Le chatbot comprend l'**anglais** : prévenir les testeurs.
- Donner à chaque testeur **3 scénarios** parmi les 6 ci-dessous (ne pas leur dire quoi taper : seulement le but).

## 2. Scénarios (cartes à donner aux testeurs)

| ID | But à atteindre |
|----|-----------------|
| S1 | Réserver un restaurant **indien bon marché** au **centre** pour **4 personnes**, **vendredi à 19h**. |
| S2 | Trouver un restaurant **italien** dans le **nord**, demander **son adresse et son téléphone** (pas de réservation). |
| S3 | Réserver un restaurant **cher** de cuisine **britannique**, **2 personnes**, **samedi à 20h**. Si le premier ne vous plaît pas, demander un autre. |
| S4 | Vous voulez un restaurant **végétarien** (le bot n'en a pas) : voir comment il réagit, puis réserver une alternative pour **3 personnes** **dimanche à 12h30**. |
| S5 | Vous n'avez **aucune préférence de prix ni de zone**, vous voulez de la cuisine **chinoise** pour **6 personnes** **jeudi à 18h**. |
| S6 | Commencer par dire bonjour, chercher un restaurant **modéré** à l'**est**, puis **changer d'avis** et le vouloir dans l'**ouest** avant de réserver pour **2 personnes** **lundi à 13h**. |

## 3. Pendant le test
Pour chaque conversation, noter (ou faire noter par le testeur) :
- **task_completed** : 1 si la réservation/l'info demandée a été obtenue correctement, sinon 0
- **n_turns** : nombre de messages envoyés par le testeur
- 3 notes de **1 (très mauvais) à 5 (excellent)** :
  - **fluency** (fluidité) : les réponses du bot sont-elles naturelles, bien écrites ?
  - **coherence** (cohérence) : le bot reste-t-il logique, se souvient-il de ce qui a été dit, ne se contredit-il pas ?
  - **efficiency** (efficacité) : la tâche a-t-elle été accomplie sans effort inutile, sans répétitions ?
- **comments** : phrases où le bot s'est trompé (très utile pour le rapport)

## 4. Résultats
Si les testeurs ont utilisé le formulaire de l'app, le fichier `reports/human_eval_results.csv` existe déjà. Sinon, copier
`eval/human_eval_template.csv` vers `reports/human_eval_results.csv` et ajouter **une ligne par conversation**. Puis :

```bash
python -m eval.analyze_human_eval
```

Le script calcule moyennes, écarts-types, taux de réussite et nombre moyen de tours, par critère et par scénario,
et écrit `reports/human_eval_summary.md` à coller dans le rapport.

## 5. À rapporter (conseil)
- Nombre de testeurs et de conversations, profil des testeurs.
- Moyennes ± écart-type pour les 3 critères et taux de réussite.
- 3 à 5 exemples d'échecs (depuis `comments`) avec une cause probable (NLU, règle, manque de données...).
- Limites : petit échantillon, testeurs non représentatifs, bot anglais testé par des non-anglophones.
