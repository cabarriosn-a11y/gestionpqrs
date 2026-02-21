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
# ⚙️ CONFIGURACIÓN V1.0.5 - SENA GUAJIRA
# ==========================================
VERSION = "1.0.5"
CENTRO = "Centro Industrial y de Energías Alternativas"
REGIONAL = "Regional Guajira"
ARCHIVO_DATOS = "registro_pqrs.csv"

# COMENTAR ESTA LÍNEA PARA STREAMLIT CLOUD
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def guardar_datos(datos):
    df_nuevo = pd.DataFrame([datos])
    if not os.path.isfile(ARCHIVO_DATOS):
        df_nuevo.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
    else:
        try:
            df_nuevo.to_csv(ARCHIVO_DATOS, mode='a', header=False, index=False, encoding='utf-8-sig')
        except:
            df_nuevo.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')

@st.cache_data(show_spinner=False)
def extraer_datos(_img):
    texto = pytesseract.image_to_string(_img, lang='eng')
    d = {"nombre": "", "cedula": "", "ficha": "", "programa": "", "radicado": "", "nis": "", "correo": "", "telefono": ""}
    
    # --- 1. RADICADO Y NIS (Común en ambos) ---
    m_rad = re.search(r'(\d-\d{4}-\d+)', texto)
    if m_rad: d["radicado"] = m_rad.group(1)
    
    m_nis = re.search(r'(\d{4}-\d{2}-\d+)', texto)
    if m_nis: d["nis"] = m_nis.group(1)
    
    # --- 2. CORREO ---
    m_cor = re.search(r'([a-zA-Z0-9._%+-]+\s?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto)
    if m_cor: d["correo"] = m_cor.group(1).replace(" ", "").upper()
    
    # --- 3. IDENTIFICACIÓN ---
    m_ced = re.search(r'(?:Identificaci|Documento)[^\d]*(\d{7,10})', texto, re.IGNORECASE)
    if m_ced: d["cedula"] = m_ced.group(1)

    # --- 4. NOMBRE (Lógica Multi-Formato) ---
    # Caso A: Portal PQRS (Nombre Persona)
    m_nom_pqrs = re.search(r'Nombre\s*Persona\s*\n\s*([A-Z\s]+)', texto, re.IGNORECASE)
    # Caso B: Oficina Virtual (Nombres + Apellidos)
    m_nombres_ov = re.search(r'Nombres\s*\n\s*([A-Z\s]+)', texto, re.IGNORECASE)
    m_apellidos_ov = re.search(r'Apellidos\s*\n\s*([A-Z\s]+)', texto, re.IGNORECASE)
    
    if m_nom_pqrs:
        d["nombre"] = m_nom_pqrs.group(1).strip()
    elif m_nombres_ov and m_apellidos_ov:
        d["nombre"] = f"{m_nombres_ov.group(1).strip()} {m_apellidos_ov.group(1).strip()}"
    
    # Limpieza final de ruidos en el nombre
    d["nombre"] = re.sub(r'SAN\s*ANTONIO|BARRIO|MUNICIPIO|MIRANDA|CAUCA|CARGO', '', d["nombre"], flags=re.IGNORECASE).strip()

    # --- 5. FICHA (Lógica Multi-Formato) ---
    # Caso A: Etiqueta directa
    m_fic_dir = re.search(r'(?:Ficha|Curso)\s*\*\s*(\d+)', texto, re.IGNORECASE)
    # Caso B: Dentro del texto de descripción
    m_fic_txt = re.search(r'Ficha\s*(\d{6,8})', texto, re.IGNORECASE)
    
    if m_fic_dir: d["ficha"] = m_fic_dir.group(1)
    elif m_fic_txt: d["ficha"] = m_fic_txt.group(1)

    # --- 6. TELÉFONO ---
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
    st.caption(f"Versión: {VERSION} | {REGIONAL}")

hoy = datetime.datetime.now()
ctx = {"DIA": hoy.day, "MES": ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"][hoy.month-1], "ANHO": hoy.year, "ACTA": hoy.month}

if menu == "Procesar PQRS":
    st.header("📄 Registro de Novedades")
    # Al subir un archivo nuevo, Streamlit refresca los datos automáticamente
    archivo = st.file_uploader("Subir Formulario (PQRS o Oficina Virtual)", type=["tif", "png", "jpg"], key="subidor_archivos")
    
    if archivo:
        img = Image.open(archivo)
        d_ocr = extraer_datos(img)
        
        # Usamos 'value' para que si el OCR falla, el usuario pueda escribir
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
        
        c1, c2 = st.columns(2)
        if c1.button("💾 GUARDAR APRENDIZ"):
            guardar_datos({"nombre": nom.upper(), "cedula": ced, "ficha": fic, "programa": prog.upper(), "radicado": rad, "nis": nis, "correo": cor.lower(), "telefono": tel, "novedad": "Retiro Voluntario"})
            st.success("¡Aprendiz guardado en la lista del mes!")
            st.cache_data.clear() # Limpiamos caché para evitar duplicidad

        if c2.button("🖨️ GENERAR CARTA"):
            doc = DocxTemplate("Plantilla_PQRS.docx")
            doc.render({**ctx, "NOMBRE": nom, "CEDULA": ced, "FICHA": fic, "PROGRAMA": prog, "RADICADO": rad, "NIS": nis, "CORREO": cor, "TELEFONO": tel})
            b = io.BytesIO(); doc.save(b)
            st.download_button("Descargar Carta Individual", b.getvalue(), f"Carta_{ced}.docx")

else:
    st.header(f"📊 Cierre Mensual: {ctx['MES']}")
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS)
        st.dataframe(df, use_container_width=True)
        if st.button("📝 GENERAR ACTA MENSUAL"):
            doc = DocxTemplate("Plantilla_Acta_Mensual.docx")
            doc.render({**ctx, "lista_aprendices": df.to_dict(orient='records')})
            b = io.BytesIO(); doc.save(b)
            st.download_button("Descargar Acta", b.getvalue(), f"Acta_{ctx['MES']}.docx")
