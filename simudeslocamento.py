import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from scipy.signal import butter, filtfilt, firwin, detrend

ARQUIVO_CSV      = 'dados_vibracao.csv'
ANTENA_RX        = 1
RANGE_BIN        = 12
FRAME_PERIODICITY_MS = 33.333  # Tempo entre frames (ms) — Ajuste conforme seu cfg (ex: 83 ms para ~12 Hz, 33 ms para ~30 Hz)
TAXA_FRAMES_HZ   = 30  # Fps do radar (Hz)
COMPRIMENTO_ONDA_MM = 5.0  # lambda = c / f = 5 mm

def butter_highpass(cutoff, fs, order=4):
    num_taps = 31  #quantidade dos coeficientes do filtro FIR (quanto maior, mais abrupto é o corte)
    nyq = fs / 2
    cut = cutoff / nyq
    cut = np.clip(cut, 1e-4, 0.999)

    # FIR passa-alta
    b = firwin(num_taps, cut, pass_zero=False)
    a = [1.0]

    return b, a

def butter_lowpass(cutoff, fs, order=4):
    num_taps = 31  #quantidade dos coeficientes do filtro FIR (quanto maior, mais abrupto é o corte)
    nyq = fs / 2
    cut = cutoff / nyq
    cut = np.clip(cut, 1e-4, 0.999)

    # FIR passa-baixa
    b = firwin(num_taps, cut)
    a = [1.0]

    return b, a

def aplicar_filtros(sinal, fs):
    # Passa-alta: remove drift e offset
    b_hp, a_hp = butter_highpass(cutoff=1, fs=fs, order=4)
    sinal_hp = filtfilt(b_hp, a_hp, sinal)

    # Passa-baixa: corta ruído
    corte_lp = 15  # Hz, ajuste conforme necessário
    b_lp, a_lp = butter_lowpass(cutoff=corte_lp, fs=fs, order=4)
    sinal_filtrado = filtfilt(b_lp, a_lp, sinal_hp)

    return sinal_filtrado

def filtro_i_e_q(I, Q, fs): 
    b_i, a_i = butter_lowpass(cutoff=5, fs=fs, order=4) 
    sinal_i_filtrado = filtfilt(b_i, a_i, I)
    sinal_q_filtrado = filtfilt(b_i, a_i, Q)
    return sinal_i_filtrado, sinal_q_filtrado

def analisar_vibracao():
    if not os.path.exists(ARQUIVO_CSV):
        print(f"Erro: '{ARQUIVO_CSV}' não encontrado.")
        return

    df = pd.read_csv(ARQUIVO_CSV)
    
    df_alvo = df.groupby('Frame').agg(
        I_Real = ('I_Real', 'mean'),
        Q_Imag = ('Q_Imag', 'mean')
    ).reset_index() 
    
    if df_alvo.empty:
        print(f"Nenhum dado para Antena {ANTENA_RX} / Bin {RANGE_BIN}.")
        return

    I_bruto  = df_alvo['I_Real'].to_numpy().astype(float)
    Q_bruto  = df_alvo['Q_Imag'].to_numpy().astype(float)

    lista_fase = np.arctan2(Q_bruto, I_bruto)
    fase_unwrapped = np.unwrap(lista_fase)

    lista_deslocamento_mm = (fase_unwrapped * COMPRIMENTO_ONDA_MM) / (4 * np.pi)
    deslocamento_filtrado_mm = aplicar_filtros(lista_deslocamento_mm, fs=TAXA_FRAMES_HZ)
    
    # fft
    #sinal_fft = np.array(lista_deslocamento_mm) - np.mean(lista_deslocamento_mm)
    sinal_fft = np.array(deslocamento_filtrado_mm) - np.mean(deslocamento_filtrado_mm)
    N         = len(sinal_fft)
    janela    = np.hanning(N)
    aux = np.fft.rfft(sinal_fft * janela)
    fft_vals  = np.abs(aux) * 2 / np.sum(janela)
    freqs  = np.fft.rfftfreq(N, d=1.0 / TAXA_FRAMES_HZ)
    #freqs = np.linspace(0, TAXA_FRAMES_HZ/2, len(aux)//2)
    idx_pico  = np.argmax(fft_vals)
    freq_pico = freqs[idx_pico]
    amp_pico  = fft_vals[idx_pico]

    #aux = np.fft.fft(lista_deslocamento_mm)
    #freqs = np.linspace(0, TAXA_FRAMES_HZ/2, len(aux)//2)
    
    fss= TAXA_FRAMES_HZ * 32   #numchirpsperframe * taxa_frames

    I_bruto  = df['I_Real'].to_numpy().astype(float)
    Q_bruto  = df['Q_Imag'].to_numpy().astype(float)

    #filtro i e q teste
    #i_filtrado, q_filtrado = filtro_i_e_q(I_bruto, Q_bruto, fs=TAXA_FRAMES_HZ)

    #lista_fase = np.arctan2(q_filtrado, i_filtrado) 
    lista_fase = np.arctan2(Q_bruto, I_bruto)
    fase_unwrapped = np.unwrap(lista_fase)
    
    lista_deslocamento_mm = (fase_unwrapped * COMPRIMENTO_ONDA_MM) / (4 * np.pi)
    #deslocamento_filtrado_mm = aplicar_filtros(lista_deslocamento_mm, fs=TAXA_FRAMES_HZ)

    # Plot
    fig, axs = plt.subplots(4, 1, figsize=(13, 14), sharex=False)
    fig.suptitle(
        f'Análise de Vibração',
        fontsize=8, fontweight='bold'
    )
    # Gráfico 0
    t = np.arange(len(lista_deslocamento_mm)) / fss
    axs[0].plot(t, lista_deslocamento_mm, label='Deslocamento (mm)')
    #axs[0].plot(t, deslocamento_filtrado_mm, label='Deslocamento high e low', color='red', linewidth=1.5)
    axs[0].set_title("Deslocamento (mm)")
    axs[0].set_ylabel("Amplitude (mm)")
    axs[0].set_xlabel("Tempo (s)")
    axs[0].legend()
    axs[0].grid(True)
    plt.subplots_adjust(hspace=0.6)

    # Gráfico 1
    axs[1].plot(t, lista_fase, label='Fase wrapped (rad)', color='orange', alpha=0.3)
    axs[1].plot(t, fase_unwrapped, label='Fase unwrapped (rads)', color='green')
    axs[1].legend()
    axs[1].set_title("Fase (rad)")
    axs[1].set_ylabel("Fase (rad)")
    axs[1].set_xlabel("Tempo (s)")
    axs[1].grid(True)
    
    # Gráfico 2: Espectro FFT
    axs[2].plot(freqs, fft_vals * 1000, color='navy', linewidth=1.2, label='Espectro')
    axs[2].axvline(freq_pico, color='orange', linestyle=':', linewidth=1.5, label=f'Pico em {freq_pico:.2f} Hz | {amp_pico*1000:.3f}')
    axs[2].set_title('Espectro de Frequência do Deslocamento')
    axs[2].set_xlabel('Frequência (Hz)')
    axs[2].set_ylabel('Amplitude')
    axs[2].set_xlim(0, TAXA_FRAMES_HZ / 2)
    axs[2].legend(fontsize=8)
    axs[2].grid(True)

    axs[3].plot(t, I_bruto, color='blue', linewidth=1.2, label='I bruto')
    axs[3].plot(t, Q_bruto, color='orange', linewidth=1.2, label='Q bruto')
    #axs[3].plot(t, i_filtrado, color='blue', alpha=0.3, linewidth=1.2, label='I filtrado')
    #axs[3].plot(t, q_filtrado, color='orange', alpha=0.3, linewidth=1.2, label='Q filtrado')
    axs[3].set_title('Sinais IQ brutos')
    axs[3].set_xlabel('Tempo (s)')
    axs[3].set_ylabel('Amplitude')
    axs[3].legend()
    axs[3].grid(True)
    plt.show()

analisar_vibracao()
