import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import get_data
from src.insights_engine import run_all
from src.report_generator import generate_html_report, save_report

def main():
    print("Cargando datos...")
    data = get_data()

    print("Detectando insights...")
    insights = run_all(data)

    print(f"Generando reporte ({len(insights)} insights)...")
    html = generate_html_report(insights, data)
    path = save_report(html)

    print(f"\nReporte listo: {path}")
    print(f"  Alta severidad : {sum(1 for i in insights if i.severity == 'high')}")
    print(f"  Media severidad: {sum(1 for i in insights if i.severity == 'medium')}")

if __name__ == "__main__":
    main()
