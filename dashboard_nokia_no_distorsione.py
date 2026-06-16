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
st.sidebar.header("Parametri Operativi")

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
st.title("D-Band Full-Duplex: Feasibility Analysis")
st.markdown("**Case 1: Ideal Hardware Baseline (No Distortion)**. Comparative analysis of FD vs traditional FDD capacity limits.")
col_fdd, col_fd = st.columns(2)
with col_fdd:
    st.latex(r"C_{FDD} = \frac{B}{2} \log_2\left(1 + \frac{P_{RX}}{P_n}\right)")
with col_fd:
    st.latex(r"C_{FD} = B \log_2\left(1 + \frac{P_{RX}}{P_n + P_{leakage}}\right)")

st.markdown("---")

# ==========================================
# SEZIONE 1: L'impatto fisico (Costellazione)
# ==========================================
st.header("1. Physical Layer Impact: Self-Interference")
st.markdown("Simultaneous trasmission and reception on the same frequency causes the local TX signal to leak into the RX chain. This imperfect isolation creates an **interference cloud** around the received QAM symbols, directly degrading the Signal-to-Interference-plus-Noise Ratio (SINR).")

# Generazione Costellazione (M=16)
M = 16
n_sym = 2000 # Limitato per fluidità Streamlit

# Punti ideali QAM normalizzati (semplificati per il plot)
I_ideal = np.array([-3, -1, 1, 3]) / np.sqrt(10)
Q_ideal = np.array([-3, -1, 1, 3]) / np.sqrt(10)
ideal_points = np.array([complex(i, q) for i in I_ideal for q in Q_ideal])

# Simulazione rumore e interferenza
noise_var = Pn_W / Prx_W
interf_var = Pi_W / Prx_W

#vettorializzazione : scegliamo simboli casuali dei punti ideali
sym_tx = np.random.choice(ideal_points, n_sym)

# Generazione vettoriale del rumore e dell'interferenza
n_vector = (np.random.randn(n_sym) + 1j*np.random.randn(n_sym)) * np.sqrt(noise_var/2)
i_vector = (np.random.randn(n_sym) + 1j*np.random.randn(n_sym)) * np.sqrt(interf_var/2)

# Segnale ricevuto
rx_points = sym_tx + n_vector + i_vector

fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=rx_points.real, y=rx_points.imag, mode='markers', 
                          marker=dict(size=3, color='rgba(0, 51, 102, 0.5)'), 
                          name="Received (SI + AWGN)"))
fig1.add_trace(go.Scatter(x=ideal_points.real, y=ideal_points.imag, mode='markers', 
                          marker=dict(symbol='cross', size=12, color='red'), 
                          name="Ideal Constellation"))
fig1.update_layout(
    title=f"16-QAM Constellation | Isolation: {iso_dB} dB | Distance: {d_m} m",
    xaxis_title="In-Phase (I)",
    yaxis_title="Quadrature (Q)",
    height=600, 
    template="plotly_white",
    yaxis=dict(scaleanchor="x", scaleratio=1, zeroline=True, zerolinewidth=1.5, zerolinecolor='black'), 
    xaxis=dict(zeroline=True, zerolinewidth=1.5, zerolinecolor='black')
)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# ==========================================
# SEZIONE 2: Il degrado teorico (BER)
# ==========================================
st.header("2. Performance Analysis: BER vs SNR")
st.markdown("Let's quantify the impact of self-interference on link reliability. As the thermal SNR increases, the Full-Duplex system enters an **Error Floor** regime. Unlike traditional networks, pumping more TX power cannot overcome this physical limit because it simultaneously amplifies the local leakage.")

EbN0_dB = np.linspace(0, 30, 100)
EbN0_lin = 10**(EbN0_dB/10)
k_bit = np.log2(M)

def calc_ber(ebn0_eff_lin):
    return (4/k_bit) * (1 - 1/np.sqrt(M)) * 0.5 * erfc(np.sqrt(3*k_bit*ebn0_eff_lin / (2*(M-1))))

# AWGN ideale
ber_ideal = calc_ber(EbN0_lin)


fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=EbN0_dB, y=ber_ideal, mode='lines', 
                          name="Ideal AWGN (Theoretical Bound)", 
                          line=dict(color='black', dash='dash', width=2)))

# Colori semantici: Rosso (peggiore), Blu (attuale), Verde (migliore)
line_colors = ['#d62728', '#1f77b4', '#2ca02c'] 
iso_tests = [iso_dB - 5, iso_dB, iso_dB + 5]

# BER per i 3 livelli di isolamento
for idx, iso_test in enumerate(iso_tests):
    Pi_test = 10 ** ((Ptx_dBm - iso_test - 30) / 10)
    
    # Calcolo SINR_effettivo e riconversione in Eb/N0 effettivo per la formula QAM
    SINR_eff = 1 / ( (1/(k_bit * EbN0_lin)) + (Pi_test/Prx_W) )
    ber_sim = calc_ber(SINR_eff / k_bit)
    
    fig2.add_trace(go.Scatter(x=EbN0_dB, y=ber_sim, mode='lines', 
                              name=f"FD (Iso = {iso_test} dB)",
                              line=dict(color=line_colors[idx], width=2.5)))
    
fig2.update_layout(
    yaxis_type="log", 
    yaxis_range=[-6, 0], 
    xaxis_title="Eb/N0 (dB)", 
    yaxis_title="Bit Error Rate (BER)", 
    template="plotly_white",
    height=500,
    hovermode="x unified",
    yaxis=dict(
        tickformat=".1e",  # Mostra come 1.0e-3
        dtick=1            # Un tick per ogni decade (10^-1, 10^-2, ecc.)
    )
)
fig2.add_hline(y=1e-6, line_dash="dot", line_color="gray", annotation_text="Pre-FEC Target BER (10⁻⁶)", annotation_position="bottom right")
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ==========================================
# SEZIONE 3: Il Momento "Wow" (Capacità vs Isolamento)
# ==========================================
st.header("3. Capacity vs. Isolation: The Break-Even Analysis")
st.markdown("This is the critical business factor. By adjusting the parameters in the sidebar, observe the **break-even point** between Full-Duplex and traditional FDD capacity at various link distances. If the isolation falls below this threshold, the self-interference penalty outweighs the spectral efficiency gain of FD.")

iso_vec = np.linspace(40, 80, 100)
dist_test = [250, 500, 1000]
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

fig3 = go.Figure()

for idx, d_test in enumerate(dist_test):
    # Calcolo Link Budget
    FSPL_test = 20 * np.log10(d_test) + 20 * np.log10(fc) + 20 * np.log10(4 * np.pi / c)
    Prx_test = 10 ** ((Ptx_dBm + Gtx_dBi + Grx_dBi - FSPL_test - 30) / 10)
    
    # FDD Reference (Uso go.Scatter invece di hline affinché appaia nel tooltip e nella legenda)
    C_FDD = (B_Hz/2 * np.log2(1 + Prx_test/Pn_W)) / 1e9
    fig3.add_trace(go.Scatter(x=[iso_vec[0], iso_vec[-1]], y=[C_FDD, C_FDD], 
                              mode='lines', 
                              name=f"FDD ({d_test}m)", 
                              line=dict(color=colors[idx], dash='dash', width=2)))
    
    # FD Capacity
    Pi_vec = 10 ** ((Ptx_dBm - iso_vec - 30) / 10)
    C_FD = (B_Hz * np.log2(1 + Prx_test/(Pn_W + Pi_vec))) / 1e9
    
    fig3.add_trace(go.Scatter(x=iso_vec, y=C_FD, 
                              mode='lines', 
                              name=f"FD ({d_test}m)", 
                              line=dict(color=colors[idx], width=3)))

fig3.update_layout(
    xaxis_title="Antenna Isolation (dB)", 
    yaxis_title="Net Capacity (Gbps)", 
    hovermode="x unified", 
    template="plotly_white",
    height=550
)
fig3.add_vline(x=iso_dB, line=dict(color="gray", dash="dot"), annotation_text="Current Isolation", annotation_position="top left")

st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")
# ==========================================
# SEZIONE 4: Il Paradosso Ingegneristico (C vs Ptx)
# ==========================================
st.header("4. The Power Bottleneck Paradox: Capacity vs. TX Power")
st.markdown("A common misconception is that pumping more transmit power solves range issues. However, in a Full-Duplex system, increasing TX power simultaneously amplifies the local leakage. As seen below, if isolation is insufficient, the system hits a **hard saturation limit** (horizontal asymptote) where adding power yields zero net capacity gain.")

Ptx_vec_dBm = np.linspace(-10, 20, 50)

fig4 = go.Figure()

# Dinamicità: testiamo 10 dB sotto, l'isolamento attuale, e 10 dB sopra
iso_tests = [iso_dB - 10, iso_dB, iso_dB + 10]
line_colors = ['#d62728', '#1f77b4', '#2ca02c'] # Rosso, Blu, Verde

for idx, iso_t in enumerate(iso_tests):
    Prx_vec = 10 ** ((Ptx_vec_dBm + Gtx_dBi + Grx_dBi - FSPL_dB - 30) / 10)
    Pi_vec = 10 ** ((Ptx_vec_dBm - iso_t - 30) / 10)
    
    C_FD_Ptx = (B_Hz * np.log2(1 + Prx_vec/(Pn_W + Pi_vec))) / 1e9
    fig4.add_trace(go.Scatter(x=Ptx_vec_dBm, y=C_FD_Ptx, mode='lines', 
                              name=f"FD (Iso = {iso_t} dB)", 
                              line=dict(color=line_colors[idx], width=2.5)))

# FDD Curve
Prx_vec_FDD = 10 ** ((Ptx_vec_dBm + Gtx_dBi + Grx_dBi - FSPL_dB - 30) / 10)
C_FDD_Ptx = (B_Hz/2 * np.log2(1 + Prx_vec_FDD/Pn_W)) / 1e9
fig4.add_trace(go.Scatter(x=Ptx_vec_dBm, y=C_FDD_Ptx, mode='lines', 
                          line=dict(color='black', dash='dash', width=2), 
                          name="FDD Reference"))

fig4.update_layout(
    xaxis_title="Transmit Power Ptx (dBm)", 
    yaxis_title="Net Capacity (Gbps)", 
    template="plotly_white",
    height=500,
    hovermode="x unified"
)
fig4.add_vline(x=Ptx_dBm, line=dict(color="gray", dash="dot"), annotation_text="Current Ptx", annotation_position="bottom right")

st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ==========================================
# SEZIONE 5: La Visione Commerciale (Heatmap)
# ==========================================
st.header("5. Commercial Feasibility Analysis: The Deployment Heatmap")
st.markdown("This Heatmap answers the ultimate deployment question for Nokia: **«Under which combinations of link distance and antenna isolation does Full-Duplex make commercial sense?»** Green areas denote where FD outperforms traditional FDD. Red areas highlight where the self-interference penalty makes FD unviable. The yellow boundary marks the zero-gain break-even line.")

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
    zmid=0, # Forza lo 0 (break-even) al centro della scala colori
    colorbar=dict(title="Net Gain (Gbps)"),
    hovertemplate="<b>Distance:</b> %{x:.0f} m<br><b>Isolation:</b> %{y:.1f} dB<br><b>Net Gain:</b> %{z:.2f} Gbps<extra></extra>"
))

fig5.update_layout(
    xaxis_title="Link Distance (m)",
    yaxis_title="Antenna Isolation (dB)",
    template="plotly_white",
    height=600
)

# Marker per la configurazione attuale
fig5.add_trace(go.Scatter(
    x=[d_m], 
    y=[iso_dB], 
    mode='markers+text', 
    text=["Operating Point"], 
    marker=dict(size=12, color='#003366', symbol='star'), # Blu Unipi
    textposition="top center", 
    showlegend=False,
    hoverinfo="skip" # Evita sovrapposizioni di tooltip con la heatmap
))

st.plotly_chart(fig5, use_container_width=True)