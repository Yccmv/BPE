import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from asn1crypto import cms
# from pathlib import Path # Non strettamente necessario qui
import threading
import time # Per simulare/gestire l'aggiornamento della progress bar

class P7MExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Estrattore P7M Avanzato")
        self.root.geometry("700x550")

        self.selected_files = []
        self.output_folder = None

        style = ttk.Style()
        style.configure('Large.TButton', font=('TkDefaultFont', 12), padding=(10, 5))

        self.create_gui()

        self.root.bind('<Return>', lambda event: self.start_extraction())

    def create_gui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Sezione Selezione ---
        # ***** CORREZIONE QUI *****
        self.selection_frame = ttk.Frame(main_frame)
        self.selection_frame.pack(fill=tk.X, pady=5)
        # *************************

        ttk.Button(
            self.selection_frame, # Usa self.selection_frame qui
            text="Seleziona File P7M",
            command=self.select_files
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        ttk.Button(
            self.selection_frame, # Usa self.selection_frame qui
            text="Seleziona Cartella Destinazione (Opzionale)",
            command=self.select_output_folder
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # --- Lista File ---
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.file_listbox = tk.Listbox(list_frame, height=12)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        # --- Label Output e Clear Button ---
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=5)

        self.output_label = ttk.Label(
            info_frame,
            text="Destinazione: Cartella sorgente dei file (default)"
        )
        self.output_label.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X) # Aggiunto expand e fill

        self.clear_button = ttk.Button(
            info_frame,
            text="Pulisci Lista",
            command=self.clear_list
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)

        # --- Progress Bar ---
        self.progress_bar = ttk.Progressbar(
            main_frame,
            orient="horizontal",
            length=300,
            mode="determinate"
        )
        self.progress_bar.pack(pady=10, fill=tk.X, padx=5)
        self.progress_label = ttk.Label(main_frame, text="")
        self.progress_label.pack(pady=(0, 5))

        # --- Pulsante Estrai ---
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
            new_files_added = 0
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
                    new_files_added += 1
            if new_files_added > 0:
                self.update_file_list()
                self.progress_label.config(text=f"{new_files_added} file aggiunti alla lista.")
            else:
                self.progress_label.config(text="Nessun nuovo file aggiunto (già in lista).")


    def select_output_folder(self):
        if hasattr(self, 'extraction_thread') and self.extraction_thread.is_alive():
            messagebox.showwarning("Attenzione", "Estrazione in corso. Attendere il completamento.")
            return

        folder = filedialog.askdirectory(
            title="Seleziona cartella destinazione"
        )
        if folder:
            self.output_folder = folder
            self.output_label.config(
                text=f"Destinazione: {self.output_folder}"
            )
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
            confirm = messagebox.askyesno("Conferma Pulizia", "Sei sicuro di voler svuotare la lista dei file selezionati?", parent=self.root)
            if confirm:
                self.selected_files.clear()
                self.update_file_list()
                self.progress_label.config(text="Lista file pulita.")
                self.progress_bar['value'] = 0
        else:
             self.progress_label.config(text="La lista è già vuota.")


    def extract_p7m(self, input_path, output_path):
        """
        Estrae il contenuto da un singolo file P7M.
        Controlla l'esistenza del file di output e chiede conferma per sovrascrivere.
        Restituisce:
            'success': Estrazione completata con successo.
            'skipped': Estrazione saltata dall'utente (non sovrascrivere).
            'failed': Errore durante l'estrazione.
        """
        try:
            if os.path.exists(output_path):
                # IMPORTANTE: Questa chiamata a messagebox da un thread secondario
                # POTREBBE causare problemi su alcune piattaforme/configurazioni.
                # Se si verificano blocchi o comportamenti anomali, sarà necessario
                # implementare un meccanismo di comunicazione basato su code
                # per far eseguire la messagebox al thread principale.
                overwrite = messagebox.askyesno(
                    "Sovrascrivere?",
                    f"Il file '{os.path.basename(output_path)}'\n"
                    f"esiste già nella cartella di destinazione.\n\n"
                    f"Vuoi sovrascriverlo?",
                    parent=self.root # Rende la finestra modale rispetto alla principale
                )
                if not overwrite:
                    print(f"Skipping (non sovrascrivere): {output_path}")
                    return 'skipped'

            with open(input_path, 'rb') as f:
                p7m_data = f.read()

            content_info = cms.ContentInfo.load(p7m_data)

            if content_info['content_type'].native != 'signed_data':
                print(f"Errore: Il file non sembra essere un P7M firmato (SignedData): {input_path}")
                return 'failed'

            signed_data = content_info['content']
            encap_content_info = signed_data['encap_content_info']

            if encap_content_info['content_type'].native == 'data' and encap_content_info['content'].native is not None:
                 content = encap_content_info['content'].native
            else:
                print(f"Errore: Contenuto non trovato o tipo non supportato nel P7M: {input_path}")
                return 'failed'

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(content)

            print(f"Successo: {output_path}")
            return 'success'

        except ValueError as e:
             print(f"Errore di parsing P7M (file corrotto o non P7M?): {input_path} - {e}")
             return 'failed'
        except Exception as e:
            print(f"Errore generico durante l'estrazione di {input_path}: {e}")
            import traceback
            traceback.print_exc()
            return 'failed'

    def set_gui_state(self, enabled):
        """Abilita o disabilita i controlli GUI durante l'estrazione."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.extract_button.config(state=state)
        self.clear_button.config(state=state)
        # Ora dovrebbe funzionare perché self.selection_frame esiste
        for widget in self.selection_frame.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.config(state=state)
        # self.file_listbox.config(state=state) # Opzionale: disabilitare anche la lista


    def start_extraction(self):
        if hasattr(self, 'extraction_thread') and self.extraction_thread.is_alive():
            messagebox.showwarning("Attenzione", "Un'estrazione è già in corso.")
            return

        if not self.selected_files:
            messagebox.showwarning("Attenzione", "Nessun file P7M selezionato nella lista!")
            return

        self.progress_bar['maximum'] = len(self.selected_files)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Preparazione estrazione...")

        self.set_gui_state(enabled=False) # Chiamata a set_gui_state

        self.extraction_thread = threading.Thread(target=self._run_extraction_thread, daemon=True)
        self.extraction_thread.start()


    def _run_extraction_thread(self):
        """Questa funzione viene eseguita nel thread separato."""
        successful = 0
        failed = 0
        skipped = 0
        processed_count = 0
        files_to_process = list(self.selected_files) # Crea una copia per evitare problemi se la lista viene modificata
        total_files = len(files_to_process)

        for file_path in files_to_process:
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                print("Finestra principale chiusa, interruzione thread.")
                break # Esce dal ciclo se la finestra è stata chiusa

            base_name = os.path.basename(file_path)
            output_name = base_name[:-4] if base_name.lower().endswith(".p7m") else base_name + "_extracted"

            if self.output_folder:
                destination_dir = self.output_folder
            else:
                destination_dir = os.path.dirname(file_path)

            output_path = os.path.join(destination_dir, output_name)

            # Aggiorna etichetta progresso (usa 'after' per sicurezza con Tkinter)
            self.root.after(0, lambda p=processed_count+1, t=total_files, f=base_name:
                            self.progress_label.config(text=f"Elaboro ({p}/{t}): {f}"))

            result = self.extract_p7m(file_path, output_path)

            if result == 'success':
                successful += 1
            elif result == 'skipped':
                skipped += 1
            else: # 'failed'
                failed += 1

            processed_count += 1

            # Aggiorna la barra di avanzamento (usa 'after' per sicurezza con Tkinter)
            self.root.after(0, lambda v=processed_count: self.progress_bar.config(value=v))
            # time.sleep(0.01) # Opzionale per vedere meglio la barra


        # Chiama la funzione di completamento nel thread principale solo se la finestra esiste ancora
        if hasattr(self, 'root') and self.root.winfo_exists():
             self.root.after(0, self._extraction_complete, successful, failed, skipped, total_files)
        else:
            print("Estrazione terminata ma finestra non trovata per il resoconto.")


    def _extraction_complete(self, successful, failed, skipped, total_files):
        """Questa funzione viene chiamata alla fine dell'estrazione, nel thread principale."""

        message = f"Estrazione completata!\n\n" \
                  f"File totali selezionati: {total_files}\n" \
                  f"Elaborati con successo: {successful}\n" \
                  f"Saltati (non sovrascritti): {skipped}\n" \
                  f"Errori: {failed}"

        if failed > 0:
             message += "\n\nControllare la console/output per dettagli sugli errori."
             messagebox.showerror("Completato con Errori", message, parent=self.root)
        elif successful == 0 and skipped == 0:
             messagebox.showerror("Errore", "Nessun file è stato elaborato. Controllare i file e i permessi.", parent=self.root)
        elif successful > 0 or skipped > 0:
             messagebox.showinfo("Completato", message, parent=self.root)
        # Caso implicito: total_files era 0 (non dovrebbe accadere per i controlli precedenti)

        # Pulisci la lista dei file elaborati (auto-clear)
        self.selected_files.clear()
        self.update_file_list()

        # Resetta la progress bar e label
        self.progress_bar['value'] = 0
        # Lascia l'ultimo messaggio o resetta? Decido di resettare.
        self.progress_label.config(text="Pronto.")

        # Riabilita i controlli GUI
        self.set_gui_state(enabled=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = P7MExtractorGUI(root)
    root.mainloop()