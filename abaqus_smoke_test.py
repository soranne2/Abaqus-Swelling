# -*- coding: mbcs -*-
from __future__ import print_function

import os
import sys
import traceback


def safe_write(path, text):
    f = open(path, "w")
    f.write(text)
    f.close()


def main():
    print("=" * 80)
    print("Abaqus python smoke test started")
    print("sys.executable:", sys.executable)
    print("sys.argv:", sys.argv)
    print("=" * 80)

    args = sys.argv[1:]

    if len(args) < 3:
        print("[ERROR] Not enough arguments")
        print("[ERROR] args:", args)
        return 1

    odb_path = args[0]
    inp_path = args[1]
    output_path = args[2]

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    started_path = os.path.join(output_path, "abaqus_smoke_test_started.txt")
    safe_write(started_path, "Abaqus python smoke test entered\n")

    print("[OK] Script entered")
    print("[INPUT] ODB:", odb_path)
    print("[INPUT] INP:", inp_path)
    print("[INPUT] OUT:", output_path)

    if not os.path.exists(odb_path):
        print("[ERROR] ODB does not exist:", odb_path)
        return 2

    if not os.path.exists(inp_path):
        print("[ERROR] INP does not exist:", inp_path)
        return 3

    try:
        from odbAccess import openOdb

        print("[INFO] Opening ODB...")
        odb = openOdb(path=odb_path, readOnly=True)

        print("[OK] ODB opened successfully")
        print("[ODB] name:", odb.name)

        print("[INFO] Steps:")
        for step_name in odb.steps.keys():
            step = odb.steps[step_name]
            print("  - %s / frames: %d" % (step_name, len(step.frames)))

        odb.close()
        print("[OK] ODB closed")

        result_path = os.path.join(output_path, "abaqus_smoke_test_result.txt")
        safe_write(result_path, "Abaqus python smoke test completed successfully\n")

        print("[OK] Result file written:", result_path)
        print("Abaqus python smoke test completed")
        return 0

    except Exception:
        err = traceback.format_exc()
        print("[ERROR] Exception occurred")
        print(err)

        error_path = os.path.join(output_path, "abaqus_smoke_test_error.txt")
        safe_write(error_path, err)

        return 10


if __name__ == "__main__":
    code = main()
    sys.exit(code)