import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from asn1crypto import cms
from pathlib import Path
import threading

class P7MExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Estrattore P7M")
        self.root.geometry("600x400")
        
        self.selected_files = []
        self.output_folder = ""
        
        self.create_gui()
        
    def create_gui(self):
        # Frame principale
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pulsanti
        ttk.Button(
            main_frame,
            text="Seleziona File P7M",
            command=self.select_files
        ).pack(pady=5)
        
        ttk.Button(
            main_frame,
            text="Seleziona Cartella Destinazione",
            command=self.select_output_folder
        ).pack(pady=5)
        
        # Lista file
        self.file_listbox = tk.Listbox(main_frame, height=10)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Label output
        self.output_label = ttk.Label(
            main_frame,
            text="Cartella destinazione: non selezionata"
        )
        self.output_label.pack(pady=5)
        
        # Pulsante estrai
        ttk.Button(
            main_frame,
            text="Estrai",
            command=self.start_extraction
        ).pack(pady=5)
        
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Seleziona file P7M",
            filetypes=[("File P7M", "*.p7m")]
        )
        if files:
            self.selected_files.extend(files)
            self.update_file_list()
            
    def select_output_folder(self):
        folder = filedialog.askdirectory(
            title="Seleziona cartella destinazione"
        )
        if folder:
            self.output_folder = folder
            self.output_label.config(
                text=f"Cartella destinazione: {folder}"
            )
            
    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for file in self.selected_files:
            self.file_listbox.insert(tk.END, os.path.basename(file))
            
    def extract_p7m(self, file_path):
        try:
            # Leggi il file P7M
            with open(file_path, 'rb') as f:
                p7m_data = f.read()
            
            # Parsing del contenuto P7M
            content_info = cms.ContentInfo.load(p7m_data)
            signed_data = content_info['content']
            
            # Estrai il contenuto originale
            content = signed_data['encap_content_info']['content'].contents
            
            # Determina l'estensione
            base_name = os.path.basename(file_path)
            output_name = base_name[:-4]  # rimuovi .p7m
            
            # Salva il file
            output_path = os.path.join(self.output_folder, output_name)
            with open(output_path, 'wb') as f:
                f.write(content)
                
            return True
            
        except Exception as e:
            return False
            
    def start_extraction(self):
        if not self.selected_files:
            messagebox.showwarning("Attenzione", "Nessun file selezionato!")
            return
            
        if not self.output_folder:
            messagebox.showwarning("Attenzione", "Seleziona una cartella di destinazione!")
            return
        
        successful = 0
        failed = 0
        
        for file_path in self.selected_files:
            if self.extract_p7m(file_path):
                successful += 1
            else:
                failed += 1
        
        # Messaggio finale con il riepilogo
        message = f"Estrazione completata!\n\nFile elaborati con successo: {successful}"
        if failed > 0:
            message += f"\nFile non elaborati: {failed}"
            
        messagebox.showinfo("Completato", message)
        
        # Pulisci la lista dei file dopo l'estrazione
        self.selected_files.clear()
        self.update_file_list()

if __name__ == "__main__":
    root = tk.Tk()
    app = P7MExtractorGUI(root)
    root.mainloop()