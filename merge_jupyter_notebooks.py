# pip install nbformat tkinter

import nbformat
import os
from nbformat import NotebookNode
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

def merge_notebooks(output_folder: str, output_filename: str, input_paths: list) -> None:
    merged_notebook: NotebookNode = nbformat.v4.new_notebook()
    output_path = os.path.join(output_folder, output_filename)
    
    log_messages = []
    log_messages.append(f"Merging notebooks into {output_path}...")

    extensions = [os.path.splitext(path)[1] for path in input_paths]
    if len(set(extensions)) > 1:
        messagebox.showwarning("Extension Mismatch", "All input files must have the same extension.")
        return
    
    for path in input_paths:
        if not path.endswith(".ipynb"):
            log_messages.append(f"Skipping {path}: not a .ipynb file.")
            continue
        try:
            log_messages.append(f"Reading {path}...")
            with open(path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
                merged_notebook.cells.extend(nb.cells)
        except Exception as e:
            log_messages.append(f"Error reading {path}: {e}")
            continue

    if 'metadata' in nb:
        merged_notebook.metadata = nb.metadata

    try:
        log_messages.append(f"Writing merged notebook to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            nbformat.write(merged_notebook, f)
        log_messages.append(f"Merged notebook successfully saved to {output_path}")
    except Exception as e:
        log_messages.append(f"Error writing to {output_path}: {e}")

    messagebox.showinfo("Merge Notebooks", "\n".join(log_messages))

def select_output_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        output_folder_entry.delete(0, tk.END)
        output_folder_entry.insert(0, folder_selected)

def select_input_files():
    files_selected = filedialog.askopenfilenames(filetypes=[("Jupyter Notebooks", "*.ipynb")])
    for file in files_selected:
        if file not in input_files_listbox.get(0, tk.END):
            input_files_listbox.insert(tk.END, file)

def on_remove_file_button_clicked():
    selected_indices = input_files_listbox.curselection()
    for index in reversed(selected_indices):
        input_files_listbox.delete(index)

def on_merge_button_clicked():
    output_folder = output_folder_entry.get()
    output_filename = output_filename_entry.get()
    if not output_filename:
        messagebox.showwarning("Input Error", "Please provide a name for the output file.")
        return
    if not output_filename.endswith(".ipynb"):
        output_filename += ".ipynb"
    input_paths = input_files_listbox.get(0, tk.END)
    if not output_folder or not input_paths or len(input_paths) < 2:
        messagebox.showwarning("Input Error", "Please provide a valid output folder and at least two input files.")
        return
    merge_notebooks(output_folder, output_filename, input_paths)

# Create the main window
root = tk.Tk()
root.title("Merge Jupyter Notebooks")

# Configure the grid to expand with window resize
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(2, weight=1)

# Create and place the widgets
ttk.Label(root, text="Output Folder:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
output_folder_entry = ttk.Entry(root, width=50)
output_folder_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
ttk.Button(root, text="Browse...", command=select_output_folder).grid(row=0, column=2, padx=10, pady=5)

ttk.Label(root, text="Output File Name:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
output_filename_entry = ttk.Entry(root, width=50)
output_filename_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

ttk.Label(root, text="Input File Paths:").grid(row=2, column=0, padx=10, pady=5, sticky=tk.NE)
input_files_listbox = tk.Listbox(root, selectmode=tk.SINGLE, width=50, height=10)
input_files_listbox.grid(row=2, column=1, padx=10, pady=5, sticky="nsew")

button_frame = ttk.Frame(root)
button_frame.grid(row=2, column=2, padx=10, pady=5, sticky="n")

ttk.Button(button_frame, text="Add...", command=select_input_files).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
ttk.Button(button_frame, text="Remove", command=on_remove_file_button_clicked).grid(row=1, column=0, padx=5, pady=5, sticky="ew")

merge_button = ttk.Button(root, text="Merge Notebooks", command=on_merge_button_clicked)
merge_button.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

# Start the main event loop
root.mainloop()
