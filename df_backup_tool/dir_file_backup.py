# Directory & File Backup Tool + GUI

import argparse
from datetime import datetime
import json
import shutil
import sys
from pathlib import Path

import tkinter
from tkinter import filedialog, messagebox

CONFIG_PATH = Path(__file__).with_suffix(".config.json")
TASK_SCHEDULER_PARAMS_PATH = Path(__file__).with_name("task_scheduler_params.txt")

def detect_python_executable():
    """Prefer PATH python; fallback to current interpreter."""
    return str(Path(shutil.which("python") or sys.executable).resolve())


def write_task_scheduler_params(source, destination):
    python_exe = str(Path(detect_python_executable()).resolve())
    script_path = Path(__file__).resolve()

    lines = [
        f"Program/script: {python_exe}",
        f"Add arguments: {script_path.name}",
        f"Start in: {str(script_path.parent)}",
        "",
        f"[Selected] Source directory/file path: {source}",
        f"[Selected] Reference destination directory: {destination}",
        f"To reset selected source directory/file path, and destination directory: python .\dir_file_backup.py --setup"
    ]
    TASK_SCHEDULER_PARAMS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_timestamped_run_dir(source, destination):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source_label = source.stem if source.is_file() else source.name
    if not source_label:
        source_label = "backup"

    run_dir = destination / f"{source_label}_{timestamp}"
    counter = 1
    while run_dir.exists():
        run_dir = destination / f"{source_label}_{timestamp}_{counter}"
        counter += 1

    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def load_config():
    if not CONFIG_PATH.exists():
        return {}

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}

    source = str(data.get("source", "")).strip()
    destination = str(data.get("destination", "")).strip()
    return {"source": source, "destination": destination}


def save_config(source, destination):
    CONFIG_PATH.write_text(
        json.dumps({"source": source, "destination": destination}, indent=2),
        encoding="utf-8",
    )
    write_task_scheduler_params(source, destination)


def copy_to_destination(source, destination):
    if not source.exists():
        raise FileNotFoundError(f"Source does not exist: {source}")

    if source.resolve() == destination.resolve():
        raise ValueError("Source and destination cannot be the same path.")

    if destination.exists() and not destination.is_dir():
        raise ValueError(f"Destination must be a directory path: {destination}")

    if destination.exists():
        print(f"Destination exists: {destination}")
    else:
        destination.mkdir(parents=True, exist_ok=True)
        print(f"Created destination: {destination}")

    run_dir = create_timestamped_run_dir(source, destination)
    print(f"Created timestamped backup folder: {run_dir}")

    if source.is_file():
        target = run_dir / source.name
        shutil.copy2(source, target)
        print(f"Copied file: {source} -> {target}")
        return

    if source.is_dir():
        target = run_dir / source.name
        shutil.copytree(source, target)
        print(f"Copied directory: {source} -> {target}")
        return

    raise ValueError(f"Source must be a file or directory: {source}")


def run_copy(source_text, destination_text):
    source = Path(source_text).expanduser().resolve()
    destination = Path(destination_text).expanduser().resolve()

    copy_to_destination(source, destination)
    print("Done.")


def run_setup_gui(existing):
    root = tkinter.Tk()
    root.title("Dir/File Backup Setup")
    root.geometry("760x220")
    root.resizable(False, False)

    source_var = tkinter.StringVar(value=existing.get("source", ""))
    destination_var = tkinter.StringVar(value=existing.get("destination", ""))

    def browse_source_file():
        selected = filedialog.askopenfilename(title="Select source file")
        if selected:
            source_var.set(selected)

    def browse_source_folder():
        selected = filedialog.askdirectory(title="Select source folder")
        if selected:
            source_var.set(selected)

    def browse_destination():
        selected = filedialog.askdirectory(title="Select destination folder")
        if selected:
            destination_var.set(selected)

    def validate_inputs():
        source_text = source_var.get().strip()
        destination_text = destination_var.get().strip()

        if not source_text:
            messagebox.showwarning("Source is required", "Please choose a source file or folder.")
            return None, None
        if not destination_text:
            messagebox.showwarning("Destination is required", "Please choose a destination folder.")
            return None, None
        return source_text, destination_text

    def save_only():
        source_text, destination_text = validate_inputs()
        if not source_text or not destination_text:
            return

        save_config(source=source_text, destination=destination_text)
        messagebox.showinfo(
            "Saved",
            "Config saved. task_scheduler_params.txt was updated.\n"
            "Future runs can execute without popup.",
        )
        root.destroy()

    def run_once():
        source_text, destination_text = validate_inputs()
        if not source_text or not destination_text:
            return

        try:
            run_copy(source_text, destination_text)
        except Exception as exc:
            messagebox.showerror("Copy failed", str(exc))
            return

        messagebox.showinfo("Done", "Copy completed.")

    root.columnconfigure(1, weight=1)

    tkinter.Label(root, text="Source:").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 0))
    tkinter.Entry(root, textvariable=source_var).grid(row=0, column=1, sticky="ew", padx=8, pady=(12, 0))
    tkinter.Button(root, text="File", width=8, command=browse_source_file).grid(row=0, column=2, padx=(0, 6), pady=(12, 0))
    tkinter.Button(root, text="Folder", width=8, command=browse_source_folder).grid(row=0, column=3, padx=(0, 12), pady=(12, 0))

    tkinter.Label(root, text="Destination:").grid(row=1, column=0, sticky="w", padx=12, pady=(10, 0))
    tkinter.Entry(root, textvariable=destination_var).grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
    tkinter.Button(root, text="Browse", command=browse_destination).grid(row=1, column=2, columnspan=2, sticky="w", pady=(10, 0))

    button_row = tkinter.Frame(root)
    button_row.grid(row=2, column=0, columnspan=4, sticky="w", padx=12, pady=16)
    tkinter.Button(button_row, text="Save Config", command=save_only).pack(side="left")
    tkinter.Button(button_row, text="Run once", command=run_once).pack(side="left", padx=(8, 0))

    root.mainloop()


def config_can_run_headless(config):
    source_text = config.get("source", "").strip()
    destination_text = config.get("destination", "").strip()
    if not source_text or not destination_text:
        return False

    return Path(source_text).expanduser().exists()


def main():
    parser = argparse.ArgumentParser(description="Copy source file/folder into a destination folder.")
    parser.add_argument("--setup", action="store_true", help="Open GUI and Setup")
    args = parser.parse_args()

    if args.setup:
        run_setup_gui(load_config())
        return

    config = load_config()
    if config_can_run_headless(config):
        run_copy(config["source"], config["destination"])
        return

    run_setup_gui(config)

if __name__ == "__main__":
    main()
