import schedule
import time
import subprocess
from datetime import datetime

def executar_backup():
    print(f"[{datetime.now()}] Executando backup agendado...")
    resultado = subprocess.run(
        ["python", "backup_sincronizacao.py", "--agendado"],
        capture_output=True,
        text=True
    )
    print(resultado.stdout)
    if resultado.stderr:
        print(f"ERROS: {resultado.stderr}")

# Agendar para todo domingo às 22h
schedule.every().sunday.at("22:00").do(executar_backup)

# Opcional: executar também nas quartas (backup extra)
schedule.every().wednesday.at("22:00").do(executar_backup)

print("="*50)
print("AGENDADOR DE BACKUP INICIADO")
print("="*50)
print("Backups programados:")
print("- Todo domingo às 22:00")
print("- Toda quarta-feira às 22:00")
print("- Pressione Ctrl+C para parar")
print("="*50)

while True:
    schedule.run_pending()
    time.sleep(60)  # Verifica a cada minuto