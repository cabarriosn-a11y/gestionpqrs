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
# ⚙️ CONFIGURACIÓN V1.0.7 - SENA GUAJIRA
# ==========================================
VERSION = "1.0.7"
CENTRO = "Centro Industrial y de Energías Alternativas"
REGIONAL = "Regional Guajira"
ARCHIVO_DATOS = "registro_pqrs.csv"

# COMENTAR PARA STREAMLIT CLOUD
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@st.cache_data(show_spinner=False)
def extraer_datos(_img):
    texto = pytesseract.image_to_string(_img, lang='eng')
    d = {"nombre": "", "cedula": "", "ficha": "", "programa": "", "radicado": "", "nis": "", "correo": "", "telefono": ""}
    
    # 1. RADICADO, NIS, CORREO Y CÉDULA (Funcionan estable)
    m_rad = re.search(r'(\d-\d{4}-\d+)', texto); d["radicado"] = m_rad.group(1) if m_rad else ""
    m_nis = re.search(r'(\d{4}-\d{2}-\d+)', texto); d["nis"] = m_nis.group(1) if m_nis else ""
    m_cor = re.search(r'([a-zA-Z0-9._%+-]+\s?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto)
    if m_cor: d["correo"] = m_cor.group(1).replace(" ", "").upper()
    m_ced = re.search(r'(?:Identificaci|Documento|No\.\s*de)[^\d]*(\d{7,10})', texto, re.IGNORECASE)
    if m_ced: d["cedula"] = m_ced.group(1)

    # 2. NOMBRE (Búsqueda por capas)
    lineas = [l.strip() for l in texto.split('\n') if len(l.strip()) > 5]
    
    # Capa 1: Por etiquetas
    for i, linea in enumerate(lineas):
        if "Nombre Persona" in linea and i + 1 < len(lineas):
            d["nombre"] = lineas[i+1]
            break
        if "Nombres" in linea and i + 1 < len(lineas):
            nombres = lineas[i+1]
            for j in range(i+1, len(lineas)):
                if "Apellidos" in lineas[j] and j + 1 < len(lineas):
                    d["nombre"] = f"{nombres} {lineas[j+1]}"
                    break
            if d["nombre"]: break

    # Capa 2: Failsafe (Si sigue vacío, busca líneas largas en MAYÚSCULAS)
    if not d["nombre"]:
        for linea in lineas:
            if linea.isupper() and len(linea) > 12 and not any(x in linea for x in ["SENA", "REGIONAL", "CENTRO", "GUAJIRA"]):
                d["nombre"] = linea
                break

    # Limpieza de "Basura" OCR
    basura = ["SAN ANTONIO", "BARRIO", "MUNICIPIO", "MIRANDA", "CAUCA", "CORREO", "TELEFONO", "CELULAR", "CARGO", "DATOS"]
    for b in basura:
        d["nombre"] = re.sub(b, '', d["nombre"], flags=re.IGNORECASE).strip()

    # 3. FICHA Y TELÉFONO
    m_fic = re.search(r'(?:Ficha|Curso)\s*\D*(\d{7,8})', texto, re.IGNORECASE)
    d["ficha"] = m_fic.group(1) if m_fic else ""
    m_tel = re.search(r'3\d{9}', texto)
    d["telefono"] = m_tel.group(0) if m_tel else ""

    return d

# --- INTERFAZ ---
st.set_page_config(page_title=f"PQRS SENA v{VERSION}", layout="wide")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=120)
    st.title("SENA Digital")
    menu = st.radio("Navegación", ["Procesar PQRS", "Acta Mensual"])
    st.markdown("---")
    st.caption(f"v{VERSION} | {REGIONAL}")

hoy = datetime.datetime.now()
ctx = {"DIA": hoy.day, "MES": ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"][hoy.month-1], "ANHO": hoy.year, "ACTA": hoy.month}

if menu == "Procesar PQRS":
    st.header("📄 Registro de Novedades")
    if st.button("🆕 LIMPIAR PANTALLA"):
        st.cache_data.clear()
        st.rerun()

    archivo = st.file_uploader("Subir Imagen", type=["tif", "png", "jpg"])
    
    if archivo:
        img = Image.open(archivo)
        d_ocr = extraer_datos(img)
        
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre (Valida siempre este campo)", value=d_ocr["nombre"])
            ced = st.text_input("Cédula", value=d_ocr["cedula"])
            fic = st.text_input("Ficha", value=d_ocr["ficha"])
            prog = st.text_input("Programa")
        with col2:
            rad = st.text_input("Radicado", value=d_ocr["radicado"])
            nis = st.text_input("NIS", value=d_ocr["nis"])
            cor = st.text_input("Email", value=d_ocr["correo"])
            tel = st.text_input("Tel", value=d_ocr["telefono"])
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 GUARDAR APRENDIZ"):
                nuevo = pd.DataFrame([{
                    "nombre": nom.upper(), "cedula": ced, "ficha": fic, 
                    "programa": prog.upper(), "radicado": rad, "nis": nis, 
                    "correo": cor.lower(), "telefono": tel, "novedad": "Retiro Voluntario"
                }])
                nuevo.to_csv(ARCHIVO_DATOS, mode='a', header=not os.path.exists(ARCHIVO_DATOS), index=False, encoding='utf-8-sig')
                st.success("¡Guardado!")
        with c2:
            if st.button("🖨️ GENERAR CARTA"):
                doc = DocxTemplate("Plantilla_PQRS.docx")
                doc.render({**ctx, "NOMBRE": nom, "CEDULA": ced, "FICHA": fic, "PROGRAMA": prog, "RADICADO": rad, "NIS": nis, "CORREO": cor, "TELEFONO": tel})
                b = io.BytesIO(); doc.save(b); st.download_button("Descargar Carta", b.getvalue(), f"Carta_{ced}.docx")

else:
    st.header(f"📊 Gestión de Base de Datos - {ctx['MES']}")
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS)
        st.dataframe(df, use_container_width=True)
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("📝 GENERAR ACTA MENSUAL"):
                doc = DocxTemplate("Plantilla_Acta_Mensual.docx")
                doc.render({**ctx, "lista_aprendices": df.to_dict(orient='records')})
                b = io.BytesIO(); doc.save(b); st.download_button("Descargar Acta", b.getvalue(), f"Acta_{ctx['MES']}.docx")
        
        with col_b:
            if st.button("🗑️ BORRAR ÚLTIMO REGISTRO"):
                df = df[:-1]
                df.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
                st.warning("Último registro eliminado.")
                st.rerun()

        st.markdown("---")
        if st.button("🚨 LIMPIAR TODA LA LISTA (RESETEAR MES)"):
            os.remove(ARCHIVO_DATOS)
            st.error("Se han borrado todos los registros de prueba.")
            st.rerun()
    else:
        st.warning("No hay registros en la lista.")
