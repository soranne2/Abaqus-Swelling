# -*- coding: utf-8 -*-
"""
main_app.py
Swelling Post Tool - Abaqus noGUI BAT launcher version
Python 3.11

ver.0.6
- Abaqus noGUI script를 Output 폴더로 복사
- cd /d "%OUT%" 후 noGUI=_abaqus_nogui_runner.py 방식으로 실행
- Abaqus cae noGUI="full path" 이슈 회피
"""

import os
import json
import time
import queue
import shutil
import threading
import subprocess
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox


APP_TITLE = "Swelling Post Tool"
APP_VERSION = "ver.0.6"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ODB_SCRIPT_DIR = os.path.join(BASE_DIR, "odb")

PROJECT_CONFIG_PATH = os.path.join(CONFIG_DIR, "project_config.json")

DEFAULT_ABQ19 = r"C:\opt\SIMULIA\Commands\abq2019.bat"
DEFAULT_ABQ21 = r"C:\opt\SIMULIA\Commands\abq2021.bat"
DEFAULT_NOGUI_SCRIPT = os.path.join(ODB_SCRIPT_DIR, "abaqus_smoke_test.py")


class SwellingPostTool(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("{} {}".format(APP_TITLE, APP_VERSION))
        self.geometry("1180x780")
        self.minsize(1080, 700)
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

        self.abq19_path_var = tk.StringVar(value=DEFAULT_ABQ19)
        self.abq21_path_var = tk.StringVar(value=DEFAULT_ABQ21)
        self.nogui_script_var = tk.StringVar(value=DEFAULT_NOGUI_SCRIPT)
        self.abaqus_version_var = tk.StringVar(value="2019")

        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)

        self.log_queue = queue.Queue()
        self.worker_thread = None
        self.current_process = None
        self.is_running = False

        self._prepare_folders()
        self._setup_style()
        self._build_ui()
        self._load_project_config()

        self.after(100, self._process_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================
    # Init
    # =========================================================
    def _get_font(self, candidates):
        families = set(tkfont.families())
        for font in candidates:
            if font in families:
                return font
        return candidates[-1]

    def _prepare_folders(self):
        for folder in [CONFIG_DIR, OUTPUT_DIR, ODB_SCRIPT_DIR]:
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
        style.configure("Title.TLabel", background=self.bg, foreground=self.text, font=(self.font_bold, 24))
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

        style.configure("TNotebook", background=self.bg, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            font=(self.font_bold, 11),
            padding=(22, 11),
            background=self.bg,
            foreground=self.subtext
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.card)],
            foreground=[("selected", self.blue)]
        )

        style.configure(
            "Horizontal.TProgressbar",
            thickness=12,
            troughcolor="#edf0f3",
            background=self.blue
        )

        style.configure(
            "Treeview",
            font=(self.font_regular, 10),
            rowheight=34,
            background=self.card,
            fieldbackground=self.card,
            foreground=self.text
        )
        style.configure(
            "Treeview.Heading",
            font=(self.font_bold, 10),
            background="#f8fafc",
            foreground=self.subtext
        )

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):
        root = ttk.Frame(self, style="Root.TFrame")
        root.pack(fill="both", expand=True, padx=28, pady=24)

        self._build_header(root)
        self._build_notebook(root)
        self._build_log_card(root)
        self._build_status_bar(root)

    def _build_header(self, parent):
        header = ttk.Frame(parent, style="Root.TFrame")
        header.pack(fill="x", pady=(0, 18))

        left = ttk.Frame(header, style="Root.TFrame")
        left.pack(side="left", fill="x", expand=True)

        ttk.Label(left, text="Swelling Post Tool", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            left,
            text="INP 기반 모델 파싱 · ODB 최소 추출 · Python 자동 후처리",
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

    def _build_notebook(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True)

        self.project_tab = ttk.Frame(self.notebook, style="Root.TFrame")
        self.set_tab = ttk.Frame(self.notebook, style="Root.TFrame")
        self.run_tab = ttk.Frame(self.notebook, style="Root.TFrame")
        self.plot_tab = ttk.Frame(self.notebook, style="Root.TFrame")

        self.notebook.add(self.project_tab, text="Project")
        self.notebook.add(self.set_tab, text="Set")
        self.notebook.add(self.run_tab, text="Run")
        self.notebook.add(self.plot_tab, text="Plot")

        self._build_project_tab()
        self._build_set_tab()
        self._build_run_tab()
        self._build_plot_tab()

    def _card(self, parent):
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(fill="both", expand=True, padx=2, pady=18)

        inner = ttk.Frame(frame, style="Card.TFrame")
        inner.pack(fill="both", expand=True, padx=28, pady=26)

        return inner

    def _build_project_tab(self):
        card = self._card(self.project_tab)

        ttk.Label(card, text="프로젝트 설정", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="ODB, INP, Output, Abaqus 실행 경로를 설정합니다.",
            style="Hint.TLabel"
        ).pack(anchor="w", pady=(6, 22))

        self._add_path_row(card, "ODB File", self.odb_path_var, "선택", self._select_odb_file)
        self._add_path_row(card, "INP File", self.inp_path_var, "선택", self._select_inp_file)
        self._add_path_row(card, "Output Folder", self.output_path_var, "선택", self._select_output_folder)
        self._add_path_row(card, "Abaqus 2019", self.abq19_path_var, "선택", self._select_abq19_file)
        self._add_path_row(card, "Abaqus 2021", self.abq21_path_var, "선택", self._select_abq21_file)
        self._add_path_row(card, "noGUI Script", self.nogui_script_var, "선택", self._select_nogui_script)

        version_row = ttk.Frame(card, style="Card.TFrame")
        version_row.pack(fill="x", pady=9)

        ttk.Label(version_row, text="Abaqus Version", style="Card.TLabel", width=15).pack(side="left")

        combo = ttk.Combobox(
            version_row,
            textvariable=self.abaqus_version_var,
            values=["2019", "2021"],
            state="readonly",
            width=15
        )
        combo.pack(side="left", padx=(10, 0))

        btn_frame = ttk.Frame(card, style="Card.TFrame")
        btn_frame.pack(fill="x", pady=(22, 0))

        ttk.Button(btn_frame, text="설정 저장", style="Ghost.TButton", command=self._save_project_config).pack(side="left")
        ttk.Button(btn_frame, text="설정 불러오기", style="Ghost.TButton", command=self._load_project_config).pack(side="left", padx=(8, 0))
        ttk.Button(btn_frame, text="경로 확인", style="Primary.TButton", command=self._check_project_paths).pack(side="right")

    def _add_path_row(self, parent, label_text, variable, button_text, command):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=7)

        ttk.Label(row, text=label_text, style="Card.TLabel", width=15).pack(side="left")

        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=(10, 10), ipady=3)

        ttk.Button(row, text=button_text, style="Ghost.TButton", command=command, width=9).pack(side="left")

    def _build_set_tab(self):
        card = self._card(self.set_tab)

        ttk.Label(card, text="Set 선택", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="다음 단계에서 INP 파싱 결과 기반 Set 선택 기능을 연결합니다.",
            style="Hint.TLabel"
        ).pack(anchor="w", pady=(6, 22))

        columns = ("type", "name", "count")
        self.set_tree = ttk.Treeview(card, columns=columns, show="headings", height=10)

        self.set_tree.heading("type", text="Type")
        self.set_tree.heading("name", text="Set Name")
        self.set_tree.heading("count", text="Count")

        self.set_tree.column("type", width=130, anchor="center")
        self.set_tree.column("name", width=620, anchor="w")
        self.set_tree.column("count", width=120, anchor="center")

        self.set_tree.pack(fill="both", expand=True)

        self.set_tree.insert("", "end", values=("ELSET", "CELL_BODY_ELSET", "-"))
        self.set_tree.insert("", "end", values=("NSET", "TEMP_NSET_CELL_BODY", "-"))
        self.set_tree.insert("", "end", values=("SURFACE", "CELL_CONTACT_SURF", "-"))

    def _build_run_tab(self):
        card = self._card(self.run_tab)

        ttk.Label(card, text="실행", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Run 버튼을 누르면 noGUI 스크립트를 Output 폴더로 복사한 뒤 Abaqus를 실행합니다.",
            style="Hint.TLabel"
        ).pack(anchor="w", pady=(6, 22))

        btn_frame = ttk.Frame(card, style="Card.TFrame")
        btn_frame.pack(fill="x")

        self.run_button = ttk.Button(
            btn_frame,
            text="Run Abaqus",
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
            text="Clear Log",
            style="Ghost.TButton",
            command=self._clear_log
        ).pack(side="left", padx=(8, 0))

        progress_box = ttk.Frame(card, style="Card.TFrame")
        progress_box.pack(fill="x", pady=(28, 0))

        ttk.Label(progress_box, text="Progress", style="Card.TLabel").pack(anchor="w")

        self.progress_bar = ttk.Progressbar(
            progress_box,
            variable=self.progress_var,
            maximum=100,
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", pady=(10, 0))

    def _build_plot_tab(self):
        card = self._card(self.plot_tab)

        ttk.Label(card, text="Plot Viewer", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="다음 단계에서 Plotly HTML 그래프와 리포트 뷰어를 연결합니다.",
            style="Hint.TLabel"
        ).pack(anchor="w", pady=(6, 22))

        ttk.Button(
            card,
            text="그래프 열기",
            style="Primary.TButton",
            command=self._open_plot_placeholder
        ).pack(anchor="w")

    def _build_log_card(self, parent):
        log_card = ttk.Frame(parent, style="Card.TFrame")
        log_card.pack(fill="x", pady=(18, 10))

        header = ttk.Frame(log_card, style="Card.TFrame")
        header.pack(fill="x", padx=20, pady=(16, 8))

        ttk.Label(header, text="Log", style="Section.TLabel").pack(side="left")

        self.log_text = tk.Text(
            log_card,
            height=8,
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

    # =========================================================
    # File selection
    # =========================================================
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

    def _select_abq19_file(self):
        path = filedialog.askopenfilename(
            title="abq2019.bat 선택",
            filetypes=[("Batch file", "*.bat"), ("All files", "*.*")]
        )
        if path:
            self.abq19_path_var.set(path)

    def _select_abq21_file(self):
        path = filedialog.askopenfilename(
            title="abq2021.bat 선택",
            filetypes=[("Batch file", "*.bat"), ("All files", "*.*")]
        )
        if path:
            self.abq21_path_var.set(path)

    def _select_nogui_script(self):
        path = filedialog.askopenfilename(
            title="Abaqus noGUI Script 선택",
            filetypes=[("Python file", "*.py"), ("All files", "*.*")]
        )
        if path:
            self.nogui_script_var.set(path)

    # =========================================================
    # Config
    # =========================================================
    def _save_project_config(self):
        data = {
            "odb_path": self.odb_path_var.get(),
            "inp_path": self.inp_path_var.get(),
            "output_path": self.output_path_var.get(),
            "abq19_path": self.abq19_path_var.get(),
            "abq21_path": self.abq21_path_var.get(),
            "nogui_script": self.nogui_script_var.get(),
            "abaqus_version": self.abaqus_version_var.get()
        }

        try:
            with open(PROJECT_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self._log("프로젝트 설정 저장 완료: {}\n".format(PROJECT_CONFIG_PATH))
            self.status_var.set("Project config saved")

        except Exception as e:
            messagebox.showerror("저장 오류", str(e))
            self._log("프로젝트 설정 저장 실패: {}\n".format(e))

    def _load_project_config(self):
        if not os.path.exists(PROJECT_CONFIG_PATH):
            return

        try:
            with open(PROJECT_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.odb_path_var.set(data.get("odb_path", ""))
            self.inp_path_var.set(data.get("inp_path", ""))
            self.output_path_var.set(data.get("output_path", OUTPUT_DIR))
            self.abq19_path_var.set(data.get("abq19_path", DEFAULT_ABQ19))
            self.abq21_path_var.set(data.get("abq21_path", DEFAULT_ABQ21))
            self.nogui_script_var.set(data.get("nogui_script", DEFAULT_NOGUI_SCRIPT))
            self.abaqus_version_var.set(data.get("abaqus_version", "2019"))

            self._log("프로젝트 설정 불러오기 완료: {}\n".format(PROJECT_CONFIG_PATH))
            self.status_var.set("Project config loaded")

        except Exception as e:
            messagebox.showerror("불러오기 오류", str(e))
            self._log("프로젝트 설정 불러오기 실패: {}\n".format(e))

    def _check_project_paths(self):
        checks = [
            ("ODB", self.odb_path_var.get()),
            ("INP", self.inp_path_var.get()),
            ("Abaqus 2019", self.abq19_path_var.get()),
            ("Abaqus 2021", self.abq21_path_var.get()),
            ("noGUI Script", self.nogui_script_var.get())
        ]

        messages = []

        for name, path in checks:
            if path and os.path.exists(path):
                messages.append("[OK] {}: {}".format(name, path))
            else:
                messages.append("[NG] {} 경로 확인 필요: {}".format(name, path))

        output_path = self.output_path_var.get()

        if output_path:
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            messages.append("[OK] Output: {}".format(output_path))
        else:
            messages.append("[NG] Output 폴더 확인 필요")

        msg = "\n".join(messages)
        self._log(msg + "\n")
        messagebox.showinfo("경로 확인", msg)

    # =========================================================
    # Abaqus run
    # =========================================================
    def _get_selected_abq_path(self):
        if self.abaqus_version_var.get() == "2021":
            return self.abq21_path_var.get()
        return self.abq19_path_var.get()

    def _validate_before_run(self):
        required = [
            ("ODB 파일", self.odb_path_var.get()),
            ("INP 파일", self.inp_path_var.get()),
            ("noGUI Script", self.nogui_script_var.get())
        ]

        for name, path in required:
            if not path or not os.path.exists(path):
                messagebox.showwarning("입력 확인", "{} 경로를 확인해주세요.".format(name))
                return False

        output_path = self.output_path_var.get()

        if not output_path:
            messagebox.showwarning("입력 확인", "Output 폴더를 선택해주세요.")
            return False

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        abq_path = self._get_selected_abq_path()

        if not abq_path or not os.path.exists(abq_path):
            messagebox.showwarning(
                "입력 확인",
                "선택한 Abaqus 실행 파일 경로를 확인해주세요.\n\n현재 경로:\n{}".format(abq_path)
            )
            return False

        return True

    def _create_abaqus_run_bat(self):
        abq_path = self._get_selected_abq_path()
        script_path = self.nogui_script_var.get()
        odb_path = self.odb_path_var.get()
        inp_path = self.inp_path_var.get()
        output_path = self.output_path_var.get()

        run_bat_path = os.path.join(output_path, "_run_abaqus_from_gui.bat")
        copied_script_path = os.path.join(output_path, "_abaqus_nogui_runner.py")

        shutil.copyfile(script_path, copied_script_path)

        bat_lines = [
            "@echo off",
            "echo ================================================================",
            "echo Swelling Post Tool - Abaqus noGUI launcher",
            "echo ================================================================",
            'set "ABQ={}"'.format(abq_path),
            'set "ODB={}"'.format(odb_path),
            'set "INP={}"'.format(inp_path),
            'set "OUT={}"'.format(output_path),
            "",
            'cd /d "%OUT%"',
            "",
            "echo CURRENT_DIR=%CD%",
            "echo ABQ=%ABQ%",
            "echo ODB=%ODB%",
            "echo INP=%INP%",
            "echo OUT=%OUT%",
            "",
            'if not exist "%ABQ%" (',
            '    echo [ERROR] Abaqus bat file does not exist: %ABQ%',
            "    exit /b 101",
            ")",
            "",
            'if not exist "_abaqus_nogui_runner.py" (',
            '    echo [ERROR] noGUI runner does not exist',
            "    exit /b 102",
            ")",
            "",
            'if not exist "%ODB%" (',
            '    echo [ERROR] ODB file does not exist: %ODB%',
            "    exit /b 103",
            ")",
            "",
            'if not exist "%INP%" (',
            '    echo [ERROR] INP file does not exist: %INP%',
            "    exit /b 104",
            ")",
            "",
            "echo.",
            "echo [INFO] Running Abaqus CAE noGUI...",
            'call "%ABQ%" cae noGUI=_abaqus_nogui_runner.py -- "%ODB%" "%INP%" "%OUT%"',
            "",
            "echo.",
            "echo [INFO] Abaqus finished with ERRORLEVEL=%ERRORLEVEL%",
            "exit /b %ERRORLEVEL%",
        ]

        with open(run_bat_path, "w", encoding="mbcs") as f:
            f.write("\r\n".join(bat_lines))

        return run_bat_path

    def _on_run_clicked(self):
        if self.is_running:
            messagebox.showwarning("실행 중", "이미 작업이 실행 중입니다.")
            return

        if not self._validate_before_run():
            return

        self._save_project_config()

        self.is_running = True
        self.run_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress_var.set(0)
        self.status_var.set("Running Abaqus...")

        self._log("=" * 80 + "\n")
        self._log("Abaqus noGUI 실행 시작\n")
        self._log("Abaqus Version: {}\n".format(self.abaqus_version_var.get()))
        self._log("=" * 80 + "\n")

        self.worker_thread = threading.Thread(target=self._worker_run_abaqus)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def _worker_run_abaqus(self):
        try:
            output_path = self.output_path_var.get()

            started_file = os.path.join(output_path, "abaqus_smoke_test_started.txt")
            result_file = os.path.join(output_path, "abaqus_smoke_test_result.txt")
            error_file = os.path.join(output_path, "abaqus_smoke_test_error.txt")
            run_log_file = os.path.join(output_path, "abaqus_gui_run_log.txt")
            copied_script_file = os.path.join(output_path, "_abaqus_nogui_runner.py")

            for old_file in [started_file, result_file, error_file, run_log_file]:
                if os.path.exists(old_file):
                    try:
                        os.remove(old_file)
                    except Exception:
                        pass

            run_bat_path = self._create_abaqus_run_bat()

            self.log_queue.put(("log", "[BAT FILE]\n{}\n".format(run_bat_path)))
            self.log_queue.put(("log", "[COPIED noGUI]\n{}\n".format(copied_script_file)))
            self.log_queue.put(("log", "[INFO] Abaqus 실행 시작...\n"))
            self.log_queue.put(("progress", 10.0))

            startupinfo = None
            creationflags = 0

            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW

            self.current_process = subprocess.Popen(
                ["cmd.exe", "/d", "/c", run_bat_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                cwd=output_path,
                startupinfo=startupinfo,
                creationflags=creationflags
            )

            self.log_queue.put(("progress", 30.0))

            with open(run_log_file, "w", encoding="utf-8", errors="replace") as log_f:
                while True:
                    if not self.is_running:
                        self.log_queue.put(("log", "[CANCEL] Abaqus 프로세스 종료 시도...\n"))
                        self._terminate_current_process()
                        self.log_queue.put(("status", "Canceled"))
                        self.log_queue.put(("progress", 0.0))
                        return

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

            self.log_queue.put(("log", "\n[INFO] Abaqus return code: {}\n".format(return_code)))
            self.log_queue.put(("log", "[INFO] GUI run log: {}\n".format(run_log_file)))

            self._log_file_check_to_queue(
                started_file,
                result_file,
                error_file,
                run_log_file,
                run_bat_path,
                copied_script_file
            )

            if return_code == 0 and os.path.exists(result_file):
                self.log_queue.put(("log", "[SUCCESS] Abaqus smoke test 완료\n"))
                self.log_queue.put(("status", "Completed"))
                self.log_queue.put(("progress", 100.0))

            elif return_code == 0 and not os.path.exists(result_file):
                self.log_queue.put(("log", "[WARNING] Abaqus return code는 0이지만 result 파일이 없습니다.\n"))
                self.log_queue.put(("log", "[CHECK] noGUI script가 실제로 실행됐는지 확인 필요\n"))
                self.log_queue.put(("status", "Completed but no result"))
                self.log_queue.put(("progress", 70.0))

            else:
                self.log_queue.put(("log", "[FAILED] Abaqus 실행 실패\n"))
                self.log_queue.put(("status", "Failed"))
                self.log_queue.put(("progress", 0.0))

        except Exception as e:
            self.log_queue.put(("log", "[ERROR] Abaqus 실행 중 오류 발생: {}\n".format(e)))
            self.log_queue.put(("status", "Error"))
            self.log_queue.put(("progress", 0.0))

        finally:
            self.log_queue.put(("done", None))

    def _log_file_check_to_queue(self, started_file, result_file, error_file, run_log_file, run_bat_path, copied_script_file):
        self.log_queue.put(("log", "\n[OUTPUT CHECK]\n"))

        file_list = [
            ("launcher_bat", run_bat_path),
            ("copied_nogui", copied_script_file),
            ("started", started_file),
            ("result", result_file),
            ("error", error_file),
            ("gui_run_log", run_log_file)
        ]

        for label, path in file_list:
            if os.path.exists(path):
                self.log_queue.put(("log", "  [OK] {} file: {}\n".format(label, path)))
            else:
                self.log_queue.put(("log", "  [NO] {} file: {}\n".format(label, path)))

    def _terminate_current_process(self):
        try:
            if self.current_process is not None:
                self.current_process.terminate()
                time.sleep(1.0)

                if self.current_process.poll() is None:
                    self.current_process.kill()

                self.current_process = None

        except Exception as e:
            self.log_queue.put(("log", "프로세스 종료 중 오류: {}\n".format(e)))

    def _on_cancel_clicked(self):
        if self.is_running:
            self.is_running = False
            self._log("Cancel 요청됨. 현재 Abaqus 작업 종료 대기 중...\n")
            self.status_var.set("Cancel requested")

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

    # =========================================================
    # Log
    # =========================================================
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

    # =========================================================
    # Plot placeholder
    # =========================================================
    def _open_plot_placeholder(self):
        messagebox.showinfo(
            "Plot Viewer",
            "다음 단계에서 Plotly HTML 그래프 열기 기능을 연결합니다."
        )
        self._log("Plot Viewer 버튼 클릭됨\n")


def main():
    app = SwellingPostTool()
    app.mainloop()


if __name__ == "__main__":
    main()