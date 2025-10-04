import winsound
import os
import time

# Caminho completo para o arquivo WAV
wav_file_path = r"W:\opencv\du\msk.wav"

try:
    if os.path.exists(wav_file_path):
        print(f"Reproduzindo áudio: {wav_file_path}")
        # winsound.PlaySound pode ser usado com winsound.SND_FILENAME para reproduzir um arquivo
        # winsound.SND_ASYNC permite que o programa continue executando enquanto o som toca
        # winsound.SND_PURGE interrompe qualquer som atualmente tocando antes de iniciar um novo
        winsound.PlaySound(wav_file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        print("Reprodução iniciada. Aguardando para garantir que o som seja reproduzido...")
        # Adiciona um pequeno atraso para permitir que o som comece a tocar
        time.sleep(2) # Ajuste conforme a duração do seu áudio, se necessário
        print("Reprodução concluída (ou em andamento em segundo plano).")
    else:
        print(f"Erro: O arquivo WAV não foi encontrado no caminho especificado: {wav_file_path}")
        print("Por favor, verifique se o caminho está correto e se o arquivo existe.")
except Exception as e:
    print(f"Ocorreu um erro ao tentar reproduzir o arquivo WAV: {e}")
