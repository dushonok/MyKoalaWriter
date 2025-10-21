import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import threading
import queue
import webbrowser

from koala_main import koala_start, print_results_pretty
from settings import *
from checks import (
    run_checks,
    format_check_res,
)

class MyKoalaWriterApp:
    def __init__(self, master, test_mode=False):
        self.master = master
        self.test_mode = test_mode
        test_mode_txt = " [TEST MODE]" if test_mode else ""
        master.title(f"{APP_NAME} {APP_VERSION}{test_mode_txt}")
        master.geometry(APP_WINDOW_SIZE)
        master.minsize(700, 500)

        # --- Description ---
        descr_label = tk.Label(master, text=f"{APP_DESCR}{test_mode_txt}", font=("Arial", 11))
        descr_label.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 8))

        # --- Notion URLs ---
        self.line_count_var = tk.StringVar(value="0 URLs")
        url_label = tk.Label(master, text="Notion URLs (one per line):")
        url_label.grid(row=1, column=0, sticky="w", padx=(10,0))
        line_count_label = tk.Label(master, textvariable=self.line_count_var, fg="gray")
        line_count_label.grid(row=1, column=1, sticky="w", padx=(5,0))

        self.url_text = scrolledtext.ScrolledText(master, height=7, wrap=tk.WORD)
        self.master.after(100, lambda: self.url_text.focus_set())
        self.url_text.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=10, pady=(0,10))
        self.url_text.bind("<KeyRelease>", self.update_line_count)
        self.url_text.bind("<FocusOut>", self.update_line_count)
        self.update_line_count()

        # --- Separator ---
        sep1 = tk.Frame(master, height=2, bd=0, relief=tk.SUNKEN, bg="#cccccc")
        sep1.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 5))

        # --- Buttons ---
        self.button_frame = tk.Frame(master)
        self.button_frame.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=5)

        self.check_btn = tk.Button(
            self.button_frame,
            text="Run Checks",
            command=self.run_checks,
            bg="#FFB7CE",
            fg="black"
        )
        self.check_btn.grid(row=0, column=0, padx=5, pady=5)

        self.koala_btn = tk.Button(
            self.button_frame,
            text="Start Execution",
            command=self.run_koala_writer,
            bg="#27ae60",
            fg="white"
        )
        self.koala_btn.grid(row=0, column=1, padx=5, pady=5)

        # --- Separator ---
        sep2 = tk.Frame(master, height=2, bd=0, relief=tk.SUNKEN, bg="#cccccc")
        sep2.grid(row=5, column=0, columnspan=4, sticky="ew", padx=10, pady=(5, 5))

        # --- WP URLs Output ---
        tk.Label(master, text="WordPress URLs:").grid(row=6, column=0, sticky="w", padx=10)
        self.wp_urls_frame = tk.Frame(master)
        self.wp_urls_frame.grid(row=7, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))

        # --- Separator ---
        sep3 = tk.Frame(master, height=2, bd=0, relief=tk.SUNKEN, bg="#cccccc")
        sep3.grid(row=8, column=0, columnspan=4, sticky="ew", padx=10, pady=(5, 5))

        # --- Log area ---
        log_label = tk.Label(master, text="Log:")
        log_label.grid(row=9, column=0, sticky="w", padx=10)

        self.processed_var = tk.StringVar()
        self.processed_var.set("0/0 processed")
        processed_label = tk.Label(master, textvariable=self.processed_var, fg="gray")
        processed_label.grid(row=9, column=1, sticky="w", padx=(5,0))

        self.copy_btn = tk.Button(master, text="📋 Copy", command=self.copy_log_to_clipboard)
        self.copy_btn.grid(row=9, column=3, sticky="w", padx=(10,0))

        self.log_text = scrolledtext.ScrolledText(
            master, height=10, wrap=tk.WORD, state=tk.DISABLED, bg="#f8f9fa",
            fg="#888", relief=tk.FLAT, borderwidth=2, font=("Consolas", 10),
            cursor="arrow"
        )
        self.log_text.grid(row=10, column=0, columnspan=4, sticky="nsew", padx=10, pady=(0,10))
        self.log_text.bind("<FocusIn>", lambda e: self.master.focus())

        master.grid_rowconfigure(2, weight=2)
        master.grid_rowconfigure(10, weight=4)
        master.grid_columnconfigure(0, weight=1)
        master.grid_columnconfigure(1, weight=0)
        master.grid_columnconfigure(2, weight=0)
        master.grid_columnconfigure(3, weight=1)

        # Logging queue and poller
        self.log_queue = queue.Queue()
        self.poll_log_queue()

        # For thread-safe WP URL output
        self.wp_urls = []

        # Progress tracking
        self._progress_total = 0
        self._progress_count = 0

    def update_line_count(self, event=None):
        raw = self.url_text.get("1.0", tk.END)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        count = len(lines)
        self.line_count_var.set(f"{count} URL{'s' if count != 1 else ''}")

    def get_urls(self):
        raw = self.url_text.get("1.0", tk.END)
        urls = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        return urls

    def log(self, msg):
        # Update processed counter if message matches pattern
        if isinstance(msg, str) and msg.startswith("Processed "):
            try:
                parts = msg.split()
                idx = int(parts[1].split('/')[0])
                self._progress_count = idx
                self.processed_var.set(f"{self._progress_count}/{self._progress_total} processed")
                return
            except Exception:
                pass
        self.log_queue.put(msg)

    def poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                if isinstance(msg, list):
                    msg = '\n'.join(str(m) for m in msg)
                self.log_text.insert(tk.END, msg + '\n')
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.master.after(100, self.poll_log_queue)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)
        self._progress_count = 0
        self.processed_var.set(f"0/{self._progress_total} processed")

    def copy_log_to_clipboard(self):
        self.log_text.config(state=tk.NORMAL)
        log_content = self.log_text.get("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.master.clipboard_clear()
        self.master.clipboard_append(log_content)
        self.copy_btn.config(text="Copied!", fg="green")
        self.master.after(1500, lambda: self.copy_btn.config(text="📋 Copy", fg="black"))

    def run_checks(self):
        urls = self.get_urls()
        if not urls:
            messagebox.showwarning("Input Needed", "Please enter at least one Notion URL.")
            return
        self.clear_log()
        self._progress_total = len(urls)
        self._progress_count = 0
        self.processed_var.set(f"0/{self._progress_total} processed")
        self.disable_all_buttons()
        def do_work():
            try:
                # Placeholder for actual checks function
                import time
                problems = run_checks(urls, callback=self.log)
                self.log(format_check_res(problems))
            except Exception as e:
                self.log(f"Error during checks: {e}")
            finally:
                self.enable_all_buttons()
        threading.Thread(target=do_work, daemon=True).start()

    def run_koala_writer(self):
        urls = self.get_urls()
        if not urls:
            messagebox.showwarning("Input Needed", "Please enter at least one Notion URL.")
            return
        self.clear_log()
        self._progress_total = len(urls)
        self._progress_count = 0
        self.processed_var.set(f"0/{self._progress_total} processed")
        self.disable_all_buttons()
        def do_work():
            try:
                results = koala_start(urls, self.test_mode, callback=self.log)
                self.log("Execution completed.")
                self.display_wp_urls(results)
            except Exception as e:
                self.log(f"Error: {e}")
            finally:
                self.enable_all_buttons()
        threading.Thread(target=do_work, daemon=True).start()

    def display_wp_urls(self, results):
        # Clear previous WP URLs
        for widget in self.wp_urls_frame.winfo_children():
            widget.destroy()
        self.wp_urls = []
        row = 0
        for result in results:
            for title, url in result.items():
                lbl = tk.Label(self.wp_urls_frame, text=title, fg="#007bff", cursor="hand2", font=("Arial", 10, "underline"))
                lbl.grid(row=row, column=0, sticky="w", padx=(0,10), pady=2)
                lbl.bind("<Button-1>", lambda e, link=url: webbrowser.open(link))
                url_lbl = tk.Label(self.wp_urls_frame, text=url, fg="#007bff", cursor="hand2")
                url_lbl.grid(row=row, column=1, sticky="w", padx=(0,10), pady=2)
                url_lbl.bind("<Button-1>", lambda e, link=url: webbrowser.open(link))
                self.wp_urls.append((title, url))
                row += 1

    def disable_all_buttons(self):
        self.check_btn.config(state=tk.DISABLED)
        self.koala_btn.config(state=tk.DISABLED)

    def enable_all_buttons(self):
        self.check_btn.config(state=tk.NORMAL)
        self.koala_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = MyKoalaWriterApp(root)
    root.mainloop()