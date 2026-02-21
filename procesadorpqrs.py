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
# ⚙️ CONFIGURACIÓN V1.0.8 - SENA GUAJIRA
# ==========================================
VERSION = "1.0.8"
CENTRO = "Centro Industrial y de Energías Alternativas"
REGIONAL = "Regional Guajira"
ARCHIVO_DATOS = "registro_pqrs.csv"

# Línea comentada para que funcione en la nube (Streamlit Cloud)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@st.cache_data(show_spinner=False)
def extraer_datos(_img):
    texto = pytesseract.image_to_string(_img, lang='eng')
    d = {"nombre": "", "cedula": "", "ficha": "", "programa": "", "radicado": "", "nis": "", "correo": "", "telefono": ""}
    
    # 1. RADICADO, NIS Y CORREO (Estables)
    m_rad = re.search(r'(\d-\d{4}-\d+)', texto); d["radicado"] = m_rad.group(1) if m_rad else ""
    m_nis = re.search(r'(\d{4}-\d{2}-\d+)', texto); d["nis"] = m_nis.group(1) if m_nis else ""
    m_cor = re.search(r'([a-zA-Z0-9._%+-]+\s?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto)
    if m_cor: d["correo"] = m_cor.group(1).replace(" ", "").upper()
    
    # 2. IDENTIFICACIÓN
    m_ced = re.search(r'(?:Identificaci|Documento|No\.\s*de)[^\d]*(\d{7,10})', texto, re.IGNORECASE)
    if m_ced: d["cedula"] = m_ced.group(1)

    # 3. NOMBRE (Lógica Multi-Capa)
    lineas = [l.strip() for l in texto.split('\n') if len(l.strip()) > 2]
    
    # Caso A: Oficina Virtual (Nombres y Apellidos por separado)
    nombres_ov = ""
    apellidos_ov = ""
    for i, linea in enumerate(lineas):
        if "Nombres" == linea.strip() and i + 1 < len(lineas):
            nombres_ov = lineas[i+1]
        if "Apellidos" == linea.strip() and i + 1 < len(lineas):
            apellidos_ov = lineas[i+1]
    
    if nombres_ov and apellidos_ov:
        d["nombre"] = f"{nombres_ov} {apellidos_ov}"
    
    # Caso B: Portal PQRS (Nombre Persona)
    if not d["nombre"]:
        for i, linea in enumerate(lineas):
            if "Nombre Persona" in linea and i + 1 < len(lineas):
                d["nombre"] = lineas[i+1]
                break

    # Limpieza Profunda de "Basura" OCR
    # Filtramos palabras que el OCR confunde o pega al nombre
    basura = ["SAN ANTONIO", "BARRIO", "MUNICIPIO", "MIRANDA", "CAUCA", "CORREO", "ELECTRO", "TELEFONO", "CELULAR", "CARGO", "DATOS", "FECHA"]
    for b in basura:
        d["nombre"] = re.sub(rf'\b{b}\b', '', d["nombre"], flags=re.IGNORECASE).strip()
    # Eliminar cualquier cosa que no sean letras o espacios
    d["nombre"] = re.sub(r'[^a-zA-Z\s]', '', d["nombre"]).strip()

    # 4. FICHA
    # Busca el número de 7-8 dígitos después de "Ficha" o "Curso"
    m_fic = re.search(r'(?:Ficha|Curso)\s*\D*(\d{7,8})', texto, re.IGNORECASE)
    d["ficha"] = m_fic.group(1) if m_fic else ""

    return d

# --- INTERFAZ ---
st.set_page_config(page_title=f"PQRS SENA v{VERSION}", layout="wide")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=120)
    st.title("SENA - Riohacha")
    menu = st.radio("Menú Principal", ["Procesar PQRS", "Acta Mensual"])
    st.markdown("---")
    st.caption(f"v{VERSION} | {REGIONAL}")

hoy = datetime.datetime.now()
ctx = {"DIA": hoy.day, "MES": ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"][hoy.month-1], "ANHO": hoy.year, "ACTA": hoy.month}

if menu == "Procesar PQRS":
    st.header("📄 Extracción de Datos")
    if st.button("🆕 LIMPIAR PARA NUEVO PROCESO"):
        st.cache_data.clear()
        st.rerun()

    archivo = st.file_uploader("Sube el formulario escaneado", type=["tif", "png", "jpg"])
    
    if archivo:
        img = Image.open(archivo)
        d_ocr = extraer_datos(img)
        
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre del Aprendiz (Corregir si es necesario)", value=d_ocr["nombre"])
            ced = st.text_input("Identificación", value=d_ocr["cedula"])
            fic = st.text_input("Ficha", value=d_ocr["ficha"])
            prog = st.text_input("Programa de Formación")
        with col2:
            rad = st.text_input("Radicado", value=d_ocr["radicado"])
            nis = st.text_input("NIS", value=d_ocr["nis"])
            cor = st.text_input("Email", value=d_ocr["correo"])
            tel = st.text_input("Teléfono", value=d_ocr["telefono"])
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 GUARDAR REGISTRO"):
                nuevo = pd.DataFrame([{
                    "nombre": nom.upper(), "cedula": ced, "ficha": fic, 
                    "programa": prog.upper(), "radicado": rad, "nis": nis, 
                    "correo": cor.lower(), "telefono": tel, "novedad": "Retiro Voluntario"
                }])
                nuevo.to_csv(ARCHIVO_DATOS, mode='a', header=not os.path.exists(ARCHIVO_DATOS), index=False, encoding='utf-8-sig')
                st.success("✅ Aprendiz guardado exitosamente.")
        with c2:
            if st.button("🖨️ GENERAR WORD"):
                try:
                    doc = DocxTemplate("Plantilla_PQRS.docx")
                    doc.render({**ctx, "NOMBRE": nom, "CEDULA": ced, "FICHA": fic, "PROGRAMA": prog, "RADICADO": rad, "NIS": nis, "CORREO": cor, "TELEFONO": tel})
                    b = io.BytesIO(); doc.save(b); st.download_button("📥 Descargar Carta", b.getvalue(), f"Carta_{ced}.docx")
                except Exception as e: st.error(f"Error: {e}")

else:
    st.header(f"📊 Control de Registros - {ctx['MES']}")
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS)
        st.dataframe(df, use_container_width=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("📄 DESCARGAR ACTA DEL MES"):
                try:
                    doc = DocxTemplate("Plantilla_Acta_Mensual.docx")
                    doc.render({**ctx, "lista_aprendices": df.to_dict(orient='records')})
                    b = io.BytesIO(); doc.save(b); st.download_button("📥 Obtener Acta Word", b.getvalue(), f"Acta_{ctx['MES']}.docx")
                except Exception as e: st.error(f"Error: {e}")
        
        with col_btn2:
            if st.button("🗑️ ELIMINAR ÚLTIMO REGISTRO"):
                df = df[:-1]
                df.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
                st.warning("Se ha borrado el último aprendiz de la lista.")
                st.rerun()

        st.markdown("---")
        if st.button("🚨 VACIAR TODA LA TABLA (Borrar Pruebas)"):
            os.remove(ARCHIVO_DATOS)
            st.error("Lista de aprendices reseteada por completo.")
            st.rerun()
    else:
        st.warning("No hay aprendices registrados todavía.")
