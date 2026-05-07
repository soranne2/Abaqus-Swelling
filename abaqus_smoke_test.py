# -*- coding: mbcs -*-
"""
scripts/abaqus_smoke_test.py

Abaqus Python 2.7에서 실행
경로 인자 받지 않음.
config/project_config.json을 읽어서 ODB / INP / Output 경로 사용.
"""

from __future__ import print_function

import os
import sys
import json
import traceback


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(BASE_DIR, "config", "project_config.json")


def write_text(path, text):
    f = open(path, "w")
    f.write(text)
    f.close()


def read_config():
    if not os.path.exists(CONFIG_PATH):
        raise RuntimeError("project_config.json not found: %s" % CONFIG_PATH)

    f = open(CONFIG_PATH, "r")
    data = json.load(f)
    f.close()

    return data


def main():
    print("=" * 80)
    print("Abaqus Python Smoke Test")
    print("sys.executable:", sys.executable)
    print("sys.argv:", sys.argv)
    print("CONFIG_PATH:", CONFIG_PATH)
    print("=" * 80)

    try:
        config = read_config()

        odb_path = config.get("odb_path", "")
        inp_path = config.get("inp_path", "")
        output_path = config.get("output_path", "")

        if not output_path:
            raise RuntimeError("output_path is empty in project_config.json")

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        started_path = os.path.join(output_path, "smoke_started.txt")
        result_path = os.path.join(output_path, "smoke_result.txt")
        error_path = os.path.join(output_path, "smoke_error.txt")

        write_text(started_path, "smoke test started\n")

        print("[INPUT] ODB:", odb_path)
        print("[INPUT] INP:", inp_path)
        print("[INPUT] OUT:", output_path)

        if not os.path.exists(odb_path):
            print("[ERROR] ODB 없음:", odb_path)
            return 2

        if not os.path.exists(inp_path):
            print("[ERROR] INP 없음:", inp_path)
            return 3

        from odbAccess import openOdb

        print("[INFO] ODB open...")
        odb = openOdb(path=odb_path, readOnly=True)

        print("[OK] ODB opened")
        print("[ODB NAME]", odb.name)

        print("[STEPS]")
        for step_name in odb.steps.keys():
            step = odb.steps[step_name]
            print("  - %s / frames: %d" % (step_name, len(step.frames)))

        odb.close()
        print("[OK] ODB closed")

        write_text(result_path, "smoke test success\n")
        print("[SUCCESS] smoke test success")

        return 0

    except Exception:
        err = traceback.format_exc()
        print("[ERROR] exception")
        print(err)

        try:
            config = read_config()
            output_path = config.get("output_path", BASE_DIR)
            if not os.path.exists(output_path):
                os.makedirs(output_path)

            error_path = os.path.join(output_path, "smoke_error.txt")
            write_text(error_path, err)
        except Exception:
            pass

        return 10


if __name__ == "__main__":
    code = main()
    sys.exit(code)