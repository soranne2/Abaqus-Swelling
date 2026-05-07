# -*- coding: utf-8 -*-
"""
main_app.py
Swelling Post Tool - Simple GUI + JSON Config Runner

Python 3.11에서 실행
Abaqus 실행 방식:
    call "%ABQ%" python "script.py"

ODB / INP / Output 경로는 config/project_config.json에 저장
"""

import os
import json
import time
import queue
import threading
import subprocess
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox


APP_TITLE = "Swelling Post Tool"
APP_VERSION = "ver.0.8"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SCRIPT_DIR = os.path.join(BASE_DIR, "scripts")

PROJECT_CONFIG_PATH = os.path.join(CONFIG_DIR, "project_config.json")

ABQ19 = r"C:\opt\SIMULIA\Commands\abq2019.bat"
ABQ21 = r"C:\opt\SIMULIA\Commands\abq2021.bat"

EXTRACT_TASKS = [
    {
        "name": "Smoke Test",
        "script": os.path.join(SCRIPT_DIR, "abaqus_smoke_test.py"),
        "mode": "python"
    }
]


class SwellingPostTool(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("{} {}".format(APP_TITLE, APP_VERSION))
        self.geometry("1050x720")
        self.minsize(980, 660)
        self.configure(bg="#f5f7fb")

        self.font_regular = self._get_font([
            "나눔스퀘어OTF",
            "나눔스퀘어 OTF",
            "NanumSquareOTF",
            "맑은 고딕"
        ])

        self.font_bold = self._get_font([
            "나눔스퀘어OTF Bold",
            "나눔스퀘어 OTF Bold",
            "NanumSquareOTF Bold",
            self.font_regular
        ])

        self.odb_path_var = tk.StringVar()
        self.inp_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar(value=OUTPUT_DIR)
        self.abaqus_version_var = tk.StringVar(value="2019")

        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)

        self.is_running = False
        self.current_process = None
        self.worker_thread = None
        self.log_queue = queue.Queue()

        self._prepare_folders()
        self._setup_style()
        self._build_ui()
        self._load_project_config()

        self.after(100, self._process_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_font(self, candidates):
        families = set(tkfont.families())
        for font in candidates:
            if font in families:
                return font
        return candidates[-1]

    def _prepare_folders(self):
        for folder in [CONFIG_DIR, OUTPUT_DIR, SCRIPT_DIR]:
            if not os.path.exists(folder):
                os.makedirs(folder)

    def _setup_style(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.bg = "#f5f7fb"
        self.card = "#ffffff"
        self.text = "#191f28"
        self.subtext = "#6b7684"
        self.blue = "#3182f6"
        self.blue_dark = "#1b64da"
        self.soft_blue = "#edf6ff"
        self.log_bg = "#101828"
        self.log_fg = "#e5e7eb"

        style.configure("Root.TFrame", background=self.bg)
        style.configure("Card.TFrame", background=self.card)
        style.configure("TFrame", background=self.bg)

        style.configure("TLabel", background=self.bg, foreground=self.text, font=(self.font_regular, 10))
        style.configure("Card.TLabel", background=self.card, foreground=self.text, font=(self.font_regular, 10))
        style.configure("Title.TLabel", background=self.bg, foreground=self.text, font=(self.font_bold, 25))
        style.configure("Subtitle.TLabel", background=self.bg, foreground=self.subtext, font=(self.font_regular, 11))
        style.configure("Section.TLabel", background=self.card, foreground=self.text, font=(self.font_bold, 15))
        style.configure("Hint.TLabel", background=self.card, foreground=self.subtext, font=(self.font_regular, 10))

        style.configure("TButton", font=(self.font_bold, 10), padding=(14, 8), borderwidth=0)

        style.configure(
            "Primary.TButton",
            font=(self.font_bold, 11),
            padding=(18, 10),
            background=self.blue,
            foreground="#ffffff"
        )

        style.map(
            "Primary.TButton",
            background=[("active", self.blue_dark), ("disabled", "#b0c9f8")],
            foreground=[("disabled", "#ffffff")]
        )

        style.configure(
            "Ghost.TButton",
            font=(self.font_bold, 10),
            padding=(14, 8),
            background="#f2f4f6",
            foreground=self.text
        )

        style.map("Ghost.TButton", background=[("active", "#e5e8eb")])
        style.configure("TEntry", font=(self.font_regular, 10), padding=(10, 8))
        style.configure("TCombobox", font=(self.font_regular, 10), padding=(10, 8))
        style.configure("Horizontal.TProgressbar", thickness=12, troughcolor="#edf0f3", background=self.blue)

    def _build_ui(self):
        root = ttk.Frame(self, style="Root.TFrame")
        root.pack(fill="both", expand=True, padx=30, pady=24)

        self._build_header(root)
        self._build_main_card(root)
        self._build_log_card(root)
        self._build_status_bar(root)

    def _build_header(self, parent):
        header = ttk.Frame(parent, style="Root.TFrame")
        header.pack(fill="x", pady=(0, 20))

        left = ttk.Frame(header, style="Root.TFrame")
        left.pack(side="left", fill="x", expand=True)

        ttk.Label(left, text="Swelling Post Tool", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            left,
            text="ODB 결과 추출 · INP 기반 후처리 · Excel 미사용 Python 자동화",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(6, 0))

        badge = tk.Label(
            header,
            text=APP_VERSION,
            bg=self.soft_blue,
            fg=self.blue,
            font=(self.font_bold, 10),
            padx=14,
            pady=7
        )
        badge.pack(side="right", anchor="n")

    def _build_main_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame")
        card.pack(fill="both", expand=True)

        inner = ttk.Frame(card, style="Card.TFrame")
        inner.pack(fill="both", expand=True, padx=30, pady=28)

        ttk.Label(inner, text="프로젝트 실행 설정", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            inner,
            text="ODB, INP, Output 폴더를 선택하면 설정 JSON 저장 후 Abaqus Python 스크립트를 실행합니다.",
            style="Hint.TLabel"
        ).pack(anchor="w", pady=(6, 24))

        self._add_path_row(inner, "ODB File", self.odb_path_var, "선택", self._select_odb_file)
        self._add_path_row(inner, "INP File", self.inp_path_var, "선택", self._select_inp_file)
        self._add_path_row(inner, "Output Folder", self.output_path_var, "선택", self._select_output_folder)

        version_row = ttk.Frame(inner, style="Card.TFrame")
        version_row.pack(fill="x", pady=(12, 4))

        ttk.Label(version_row, text="Abaqus Version", style="Card.TLabel", width=15).pack(side="left")

        version_combo = ttk.Combobox(
            version_row,
            textvariable=self.abaqus_version_var,
            values=["2019", "2021"],
            state="readonly",
            width=12
        )
        version_combo.pack(side="left", padx=(10, 0))

        ttk.Label(
            version_row,
            text="ABQ 경로는 main_app.py 상단 ABQ19 / ABQ21에서 관리",
            style="Hint.TLabel"
        ).pack(side="left", padx=(14, 0))

        btn_frame = ttk.Frame(inner, style="Card.TFrame")
        btn_frame.pack(fill="x", pady=(28, 0))

        self.run_button = ttk.Button(
            btn_frame,
            text="Run",
            style="Primary.TButton",
            command=self._on_run_clicked
        )
        self.run_button.pack(side="left")

        self.cancel_button = ttk.Button(
            btn_frame,
            text="Cancel",
            style="Ghost.TButton",
            command=self._on_cancel_clicked,
            state="disabled"
        )
        self.cancel_button.pack(side="left", padx=(8, 0))

        ttk.Button(
            btn_frame,
            text="경로 확인",
            style="Ghost.TButton",
            command=self._check_paths
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            btn_frame,
            text="설정 저장",
            style="Ghost.TButton",
            command=self._save_project_config
        ).pack(side="right")

        progress_frame = ttk.Frame(inner, style="Card.TFrame")
        progress_frame.pack(fill="x", pady=(28, 0))

        ttk.Label(progress_frame, text="Progress", style="Card.TLabel").pack(anchor="w")

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", pady=(10, 0))

    def _add_path_row(self, parent, label_text, variable, button_text, command):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=9)

        ttk.Label(row, text=label_text, style="Card.TLabel", width=15).pack(side="left")

        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=(10, 10), ipady=3)

        ttk.Button(row, text=button_text, style="Ghost.TButton", command=command, width=9).pack(side="left")

    def _build_log_card(self, parent):
        log_card = ttk.Frame(parent, style="Card.TFrame")
        log_card.pack(fill="x", pady=(18, 10))

        header = ttk.Frame(log_card, style="Card.TFrame")
        header.pack(fill="x", padx=20, pady=(16, 8))

        ttk.Label(header, text="Log", style="Section.TLabel").pack(side="left")

        ttk.Button(
            header,
            text="Clear",
            style="Ghost.TButton",
            command=self._clear_log
        ).pack(side="right")

        self.log_text = tk.Text(
            log_card,
            height=10,
            wrap="word",
            font=("Consolas", 10),
            bg=self.log_bg,
            fg=self.log_fg,
            insertbackground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=12
        )

        scrollbar = ttk.Scrollbar(log_card, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=(0, 20))
        scrollbar.pack(side="right", fill="y", padx=(0, 20), pady=(0, 20))

    def _build_status_bar(self, parent):
        status = ttk.Frame(parent, style="Root.TFrame")
        status.pack(fill="x")

        tk.Label(
            status,
            textvariable=self.status_var,
            bg=self.bg,
            fg=self.subtext,
            font=(self.font_regular, 10)
        ).pack(side="left")

    def _select_odb_file(self):
        path = filedialog.askopenfilename(
            title="ODB 파일 선택",
            filetypes=[("Abaqus ODB", "*.odb"), ("All files", "*.*")]
        )
        if path:
            self.odb_path_var.set(path)
            self._log("ODB 선택: {}\n".format(path))

    def _select_inp_file(self):
        path = filedialog.askopenfilename(
            title="INP 파일 선택",
            filetypes=[("Abaqus INP", "*.inp"), ("All files", "*.*")]
        )
        if path:
            self.inp_path_var.set(path)
            self._log("INP 선택: {}\n".format(path))

    def _select_output_folder(self):
        path = filedialog.askdirectory(title="Output 폴더 선택")
        if path:
            self.output_path_var.set(path)
            self._log("Output 폴더 선택: {}\n".format(path))

    def _save_project_config(self):
        data = {
            "base_dir": BASE_DIR,
            "odb_path": self.odb_path_var.get(),
            "inp_path": self.inp_path_var.get(),
            "output_path": self.output_path_var.get(),
            "abaqus_version": self.abaqus_version_var.get()
        }

        try:
            if not os.path.exists(CONFIG_DIR):
                os.makedirs(CONFIG_DIR)

            with open(PROJECT_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self._log("설정 저장 완료: {}\n".format(PROJECT_CONFIG_PATH))
            self.status_var.set("Config saved")

        except Exception as e:
            messagebox.showerror("저장 오류", str(e))
            self._log("설정 저장 실패: {}\n".format(e))

    def _load_project_config(self):
        if not os.path.exists(PROJECT_CONFIG_PATH):
            return

        try:
            with open(PROJECT_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.odb_path_var.set(data.get("odb_path", ""))
            self.inp_path_var.set(data.get("inp_path", ""))
            self.output_path_var.set(data.get("output_path", OUTPUT_DIR))
            self.abaqus_version_var.set(data.get("abaqus_version", "2019"))

            self._log("설정 불러오기 완료: {}\n".format(PROJECT_CONFIG_PATH))
            self.status_var.set("Config loaded")

        except Exception as e:
            messagebox.showerror("불러오기 오류", str(e))
            self._log("설정 불러오기 실패: {}\n".format(e))

    def _get_abq_path(self):
        if self.abaqus_version_var.get() == "2021":
            return ABQ21
        return ABQ19

    def _check_paths(self):
        odb_path = self.odb_path_var.get()
        inp_path = self.inp_path_var.get()
        output_path = self.output_path_var.get()
        abq_path = self._get_abq_path()

        messages = []

        messages.append("[OK] ODB: {}".format(odb_path) if os.path.exists(odb_path) else "[NG] ODB 없음: {}".format(odb_path))
        messages.append("[OK] INP: {}".format(inp_path) if os.path.exists(inp_path) else "[NG] INP 없음: {}".format(inp_path))

        if output_path:
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            messages.append("[OK] Output: {}".format(output_path))
        else:
            messages.append("[NG] Output 없음")

        messages.append("[OK] Abaqus: {}".format(abq_path) if os.path.exists(abq_path) else "[NG] Abaqus 경로 없음: {}".format(abq_path))

        for task in EXTRACT_TASKS:
            script_path = task["script"]
            messages.append(
                "[OK] Script({}): {}".format(task["name"], script_path)
                if os.path.exists(script_path)
                else "[NG] Script({}) 없음: {}".format(task["name"], script_path)
            )

        msg = "\n".join(messages)
        self._log(msg + "\n")
        messagebox.showinfo("경로 확인", msg)

    def _validate_before_run(self):
        odb_path = self.odb_path_var.get()
        inp_path = self.inp_path_var.get()
        output_path = self.output_path_var.get()
        abq_path = self._get_abq_path()

        if not odb_path or not os.path.exists(odb_path):
            messagebox.showwarning("입력 확인", "ODB 파일을 선택해주세요.")
            return False

        if not inp_path or not os.path.exists(inp_path):
            messagebox.showwarning("입력 확인", "INP 파일을 선택해주세요.")
            return False

        if not output_path:
            messagebox.showwarning("입력 확인", "Output 폴더를 선택해주세요.")
            return False

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        if not os.path.exists(abq_path):
            messagebox.showwarning(
                "Abaqus 경로 확인",
                "Abaqus 실행 파일 경로가 없습니다.\n\nmain_app.py 상단 ABQ19 / ABQ21 값을 확인해주세요.\n\n현재 경로:\n{}".format(abq_path)
            )
            return False

        for task in EXTRACT_TASKS:
            if not os.path.exists(task["script"]):
                messagebox.showwarning(
                    "Script 경로 확인",
                    "{} 스크립트가 없습니다.\n\n{}".format(task["name"], task["script"])
                )
                return False

        return True

    def _on_run_clicked(self):
        if self.is_running:
            messagebox.showwarning("실행 중", "이미 실행 중입니다.")
            return

        if not self._validate_before_run():
            return

        self._save_project_config()

        self.is_running = True
        self.run_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress_var.set(0)
        self.status_var.set("Running...")

        self._log("=" * 80 + "\n")
        self._log("Swelling Post Tool 실행 시작\n")
        self._log("Abaqus Version: {}\n".format(self.abaqus_version_var.get()))
        self._log("=" * 80 + "\n")

        self.worker_thread = threading.Thread(target=self._worker_run_tasks)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def _build_task_command(self, task):
        abq_path = self._get_abq_path()
        script_path = task["script"]
        mode = task.get("mode", "python")

        if mode == "cae":
            cmd = 'set "ABQ={}" && call "%ABQ%" cae noGUI="{}"'.format(
                abq_path,
                script_path
            )
        else:
            cmd = 'set "ABQ={}" && call "%ABQ%" python "{}"'.format(
                abq_path,
                script_path
            )

        return cmd

    def _worker_run_tasks(self):
        try:
            total = len(EXTRACT_TASKS)

            for idx, task in enumerate(EXTRACT_TASKS, start=1):
                if not self.is_running:
                    self.log_queue.put(("log", "[CANCEL] 사용자 요청으로 중단\n"))
                    self.log_queue.put(("status", "Canceled"))
                    self.log_queue.put(("progress", 0.0))
                    return

                task_name = task["name"]
                cmd = self._build_task_command(task)

                self.log_queue.put(("log", "\n[{} / {}] {}\n".format(idx, total, task_name)))
                self.log_queue.put(("log", "[COMMAND]\n{}\n".format(cmd)))

                start_progress = float(idx - 1) / float(total) * 100.0
                self.log_queue.put(("progress", start_progress))

                return_code = self._run_command_realtime(cmd)

                if return_code != 0:
                    self.log_queue.put(("log", "[FAILED] {} 실패 / return code: {}\n".format(task_name, return_code)))
                    self.log_queue.put(("status", "Failed"))
                    self.log_queue.put(("progress", 0.0))
                    return

                end_progress = float(idx) / float(total) * 100.0
                self.log_queue.put(("progress", end_progress))
                self.log_queue.put(("log", "[OK] {} 완료\n".format(task_name)))

            self.log_queue.put(("log", "\n[SUCCESS] 모든 작업 완료\n"))
            self.log_queue.put(("status", "Completed"))
            self.log_queue.put(("progress", 100.0))

        except Exception as e:
            self.log_queue.put(("log", "[ERROR] 실행 중 예외 발생: {}\n".format(e)))
            self.log_queue.put(("status", "Error"))
            self.log_queue.put(("progress", 0.0))

        finally:
            self.log_queue.put(("done", None))

    def _run_command_realtime(self, cmd):
        output_path = self.output_path_var.get()
        run_log_path = os.path.join(output_path, "gui_run_log.txt")

        startupinfo = None
        creationflags = 0

        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW

        self.current_process = subprocess.Popen(
            ["cmd.exe", "/d", "/c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
            cwd=BASE_DIR,
            startupinfo=startupinfo,
            creationflags=creationflags
        )

        with open(run_log_path, "a", encoding="utf-8", errors="replace") as log_f:
            log_f.write("\n" + "=" * 80 + "\n")
            log_f.write(cmd + "\n")
            log_f.write("=" * 80 + "\n")

            while True:
                if not self.is_running:
                    self.log_queue.put(("log", "[CANCEL] 프로세스 종료 시도...\n"))
                    self._terminate_current_process()
                    return -999

                line = self.current_process.stdout.readline()

                if line:
                    log_f.write(line)
                    log_f.flush()
                    self.log_queue.put(("log", line))
                else:
                    if self.current_process.poll() is not None:
                        break
                    time.sleep(0.1)

        return_code = self.current_process.wait()
        self.current_process = None

        self.log_queue.put(("log", "[RETURN CODE] {}\n".format(return_code)))
        self.log_queue.put(("log", "[RUN LOG] {}\n".format(run_log_path)))

        return return_code

    def _on_cancel_clicked(self):
        if self.is_running:
            self.is_running = False
            self.status_var.set("Cancel requested")
            self._log("[CANCEL] 요청됨\n")

    def _terminate_current_process(self):
        try:
            if self.current_process is not None:
                self.current_process.terminate()
                time.sleep(1.0)

                if self.current_process.poll() is None:
                    self.current_process.kill()

                self.current_process = None

        except Exception as e:
            self.log_queue.put(("log", "[WARNING] 프로세스 종료 중 오류: {}\n".format(e)))

    def _on_worker_done(self):
        self.is_running = False
        self.run_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

    def _on_close(self):
        if self.is_running:
            answer = messagebox.askyesno("종료 확인", "작업이 실행 중입니다. 종료할까요?")
            if not answer:
                return

            self.is_running = False
            self._terminate_current_process()

        self.destroy()

    def _log(self, message):
        self.log_text.insert("end", message)
        self.log_text.see("end")

    def _clear_log(self):
        self.log_text.delete("1.0", "end")

    def _process_log_queue(self):
        try:
            while True:
                item_type, value = self.log_queue.get_nowait()

                if item_type == "log":
                    self._log(value)
                elif item_type == "progress":
                    self.progress_var.set(value)
                elif item_type == "status":
                    self.status_var.set(value)
                elif item_type == "done":
                    self._on_worker_done()

        except queue.Empty:
            pass

        self.after(100, self._process_log_queue)


def main():
    app = SwellingPostTool()
    app.mainloop()


if __name__ == "__main__":
    main()