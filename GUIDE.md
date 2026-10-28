# Guide pas à pas — du dataset au chatbot

Chaque étape : **idée → fichier → commande → ce que tu dois voir**.

## Étape 0 — Installer
Voir `README.md` (venv + `pip install -r requirements.txt`).

## Étape 1 — Acquisition du dataset
- **Idée** : MultiWOZ 2.2 contient des dialogues humain–humain annotés (intentions, slots). On garde uniquement ceux qui parlent
  *seulement* de restaurant (`services == ["restaurant"]`) → 1 387 dialogues, 12 000 tours environ.
- **Fichier** : `src/prepare_data.py` (fonction `download_raw`).
- **Commande** : `python -m src.prepare_data` (télécharge ≈ 210 Mo, une seule fois). Les résultats sont déjà fournis.
- **Résultat** : `data/processed/dialogues.jsonl` + message « 1387 dialogues restaurant -> OK ».

## Étape 2 — Prétraitement
- **Nettoyage** (`src/text_utils.py`) : espaces, apostrophes typographiques, ponctuation collée ; tokenisation (mots, heures `19:45`, ponctuation).
- **Tours de parole** : chaque dialogue est une liste de tours `USER` / `SYSTEM`. Pour chaque tour utilisateur on garde
  la phrase, la dernière réponse du système (le **contexte**) et l'état avant le tour.
- **Étiquette d'intention** (dérivée des annotations) :

| Intention | Quand |
|---|---|
| `bye` | l'annotation dit qu'il n'y a plus d'intention (merci, au revoir) |
| `request_info` | l'utilisateur demande adresse, téléphone, code postal, prix... |
| `book` | détails de réservation (personnes/jour/heure) ou numéro de référence |
| `inform` | critère de recherche donné ou modifié (cuisine, zone, prix) ou restaurant nommé |
| `other` | le reste (« un autre ? », « peu importe »...) |

- **Découpage** par dialogue (pas par phrase, pour éviter qu'un même dialogue soit dans train et test) : 80 / 10 / 10.
- **Résultat** : `intents_train.csv`, `intents_val.csv`, `intents_test.csv`, `lexicon.json`, `stats.json`.

## Étape 3 — Représentation (embeddings)
- **Idée** : transformer chaque tour en vecteur numérique avec 3 morceaux : la **phrase**, la **réponse précédente du bot**,
  et **7 indicateurs** (cuisine/zone/prix/restaurant/personnes/jour/heure déjà connus ?). Les deux derniers = l'**état du dialogue**.
- **Fichier** : `src/embeddings.py` (classe `DialogueFeaturizer`).
- **Trois backends** : `spacy` (**embeddings contextuels RoBERTa**, modèle principal), `sbert` (Sentence-BERT, optionnel) et `tfidf` (baseline non contextuelle).
- **Commande** : `python -m src.embeddings --backend spacy` → matrices sauvegardées dans `data/processed/`.

## Étape 4 — Modélisation (système hybride)

```
message ─► NLU (règles) ──► cuisine, zone, prix, personnes, jour, heure, nom, "merci", "un autre"...
        └► Classifieur ML ─► intention + confiance
                 │
          règles de correction (ex. « ok sounds good » n'est pas un au revoir)
                 ▼
        mise à jour de l'ÉTAT ─► POLITIQUE ─► action ─► templates ─► réponse
```

1. **Classifieur d'intention** (`src/train_intent.py`, `src/intent.py`) : régression logistique sur les vecteurs de l'étape 3 ;
   `python -m src.train_intent --backend spacy --out models/intent_clf_spacy.joblib` (choisit C sur le split val).
   Au lancement du chatbot, le modèle RoBERTa est chargé s'il est disponible, sinon le modèle TF-IDF.
2. **NLU à règles** (`src/nlu.py`) : expressions régulières + lexique de cuisines (base + annotations d'entraînement).
3. **État du dialogue** (`DialogueState` dans `src/dialogue_manager.py`) : critères, restaurant en cours, propositions, réservations.
4. **Politique** (`DialogueManager`) : selon l'intention et l'état → demander un critère manquant, proposer un restaurant,
   donner une info, proposer « un autre », demander les détails de réservation, confirmer avec une référence.
   Si aucun résultat : propose d'assouplir un critère.
5. **Réponses** (`src/nlg.py`) : templates avec plusieurs variantes.

## Étape 5 — Évaluation
- **Intention** : `python -m eval.evaluate_intent` → accuracy, F1 par classe, matrice (`reports/confusion_matrix.png`),
  erreurs (`reports/intent_errors.csv`), ablation (phrase seule vs avec contexte).
- **Dialogue** : `python -m eval.evaluate_dialogue` → Joint Goal Accuracy sur de vrais dialogues + utilisateurs simulés
  (hybride vs règles seules). C'est automatique, **pas** un test humain.
- **Scénarios** : `python -m eval.run_scenarios` (S1–S6, 2 formulations chacun) → `reports/scenario_transcripts.md`.
- **Humaine** : suis `eval/human_eval.md` (6 scénarios, notes 1–5 sur fluidité / cohérence / efficacité). Les testeurs notent dans
  l'app (encadré « 📝 Évaluation humaine ») → `reports/human_eval_results.csv`, puis `python -m eval.analyze_human_eval`.
- **Rapport** : `reports/rapport_evaluation.md` (tout est rempli sauf §4.3, à compléter avec tes testeurs).

## Étape 6 — Démonstration
- **Web** : `streamlit run app_streamlit.py`. La barre latérale montre l'état du dialogue (slots), l'intention détectée avec sa
  confiance, les réservations, et des phrases d'exemple.
- **Terminal** : `python -m src.chatbot --debug` (`/reset`, `/quit`).
- **Conversation type** :

```
Toi : I'm looking for a Chinese restaurant
Bot : Okay, I'm looking for chinese restaurants. Which part of town would you like: north, south, east, west or the centre?
Toi : in the centre
Bot : I found 10 matching restaurants. How about Charlie Chan? It is a cheap chinese restaurant in the centre. Shall I book it for you?
Toi : yes please
Bot : Sure, let's book Charlie Chan. For how many people?
Toi : for 4 people  /  on friday  /  7:30 pm
Bot : Your booking is confirmed: Charlie Chan, 4 people, Friday at 19:30. Reference number: ...
```

## Points à expliquer à l'oral
- **Pourquoi hybride ?** Le ML reconnaît l'intention malgré la variété des phrases ; les règles garantissent un comportement
  fiable (pas d'hallucination, réservation toujours complète). Exemple concret trouvé pendant les tests : le ML prenait
  « ok sounds good » pour un au revoir ; une règle corrige.
- **Pourquoi le contexte ?** Le même « yes please » n'a pas le même sens après une proposition ou après une question de réservation
  (ablation : +1,6 à +2,3 pts d'accuracy avec le contexte, TF-IDF comme RoBERTa).
- **Contextuel vs TF-IDF ?** Résultat honnête : accuracy équivalente (0,911 vs 0,916). Le gain principal vient du contexte du dialogue ; les embeddings contextuels aident un peu sur la phrase seule (macro-F1 +1,1 pt).
- **Limites** : voir `README.md` (étiquettes automatiques, évaluation humaine à faire, bot en anglais).

## Pistes d'amélioration
Comparer SBERT à RoBERTa ; ajouter un modèle Seq2Seq (T5-small) pour générer les réponses et le comparer aux templates ;
traduire le NLU en français ; gérer les négations (« not expensive »).
