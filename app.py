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

    st.title("✈️ Operations Center")
    st.caption("King Air 250 • Fleet Monitoring System")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("✈️ Aircraft", "King Air 250")
    col2.metric("⏱️ Total Hours", f"{HORAS_ACTUALES_AVION:.1f}")
    col3.metric("🔴 Critical Items", criticos)
    col4.metric("🟢 OK Items", vigentes)

    st.divider()

    colA, colB = st.columns(2)

    with colA:
        st.subheader("📊 System Overview")

        st.markdown(
            """
            - Monitoring activo de aeronave
            - Control de vencimientos de tripulación
            - Tracking de mantenimiento en tiempo real
            """
        )

    with colB:
        st.subheader("⚠️ Alerts Summary")

        if criticos > 0:
            st.error(f"{criticos} critical items require immediate attention")
        else:
            st.success("No critical alerts")

# ======================================================
# 2. PILOTOS
# ======================================================

elif menu == "👨‍✈️ Pilotos":

    st.title("👨‍✈️ Crew Management")
    st.caption("Licenses & Training Status")

    lista_pilotos = df_pilotos["Piloto"].unique()

    for piloto in lista_pilotos:

        with st.expander(f"👨‍✈️ {piloto}"):

            datos = df_pilotos[df_pilotos["Piloto"] == piloto]

            for _, fila in datos.iterrows():

                documento = fila["Documento/Curso"]
                vence = fila["Vencimiento"]

                if pd.isnull(vence):
                    st.info(f"🟡 {documento} • No expiration date")
                    continue

                dias = (vence - hoy).days

                if dias <= 0:
                    st.error(f"🔴 {documento} • EXPIRED")

                elif dias <= 30:
                    st.warning(f"🟡 {documento} • {dias} days left")

                else:
                    st.success(f"🟢 {documento} • OK")


# ======================================================
# 3. AERONAVE
# ======================================================

elif menu == "✈️ Aeronave":

    st.title("✈️ Aircraft Maintenance Control Center")
    st.caption("King Air 250 • Airline Operations System")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Aircraft", "King Air 250")
    col2.metric("Total Hours", f"{HORAS_ACTUALES_AVION:.1f}")
    col3.metric("Critical", criticos)
    col4.metric("Warnings", advertencias)

    st.divider()

    # ======================================================
    # 1. BUILD MASTER DATASET
    # ======================================================

    items = []

    for _, fila in df_avion.iterrows():

        item = fila["Item"]
        tipo = fila["Tipo Vencimiento"]
        f_vence = fila["Fecha Vence"]
        h_vence = fila["Horas Vence"]

        sistema = fila["Sistema"] if "Sistema" in df_avion.columns else "General"

        estado = "ok"
        detalle = []

        # Fecha logic
        if tipo in ["Fecha", "Mixto"] and pd.notnull(f_vence):

            dias = (f_vence - hoy).days
            detalle.append(f"📅 {f_vence.strftime('%d/%m/%Y')}")

            if dias <= 0:
                estado = "critico"
            elif dias <= 30:
                estado = "warning"

        # Hours logic
        if tipo in ["Horas", "Mixto"] and pd.notnull(h_vence):

            restantes = h_vence - HORAS_ACTUALES_AVION
            detalle.append(f"⏱️ {int(restantes)}h remaining")

            if restantes <= 0:
                estado = "critico"
            elif restantes <= 25:
                estado = "warning"

        items.append({
            "item": item,
            "sistema": sistema,
            "estado": estado,
            "detalle": " • ".join(detalle)
        })

    # ======================================================
    # 2. SORT (AIRLINE PRIORITY LOGIC)
    # ======================================================

    priority = {"critico": 0, "warning": 1, "ok": 2}
    items = sorted(items, key=lambda x: priority[x["estado"]])

    # ======================================================
    # 3. FILTER BAR (AIRLINE STYLE CONTROL)
    # ======================================================

    filtro = st.radio(
        "View",
        ["All", "Critical", "Warning", "Nominal"],
        horizontal=True
    )

    def show(item):
        if filtro == "All":
            return True
        if filtro == "Critical":
            return item["estado"] == "critico"
        if filtro == "Warning":
            return item["estado"] == "warning"
        if filtro == "Nominal":
            return item["estado"] == "ok"
        return True

    # ======================================================
    # 4. GROUP BY SYSTEM (AIRLINE STYLE)
    # ======================================================

    sistemas = {}

    for i in items:
        if show(i):
            sistemas.setdefault(i["sistema"], []).append(i)

    # ======================================================
    # 5. RENDER (AIRLINE DISPATCH STYLE)
    # ======================================================

    def render_card(title, detail, state):

        colors = {
            "critico": "#ff4b4b",
            "warning": "#ffa500",
            "ok": "#2ecc71"
        }

        icons = {
            "critico": "🔴",
            "warning": "🟡",
            "ok": "🟢"
        }

        st.markdown(
            f"""
            <div style="
                background:#0e1117;
                border-left:5px solid {colors[state]};
                padding:12px;
                border-radius:10px;
                margin-bottom:8px;
            ">
                <div style="font-weight:600; font-size:14px;">
                    {icons[state]} {title}
                </div>
                <div style="font-size:12px; opacity:0.7;">
                    {detail}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ======================================================
    # 6. DISPLAY BY SYSTEM (REAL AIRLINE STRUCTURE)
    # ======================================================

    for sistema, lista in sistemas.items():

        st.subheader(f"🧩 {sistema}")

        for i in lista:
            render_card(i["item"], i["detalle"], i["estado"])
