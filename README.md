# Estrattore P7M per Windows

Strumento grafico per estrarre il documento originale dai file firmati digitalmente in formato **P7M** (firma CAdES), con integrazione nel menu contestuale del tasto destro di Windows.

---

## Funzionalità

- **Tasto destro** su uno o più file `.p7m` → voce "Estrai contenuto P7M"
- **Finestra singola**: selezionando anche 20 file insieme si apre una sola finestra che li elabora tutti
- Barra di avanzamento con conteggio file elaborati
- Scelta opzionale della cartella di destinazione
- Compatibile con PC che hanno già installato **InfoCamere firma4ng**, **GoSignDesktop**, **Dike** o altri software di firma digitale
- Chiede conferma prima di sovrascrivere file già esistenti

---

## Requisiti

- Windows 10 / 11
- [Python 3.8 o superiore](https://www.python.org/downloads/) — durante l'installazione spuntare **"Add Python to PATH"**

La libreria `asn1crypto` viene installata automaticamente dall'installer.

---

## Installazione

1. Scarica o clona questa repository
2. Metti tutti i file nella stessa cartella
3. Fai **doppio clic su `INSTALLA_TUTTO.bat`**
4. Se Windows chiede conferma di sicurezza, clicca **"Esegui comunque"**
5. Lo script si riavvia da solo come Amministratore e fa tutto in automatico

Al termine, fai clic destro su qualsiasi file `.p7m`: comparirà la voce **"Estrai contenuto P7M"**.

---

## Utilizzo

### Dal tasto destro
Seleziona uno o più file `.p7m` in Esplora File, fai clic destro e scegli **"Estrai contenuto P7M"**. Il file estratto viene salvato nella stessa cartella del `.p7m` originale, con lo stesso nome ma senza l'estensione `.p7m`.

Esempio: `fattura.pdf.p7m` → `fattura.pdf`

### Dall'interfaccia grafica
Lancia direttamente `p7m_extractor.py` per usare il programma in modalità manuale, con selezione file tramite finestra di dialogo e possibilità di scegliere una cartella di destinazione personalizzata.

---

## Disinstallazione

Lancia `DISINSTALLA.bat` oppure esegui direttamente il file presente in `C:\Programmi\P7MExtractor\DISINSTALLA.bat`.

---

## Come funziona tecnicamente

Il formato P7M (CAdES) è un file firmato digitalmente secondo lo standard **CMS/PKCS#7**. Il documento originale è incorporato all'interno come payload `SignedData`. Il programma usa la libreria [`asn1crypto`](https://github.com/wbond/asn1crypto) per decodificare la struttura ASN.1 ed estrarre il contenuto.

Per gestire la selezione multipla di file dal tasto destro (Windows lancia il programma una volta per ogni file), è implementato un meccanismo di **istanza singola** basato su socket locale: la prima istanza avviata apre la finestra e mette in ascolto una porta TCP locale; le istanze successive trovano la porta occupata, inviano il percorso del loro file alla finestra già aperta e si chiudono immediatamente.

---

## File inclusi

| File | Descrizione |
|------|-------------|
| `p7m_extractor.py` | Programma principale |
| `INSTALLA_TUTTO.bat` | Installer completo (copia file + registro + dipendenze) |
| `DISINSTALLA.bat` | Rimuove il menu e la cartella di installazione |

---

## Licenza

MIT License — libero uso, modifica e distribuzione.
