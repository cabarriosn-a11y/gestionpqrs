import streamlit as st
import pytesseract
from PIL import Image
import re
from docxtpl import DocxTemplate
import io
import datetime
import pandas as pd
import os

# ==========================================
# ⚙️ CONFIGURACIÓN V1.1.1 - SENA GUAJIRA
# ==========================================
VERSION = "1.1.1"
CENTRO = "Centro Industrial y de Energías Alternativas"
REGIONAL = "Regional Guajira"
ARCHIVO_DATOS = "registro_pqrs.csv"

# COMENTAR PARA STREAMLIT CLOUD
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@st.cache_data(show_spinner=False)
def extraer_datos(_img):
    texto = pytesseract.image_to_string(_img, lang='eng')
    d = {"nombre": "", "cedula": "", "ficha": "", "programa": "", "radicado": "", "nis": "", "correo": "", "telefono": ""}
    
    # OCR - Datos Básicos
    m_rad = re.search(r'(\d-\d{4}-\d+)', texto); d["radicado"] = m_rad.group(1) if m_rad else ""
    m_nis = re.search(r'(\d{4}-\d{2}-\d+)', texto); d["nis"] = m_nis.group(1) if m_nis else ""
    m_cor = re.search(r'([a-zA-Z0-9._%+-]+\s?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto)
    if m_cor: d["correo"] = m_cor.group(1).replace(" ", "").upper()
    m_ced = re.search(r'(?:Identificaci|Documento|No\.\s*de)[^\d]*(\d{7,10})', texto, re.IGNORECASE)
    if m_ced: d["cedula"] = m_ced.group(1)

    # Lógica de Nombre
    lineas = [l.strip() for l in texto.split('\n') if len(l.strip()) > 2]
    n_ov = ""; a_ov = ""
    for i, l in enumerate(lineas):
        if "Nombres" == l.strip() and i+1 < len(lineas): n_ov = lineas[i+1]
        if "Apellidos" == l.strip() and i+1 < len(lineas): a_ov = lineas[i+1]
        if "Nombre Persona" in l and i+1 < len(lineas): d["nombre"] = lineas[i+1]
    if n_ov and a_ov: d["nombre"] = f"{n_ov} {a_ov}"

    # Limpieza
    for b in ["SAN ANTONIO", "BARRIO", "MUNICIPIO", "MIRANDA", "CAUCA", "CORREO", "TELEFONO"]:
        d["nombre"] = re.sub(rf'\b{b}\b', '', d["nombre"], flags=re.IGNORECASE).strip()
    d["nombre"] = re.sub(r'[^a-zA-Z\s]', '', d["nombre"]).strip()
    
    m_fic = re.search(r'(?:Ficha|Curso)\s*\D*(\d{7,10})', texto, re.IGNORECASE)
    d["ficha"] = m_fic.group(1) if m_fic else ""
    
    return d

# --- INTERFAZ ---
st.set_page_config(page_title=f"SENA Guajira v{VERSION}", layout="wide")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=120)
    st.title("SENA - Riohacha")
    # TRES OPCIONES CLARAS
    menu = st.radio("MENÚ PRINCIPAL", [
        "1. Procesar Retiros (Base de Datos)", 
        "2. Redactor Libre IA (Otros Temas)", 
        "3. Acta Mensual de Retiros"
    ])
    st.markdown("---")
    st.caption(f"v{VERSION} | {REGIONAL}")

hoy = datetime.datetime.now()
ctx = {"DIA": hoy.day, "MES": ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"][hoy.month-1], "ANHO": hoy.year, "ACTA": hoy.month}

# ==========================================
# OPCIÓN 1: RETIROS (CON GUARDADO)
# ==========================================
if menu == "1. Procesar Retiros (Base de Datos)":
    st.header("📄 Gestión de Retiros Voluntarios")
    st.info("Nota: Los datos procesados aquí se guardarán para el Acta Mensual.")
    
    archivo = st.file_uploader("Sube el formulario de retiro", type=["tif", "png", "jpg"])
    if archivo:
        img = Image.open(archivo); d_ocr = extraer_datos(img)
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre", value=d_ocr["nombre"])
            ced = st.text_input("Cédula", value=d_ocr["cedula"])
            fic = st.text_input("Ficha", value=d_ocr["ficha"])
        with col2:
            rad = st.text_input("Radicado", value=d_ocr["radicado"])
            prog = st.text_input("Programa")
            novedad = "Retiro Voluntario"

        c1, c2 = st.columns(2)
        if c1.button("💾 GUARDAR EN LISTA"):
            pd.DataFrame([{"nombre": nom.upper(), "cedula": ced, "ficha": fic, "programa": prog.upper(), "radicado": rad, "novedad": novedad}]).to_csv(ARCHIVO_DATOS, mode='a', header=not os.path.exists(ARCHIVO_DATOS), index=False, encoding='utf-8-sig')
            st.success("Guardado en la base de datos de retiros.")
        
        if c2.button("🖨️ GENERAR CARTA"):
            doc = DocxTemplate("Plantilla_PQRS.docx")
            doc.render({**ctx, "NOMBRE": nom, "CEDULA": ced, "FICHA": fic, "PROGRAMA": prog, "RADICADO": rad, "CUERPO": "Se procede a realizar el trámite de retiro voluntario de acuerdo a su solicitud."})
            b = io.BytesIO(); doc.save(b); st.download_button("Descargar Carta", b.getvalue(), f"Retiro_{ced}.docx")

# ==========================================
# OPCIÓN 2: REDACTOR LIBRE (SIN GUARDADO)
# ==========================================
elif menu == "2. Redactor Libre IA (Otros Temas)":
    st.header("🤖 Redactor de Respuestas IA (Cualquier Tema)")
    st.warning("Esta opción NO guarda datos en el acta mensual. Es solo para redactar y descargar.")
    
    # También permite OCR para no escribir el nombre
    archivo_ia = st.file_uploader("Sube el documento (opcional para extraer nombre)", type=["tif", "png", "jpg"], key="ia_ocr")
    d_ia = extraer_datos(Image.open(archivo_ia)) if archivo_ia else {"nombre": "", "cedula": "", "ficha": "", "programa": "", "radicado": ""}

    col_ia1, col_ia2 = st.columns(2)
    with col_ia1:
        nom_ia = st.text_input("Nombre del Aprendiz", value=d_ia["nombre"])
        ced_ia = st.text_input("Identificación", value=d_ia["cedula"])
        rad_ia = st.text_input("Número de Radicado", value=d_ia["radicado"])
    with col_ia2:
        tema = st.selectbox("Tema de la respuesta", ["Certificación", "Traslado de Centro", "Inconformidad Instructor", "Otro Tema"])
        prog_ia = st.text_input("Programa", value=d_ia["programa"])

    st.markdown("### ✍️ Redacción de la Respuesta")
    if tema == "Certificación":
        problema = st.text_area("Detalle del problema", "El aprendiz no visualiza su certificado de etapa productiva.")
        solucion = st.text_input("Solución brindada", "Se enviará el reporte a coordinación académica para firma.")
        cuerpo_final = f"En atención a su requerimiento sobre la certificación del programa {prog_ia}, le informamos que {problema}. Por tal motivo, {solucion}. Estaremos informando el avance a su correo."
    else:
        cuerpo_final = st.text_area("Redacta aquí la respuesta oficial:", "Escribe aquí los párrafos de la respuesta...")

    st.info(f"**Cuerpo redactado:**\n\n{cuerpo_final}")

    if st.button("🖨️ GENERAR DOCUMENTO WORD (SIN GUARDAR)"):
        try:
            doc = DocxTemplate("Plantilla_PQRS.docx")
            doc.render({**ctx, "NOMBRE": nom_ia.upper(), "CEDULA": ced_ia, "RADICADO": rad_ia, "PROGRAMA": prog_ia.upper(), "CUERPO": cuerpo_final})
            b = io.BytesIO(); doc.save(b); st.download_button("📥 Descargar Documento IA", b.getvalue(), f"Respuesta_IA_{ced_ia}.docx")
        except Exception as e: st.error(f"Error: {e}")

# ==========================================
# OPCIÓN 3: ACTA MENSUAL
# ==========================================
else:
    st.header(f"📊 Acta Mensual de Retiros - {ctx['MES']}")
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS)
        st.dataframe(df, use_container_width=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📝 GENERAR ACTA MENSUAL"):
                doc = DocxTemplate("Plantilla_Acta_Mensual.docx")
                doc.render({**ctx, "lista_aprendices": df.to_dict(orient='records')})
                b = io.BytesIO(); doc.save(b); st.download_button("Descargar Acta", b.getvalue(), f"Acta_{ctx['MES']}.docx")
        with c2:
            if st.button("🚨 VACIAR LISTA (Resetear Mes)"):
                os.remove(ARCHIVO_DATOS); st.rerun()
    else:
        st.warning("No hay retiros registrados este mes.")
