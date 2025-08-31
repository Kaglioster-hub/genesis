from deep_translator import GoogleTranslator

def traduci_testo(testo, source="en", target="it"):
    try:
        return GoogleTranslator(source=source, target=target).translate(testo)
    except Exception as e:
        print("Errore traduzione:", e)
        return testo
