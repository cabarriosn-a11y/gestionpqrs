import streamlit as st
import pytesseract
from PIL import Image
import re
from docxtpl import DocxTemplate
import io
import datetime
import pandas as pd
import os
import google.generativeai as genai

# ==========================================
# ⚙️ CONFIGURACIÓN FINAL - SENA GUAJIRA
# ==========================================
VERSION = "1.2.2"
CENTRO = "Centro Industrial y de Energías Alternativas"
REGIONAL = "Regional Guajira"
ARCHIVO_DATOS = "registro_pqrs.csv"

# Configuración de Gemini desde Secrets de Streamlit
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.error("❌ Falta GEMINI_API_KEY en Secrets.")

# COMENTAR ESTA LÍNEA PARA PRODUCCIÓN EN LA NUBE
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- FUNCIONES DE INTELIGENCIA ---

def redactar_con_ia(prompt_usuario):
    """Genera respuesta usando el modelo disponible en 2026"""
    try:
        # Usamos el modelo 2.5-flash que apareció en tu diagnóstico
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        contexto = (
            "Eres un experto administrativo del SENA Regional Guajira. "
            "Redacta una respuesta formal, cordial y técnica. "
            "La situación a responder es: "
        )
        
        response = model.generate_content(contexto + prompt_usuario)
        return response.text
    except Exception as e:
        return f"Error con Gemini 2.5: {e}. Intenta usar 'gemini-2.0-flash' si persiste."

@st.cache_data(show_spinner=False)
def extraer_datos(_img):
    """OCR inteligente para Portal PQRS y Oficina Virtual"""
    texto = pytesseract.image_to_string(_img, lang='eng')
    d = {"nombre": "", "cedula": "", "ficha": "", "programa": "", "radicado": "", "nis": "", "correo": "", "telefono": ""}
    
    # Radicado, NIS, Correo, Cédula
    m_rad = re.search(r'(\d-\d{4}-\d+)', texto); d["radicado"] = m_rad.group(1) if m_rad else ""
    m_nis = re.search(r'(\d{4}-\d{2}-\d+)', texto); d["nis"] = m_nis.group(1) if m_nis else ""
    m_cor = re.search(r'([a-zA-Z0-9._%+-]+\s?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto)
    if m_cor: d["correo"] = m_cor.group(1).replace(" ", "").upper()
    m_ced = re.search(r'(?:Identificaci|Documento|No\.\s*de)[^\d]*(\d{7,10})', texto, re.IGNORECASE)
    if m_ced: d["cedula"] = m_ced.group(1)

    # Lógica de Nombre Multi-Formato
    lineas = [l.strip() for l in texto.split('\n') if len(l.strip()) > 2]
    n_ov, a_ov = "", ""
    for i, l in enumerate(lineas):
        if "Nombres" == l.strip() and i+1 < len(lineas): n_ov = lineas[i+1]
        if "Apellidos" == l.strip() and i+1 < len(lineas): a_ov = lineas[i+1]
        if "Nombre Persona" in l and i+1 < len(lineas): d["nombre"] = lineas[i+1]
    if n_ov and a_ov: d["nombre"] = f"{n_ov} {a_ov}"
    
    # Limpieza de ruidos (Barrio, Cargo, etc.)
    d["nombre"] = re.sub(r'SAN\s*ANTONIO|BARRIO|MUNICIPIO|MIRANDA|CAUCA|CORREO|TELEFONO', '', d["nombre"], flags=re.IGNORECASE).strip()
    d["nombre"] = re.sub(r'[^a-zA-Z\s]', '', d["nombre"]).strip()

    # Ficha
    m_fic = re.search(r'(?:Ficha|Curso)\s*\D*(\d{7,10})', texto, re.IGNORECASE)
    d["ficha"] = m_fic.group(1) if m_fic else ""
    
    return d

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title=f"SENA Guajira v{VERSION}", layout="wide")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=120)
    st.title("SENA - Riohacha")
    menu = st.radio("MENÚ PRINCIPAL", [
        "1. Retiros Voluntarios (Base de Datos)", 
        "2. Redactor Inteligente IA (Temas Varios)", 
        "3. Acta de Cierre Mensual"
    ])
    st.markdown("---")
    st.caption(f"v{VERSION} | {REGIONAL}\n{CENTRO}")

hoy = datetime.datetime.now()
ctx = {"DIA": hoy.day, "MES": ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"][hoy.month-1], "ANHO": hoy.year, "ACTA": hoy.month}

# ==========================================
# OPCIÓN 1: RETIROS
# ==========================================
if menu == "1. Retiros Voluntarios (Base de Datos)":
    st.header("📄 Procesamiento de Retiros Voluntarios")
    archivo = st.file_uploader("Subir formulario de retiro", type=["tif", "png", "jpg"])
    
    if archivo:
        img = Image.open(archivo); d_ocr = extraer_datos(img)
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre Aprendiz", value=d_ocr["nombre"])
            ced = st.text_input("Cédula", value=d_ocr["cedula"])
            fic = st.text_input("Ficha", value=d_ocr["ficha"])
        with col2:
            rad = st.text_input("Radicado", value=d_ocr["radicado"])
            prog = st.text_input("Programa")
            nov = "Retiro Voluntario"

        c1, c2 = st.columns(2)
        if c1.button("💾 GUARDAR EN LISTA"):
            pd.DataFrame([{"nombre": nom.upper(), "cedula": ced, "ficha": fic, "programa": prog.upper(), "radicado": rad, "novedad": nov}]).to_csv(ARCHIVO_DATOS, mode='a', header=not os.path.exists(ARCHIVO_DATOS), index=False, encoding='utf-8-sig')
            st.success("✅ Guardado para el acta mensual.")
        
        if c2.button("🖨️ GENERAR CARTA DE RETIRO"):
            doc = DocxTemplate("Plantilla_PQRS.docx")
            doc.render({**ctx, "NOMBRE": nom, "CEDULA": ced, "FICHA": fic, "PROGRAMA": prog, "RADICADO": rad, "CUERPO": "Se tramita retiro voluntario según solicitud oficial."})
            b = io.BytesIO(); doc.save(b); st.download_button("📥 Descargar Carta", b.getvalue(), f"Retiro_{ced}.docx")

# ==========================================
# OPCIÓN 2: REDACTOR IA (Cualquier tema)
# ==========================================
elif menu == "2. Redactor Inteligente IA (Temas Varios)":
    st.header("🤖 Asistente de Redacción Gemini")
    st.warning("Esta sección usa 'Plantilla_Generica_IA.docx' y no guarda en la base de datos.")
    
    archivo_ia = st.file_uploader("Opcional: Subir imagen para datos", type=["tif", "png", "jpg"])
    d_ia = extraer_datos(Image.open(archivo_ia)) if archivo_ia else {"nombre": "", "cedula": "", "radicado": "", "programa": ""}

    col_ia1, col_ia2 = st.columns(2)
    with col_ia1:
        nom_ia = st.text_input("Nombre", value=d_ia["nombre"])
        ced_ia = st.text_input("Identificación", value=d_ia["cedula"])
    with col_ia2:
        rad_ia = st.text_input("Radicado", value=d_ia["radicado"])
        prog_ia = st.text_input("Programa", value=d_ia["programa"])

    st.markdown("### 📝 Instrucción de Redacción")
    prompt = st.text_area("Explica la situación (Ej: Niega certificación por falta de horas)", "Informa que el certificado está en proceso de firma y llegará en 3 días.")
    
    if st.button("✨ GENERAR TEXTO CON IA"):
        with st.spinner("Gemini redactando..."):
            st.session_state['cuerpo_ia'] = redactar_con_ia(f"Aprendiz: {nom_ia}. Programa: {prog_ia}. Situación: {prompt}")

    if 'cuerpo_ia' in st.session_state:
        cuerpo_final = st.text_area("Edita la redacción:", value=st.session_state['cuerpo_ia'], height=250)
        if st.button("🖨️ GENERAR WORD GENÉRICO"):
            doc = DocxTemplate("Plantilla_Generica_IA.docx")
            doc.render({**ctx, "NOMBRE": nom_ia.upper(), "CEDULA": ced_ia, "RADICADO": rad_ia, "PROGRAMA": prog_ia.upper(), "CUERPO": cuerpo_final})
            b = io.BytesIO(); doc.save(b); st.download_button("📥 Descargar Documento IA", b.getvalue(), f"Respuesta_IA_{ced_ia}.docx")

# ==========================================
# OPCIÓN 3: ACTA MENSUAL
# ==========================================
else:
        st.header(f"📊 Acta de Retiros - {ctx['MES']}")
        if os.path.exists(ARCHIVO_DATOS):
            df = pd.read_csv(ARCHIVO_DATOS)
            st.table(df) # Muestra los datos actuales en la app
            
            # Creamos dos columnas para los botones
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📝 GENERAR ACTA AUTOMÁTICA", key="btn_auto_final"):
                    try:
                        doc = DocxTemplate("Plantilla_Acta_Mensual.docx")
                        subdoc = doc.new_subdoc()
                        tabla = subdoc.add_table(rows=1, cols=6)
                        tabla.style = 'Table Grid'
                        
                        # Encabezados
                        titulos = ['Nombre', 'Identificación', 'Ficha', 'Programa', 'Novedad', 'Radicado']
                        for i, texto in enumerate(titulos):
                            tabla.rows[0].cells[i].text = texto
                        
                        # Llenado de datos
                        for _, fila in df.iterrows():
                            celdas = tabla.add_row().cells
                            celdas[0].text = str(fila['nombre'])
                            celdas[1].text = str(fila['cedula'])
                            celdas[2].text = str(fila['ficha'])
                            celdas[3].text = str(fila['programa'])
                            celdas[4].text = "Retiro Voluntario"
                            celdas[5].text = str(fila['radicado'])
                        
                        doc.render({**ctx, "TABLA_RETIROS": subdoc})
                        b = io.BytesIO()
                        doc.save(b)
                        st.download_button("📥 Descargar Acta", b.getvalue(), f"Acta_{ctx['MES']}.docx")
                    except Exception as e:
                        st.error(f"Error: {e}")

            with col2:
                # El "botoncito" para borrar la base de datos y reiniciar
                if st.button("🚨 REINICIAR MES (Borrar todo)", key="btn_borrar_db"):
                    os.remove(ARCHIVO_DATOS)
                    st.success("Base de datos borrada. Reiniciando...")
                    st.rerun() # Refresca la app para mostrar que ya no hay datos
        else:
            st.warning("No hay registros para este mes.")







