# File Organizer + GUI

import shutil
from pathlib import Path

import tkinter as tkinter
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

# extension-based categorization -> standard type-based folders
EXT_CATEGORY_MAP = {
    "Images": ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"],
    "Documents": ["doc", "docx", "odt", "rtf", "txt", "md"],
    "Spreadsheets": ["xls", "xlsx", "csv", "ods"],
    "PDFs": ["pdf"],
    "Archives": ["zip", "rar", "7z", "tar", "gz", "bz2"],
    "Videos": ["mp4", "avi", "mkv", "mov", "wmv"],
    "Audio": ["mp3", "wav", "flac", "aac", "ogg"],
    "Presentations": ["ppt", "pptx", "key"],
    "Code": ["py", "js", "ts", "java", "c", "cpp", "cs", "go", "rb", "php", "html", "css"],
}

EXTENSION_TO_CATEGORY = {}
for category, extensions in EXT_CATEGORY_MAP.items():
    for extension in extensions:
        EXTENSION_TO_CATEGORY[extension] = category


def extension_for(filename):
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def category_for(extension):
    if not extension:
        return "NoExtension"
    return EXTENSION_TO_CATEGORY.get(extension, extension.upper())


def unique_dest(folder, filename):
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = folder / filename
    counter = 1

    while candidate.exists():
        candidate = folder / f"{stem} ({counter}){suffix}"
        counter += 1

    return candidate


def scan_directory(directory):
    root = Path(directory)
    if not root.is_dir():
        return {}

    result = {}
    for entry in root.iterdir():
        if entry.is_file():
            extension = extension_for(entry.name)
            result.setdefault(extension, []).append(entry.name)

    return result


def organize_dir(directory, selected_ext, log):
    root = Path(directory)
    if not root.is_dir():
        log(f"Directory not found: {root}")
        return 0, 0

    chosen = set(selected_ext)
    moved = 0
    skipped = 0

    for entry in root.iterdir():
        if not entry.is_file():
            continue

        extension = extension_for(entry.name)
        if extension not in chosen:
            skipped += 1
            continue

        category = category_for(extension)
        destination_folder = root / category
        destination_folder.mkdir(exist_ok=True)
        destination_path = unique_dest(destination_folder, entry.name)

        try:
            shutil.move(str(entry), str(destination_path))
            moved += 1
            relative_path = destination_path.relative_to(root)
            log(f"Moved: {entry.name} -> {relative_path}")
        except PermissionError:
            log(f"Permission denied: {entry.name}")
        except Exception as exc:  # pragma: no cover
            log(f"Error moving {entry.name}: {exc}")

    log(f"Done. Moved: {moved}. Skipped: {skipped}.")
    return moved, skipped


class FileOrganizerApp(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Organizer")
        self.geometry("980x680")
        self.minsize(900, 620)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.directory_var = tkinter.StringVar()
        self.type_vars = {}

        panel = self._build_main_panel()
        panel.grid(row=0, column=0, sticky="nsew")

    def _build_main_panel(self):
        panel = tkinter.Frame(self)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(5, weight=1)

        tkinter.Label(panel, text="File Organizer", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        tkinter.Label(panel, text="1) Choose folder  2) Uncheck file types to skip  3) Click Run").grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        controls = tkinter.Frame(panel)
        controls.grid(row=2, column=0, sticky="ew", padx=12)
        controls.columnconfigure(1, weight=1)

        tkinter.Label(controls, text="Folder:").grid(row=0, column=0, sticky="w")
        tkinter.Entry(controls, textvariable=self.directory_var).grid(row=0, column=1, sticky="ew", padx=8)
        tkinter.Button(controls, text="Browse", command=self.browse_directory).grid(row=0, column=2, padx=(0, 8))
        tkinter.Button(controls, text="Scan", command=self.scan_types).grid(row=0, column=3)

        self.types_frame = tkinter.LabelFrame(panel, text="Detected File Types")
        self.types_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=10)
        tkinter.Label(self.types_frame, text="Select a folder and click Scan.").grid(row=0, column=0, sticky="w", padx=8, pady=8)

        run_button = tkinter.Button(panel, text="Run Script", command=self.run_organizer)
        run_button.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 10))

        self.log_box = ScrolledText(panel, height=14)
        self.log_box.grid(row=5, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log_box.configure(state="disabled")
        self.log("Ready.")

        return panel

    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def browse_directory(self):
        directory = filedialog.askdirectory(title="Select directory")
        if directory:
            self.directory_var.set(directory)
            self.scan_types()

    def scan_types(self):
        directory = self.directory_var.get().strip()
        if not directory:
            messagebox.showwarning("Folder is required", "Please choose a folder first.")
            return

        if not Path(directory).is_dir():
            messagebox.showwarning("Folder is required", "Please choose a valid folder.")
            return

        detected = scan_directory(directory)
        self.render_type_checkboxes(detected)

        total_files = sum(len(files) for files in detected.values())
        self.log(f"Scanned: {directory}")
        self.log(f"Found {total_files} file(s) across {len(detected)} type group(s).")

    def render_type_checkboxes(self, detected_types):
        for child in self.types_frame.winfo_children():
            child.destroy()

        self.type_vars.clear()

        if not detected_types:
            tkinter.Label(self.types_frame, text="No files were found in this folder.").grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        sorted_types = sorted(detected_types.items(), key=lambda item: (-len(item[1]), item[0]))
        for index, (extension, files) in enumerate(sorted_types):
            label = extension or "(no extension)"
            var = tkinter.IntVar(value=1)

            tkinter.Checkbutton(self.types_frame, text=f"{label} - {len(files)} file(s)", variable=var).grid(
                row=index // 3,
                column=index % 3,
                sticky="w",
                padx=8,
                pady=6,
            )
            self.type_vars[extension] = var

    def selected_ext(self):
        return [extension for extension, var in self.type_vars.items() if var.get()]

    def run_organizer(self):
        directory = self.directory_var.get().strip()
        if not Path(directory).is_dir():
            messagebox.showwarning("Folder is required", "Please choose a valid folder to organize!")
            return

        if not self.type_vars:
            self.scan_types()
            if not self.type_vars:
                return

        chosen = self.selected_ext()
        if not chosen:
            messagebox.showwarning("No types were selected", "Please select at least one file type.")
            return

        if not messagebox.askyesno("Confirm", "Move files into their type folders now?"):
            return

        self.clear_log()
        organize_dir(directory=directory, selected_ext=chosen, log=self.log)
        messagebox.showinfo("Done", "Organized!")


def main():
    FileOrganizerApp().mainloop()


if __name__ == "__main__":
    main()