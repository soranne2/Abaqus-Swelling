# -*- coding: mbcs -*-
from __future__ import print_function

import os
import sys
import traceback


def write_text(path, text):
    f = open(path, "w")
    f.write(text)
    f.close()


def main():
    print("=" * 80)
    print("Abaqus Python Smoke Test")
    print("sys.executable:", sys.executable)
    print("sys.argv:", sys.argv)
    print("=" * 80)

    if len(sys.argv) < 4:
        print("[ERROR] arguments 부족")
        print("Usage: abaqus python abaqus_smoke_test.py odb_path inp_path output_path")
        return 1

    odb_path = sys.argv[1]
    inp_path = sys.argv[2]
    output_path = sys.argv[3]

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

    try:
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

        write_text(error_path, err)
        return 10


if __name__ == "__main__":
    code = main()
    sys.exit(code)