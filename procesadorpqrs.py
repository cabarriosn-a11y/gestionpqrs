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
# ⚙️ CONFIGURACIÓN V1.0.4 - SENA
# ==========================================
VERSION = "1.0.4"
CENTRO = "Centro Industrial y de Energías Alternativas"
REGIONAL = "Regional Guajira"
ARCHIVO_DATOS = "registro_pqrs.csv"

# Línea para Tesseract (Comentar si vas a publicar en Streamlit Cloud)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def guardar_datos(datos):
    df_nuevo = pd.DataFrame([datos])
    if not os.path.isfile(ARCHIVO_DATOS):
        df_nuevo.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
    else:
        # Si el archivo existe pero tiene columnas viejas, lo sobreescribimos
        try:
            df_nuevo.to_csv(ARCHIVO_DATOS, mode='a', header=False, index=False, encoding='utf-8-sig')
        except:
            df_nuevo.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')

@st.cache_data 
def extraer_datos(_img):
    texto = pytesseract.image_to_string(_img, lang='eng')
    d = {"nombre": "", "cedula": "", "ficha": "", "programa": "", "radicado": "", "nis": "", "correo": "", "telefono": ""}
    
    # Lógica de extracción (Regex)
    m_rad = re.search(r'(\d-\d{4}-\d+)', texto)
    if m_rad: d["radicado"] = m_rad.group(1)
    
    m_nis = re.search(r'(\d{4}-\d{2}-\d+)', texto)
    if m_nis: d["nis"] = m_nis.group(1)
    
    m_cor = re.search(r'([a-zA-Z0-9._%+-]+\s?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto)
    if m_cor: d["correo"] = m_cor.group(1).replace(" ", "").upper()
    
    m_fic = re.search(r'(?:Ficha|Curso)\s*\*\s*(\d+)', texto, re.IGNORECASE)
    if m_fic: d["ficha"] = m_fic.group(1)
    
    m_ced = re.search(r'(\d{10})', texto)
    if m_ced: d["cedula"] = m_ced.group(1)

    m_tel = re.search(r'3\d{9}', texto)
    if m_tel: d["telefono"] = m_tel.group(0)

    bloque = re.search(r'Nombre\s*Persona(.*?)\s*Telefono\s*Celular', texto, re.DOTALL | re.IGNORECASE)
    if bloque:
        limpio = re.sub(r'SAN\s*ANTONIO|Barrio|Municipio|MIRANDA|CAUCA', '', bloque.group(1), flags=re.IGNORECASE)
        lineas = [l.strip() for l in limpio.split('\n') if len(l.strip()) > 8]
        if lineas: d["nombre"] = lineas[0].strip()
    return d

# --- INTERFAZ ---
st.set_page_config(page_title=f"PQRS SENA v{VERSION}", layout="wide")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=120)
    st.title("SENA Digital")
    menu = st.radio("Navegación", ["Procesar PQRS", "Acta Mensual"])
    st.markdown("---")
    st.caption(f"Versión: {VERSION}\n{REGIONAL}")

hoy = datetime.datetime.now()
ctx = {"DIA": hoy.day, "MES": ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"][hoy.month-1], "ANHO": hoy.year, "ACTA": hoy.month}

if menu == "Procesar PQRS":
    st.header("📄 Registro de Novedades")
    archivo = st.file_uploader("Formulario", type=["tif", "png", "jpg"])
    if archivo:
        img = Image.open(archivo)
        d_ocr = extraer_datos(img)
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre", d_ocr["nombre"])
            ced = st.text_input("Cédula", d_ocr["cedula"])
            fic = st.text_input("Ficha", d_ocr["ficha"])
            prog = st.text_input("Programa")
        with col2:
            rad = st.text_input("Radicado", d_ocr["radicado"])
            nis = st.text_input("NIS", d_ocr["nis"])
            cor = st.text_input("Email", d_ocr["correo"])
            tel = st.text_input("Tel", d_ocr["telefono"])
        
        c1, c2 = st.columns(2)
        if c1.button("💾 GUARDAR"):
            guardar_datos({"nombre": nom.upper(), "cedula": ced, "ficha": fic, "programa": prog.upper(), "radicado": rad, "nis": nis, "correo": cor.lower(), "telefono": tel, "novedad": "Retiro Voluntario"})
            st.success("Guardado.")
        if c2.button("🖨️ CARTA WORD"):
            doc = DocxTemplate("Plantilla_PQRS.docx")
            doc.render({**ctx, "NOMBRE": nom, "CEDULA": ced, "FICHA": fic, "PROGRAMA": prog, "RADICADO": rad, "NIS": nis, "CORREO": cor, "TELEFONO": tel})
            b = io.BytesIO(); doc.save(b)
            st.download_button("Descargar", b.getvalue(), f"Carta_{ced}.docx")

else:
    st.header(f"📊 Cierre de Mes: {ctx['MES']}")
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS)
        st.dataframe(df)
        if st.button("📝 GENERAR ACTA"):
            doc = DocxTemplate("Plantilla_Acta_Mensual.docx")
            doc.render({**ctx, "lista_aprendices": df.to_dict(orient='records')})
            b = io.BytesIO(); doc.save(b)

            st.download_button("Descargar Acta", b.getvalue(), f"Acta_{ctx['MES']}.docx")

