# Projet 18 — Chatbot de réservation de restaurant (hybride : intentions + règles)

Chatbot qui trouve un restaurant à Cambridge (cuisine, zone, prix) et réserve une table.
Données : **MultiWOZ 2.2**, domaine restaurant (1 387 dialogues). Interface : **Streamlit**.
Embeddings **contextuels RoBERTa** (spaCy) pour la classification d'intention, avec baseline TF-IDF.
Le chatbot comprend l'**anglais** (langue du corpus).

```
message ─► NLU à règles (slots) ─┐
        └► classifieur d'intention (ML) ─► correction par les règles ─► état du dialogue
                                                   ─► politique (règles) ─► templates ─► réponse
```

## Démarrage rapide (VS Code, 5 commandes)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   |   source .venv/bin/activate  (Mac/Linux)
pip install -r requirements.txt
pip install spacy spacy-transformers && python -m spacy download en_core_web_trf   # embeddings contextuels
python -m src.prepare_data        # télécharge MultiWOZ (~210 Mo) + prétraitement
python -m src.train_intent                                        # baseline TF-IDF (secondes)
python -m src.train_intent --backend spacy --out models/intent_clf_spacy.joblib   # RoBERTa (~15 min CPU, 1re fois)
streamlit run app_streamlit.py    # ouvre le chatbot dans le navigateur
```

Dans VS Code : *Ctrl+Shift+P → Python: Select Interpreter → .venv*, puis ouvre un terminal intégré (Ctrl+`).
Toutes les commandes se lancent **depuis la racine du projet** (le dossier qui contient `src/`).

## Commandes utiles

| Commande | Rôle |
|---|---|
| `python -m src.chatbot --debug` | chatbot en terminal, avec intention/confiance/slots |
| `python -m src.chatbot --rules-only` | sans ML (règles seules) |
| `python -m eval.evaluate_intent` | accuracy, F1, matrice de confusion, ablation |
| `python -m eval.evaluate_dialogue` | suivi d'état + utilisateurs simulés |
| `python -m eval.run_scenarios` | 6 scénarios S1–S6 × 2 formulations + transcriptions |
| `python -m eval.analyze_human_eval` | synthèse de l'évaluation humaine |
| `python -m pytest -q` | 20 tests automatiques |
| `python -m src.train_intent --backend sbert` | variante Sentence-BERT (optionnelle, non testée) |

## Structure

```
src/prepare_data.py     étapes 1-2 : acquisition, nettoyage, tours de parole, étiquettes d'intention, split
src/embeddings.py       étape 3 : vecteurs (RoBERTa/spaCy, SBERT ou TF-IDF) = phrase + dernière réponse du bot + état du dialogue
src/train_intent.py     étape 4.1 : classifieur d'intention (régression logistique)
src/nlu.py              extraction des slots par règles (cuisine, zone, prix, personnes, jour, heure, nom)
src/dialogue_manager.py étape 4.2 : état + politique à base de règles (hybride ML + règles)
src/nlg.py              réponses par templates
src/chatbot.py          étape 6 : version terminal
app_streamlit.py        étape 6 : interface web
eval/                   étape 5 : métriques, scénarios, protocole d'évaluation humaine (+ formulaire dans l'app)
reports/                résultats générés (JSON, CSV, matrice de confusion)
```

Voir **GUIDE.md** (explications étape par étape) et **reports/rapport_evaluation.md** (chiffres + limites).

## Limites 
- Étiquettes d'intention dérivées automatiquement des annotations → imparfaites, surtout la classe `other` (rappel 36 %).
- NLU à règles : pas de négation (« not expensive »), pas de fautes de frappe, anglais uniquement.
- Les 100 % en simulation viennent d'un simulateur écrit avec le NLU : ce n'est pas une garantie sur de vrais utilisateurs.
- Embeddings contextuels (RoBERTa) ≈ TF-IDF en accuracy (0,911 vs 0,916) : le gain vient surtout du **contexte du dialogue**, pas de l'encodeur.
