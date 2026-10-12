"""Reproducible local validation; compiles but never uploads firmware."""
import ast
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from datetime import datetime,timedelta,timezone
from build_firmware import build_native,build_avr,PROJECT,BUILD


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='Build and test the traffic signal code')
    parser.add_argument('--native-only',action='store_true',help='Run PC simulation tests without the AVR build')
    options=parser.parse_args()
    report={'timestamp':datetime.now(timezone(timedelta(hours=9))).isoformat(),
            'claim':'Code compilation and PC simulation; no physical board or webcam validation',
            'scope':'12-field presence messages, 5-second decisions, 2-second yellow and pedestrian phase coordination'}
    errors=[]
    python_files=list((PROJECT/'src/python').rglob('*.py'))+list((PROJECT/'tests').glob('*.py'))
    for path in python_files:
        try:compile(ast.parse(path.read_text(encoding='utf-8'),filename=str(path)),str(path),'exec')
        except SyntaxError as error:errors.append(str(error))
    report['python_syntax']={'files':len(python_files),'errors':errors}
    builders=[('native',build_native)]
    if not options.native_only:builders.append(('avr',build_avr))
    else:report['avr']={'requested':False}
    for key,builder in builders:
        try:report[key]={'passed':True,**builder()}
        except (RuntimeError,OSError) as error:report[key]={'passed':False,'error':str(error)};print(f'{key} build failed: {error}')
    os.environ['SIGNAL_NATIVE_AVAILABLE']='1' if report['native']['passed'] else '0'
    suite=unittest.defaultTestLoader.discover(str(PROJECT/'tests'),pattern='test_*.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report['tests']={'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
                     'details':[(str(case),detail) for case,detail in result.failures+result.errors],
                     'skips':[(str(case),detail) for case,detail in result.skipped]}
    source_files=list((PROJECT/'src/python').rglob('*'))+list((PROJECT/'src/config').rglob('*'))+list((PROJECT/'tests').rglob('*'))
    source_files += list((PROJECT/'src/arduino/arduino1_car').rglob('*'))+list((PROJECT/'src/arduino/arduino2_slave_person').rglob('*'))
    report['tested_source_sha256']={str(path.relative_to(PROJECT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files if path.is_file() and path.suffix in ('.py','.cpp','.h','.ino','.json','.properties') and '__pycache__' not in path.parts}
    BUILD.mkdir(exist_ok=True)
    target=BUILD/'validation-results.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='tested_source_sha256'},ensure_ascii=False,indent=2))
    avr_ok=options.native_only or report['avr'].get('passed',False)
    return 0 if not errors and result.wasSuccessful() and report['native']['passed'] and avr_ok else 1


if __name__=='__main__':sys.exit(main())
