"""
Workspace Launcher
Remembers the files, folders, software and links you use for a piece of work,
and opens them all with one click.

Run the window:        python workspace_launcher.py
Open a workspace fast: python workspace_launcher.py --launch "AgileFlow"
List workspaces:       python workspace_launcher.py --list

Your data is saved in:  ~/.workspace_launcher.json  (plain JSON, safe to edit or back up)
Needs only Python 3.8+ (tkinter ships with it on Windows and macOS).
"""

import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, simpledialog, messagebox
except ImportError:  # CLI still works without tkinter
    tk = None

DATA_FILE = Path.home() / ".workspace_launcher.json"


# ---------- storage ----------
def load():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data:
            return data
    except Exception:
        pass
    return {"Default": []}


def save(data):
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------- opening things ----------
def open_item(item):
    """Open one saved item. Returns None on success, or an error message."""
    kind, target = item["type"], item["path"]
    try:
        if kind == "url":
            webbrowser.open(target)
        elif kind != "url" and not Path(target).exists():
            return "not found"
        elif sys.platform.startswith("win"):
            os.startfile(target)  # works for files, folders and .exe
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        elif kind == "app":
            subprocess.Popen([target])
        else:
            subprocess.Popen(["xdg-open", target])
        return None
    except Exception as e:
        return str(e)


# ---------- command line ----------
def run_cli(args):
    data = load()
    if "--list" in args:
        for name, items in data.items():
            print(f"{name}: {len(items)} items")
        return
    if "--launch" in args:
        i = args.index("--launch")
        name = args[i + 1] if i + 1 < len(args) else ""
        if name not in data:
            print(f'No workspace named "{name}". Available: {", ".join(data)}')
            return
        for item in data[name]:
            err = open_item(item)
            print(("FAILED " + err + ": " if err else "opened: ") + item["path"])


# ---------- window ----------
if tk:

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Workspace Launcher")
            self.geometry("820x480")
            self.minsize(640, 380)
            self.data = load()
            self.current = tk.StringVar(value=next(iter(self.data)))

            # top bar: choose / create / delete a workspace
            top = ttk.Frame(self, padding=10)
            top.pack(fill="x")
            ttk.Label(top, text="Workspace:").pack(side="left")
            self.combo = ttk.Combobox(top, textvariable=self.current,
                                      values=list(self.data), state="readonly", width=24)
            self.combo.pack(side="left", padx=8)
            self.combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
            ttk.Button(top, text="New", command=self.new_workspace).pack(side="left")
            ttk.Button(top, text="Delete", command=self.delete_workspace).pack(side="left", padx=4)
            ttk.Button(top, text="Launch all", command=self.launch_all).pack(side="right")

            # list of saved items
            mid = ttk.Frame(self, padding=(10, 0))
            mid.pack(fill="both", expand=True)
            self.tree = ttk.Treeview(mid, columns=("type", "path", "status"),
                                     show="headings", selectmode="extended")
            self.tree.heading("type", text="Type")
            self.tree.heading("path", text="Path or link")
            self.tree.heading("status", text="Status")
            self.tree.column("type", width=80, stretch=False)
            self.tree.column("path", width=560)
            self.tree.column("status", width=80, stretch=False)
            scroll = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=scroll.set)
            self.tree.pack(side="left", fill="both", expand=True)
            scroll.pack(side="right", fill="y")
            self.tree.bind("<Double-1>", lambda e: self.open_selected())
            self.tree.bind("<Delete>", lambda e: self.remove_selected())

            # buttons
            bar = ttk.Frame(self, padding=10)
            bar.pack(fill="x")
            for text, cmd in [("Add file", self.add_file), ("Add folder", self.add_folder),
                              ("Add software", self.add_app), ("Add link", self.add_link)]:
                ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=(0, 6))
            ttk.Button(bar, text="Open selected", command=self.open_selected).pack(side="right")
            ttk.Button(bar, text="Remove selected", command=self.remove_selected).pack(side="right", padx=6)

            self.status = ttk.Label(self, text="", padding=(10, 0, 10, 8))
            self.status.pack(fill="x")
            self.refresh()

        # --- helpers ---
        def items(self):
            return self.data[self.current.get()]

        def refresh(self):
            self.tree.delete(*self.tree.get_children())
            for i, item in enumerate(self.items()):
                missing = item["type"] != "url" and not Path(item["path"]).exists()
                self.tree.insert("", "end", iid=str(i),
                                 values=(item["type"], item["path"], "missing" if missing else "ok"))
            self.combo["values"] = list(self.data)

        def add(self, kind, path):
            if not path:
                return
            if any(x["path"] == path for x in self.items()):
                self.status.config(text="Already in this workspace.")
                return
            self.items().append({"type": kind, "path": path})
            save(self.data)
            self.refresh()
            self.status.config(text=f"Added: {path}")

        # --- add / remove ---
        def add_file(self):
            for p in filedialog.askopenfilenames(title="Choose files"):
                self.add("file", p)

        def add_folder(self):
            self.add("folder", filedialog.askdirectory(title="Choose a folder"))

        def add_app(self):
            self.add("app", filedialog.askopenfilename(
                title="Choose a program (.exe, .lnk, .app or a launcher)"))

        def add_link(self):
            url = simpledialog.askstring("Add link", "Paste a URL (for example http://localhost:3000):")
            if url:
                self.add("url", url.strip())

        def remove_selected(self):
            chosen = sorted((int(i) for i in self.tree.selection()), reverse=True)
            for i in chosen:
                del self.items()[i]
            if chosen:
                save(self.data)
                self.refresh()
                self.status.config(text=f"Removed {len(chosen)} item(s).")

        # --- open ---
        def open_selected(self):
            for i in self.tree.selection():
                err = open_item(self.items()[int(i)])
                if err:
                    self.status.config(text=f"Could not open: {err}")

        def launch_all(self):
            items = list(self.items())
            if not items:
                self.status.config(text="Nothing to open yet. Add something first.")
                return
            failed = []

            def step(n=0):
                if n >= len(items):
                    self.status.config(text="Opened everything." if not failed
                                       else f"{len(failed)} item(s) could not open: " + "; ".join(failed))
                    return
                err = open_item(items[n])
                if err:
                    failed.append(f'{items[n]["path"]} ({err})')
                self.after(500, step, n + 1)  # small gap so windows do not fight

            step()

        # --- workspaces ---
        def new_workspace(self):
            name = simpledialog.askstring("New workspace", "Name (for example Dissertation):")
            if name and name.strip() and name.strip() not in self.data:
                self.data[name.strip()] = []
                save(self.data)
                self.current.set(name.strip())
                self.refresh()

        def delete_workspace(self):
            name = self.current.get()
            if len(self.data) == 1:
                messagebox.showinfo("Workspace Launcher", "You need at least one workspace.")
                return
            if messagebox.askyesno("Delete workspace", f'Delete "{name}" and its list?'):
                del self.data[name]
                save(self.data)
                self.current.set(next(iter(self.data)))
                self.refresh()


def main():
    if len(sys.argv) > 1:
        run_cli(sys.argv[1:])
    elif tk:
        App().mainloop()
    else:
        print("tkinter is not installed. Use --list or --launch NAME.")


if __name__ == "__main__":
    main()
