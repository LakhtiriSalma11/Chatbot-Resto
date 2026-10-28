"""Étape 6 — Chatbot en ligne de commande.

    python -m src.chatbot            # conversation normale
    python -m src.chatbot --debug    # affiche intention, confiance, source de la décision, slots
    python -m src.chatbot --rules-only   # sans classifieur ML (règles seules)

Commandes : /reset (nouvelle conversation), /quit (ou Ctrl+C) pour sortir.
"""
import argparse

from src.dialogue_manager import DialogueManager


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--rules-only", action="store_true")
    args = ap.parse_args(argv)

    bot = DialogueManager.from_defaults(rules_only=args.rules_only)
    print("=== Restaurant chatbot (Cambridge) — tape /reset pour recommencer, /quit pour sortir ===\n")
    print("Bot :", bot.opening_message())
    while True:
        try:
            text = input("Toi : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir !")
            break
        if text.lower() in ("/quit", "/exit", "quit", "exit"):
            print("Au revoir !")
            break
        if text.lower() == "/reset":
            bot.reset()
            print("Bot :", bot.opening_message())
            continue
        res = bot.respond(text)
        print("Bot :", res.reply)
        if args.debug:
            slots = {k: v for k, v in res.slots.items() if v is not None}
            print(f"      [intent={res.intent} conf={res.confidence:.2f} action={res.action} "
                  f"source={res.debug.get('source')}] slots={slots}")


if __name__ == "__main__":
    main()
