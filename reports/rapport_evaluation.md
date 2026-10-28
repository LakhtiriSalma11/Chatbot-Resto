# Rapport d'évaluation — Chatbot de réservation de restaurant (Projet 18)

*Chiffres générés par `eval/evaluate_intent.py`, `eval/evaluate_dialogue.py` et `eval/run_scenarios.py` (graine fixe, reproductibles).
La section 4.3 (évaluation humaine) est à compléter avec de vrais testeurs.*

## 1. Données
- MultiWOZ 2.2, dialogues dont le seul service est `restaurant` : **1 387 dialogues** (≥ 1 000 requis), 8,7 tours en moyenne.
- Découpage par dialogue (80/10/10) : train 1 109 · val 138 · test 140 dialogues → **4 823 / 593 / 641 tours utilisateur**.
- Intentions (étiquettes dérivées des annotations, voir Limites) : `inform`, `request_info`, `book`, `bye`, `other`.

## 2. Représentation et classification d'intention (split test, 641 tours)

**Représentation (étape 3).** Chaque tour = [phrase] + [dernière réponse du bot] + [7 indicateurs d'état du dialogue].
Deux encodeurs comparés :
- **RoBERTa contextuel** (spaCy `en_core_web_trf`, 768 dim, moyenne des vecteurs de tokens de la dernière couche) — **modèle principal** ;
- **TF-IDF** (uni+bigrammes) — baseline non contextuelle.

Classifieur : régression logistique, C choisi sur `val` (macro-F1), score final mesuré une seule fois sur `test`.

| Métrique (modèle principal, RoBERTa) | Valeur |
|---|---|
| Accuracy | **0,911** (IC 95 % bootstrap : 0,889 – 0,933) |
| Macro-F1 | 0,839 |
| Baseline « classe majoritaire » | 0,424 |

| Classe | Précision | Rappel | F1 | Support |
|---|---|---|---|---|
| inform | 0,905 | 0,945 | 0,924 | 272 |
| request_info | 0,960 | 0,923 | 0,941 | 104 |
| book | 0,862 | 0,920 | 0,890 | 88 |
| bye | 0,946 | 0,933 | 0,939 | 149 |
| other | 0,688 | 0,393 | 0,500 | 28 |

Matrice de confusion : `reports/confusion_matrix.png`. Erreurs : `reports/intent_errors.csv` (57 sur 641).

**Ablation** (C choisi sur val ; `reports/intent_ablation.csv`) :

| Encodeur | Entrée | Accuracy test | Macro-F1 test |
|---|---|---|---|
| TF-IDF | phrase seule | 0,892 | 0,798 |
| TF-IDF | phrase + réponse du bot + état | **0,916** | **0,843** |
| RoBERTa (contextuel) | phrase seule | 0,896 | 0,810 |
| RoBERTa (contextuel) | phrase + réponse du bot + état | 0,911 | 0,839 |

**Lecture honnête des résultats.**
1. Ajouter le **contexte du dialogue** (réponse du bot + état) apporte +1,6 à +2,3 points d'accuracy avec les deux encodeurs : c'est l'effet le plus net.
2. Les embeddings **contextuels** n'améliorent pas la précision globale par rapport à TF-IDF (0,911 vs 0,916, écart inférieur à l'intervalle de confiance ±2 points). Sur la phrase seule ils sont légèrement meilleurs (+0,3 pt accuracy, +1,1 pt macro-F1), ce qui est cohérent avec leur meilleure généralisation sur des formulations rares ; ici, les phrases du corpus sont courtes et très répétitives, donc le sac de mots suffit déjà.
3. Les données (étiquettes automatiques, domaine étroit) limitent le plafond : les deux modèles butent sur la classe `other`.

**Analyse d'erreurs.** La classe `other` est faible (rappel 39 %, seulement 28 exemples) : elle est confondue avec `inform`
(« I was really hoping for Sri Lankan » ressemble à un critère). Les autres confusions viennent surtout de phrases très courtes et
ambiguës (« 16:30 please », « That was all thank you ») dont le sens dépend du contexte. Dans le système complet, les règles
de la politique corrigent une partie de ces cas.

## 3. Système de dialogue (évaluation automatique)

**Suivi d'état** sur les dialogues réels du split test (NLU à règles, 641 tours) :
Joint Goal Accuracy **0,789** ; F1 slot-valeur (micro) **0,946** ; par slot : cuisine 0,95 · zone 0,93 · prix 0,93 ·
personnes 0,98 · jour 0,98 · heure 0,95.
(JGA passée de 0,769 à 0,789 après correction du NLU : « I don't care about the price or the area » n'était pas reconnu.)

**Utilisateurs simulés** (300 dialogues, 4 styles de conversation, 1 à 3 critères donnés d'emblée) :
hybride ML + règles **100 %** de réservations correctes, règles seules **100 %**, ≈ 3,6 tours en moyenne.

⚠️ À interpréter avec prudence : le simulateur est écrit par le même auteur que le NLU, avec un vocabulaire limité.
Ces 100 % montrent que la logique de dialogue est cohérente, **pas** que le bot réussira 100 % avec de vrais utilisateurs.
Le fait que ML + règles et règles seules soient à égalité signifie aussi que, sur ces scénarios simples, le ML n'apporte pas de gain
mesurable : son intérêt apparaît sur des formulations plus libres (voir 4.1) et pour la reconnaissance d'intention elle-même (section 2).

## 4. Évaluation de la fluidité, de la cohérence et de l'efficacité

### 4.1 Test de scénarios S1–S6 (automatique)
Les 6 scénarios du protocole (`eval/human_eval.md`) sont joués avec 2 formulations libres chacun (`python -m eval.run_scenarios`,
transcriptions complètes dans `reports/scenario_transcripts.md`). Succès = bonne réservation (cuisine, zone, prix, personnes, jour, heure)
ou bonne information (S2).

**Résultat : 12 / 12 conversations réussies**, 2,75 tours utilisateur en moyenne. Ce test a révélé un défaut, corrigé :
« I don't care about the price or the area » (S5) n'était pas compris → le bot reposait la question de la zone.

### 4.2 Relecture qualitative des transcriptions (par l'assistant IA — ce n'est PAS une évaluation humaine)
Notes de 1 à 5 sur les 12 transcriptions (`reports/revue_ia_scenarios.csv`), mêmes critères que la grille humaine :

| Critère | Moyenne /5 | Écart-type |
|---|---|---|
| Fluidité | 4,00 | 0,00 |
| Cohérence | 4,75 | 0,45 |
| Efficacité | 4,50 | 0,52 |
| Taux de réussite de la tâche | 100 % | |

Défauts relevés : réponses à base de templates (fluidité plafonnée à 4), question « Would you like me to book a table? » répétée après
chaque information (S2), même message d'accueil renvoyé deux fois à « Hi there » (S6), zone choisie par le bot quand l'utilisateur
n'en donne pas (S4). Ces notes viennent d'une seule relectrice et des mêmes scénarios que ceux qui ont servi à corriger le bot :
elles sont **optimistes** et ne remplacent pas des testeurs.

### 4.3 Évaluation humaine — À COMPLÉTER
Protocole : `eval/human_eval.md`. Les testeurs notent directement dans l'app (encadré « 📝 Évaluation humaine »), les lignes
s'ajoutent à `reports/human_eval_results.csv`. Ensuite : `python -m eval.analyze_human_eval` → `reports/human_eval_summary.md`, à coller ici.

| Critère | Moyenne /5 | Écart-type |
|---|---|---|
| Fluidité | … | … |
| Cohérence | … | … |
| Efficacité | … | … |
| Taux de réussite de la tâche | … % | |

## 5. Limites
- **Étiquettes d'intention automatiques** : dérivées des annotations MultiWOZ par règles, donc imparfaites (surtout `other`).
- **Embeddings contextuels sans gain global** sur ce corpus (voir section 2) ; SBERT (`--backend sbert`) est codé mais non testé (Hugging Face inaccessible dans mon environnement) — RoBERTa via spaCy a été utilisé à la place.
- **Slot extraction par règles** : ne gère ni les négations (« not expensive »), ni les fautes de frappe, ni le français.
- **Jour/heure** : « 7 » sans am/pm est interprété comme 19h ; « today/tomorrow » dépend de la date du jour.
- **Base de 110 restaurants** de Cambridge : les réservations sont simulées (la référence est générée localement).
- **Évaluation humaine non réalisée à ce jour** (section 4.3) : petit échantillon attendu, bot en anglais testé par des non-anglophones.
