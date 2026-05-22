import streamlit as st
import pandas as pd
import requests
import re

from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# ======================================================
# CONFIG
# ======================================================

st.set_page_config(
    page_title="King Air 250 Ops",
    page_icon="✈️",
    layout="centered"
)

# ======================================================
# AUTO REFRESH
# ======================================================

st_autorefresh(interval=300000, key="refresh")

# ======================================================
# CSS
# ======================================================

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ======================================================
# TITULO
# ======================================================

st.title("✈️ King Air 250 Ops")
st.caption("Control Operacional y Vencimientos")

menu = st.sidebar.radio(
    "📌 MENÚ",
    ["🏠 Dashboard", "✈️ Aeronave", "👨‍✈️ Pilotos", "🛩️ Mantenimiento"]
)

st.divider()

# ======================================================
# DRIVE
# ======================================================

ID_CARPETA_DRIVE = "1SOX5xoOsl6GPp9yhneHuA1oKqnWefV3S"

MESES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE"
}

hoy = date.today()

archivo_actual = f"VUELOS {MESES[hoy.month]} {hoy.year}"

if hoy.month == 1:
    mes_ant = 12
    anio_ant = hoy.year - 1
else:
    mes_ant = hoy.month - 1
    anio_ant = hoy.year

archivo_anterior = f"VUELOS {MESES[mes_ant]} {anio_ant}"

# ======================================================
# FUNCIONES
# ======================================================

def escanear_columna_k_excel(id_archivo):

    try:

        url = f"https://docs.google.com/spreadsheets/d/{id_archivo}/export?format=xlsx"

        df = pd.read_excel(url, sheet_name=0, header=None)

        if df.shape[1] > 10:

            columna_k = df.iloc[:, 10]

            columna_limpia = (
                columna_k.astype(str)
                .str.replace(",", ".")
                .str.strip()
            )

            valores = pd.to_numeric(
                columna_limpia,
                errors="coerce"
            ).dropna()

            if len(valores) > 0:
                return float(valores.max())

        return None

    except:
        return None


@st.cache_data(ttl=300)

def buscar_telemetria():

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        url = (
            f"https://drive.google.com/"
            f"embeddedfolderview?id={ID_CARPETA_DRIVE}"
        )

        respuesta = requests.get(
            url,
            headers=headers,
            timeout=5
        )

        if respuesta.status_code == 200:

            html = respuesta.text

            matches = re.findall(
                r'href="https://docs.google.com/spreadsheets/d/([^/]+)/[^"]+"[^>]*>([^<]+)',
                html
            )

            archivos = {
                nombre.upper().strip(): file_id
                for file_id, nombre in matches
            }

            for nombre, file_id in archivos.items():

                if archivo_actual.upper() in nombre:

                    horas = escanear_columna_k_excel(file_id)

                    if horas:
                        return horas, archivo_actual

            for nombre, file_id in archivos.items():

                if archivo_anterior.upper() in nombre:

                    horas = escanear_columna_k_excel(file_id)

                    if horas:
                        return horas, archivo_anterior

        return 2096.4, "Resguardo"

    except:

        return 2096.4, "Resguardo"

# ======================================================
# TELEMETRIA
# ======================================================

with st.spinner("Conectando telemetría..."):

    HORAS_ACTUALES_AVION, fuente = buscar_telemetria()

# ======================================================
# EXCEL
# ======================================================

try:

    df_pilotos = pd.read_excel(
        "vencimientos.xlsx",
        sheet_name="Pilotos"
    )

    df_avion = pd.read_excel(
        "vencimientos.xlsx",
        sheet_name="Avion"
    )

    df_pilotos["Vencimiento"] = pd.to_datetime(
        df_pilotos["Vencimiento"],
        errors="coerce"
    ).dt.date

    df_avion["Fecha Vence"] = pd.to_datetime(
        df_avion["Fecha Vence"],
        errors="coerce"
    ).dt.date

except FileNotFoundError:

    st.error("No se encontró vencimientos.xlsx")
    st.stop()

except Exception as e:

    st.error(f"Error cargando Excel: {e}")
    st.stop()

# ======================================================
# CALCULOS
# ======================================================

criticos = 0
advertencias = 0
vigentes = 0

for _, fila in df_avion.iterrows():

    tipo = fila["Tipo Vencimiento"]

    f_vence = fila["Fecha Vence"]

    h_vence = fila["Horas Vence"]

    alerta = False

    if tipo in ["Fecha", "Mixto"] and pd.notnull(f_vence):

        dias = (f_vence - hoy).days

        if dias <= 0:
            criticos += 1
            alerta = True

        elif dias <= 30:
            advertencias += 1
            alerta = True

    if tipo in ["Horas", "Mixto"] and pd.notnull(h_vence):

        horas_restantes = h_vence - HORAS_ACTUALES_AVION

        if horas_restantes <= 0:
            criticos += 1
            alerta = True

        elif horas_restantes <= 25:
            advertencias += 1
            alerta = True

    if not alerta:
        vigentes += 1

# ======================================================
# 1. DASHBOARD
# ======================================================

if menu == "🏠 Dashboard":

    st.title("✈️ Operational Dashboard")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("✈️ Aeronave", "King Air 250")
    c2.metric("⏱️ Horas Totales", f"{HORAS_ACTUALES_AVION:.1f}")
    c3.metric("🔴 Críticos", criticos)
    c4.metric("🟢 Vigentes", vigentes)

    st.divider()

    colA, colB = st.columns(2)

    with colA:
        st.subheader("📊 Estado General")
        st.info("Sistema operativo de vencimientos activo")

    with colB:
        st.subheader("⚠️ Alertas rápidas")

        if criticos > 0:
            st.error(f"{criticos} ítems críticos requieren atención")
        else:
            st.success("Sin ítems críticos")

# ======================================================
# 2. PILOTOS
# ======================================================

elif menu == "👨‍✈️ Pilotos":

    st.title("👨‍✈️ Crew Management")
    st.subheader("Vencimientos de tripulación")

    lista_pilotos = df_pilotos["Piloto"].unique()

    for piloto in lista_pilotos:

        with st.expander(f"👨‍✈️ {piloto}"):

            datos = df_pilotos[df_pilotos["Piloto"] == piloto]

            for _, fila in datos.iterrows():

                documento = fila["Documento/Curso"]
                vence = fila["Vencimiento"]

                if pd.isnull(vence):
                    st.info(f"{documento} → Sin fecha")
                    continue

                dias = (vence - hoy).days

                if dias <= 0:
                    st.error(f"{documento} → VENCIDO")

                elif dias <= 30:
                    st.warning(f"{documento} → {dias} días")

                else:
                    st.success(f"{documento} → OK")


# ======================================================
# 3. AERONAVE
# ======================================================

elif menu == "✈️ Aeronave":

    st.title("✈️ Aircraft Systems")
    st.caption("King Air 250 - Operational Cockpit View")

    col1, col2, col3 = st.columns(3)

    col1.metric("✈️ Aeronave", "King Air 250")
    col2.metric("⏱️ Horas Totales", f"{HORAS_ACTUALES_AVION:.1f}")
    col3.metric("🔴 Críticos", criticos)

    st.divider()

    st.subheader("🧭 System Status")

    criticos_list = []
    warning_list = []
    ok_list = []

    for _, fila in df_avion.iterrows():

        item = fila["Item"]
        tipo = fila["Tipo Vencimiento"]
        f_vence = fila["Fecha Vence"]
        h_vence = fila["Horas Vence"]

        estado = "ok"
        detalles = []

        # =========================
        # CONTROL POR FECHA
        # =========================
        if tipo in ["Fecha", "Mixto"] and pd.notnull(f_vence):

            dias = (f_vence - hoy).days
            detalles.append(f"📅 {f_vence.strftime('%d/%m/%Y')}")

            if dias <= 0:
                estado = "critico"
            elif dias <= 30 and estado != "critico":
                estado = "warning"

        # =========================
        # CONTROL POR HORAS
        # =========================
        if tipo in ["Horas", "Mixto"] and pd.notnull(h_vence):

            restantes = h_vence - HORAS_ACTUALES_AVION
            detalles.append(f"⏱️ {int(restantes)} hs restantes")

            if restantes <= 0:
                estado = "critico"
            elif restantes <= 25 and estado != "critico":
                estado = "warning"

        texto = f"{item} — " + " | ".join(detalles)

        # =========================
        # CLASIFICACIÓN FINAL
        # =========================
        if estado == "critico":
            criticos_list.append(texto)

        elif estado == "warning":
            warning_list.append(texto)

        else:
            ok_list.append(texto)

    # =========================
    # BLOQUE 1: CRÍTICOS
    # =========================
    if criticos_list:
        st.error("🔴 CRITICAL SYSTEMS")
        for item in criticos_list:
            st.write(item)

    # =========================
    # BLOQUE 2: WARNING
    # =========================
    if warning_list:
        st.warning("🟡 ATTENTION REQUIRED")
        for item in warning_list:
            st.write(item)

    # =========================
    # BLOQUE 3: OK
    # =========================
    if ok_list:
        st.success("🟢 NOMINAL STATUS")
        for item in ok_list:
            st.write(item)
