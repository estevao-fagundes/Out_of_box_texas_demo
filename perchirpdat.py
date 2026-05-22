import struct
import csv
import os

try:
    import numpy as np
    import matplotlib.pyplot as plt
    has_plot = True
except ImportError:
    has_plot = False
    print("[AVISO] Matplotlib ou Numpy não instalados. O gráfico não será mostrado e a vibração não será calculada, mas o CSV bruto será gerado.")
    print("DICA: Para ver o gráfico, digite no terminal: pip install numpy matplotlib")

# A "Palavra Mágica" que a TI usa para indicar o início de um pacote (Header)
MAGIC_WORD = b'\x02\x01\x04\x03\x06\x05\x08\x07'

# Constante Física do Radar (IWR6843 -> 60GHz)
LAMBDA_MM = (3e8 / 60e9) * 1000  # Comprimento de onda = ~5 mm

def ler_arquivo_dat(caminho_arquivo):
    print(f"\nAbrindo arquivo: {caminho_arquivo}...")
    
    with open(caminho_arquivo, 'rb') as f:
        data = f.read()

    offset = 0
    dados_extraidos = []
    
    total_frames = 0
    contagem_tipos = {} 


    # Varre o arquivo inteiro procurando os pacotes
    while offset < len(data):
        idx = data.find(MAGIC_WORD, offset)
        if idx == -1:
            break 
            
        offset = idx
        
        try:
            header = struct.unpack_from('<8s8I', data, offset)
        except struct.error:
            break
            
        packet_len = header[2]
        num_tlvs = header[7]
        
        total_frames += 1
        offset += 40 # Pula o cabeçalho principal
        
        # Lê as Caixas (TLVs)
        for _ in range(num_tlvs):
            if offset >= len(data): break
            
            tlv_type, tlv_length = struct.unpack_from('<II', data, offset)
            offset += 8 # Pula a etiqueta
            
            # Conta o tipo
            if tlv_type in contagem_tipos:
                contagem_tipos[tlv_type] += 1
            else:
                contagem_tipos[tlv_type] = 1
            
            # É A NOSSA NOVA CAIXA DE ALTA VELOCIDADE? (Tipo 10)
            if tlv_type == 10:
                # 1. Lê o nosso novo Header de 12 bytes
                # Formato: uint32, uint16, uint16, uint16, uint16 (padding)
                frame, rx, rbin, numChirps, padding = struct.unpack_from('<IHHHH', data, offset)
                payload_offset = offset + 12
                # 2. Lê os Dados (O array de Chirps daquele Frame)
                # '<...h' lê 'h' (int16) seguidos. Multiplicamos por 2 porque tem I e Q
                chirps_fmt = f'<{numChirps * 2}h' 


                
                chirps_data = struct.unpack_from(chirps_fmt, data, payload_offset)
                
                # A TI envia Imag (Q) primeiro, Real (I) depois
                q_vals = chirps_data[0::2]
                i_vals = chirps_data[1::2]
                
                # 3. Guarda as amostras individualmente
                for c_idx in range(numChirps):
                    dados_extraidos.append([frame, c_idx, rx, rbin, i_vals[c_idx], q_vals[c_idx]])
                
            offset += tlv_length
            
        offset = idx + packet_len

    return dados_extraidos, total_frames, contagem_tipos


# ==========================================================
# --- EXECUÇÃO PRINCIPAL ---
# ==========================================================
print("="*60)
print(" LEITOR DE VIBRAÇÃO FAST-TIME DO RADAR TI (IWR6843ISK)")
print("="*60)

caminho_digitado = input("Digite (ou arraste aqui) o caminho do arquivo .dat:\n> ")
caminho_digitado = caminho_digitado.strip(' "\'')

if not os.path.exists(caminho_digitado):
    print(f"\n[ERRO] O arquivo não foi encontrado no caminho:\n{caminho_digitado}")
else:
    resultados, total_frames, contagem_tipos = ler_arquivo_dat(caminho_digitado)
    
    print("\n" + "="*50)
    print(" 📊 RELATÓRIO DO ARQUIVO .DAT")
    print("="*50)
    print(f" TOTAL DE FRAMES GRAVADOS : {total_frames}")
    print(f" TOTAL DE TLVs (Caixas)   : {sum(contagem_tipos.values())}")
    print("\n Detalhamento do que o Radar enviou:")
    
    for tipo in sorted(contagem_tipos.keys()):
        qtd = contagem_tipos[tipo]
        if tipo == 10:
            print(f"   -> Tipo 10 (Nossos dados)      : {qtd} frames contendo vibração!")
        else:
            print(f"   -> Tipo {tipo:<2} (Original da TI)   : {qtd} blocos")
            
    print(f"\n 🎯 AMOSTRAGEM TOTAL (FAST TIME) : {len(resultados)} pontos de vibração medidos!")
    print("="*50 + "\n")

    # --- SALVAR E PLOTAR OS NOSSOS DADOS ---
    if len(resultados) > 0:
        pasta_do_arquivo = r"C:\Users\estev\parsepy\dados csv\amostragem por chirp\bin 12\debug" # Altere para a pasta onde deseja salvar o CSV
        nome_csv = os.path.join(pasta_do_arquivo, 'dados_vibracao.csv')
        # Salva o CSV com a nova coluna 'Chirp'
        with open(nome_csv, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Frame', 'Chirp', 'Antena_RX', 'Range_Bin', 'I_Real', 'Q_Imag'])
            writer.writerows(resultados)
        print(f"Dados I/Q salvos com sucesso em: {nome_csv}")

        # if has_plot:
        #     # Extrai apenas as colunas de I e Q em formato numérico
        #     i_array = np.array([linha[4] for linha in resultados], dtype=float)
        #     q_array = np.array([linha[5] for linha in resultados], dtype=float)

        #     # MATEMÁTICA DA VIBRAÇÃO
        #     # 1. Remove DC Offset (Centraliza o círculo I/Q no zero)
        #     i_array -= np.mean(i_array)
        #     q_array -= np.mean(q_array)

        #     # 2. Calcula a Fase em radianos (arctan2)
        #     fase_rad = np.arctan2(q_array, i_array)

        #     # 3. Unwrap (Desfaz os saltos de fase, revelando o movimento contínuo)
        #     fase_unwrapped = np.unwrap(fase_rad)

        #     # 4. Converte Variação de Fase para Deslocamento (em Milímetros)
        #     # Deslocamento = (Lambda / 4Pi) * Delta Fase
        #     # O fator 4 entra porque a onda do radar VAI e VOLTA.
        #     deslocamento_mm = (LAMBDA_MM / (4 * np.pi)) * fase_unwrapped
            
        #     # Zera o gráfico no ponto inicial para ficar bonito
        #     deslocamento_mm -= deslocamento_mm[0] 

        #     # PLOTAGEM
        #     plt.figure(figsize=(12, 6))
            
        #     # Eixo X agora são as Amostras Contínuas (Fast Time)
        #     amostras = np.arange(len(deslocamento_mm))
            
        #     plt.plot(amostras, deslocamento_mm, color='red', linewidth=1)
        #     plt.title('Vibração Mecânica Medida (Sinal de Alta Resolução)')
        #     plt.xlabel('Amostras Contínuas (Chirps ao longo de vários frames)')
        #     plt.ylabel('Deslocamento Físico (Milímetros)')
        #     plt.grid(True)
            
        #     # Dica visual
        #     max_mm = np.max(deslocamento_mm)
        #     min_mm = np.min(deslocamento_mm)
        #     plt.axhline(0, color='black', linewidth=1)
        #     print(f"\n[INFO GRÁFICO] Amplitude máxima do movimento: {max_mm - min_mm:.3f} mm")
            
        #     plt.show()