"""Use existing MSVC and AVR/UNO tools. Never install tools or upload a board."""
import os
from pathlib import Path
import subprocess

PROJECT = Path(__file__).resolve().parents[1]
BUILD = PROJECT / "build"


def checked(args, **kwargs):
    result = subprocess.run([str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
    output = result.stdout.decode("utf-8",errors="replace")
    if result.returncode:
        raise RuntimeError("Command failed: " + " ".join(map(str,args)) + "\n" + output)
    return output


def build_native():
    roots = [Path(os.environ.get("ProgramFiles(x86)",r"C:\Program Files (x86)"))/"Microsoft Visual Studio",
             Path(os.environ.get("ProgramFiles",r"C:\Program Files"))/"Microsoft Visual Studio"]
    compilers = sorted(p for root in roots if root.exists() for p in root.glob("*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe"))
    if not compilers: raise RuntimeError("No installed MSVC x64 compiler found")
    compiler = compilers[-1]
    vcvars = compiler.parents[6]/"Auxiliary/Build/vcvars64.bat"
    # Vendor script exports this compiler's process environment; no persistent setting changes.
    BUILD.mkdir(exist_ok=True)
    (BUILD/"msvc_environment.cmd").write_text(f'@call "{vcvars}" >nul\n@set\n',encoding="ascii")
    environment_text = checked(["cmd.exe","/d","/c","msvc_environment.cmd"],cwd=BUILD)
    environment = dict(os.environ)
    for line in environment_text.splitlines():
        if "=" in line and not line.startswith("="):
            key,value=line.split("=",1);environment[key]=value
    checked([compiler,"/nologo","/EHsc","/std:c++14","/utf-8","/W4","/I../tests/stubs",
             "/Fefirmware_harness.exe","/Fofirmware_harness.obj","../tests/firmware_harness.cpp"],cwd=BUILD,env=environment)
    return {"compiler":str(compiler),"executable":str(BUILD/"firmware_harness.exe")}


def build_avr():
    packages=Path(os.environ["LOCALAPPDATA"])/"Arduino15/packages/arduino"
    cores=sorted((packages/"hardware/avr").glob("*/cores/arduino"))
    tools=sorted((packages/"tools/avr-gcc").glob("*/bin/avr-g++.exe"))
    if not cores or not tools:raise RuntimeError("Installed AVR GCC / Arduino AVR core not found")
    core=cores[-1]; platform=core.parents[1]; bin_dir=tools[-1].parent
    wire=platform/"libraries/Wire/src"; variant=platform/"variants/standard"
    BUILD.mkdir(exist_ok=True)
    work=BUILD/"avr";work.mkdir(exist_ok=True)
    flags=["-mmcu=atmega328p","-DF_CPU=16000000L","-DARDUINO=10819","-DARDUINO_AVR_UNO","-DARDUINO_ARCH_AVR",
           "-Os","-ffunction-sections","-fdata-sections","-flto"]
    includes=["-I"+str(p) for p in (core,variant,wire)]
    core_objects=[]
    for source in sorted(core.iterdir()):
        if source.suffix not in (".cpp",".c",".S"):continue
        output="core_"+source.name.replace('.','_')+".o"
        compiler=bin_dir/("avr-g++.exe" if source.suffix==".cpp" else "avr-gcc.exe")
        language=["-std=gnu++11","-fno-exceptions","-fno-threadsafe-statics"] if source.suffix==".cpp" else ["-std=gnu11"] if source.suffix==".c" else ["-x","assembler-with-cpp"]
        checked([compiler,*flags,*language,*includes,"-c",source,"-o",output],cwd=work)
        core_objects.append(output)
    checked([bin_dir/"avr-gcc-ar.exe","rcs","core.a",*core_objects],cwd=work)
    for source,name in ((wire/"Wire.cpp","Wire.o"),(wire/"utility/twi.c","twi.o")):
        compiler=bin_dir/("avr-g++.exe" if source.suffix==".cpp" else "avr-gcc.exe")
        language=["-std=gnu++11","-fno-exceptions","-fno-threadsafe-statics"] if source.suffix==".cpp" else ["-std=gnu11"]
        checked([compiler,*flags,*language,*includes,"-c",source,"-o",name],cwd=work)
    sizes={}
    for sketch in ("arduino1_car","arduino2_slave_person"):
        source_path=PROJECT/'src/arduino'/sketch/(sketch+'.ino')
        # Minimal equivalent of Arduino's automatic function prototypes.
        prototypes='void receiveEvent(int bytes);\nvoid updatePedestrianLights(int phase);\n' if sketch=='arduino2_slave_person' else ''
        source=Path(sketch+'.ino.cpp')
        (work/source).write_text('#include <Arduino.h>\n'+prototypes+source_path.read_text(encoding='utf-8'),encoding='utf-8')
        checked([bin_dir/"avr-g++.exe",*flags,"-std=gnu++11","-fno-exceptions","-fno-threadsafe-statics",*includes,
                 "-x","c++","-c",source,"-o",sketch+".o"],cwd=work)
        checked([bin_dir/"avr-g++.exe","-mmcu=atmega328p","-Os","-flto","-Wl,--gc-sections","-o",sketch+".elf",
                 sketch+".o","Wire.o","twi.o","core.a","-lm"],cwd=work)
        checked([bin_dir/"avr-objcopy.exe","-O","ihex","-R",".eeprom",sketch+".elf",sketch+".hex"],cwd=work)
        sizes[sketch]=checked([bin_dir/"avr-size.exe","-C","--mcu=atmega328p",sketch+".elf"],cwd=work).strip()
    return {"compiler":str(tools[-1]),"core":str(platform),"board":"Arduino AVR UNO / ATmega328P / 16 MHz","sizes":sizes}


if __name__=="__main__":
    import json
    print(json.dumps({"native":build_native(),"avr":build_avr()},ensure_ascii=False,indent=2))
