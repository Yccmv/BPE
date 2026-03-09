import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
import time
import json
import tempfile
import socket
from asn1crypto import cms

# ============================================================
#  MECCANISMO ISTANZA SINGOLA - doppio livello di protezione
#
#  LIVELLO 1 - File di lock esclusivo su disco:
#    Il primo processo crea e tiene aperto un file di lock.
#    I processi successivi vedono il lock, scrivono il loro
#    file nella coda e si chiudono subito.
#
#  LIVELLO 2 - Socket come canale di notifica:
#    La finestra principale ascolta sul socket e quando arriva
#    una notifica va a leggere i nuovi file dalla coda su disco.
#
#  Questo approccio funziona anche se Windows lancia 20 processi
#  nello stesso millisecondo: il file lock è atomico a livello
#  di sistema operativo, uno solo vince.
# ============================================================

LOCK_FILE   = os.path.join(tempfile.gettempdir(), 'p7m_extractor.lock')
QUEUE_DIR   = os.path.join(tempfile.gettempdir(), 'p7m_extractor_queue')
NOTIFY_PORT = 47823


# ------------------------------------------------------------------
#  Funzioni di lock / coda
# ------------------------------------------------------------------

def try_acquire_lock():
    """
    Tenta di acquisire il lock esclusivo.
    Ritorna il file handle se riesce (istanza principale),
    None se il lock è già tenuto da un altro processo.
    """
    try:
        # Apre il file in modalità esclusiva su Windows
        import msvcrt
        fh = open(LOCK_FILE, 'w')
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        fh.write(str(os.getpid()))
        fh.flush()
        return fh
    except (OSError, IOError):
        return None


def release_lock(fh):
    try:
        import msvcrt
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        fh.close()
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass
    except Exception:
        pass


def enqueue_files(files):
    """Scrive i file in un file JSON nella cartella coda, poi notifica via socket."""
    os.makedirs(QUEUE_DIR, exist_ok=True)
    # Nome file univoco basato su pid + timestamp in nanosecondi
    fname = os.path.join(QUEUE_DIR, f'{os.getpid()}_{time.time_ns()}.json')
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(files, f)
    # Notifica la finestra principale tramite socket (best-effort)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('127.0.0.1', NOTIFY_PORT))
        s.sendall(b'NEW')
        s.close()
    except Exception:
        pass  # La finestra principale controlla la coda anche periodicamente


def dequeue_all_files():
    """Legge e rimuove tutti i file in coda, restituisce lista di percorsi."""
    result = []
    if not os.path.isdir(QUEUE_DIR):
        return result
    for fname in os.listdir(QUEUE_DIR):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(QUEUE_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                files = json.load(f)
            result.extend(files)
            os.remove(fpath)
        except Exception:
            pass
    return result


# ------------------------------------------------------------------
#  GUI
# ------------------------------------------------------------------

class P7MExtractorGUI:
    def __init__(self, root, lock_handle, initial_files=None):
        self.root = root
        self.lock_handle = lock_handle
        self.root.title("Estrattore P7M Avanzato")
        self.root.geometry("700x550")

        self.selected_files = []
        self.output_folder = None

        style = ttk.Style()
        style.configure('Large.TButton', font=('TkDefaultFont', 12), padding=(10, 5))

        self.create_gui()
        self.root.bind('<Return>', lambda event: self.start_extraction())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Avvia server di notifica e polling coda
        self._start_notify_server()
        self._poll_queue()

        # File passati direttamente all'avvio
        if initial_files:
            self._add_files(initial_files)
            if self.selected_files:
                self.root.after(600, self.start_extraction)

    def _on_close(self):
        release_lock(self.lock_handle)
        self.root.destroy()

    # ---- Server di notifica ----

    def _start_notify_server(self):
        def server_loop():
            try:
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(('127.0.0.1', NOTIFY_PORT))
                srv.listen(20)
                srv.settimeout(1)
                while True:
                    if not (hasattr(self, 'root') and self.root.winfo_exists()):
                        break
                    try:
                        conn, _ = srv.accept()
                        conn.recv(16)
                        conn.close()
                        # Sveglia il thread principale per leggere la coda
                        self.root.after(0, self._check_queue)
                    except socket.timeout:
                        continue
                srv.close()
            except Exception as e:
                print(f"Notify server error: {e}")

        threading.Thread(target=server_loop, daemon=True).start()

    def _poll_queue(self):
        """Controllo periodico della coda ogni 500ms (fallback se il socket non arriva)."""
        self._check_queue()
        self.root.after(500, self._poll_queue)

    def _check_queue(self):
        """Legge i file in coda e li aggiunge alla lista."""
        files = dequeue_all_files()
        if files:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self._add_files(files)
            if not (hasattr(self, 'extraction_thread') and self.extraction_thread.is_alive()):
                if self.selected_files:
                    self.root.after(300, self.start_extraction)

    # ---- Gestione lista file ----

    def _add_files(self, files):
        added = 0
        for f in files:
            f = f.strip('"').strip("'")
            if os.path.isfile(f) and f not in self.selected_files:
                self.selected_files.append(f)
                added += 1
        if added:
            self.update_file_list()
            self.progress_label.config(text=f"{added} file aggiunti alla lista.")

    # ---- Costruzione GUI ----

    def create_gui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.selection_frame = ttk.Frame(main_frame)
        self.selection_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            self.selection_frame,
            text="Seleziona File P7M",
            command=self.select_files
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        ttk.Button(
            self.selection_frame,
            text="Seleziona Cartella Destinazione (Opzionale)",
            command=self.select_output_folder
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.file_listbox = tk.Listbox(list_frame, height=12)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=5)

        self.output_label = ttk.Label(
            info_frame,
            text="Destinazione: Cartella sorgente dei file (default)"
        )
        self.output_label.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.clear_button = ttk.Button(
            info_frame,
            text="Pulisci Lista",
            command=self.clear_list
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)

        self.progress_bar = ttk.Progressbar(
            main_frame, orient="horizontal", length=300, mode="determinate"
        )
        self.progress_bar.pack(pady=10, fill=tk.X, padx=5)

        self.progress_label = ttk.Label(main_frame, text="")
        self.progress_label.pack(pady=(0, 5))

        self.extract_button = ttk.Button(
            main_frame,
            text="Estrai File Selezionati",
            command=self.start_extraction,
            style='Large.TButton'
        )
        self.extract_button.pack(pady=10, ipady=10, fill=tk.X, padx=5)

    def select_files(self):
        if hasattr(self, 'extraction_thread') and self.extraction_thread.is_alive():
            messagebox.showwarning("Attenzione", "Estrazione in corso. Attendere il completamento.")
            return
        files = filedialog.askopenfilenames(
            title="Seleziona uno o più file P7M",
            filetypes=[("File P7M", "*.p7m"), ("Tutti i file", "*.*")]
        )
        if files:
            self._add_files(list(files))

    def select_output_folder(self):
        if hasattr(self, 'extraction_thread') and self.extraction_thread.is_alive():
            messagebox.showwarning("Attenzione", "Estrazione in corso. Attendere il completamento.")
            return
        folder = filedialog.askdirectory(title="Seleziona cartella destinazione")
        if folder:
            self.output_folder = folder
            self.output_label.config(text=f"Destinazione: {self.output_folder}")
        else:
            self.output_folder = None
            self.output_label.config(text="Destinazione: Cartella sorgente dei file (default)")

    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for file in self.selected_files:
            self.file_listbox.insert(tk.END, os.path.basename(file))

    def clear_list(self):
        if hasattr(self, 'extraction_thread') and self.extraction_thread.is_alive():
            messagebox.showwarning("Attenzione", "Estrazione in corso. Attendere il completamento.")
            return
        if self.selected_files:
            if messagebox.askyesno("Conferma Pulizia", "Svuotare la lista?", parent=self.root):
                self.selected_files.clear()
                self.update_file_list()
                self.progress_label.config(text="Lista file pulita.")
                self.progress_bar['value'] = 0
        else:
            self.progress_label.config(text="La lista è già vuota.")

    # ---- Estrazione ----

    def extract_p7m(self, input_path, output_path):
        try:
            if os.path.exists(output_path):
                overwrite = messagebox.askyesno(
                    "Sovrascrivere?",
                    f"Il file '{os.path.basename(output_path)}' esiste già.\n\nVuoi sovrascriverlo?",
                    parent=self.root
                )
                if not overwrite:
                    return 'skipped'

            with open(input_path, 'rb') as f:
                p7m_data = f.read()

            content_info = cms.ContentInfo.load(p7m_data)
            if content_info['content_type'].native != 'signed_data':
                return 'failed'

            signed_data = content_info['content']
            encap_content_info = signed_data['encap_content_info']

            if (encap_content_info['content_type'].native == 'data'
                    and encap_content_info['content'].native is not None):
                content = encap_content_info['content'].native
            else:
                return 'failed'

            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(content)
            return 'success'

        except Exception as e:
            print(f"Errore: {input_path} - {e}")
            return 'failed'

    def set_gui_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.extract_button.config(state=state)
        self.clear_button.config(state=state)
        for widget in self.selection_frame.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.config(state=state)

    def start_extraction(self):
        if hasattr(self, 'extraction_thread') and self.extraction_thread.is_alive():
            return
        if not self.selected_files:
            messagebox.showwarning("Attenzione", "Nessun file P7M selezionato!")
            return

        self.progress_bar['maximum'] = len(self.selected_files)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Preparazione estrazione...")
        self.set_gui_state(enabled=False)

        self.extraction_thread = threading.Thread(target=self._run_extraction_thread, daemon=True)
        self.extraction_thread.start()

    def _run_extraction_thread(self):
        successful = 0
        failed = 0
        skipped = 0
        processed_count = 0
        files_to_process = list(self.selected_files)
        total_files = len(files_to_process)

        for file_path in files_to_process:
            if not (hasattr(self, 'root') and self.root.winfo_exists()):
                break

            base_name = os.path.basename(file_path)
            output_name = base_name[:-4] if base_name.lower().endswith(".p7m") else base_name + "_extracted"
            destination_dir = self.output_folder if self.output_folder else os.path.dirname(file_path)
            output_path = os.path.join(destination_dir, output_name)

            self.root.after(0, lambda p=processed_count+1, t=total_files, f=base_name:
                            self.progress_label.config(text=f"Elaboro ({p}/{t}): {f}"))

            result = self.extract_p7m(file_path, output_path)
            if result == 'success':
                successful += 1
            elif result == 'skipped':
                skipped += 1
            else:
                failed += 1

            processed_count += 1
            self.root.after(0, lambda v=processed_count: self.progress_bar.config(value=v))

        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.after(0, self._extraction_complete, successful, failed, skipped, total_files)

    def _extraction_complete(self, successful, failed, skipped, total_files):
        message = (
            f"Estrazione completata!\n\n"
            f"File totali: {total_files}\n"
            f"Successo: {successful}\n"
            f"Saltati: {skipped}\n"
            f"Errori: {failed}"
        )
        if failed > 0:
            message += "\n\nControllare la console per dettagli sugli errori."
            messagebox.showerror("Completato con Errori", message, parent=self.root)
        elif successful == 0 and skipped == 0:
            messagebox.showerror("Errore", "Nessun file elaborato.", parent=self.root)
        else:
            messagebox.showinfo("Completato", message, parent=self.root)

        self.selected_files.clear()
        self.update_file_list()
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Pronto.")
        self.set_gui_state(enabled=True)


# ------------------------------------------------------------------
#  AUTO-INSTALLAZIONE (solo quando eseguito come .exe PyInstaller)
# ------------------------------------------------------------------

INSTALL_DIR  = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Programmi'), 'P7MExtractor')
INSTALL_NAME = 'EstrattoreP7M.exe'
INSTALL_PATH = os.path.join(INSTALL_DIR, INSTALL_NAME)
MARKER_FILE  = os.path.join(INSTALL_DIR, '.installed')


def _is_frozen():
    """Ritorna True se siamo dentro un exe PyInstaller."""
    return getattr(sys, 'frozen', False)


def _is_already_installed():
    """Controlla se l'exe corrente è già nella cartella di installazione."""
    if not _is_frozen():
        return True  # script .py: non installiamo nulla
    current = os.path.abspath(sys.executable)
    target  = os.path.abspath(INSTALL_PATH)
    return current.lower() == target.lower()


def _run_install():
    """
    Copia l'exe in INSTALL_DIR, scrive le chiavi di registro per il
    tasto destro su .p7m e crea il file marker.
    Chiede elevazione UAC se necessario.
    """
    import ctypes, shutil, subprocess

    # --- Controlla se abbiamo già i permessi di amministratore ---
    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

    if not is_admin:
        # Rilancia se stesso con RunAs (UAC prompt)
        params = ' '.join(f'"{a}"' for a in sys.argv[1:])
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        if ret > 32:
            # Rilanciato con successo come admin: chiudi questa istanza
            sys.exit(0)
        else:
            tk.messagebox.showerror(
                "Errore",
                "Impossibile ottenere i permessi di amministratore.\n"
                "Prova a eseguire il programma come Amministratore."
            )
            sys.exit(1)

    # --- Siamo admin: procedi con l'installazione ---
    try:
        os.makedirs(INSTALL_DIR, exist_ok=True)
        shutil.copy2(sys.executable, INSTALL_PATH)

        # Rimuovi eventuali chiavi precedenti
        subprocess.run(
            ['reg', 'delete', r'HKEY_CLASSES_ROOT\*\shell\EstraiP7M', '/f'],
            capture_output=True
        )

        exe_esc = INSTALL_PATH.replace('\\', '\\\\')

        # Voce menu tasto destro (solo su file .p7m)
        subprocess.run(['reg', 'add',
            r'HKEY_CLASSES_ROOT\*\shell\EstraiP7M',
            '/ve', '/d', 'Estrai contenuto P7M', '/f'], capture_output=True)
        subprocess.run(['reg', 'add',
            r'HKEY_CLASSES_ROOT\*\shell\EstraiP7M',
            '/v', 'Icon', '/d', 'shell32.dll,1', '/f'], capture_output=True)
        subprocess.run(['reg', 'add',
            r'HKEY_CLASSES_ROOT\*\shell\EstraiP7M',
            '/v', 'AppliesTo', '/d', r'System.FileName:"*.p7m"', '/f'], capture_output=True)
        subprocess.run(['reg', 'add',
            r'HKEY_CLASSES_ROOT\*\shell\EstraiP7M\command',
            '/ve', '/d', f'"{exe_esc}" "%1"', '/f'], capture_output=True)

        # Crea uninstaller nel registro (Programmi e funzionalità)
        uninst_key = r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\EstrattoreP7M'
        subprocess.run(['reg', 'add', uninst_key,
            '/v', 'DisplayName', '/d', 'Estrattore P7M', '/f'], capture_output=True)
        subprocess.run(['reg', 'add', uninst_key,
            '/v', 'UninstallString', '/d',
            f'"{INSTALL_PATH}" --uninstall', '/f'], capture_output=True)
        subprocess.run(['reg', 'add', uninst_key,
            '/v', 'DisplayIcon', '/d', INSTALL_PATH, '/f'], capture_output=True)
        subprocess.run(['reg', 'add', uninst_key,
            '/v', 'Publisher', '/d', 'Estrattore P7M', '/f'], capture_output=True)

        # File marker
        with open(MARKER_FILE, 'w') as f:
            f.write('installed')

        # Riavvia Esplora File per aggiornare il menu contestuale
        subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             'Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue; '
             'Start-Sleep -Seconds 1; Start-Process explorer'],
            capture_output=True
        )

        tk.messagebox.showinfo(
            "Installazione completata",
            f"Estrattore P7M installato in:\n{INSTALL_DIR}\n\n"
            "Ora puoi fare clic destro su qualsiasi file .p7m\n"
            "e scegliere «Estrai contenuto P7M».\n\n"
            "Il programma si aprirà ora."
        )

        # Riavvia dalla posizione installata
        subprocess.Popen([INSTALL_PATH] + sys.argv[1:])
        sys.exit(0)

    except Exception as e:
        tk.messagebox.showerror("Errore installazione", str(e))
        sys.exit(1)


def _run_uninstall():
    """Disinstalla: rimuove registro e cartella."""
    import ctypes, shutil, subprocess

    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    if not is_admin:
        params = '--uninstall'
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        sys.exit(0)

    risposta = tk.messagebox.askyesno(
        "Disinstalla Estrattore P7M",
        "Rimuovere Estrattore P7M dal sistema?\n\n"
        f"Verrà eliminata la cartella:\n{INSTALL_DIR}\n"
        "e la voce dal menu tasto destro."
    )
    if not risposta:
        sys.exit(0)

    subprocess.run(
        ['reg', 'delete', r'HKEY_CLASSES_ROOT\*\shell\EstraiP7M', '/f'],
        capture_output=True)
    subprocess.run(
        ['reg', 'delete',
         r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\EstrattoreP7M',
         '/f'],
        capture_output=True)

    # Non possiamo cancellare se stessi mentre siamo in esecuzione:
    # usiamo un piccolo script cmd ritardato
    bat = os.path.join(tempfile.gettempdir(), '_p7m_uninstall.bat')
    with open(bat, 'w') as f:
        f.write(f'@echo off\n'
                f'ping 127.0.0.1 -n 3 >nul\n'
                f'rmdir /s /q "{INSTALL_DIR}"\n'
                f'del "%~f0"\n')
    subprocess.Popen(['cmd', '/c', bat], close_fds=True)

    tk.messagebox.showinfo("Disinstallazione completata",
                           "Estrattore P7M è stato rimosso dal sistema.")
    sys.exit(0)


# ------------------------------------------------------------------
#  ENTRY POINT
# ------------------------------------------------------------------

if __name__ == "__main__":
    initial_files = [f.strip('"').strip("'") for f in sys.argv[1:]] if len(sys.argv) > 1 else []

    # ── Gestione --uninstall ──────────────────────────────────────
    if '--uninstall' in sys.argv:
        _root_tmp = tk.Tk(); _root_tmp.withdraw()
        _run_uninstall()

    # ── Auto-installazione al primo avvio ─────────────────────────
    if _is_frozen() and not _is_already_installed():
        _root_tmp = tk.Tk(); _root_tmp.withdraw()
        _run_install()   # non ritorna: rilancia da INSTALL_PATH

    # Tenta di acquisire il lock esclusivo
    lock_handle = try_acquire_lock()

    if lock_handle is None:
        # --- Istanza secondaria ---
        # Un'altra finestra è già aperta: metti i file in coda e chiudi
        if initial_files:
            enqueue_files(initial_files)
        sys.exit(0)

    # --- Istanza principale ---
    # Pulisci eventuali residui di coda da esecuzioni precedenti
    for f in (dequeue_all_files() or []):
        if f not in initial_files and os.path.isfile(f):
            initial_files.append(f)

    root = tk.Tk()
    app = P7MExtractorGUI(root, lock_handle, initial_files=initial_files)
    root.mainloop()
