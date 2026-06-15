import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.special import erfc

# ==========================================
# 0. CONFIGURAZIONE PAGINA E COSTANTI
# ==========================================
st.set_page_config(page_title="Nokia D-Band Full Duplex", layout="wide")

# Costanti di sistema (Nokia Baseline)
fc = 145e9      # 145 GHz
c = 3e8         # m/s
Gtx_dBi = 40    # dBi
Grx_dBi = 40    # dBi
T0 = 290        # K
k_B = 1.38e-23  # J/K

# ==========================================
# 1. SIDEBAR: CONTROLLI INTERATTIVI
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/02/Nokia_wordmark.svg/1200px-Nokia_wordmark.svg.png", width=150)
st.sidebar.header("⚙️ Parametri Operativi")

d_m = st.sidebar.slider("Distanza Link (m)", 100, 1000, 500, step=50)
iso_dB = st.sidebar.slider("Isolamento Antenna (dB)", 40, 80, 55, step=1)
Ptx_dBm = st.sidebar.slider("Potenza TX (dBm)", -10, 20, 0, step=1)
B_MHz = st.sidebar.slider("Banda del Canale (MHz)", 250, 2000, 1000, step=50)
NF_dB = st.sidebar.slider("Noise Figure RX (dB)", 4, 10, 6, step=1)

B_Hz = B_MHz * 1e6
Ptx_W = 10 ** ((Ptx_dBm - 30) / 10)

# Calcoli base Link Budget
FSPL_dB = 20 * np.log10(d_m) + 20 * np.log10(fc) + 20 * np.log10(4 * np.pi / c)
Prx_dBm = Ptx_dBm + Gtx_dBi + Grx_dBi - FSPL_dB
Prx_W = 10 ** ((Prx_dBm - 30) / 10)

Pn_W = k_B * T0 * B_Hz * (10 ** (NF_dB / 10))
Pi_W = 10 ** ((Ptx_dBm - iso_dB - 30) / 10)

# ==========================================
# HEADER NARRATIVO
# ==========================================
st.title("📡 Full Duplex in Banda D: Analisi di Fattibilità")
st.markdown("Questa dashboard esplora le prestazioni di un sistema Full-Duplex (FD) rispetto a un FDD tradizionale. Scorri verso il basso per l'analisi dal livello fisico fino alla fattibilità di sistema.")
st.markdown("---")

# ==========================================
# SEZIONE 1: L'impatto fisico (Costellazione)
# ==========================================
st.header("1. Il problema fisico: La Self-Interference")
st.markdown("Cosa succede al segnale quando trasmettiamo e riceviamo contemporaneamente sulla stessa frequenza? L'isolamento imperfetto crea una **nuvola di interferenza** attorno ai simboli ricevuti.")

# Generazione Costellazione (M=16)
M = 16
n_sym = 2000 # Limitato per fluidità Streamlit
data_tx = np.random.randint(0, 2, n_sym)
data_i = np.random.randint(0, 2, n_sym)

# Punti ideali QAM normalizzati (semplificati per il plot)
I_ideal = np.array([-3, -1, 1, 3]) / np.sqrt(10)
Q_ideal = np.array([-3, -1, 1, 3]) / np.sqrt(10)
ideal_points = [complex(i, q) for i in I_ideal for q in Q_ideal]

# Simulazione rumore e interferenza
noise_var = Pn_W / Prx_W
interf_var = Pi_W / Prx_W

# Generiamo punti perturbati attorno agli ideali
rx_points = []
for p in ideal_points:
    for _ in range(n_sym // 16):
        n = (np.random.randn() + 1j*np.random.randn()) * np.sqrt(noise_var/2)
        i = (np.random.randn() + 1j*np.random.randn()) * np.sqrt(interf_var/2)
        rx_points.append(p + n + i)

rx_points = np.array(rx_points)

fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=rx_points.real, y=rx_points.imag, mode='markers', marker=dict(size=3, color='rgba(100,149,237,0.6)'), name="Ricevuti (con Interferenza)"))
fig1.add_trace(go.Scatter(x=[p.real for p in ideal_points], y=[p.imag for p in ideal_points], mode='markers', marker=dict(symbol='cross', size=12, color='red'), name="Ideali"))
fig1.update_layout(title=f"Costellazione 16-QAM | Isolamento: {iso_dB} dB | Distanza: {d_m} m", xaxis_title="I", yaxis_title="Q", width=700, height=500, template="plotly_white")
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# ==========================================
# SEZIONE 2: Il degrado teorico (BER)
# ==========================================
st.header("2. Analisi delle Prestazioni: BER vs SNR Termico")
st.markdown("Quantifichiamo l'impatto dell'interferenza: all'aumentare dell'SNR termico, il sistema FD entra in un **regime di saturazione (Error Floor)** causato dall'auto-interferenza residua.")

EbN0_dB = np.linspace(0, 30, 100)
EbN0_lin = 10**(EbN0_dB/10)
k_bit = np.log2(M)

def calc_ber(snr_linear):
    return (4/k_bit) * (1 - 1/np.sqrt(M)) * 0.5 * erfc(np.sqrt(3*k_bit*snr_linear / (2*(M-1))))

# AWGN ideale
ber_ideal = calc_ber(EbN0_lin)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=EbN0_dB, y=ber_ideal, mode='lines', name="AWGN Ideale", line=dict(color='black', dash='dash')))

# BER per 3 livelli di isolamento
for iso_test in [iso_dB - 5, iso_dB, iso_dB + 5]:
    Pi_test = 10 ** ((Ptx_dBm - iso_test - 30) / 10)
    # Calcolo SINR effettivo considerando l'interferenza come rumore
    SINR_eff = 1 / ( (1/(k_bit * EbN0_lin)) + (Pi_test/Prx_W) )
    ber_sim = calc_ber(SINR_eff / k_bit)
    fig2.add_trace(go.Scatter(x=EbN0_dB, y=ber_sim, mode='lines', name=f"FD (Iso = {iso_test} dB)"))

fig2.update_layout(yaxis_type="log", yaxis_range=[-6, 0], xaxis_title="Eb/N0 Termico (dB)", yaxis_title="Bit Error Rate (BER)", template="plotly_white")
fig2.add_hline(y=1e-6, line_dash="dot", annotation_text="Target BER 10^-6")
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ==========================================
# SEZIONE 3: Il Momento "Wow" (Capacità vs Isolamento)
# ==========================================
st.header("3. Capacità vs Isolamento: Quando vince il Full-Duplex?")
st.markdown("Questo è il fattore critico. Modificando i parametri nella sidebar, osserva il **punto di incrocio (break-even)** tra la capacità del Full-Duplex e quella dell'FDD tradizionale alle diverse distanze.")

iso_vec = np.linspace(40, 80, 100)
dist_test = [250, 500, 1000]
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

fig3 = go.Figure()

for idx, d_test in enumerate(dist_test):
    FSPL_test = 20 * np.log10(d_test) + 20 * np.log10(fc) + 20 * np.log10(4 * np.pi / c)
    Prx_test = 10 ** ((Ptx_dBm + Gtx_dBi + Grx_dBi - FSPL_test - 30) / 10)
    
    # FDD Reference
    C_FDD = (B_Hz/2 * np.log2(1 + Prx_test/Pn_W)) / 1e9
    fig3.add_hline(y=C_FDD, line=dict(color=colors[idx], dash='dash'), annotation_text=f"FDD {d_test}m")
    
    # FD Capacity
    Pi_vec = 10 ** ((Ptx_dBm - iso_vec - 30) / 10)
    C_FD = (B_Hz * np.log2(1 + Prx_test/(Pn_W + Pi_vec))) / 1e9
    
    fig3.add_trace(go.Scatter(x=iso_vec, y=C_FD, mode='lines', name=f"FD a {d_test}m", line=dict(color=colors[idx], width=3)))

fig3.update_layout(xaxis_title="Isolamento Antenna (dB)", yaxis_title="Capacità Netta (Gbps)", hovermode="x unified", template="plotly_white")
fig3.add_vline(x=iso_dB, line=dict(color="gray", dash="dot"), annotation_text="Il tuo Isolamento")
st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ==========================================
# SEZIONE 4: Il Paradosso Ingegneristico (C vs Ptx)
# ==========================================
st.header("4. Il Collo di Bottiglia della Potenza (Capacità vs Ptx)")
st.markdown("Aumentare la potenza trasmessa non sempre aiuta. A causa della Self-Interference, se l'isolamento è troppo basso, **il sistema va in saturazione**: si amplifica sia il segnale utile che l'interferenza locale.")

Ptx_vec_dBm = np.linspace(-10, 20, 50)
Ptx_vec_W = 10 ** ((Ptx_vec_dBm - 30) / 10)

fig4 = go.Figure()

for iso_t in [45, 55, 65]:
    Prx_vec = 10 ** ((Ptx_vec_dBm + Gtx_dBi + Grx_dBi - FSPL_dB - 30) / 10)
    Pi_vec = 10 ** ((Ptx_vec_dBm - iso_t - 30) / 10)
    
    C_FD_Ptx = (B_Hz * np.log2(1 + Prx_vec/(Pn_W + Pi_vec))) / 1e9
    fig4.add_trace(go.Scatter(x=Ptx_vec_dBm, y=C_FD_Ptx, mode='lines', name=f"FD (Iso = {iso_t} dB)"))

# FDD Curve
Prx_vec_FDD = 10 ** ((Ptx_vec_dBm + Gtx_dBi + Grx_dBi - FSPL_dB - 30) / 10)
C_FDD_Ptx = (B_Hz/2 * np.log2(1 + Prx_vec_FDD/Pn_W)) / 1e9
fig4.add_trace(go.Scatter(x=Ptx_vec_dBm, y=C_FDD_Ptx, mode='lines', line=dict(color='black', dash='dash'), name="FDD Reference"))

fig4.update_layout(xaxis_title="Potenza Trasmissione TX (dBm)", yaxis_title="Capacità Netta (Gbps)", template="plotly_white")
fig4.add_vline(x=Ptx_dBm, line=dict(color="gray", dash="dot"))
st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ==========================================
# SEZIONE 5: La Visione Commerciale (Heatmap)
# ==========================================
st.header("5. Analisi di Fattibilità Commerciale")
st.markdown("Questa Heatmap risponde alla domanda finale di Nokia: **«Per quali combinazioni di distanza e isolamento ha senso investire nel Full-Duplex?»** Le aree verdi indicano dove il Full-Duplex offre prestazioni superiori all'FDD, le aree rosse indicano dove fallisce.")

dist_grid = np.linspace(100, 1000, 50)
iso_grid = np.linspace(40, 80, 50)
D_mesh, Iso_mesh = np.meshgrid(dist_grid, iso_grid)

# Calcoli matriciali per la heatmap
FSPL_mesh = 20 * np.log10(D_mesh) + 20 * np.log10(fc) + 20 * np.log10(4 * np.pi / c)
Prx_mesh = 10 ** ((Ptx_dBm + Gtx_dBi + Grx_dBi - FSPL_mesh - 30) / 10)
Pi_mesh = 10 ** ((Ptx_dBm - Iso_mesh - 30) / 10)

C_FD_mesh = (B_Hz * np.log2(1 + Prx_mesh/(Pn_W + Pi_mesh))) / 1e9
C_FDD_mesh = (B_Hz/2 * np.log2(1 + Prx_mesh/Pn_W)) / 1e9

# Calcolo del guadagno in Gbps (FD - FDD)
Gain_mesh = C_FD_mesh - C_FDD_mesh

fig5 = go.Figure(data=go.Heatmap(
    z=Gain_mesh,
    x=dist_grid,
    y=iso_grid,
    colorscale='RdYlGn',
    zmid=0, # Forza lo 0 (break-even) al centro della scala colori (colore giallo/neutro)
    colorbar=dict(title="Guadagno (Gbps)")
))

fig5.update_layout(
    xaxis_title="Distanza (m)",
    yaxis_title="Isolamento Antenna (dB)",
    template="plotly_white",
    height=600
)
# Aggiungo un marker per la configurazione attuale
fig5.add_trace(go.Scatter(x=[d_m], y=[iso_dB], mode='markers+text', text=["Punto Attuale"], marker=dict(size=10, color='blue', symbol='star'), textposition="top center", showlegend=False))

st.plotly_chart(fig5, use_container_width=True)