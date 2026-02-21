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
# ⚙️ CONFIGURACIÓN V1.0.6 - SENA GUAJIRA
# ==========================================
VERSION = "1.0.6"
CENTRO = "Centro Industrial y de Energías Alternativas"
REGIONAL = "Regional Guajira"
ARCHIVO_DATOS = "registro_pqrs.csv"

# Línea de Tesseract para Nube
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@st.cache_data(show_spinner=False)
def extraer_datos(_img):
    texto = pytesseract.image_to_string(_img, lang='eng')
    d = {"nombre": "", "cedula": "", "ficha": "", "programa": "", "radicado": "", "nis": "", "correo": "", "telefono": ""}
    
    # 1. RADICADO Y NIS
    m_rad = re.search(r'(\d-\d{4}-\d+)', texto)
    if m_rad: d["radicado"] = m_rad.group(1)
    m_nis = re.search(r'(\d{4}-\d{2}-\d+)', texto)
    if m_nis: d["nis"] = m_nis.group(1)
    
    # 2. CORREO
    m_cor = re.search(r'([a-zA-Z0-9._%+-]+\s?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto)
    if m_cor: d["correo"] = m_cor.group(1).replace(" ", "").upper()
    
    # 3. IDENTIFICACIÓN
    m_ced = re.search(r'(?:Identificaci|Documento|No\.\s*de)[^\d]*(\d{7,10})', texto, re.IGNORECASE)
    if m_ced: d["cedula"] = m_ced.group(1)

    # 4. NOMBRE (Cerebro Mejorado para evitar uniones raras)
    # Dividimos por líneas para analizar mejor
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    for i, linea in enumerate(lineas):
        # Caso Portal PQRS: El nombre suele estar justo debajo de "Nombre Persona"
        if "Nombre Persona" in linea and i + 1 < len(lineas):
            d["nombre"] = lineas[i+1]
            break
        # Caso Oficina Virtual: El nombre está entre "Nombres" y "Apellidos"
        if "Nombres" == linea and i + 1 < len(lineas):
            nombres = lineas[i+1]
            # Buscamos apellidos más adelante
            for j in range(i+1, len(lineas)):
                if "Apellidos" in lineas[j] and j + 1 < len(lineas):
                    d["nombre"] = f"{nombres} {lineas[j+1]}"
                    break
            if d["nombre"]: break

    # Limpiamos el nombre de palabras que se filtran (Basura del OCR)
    basura = ["SAN ANTONIO", "BARRIO", "MUNICIPIO", "MIRANDA", "CAUCA", "CORREO", "ELECTRO", "TELEFONO", "CELULAR", "CARGO"]
    for b in basura:
        d["nombre"] = re.sub(b, '', d["nombre"], flags=re.IGNORECASE).strip()

    # 5. FICHA
    m_fic = re.search(r'(?:Ficha|Curso)\s*\D*(\d{7,8})', texto, re.IGNORECASE)
    if m_fic: d["ficha"] = m_fic.group(1)

    # 6. TELÉFONO
    m_tel = re.search(r'3\d{9}', texto)
    if m_tel: d["telefono"] = m_tel.group(0)

    return d

# --- INTERFAZ ---
st.set_page_config(page_title=f"SENA PQRS v{VERSION}", layout="wide")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=120)
    st.title("SENA Digital")
    menu = st.radio("Navegación", ["Procesar PQRS", "Acta Mensual"])
    st.markdown("---")
    st.caption(f"v{VERSION} | {REGIONAL}")

hoy = datetime.datetime.now()
ctx = {"DIA": hoy.day, "MES": ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"][hoy.month-1], "ANHO": hoy.year, "ACTA": hoy.month}

if menu == "Procesar PQRS":
    st.header("📄 Registro de Aprendiz")
    # Botón para limpiar todo antes de empezar
    if st.button("🆕 LIMPIAR PARA NUEVO APRENDIZ"):
        st.cache_data.clear()
        st.rerun()

    archivo = st.file_uploader("Subir Imagen (Formato PQRS o Oficina Virtual)", type=["tif", "png", "jpg"])
    
    if archivo:
        img = Image.open(archivo)
        d_ocr = extraer_datos(img)
        
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre", value=d_ocr["nombre"])
            ced = st.text_input("Cédula", value=d_ocr["cedula"])
            fic = st.text_input("Ficha", value=d_ocr["ficha"])
            prog = st.text_input("Programa")
        with col2:
            rad = st.text_input("Radicado", value=d_ocr["radicado"])
            nis = st.text_input("NIS", value=d_ocr["nis"])
            cor = st.text_input("Email", value=d_ocr["correo"])
            tel = st.text_input("Tel", value=d_ocr["telefono"])
        
        if st.button("💾 GUARDAR APRENDIZ"):
            pd.DataFrame([{
                "nombre": nom.upper(), "cedula": ced, "ficha": fic, 
                "programa": prog.upper(), "radicado": rad, "nis": nis, 
                "correo": cor.lower(), "telefono": tel, "novedad": "Retiro Voluntario"
            }]).to_csv(ARCHIVO_DATOS, mode='a', header=not os.path.exists(ARCHIVO_DATOS), index=False, encoding='utf-8-sig')
            st.success("¡Datos guardados!")

        if st.button("🖨️ GENERAR CARTA"):
            doc = DocxTemplate("Plantilla_PQRS.docx")
            doc.render({**ctx, "NOMBRE": nom, "CEDULA": ced, "FICHA": fic, "PROGRAMA": prog, "RADICADO": rad, "NIS": nis, "CORREO": cor, "TELEFONO": tel})
            b = io.BytesIO(); doc.save(b)
            st.download_button("Descargar Carta", b.getvalue(), f"Carta_{ced}.docx")

else:
    st.header(f"📊 Cierre Mensual: {ctx['MES']}")
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS)
        st.table(df)
        if st.button("📝 GENERAR ACTA"):
            doc = DocxTemplate("Plantilla_Acta_Mensual.docx")
            doc.render({**ctx, "lista_aprendices": df.to_dict(orient='records')})
            b = io.BytesIO(); doc.save(b)
            st.download_button("Descargar Acta", b.getvalue(), f"Acta_{ctx['MES']}.docx")
