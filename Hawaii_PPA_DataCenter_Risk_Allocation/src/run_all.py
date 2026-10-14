"""프로젝트 루트 기준: python src/run_all.py"""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
for script in ['01_prepare_validate.py','02_tariff_stress_test.py','03_make_figures.py']:
    print('\n===',script,'===',flush=True)
    subprocess.run([sys.executable,str(ROOT/'src'/script)],check=True,cwd=ROOT)
print('\nSUCCESS: processed CSV, validation tables, illustrative stress test and figures generated')
