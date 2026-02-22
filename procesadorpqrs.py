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
from datetime import datetime

# --- DEFINICIÓN DEL PERIODO (Pégalo arriba de los menús) ---
meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
fecha_actual = datetime.now()
periodo_actual = f"{meses_nombres[fecha_actual.month - 1]}-{fecha_actual.year}"
if menu == "1. Retiros Voluntarios (Base de Datos)":
    st.header("📄 Procesamiento de Retiros Voluntarios")
    
    # Usamos un key para que el uploader también se pueda resetear
    archivo = st.file_uploader("Subir formulario de retiro", type=["tif", "png", "jpg"], key="uploader_retiro")
    
    if archivo:
        # Solo ejecutamos OCR si no tenemos los datos en sesión (para no borrar lo que edites manualmente)
        if "datos_ocr" not in st.session_state:
            img = Image.open(archivo)
            st.session_state["datos_ocr"] = extraer_datos(img)

        d_ocr = st.session_state["datos_ocr"]

        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre Aprendiz", value=d_ocr["nombre"], key="nombre_input")
            ced = st.text_input("Cédula", value=d_ocr["cedula"], key="cedula_input")
            fic = st.text_input("Ficha", value=d_ocr["ficha"], key="ficha_input")
        with col2:
            rad = st.text_input("Radicado", value=d_ocr["radicado"], key="radicado_input")
            prog = st.text_input("Programa", key="programa_input")
            nov = "Retiro Voluntario"

        c1, c2 = st.columns(2)
        
        # --- BOTÓN GUARDAR ---
        if c1.button("💾 GUARDAR EN LISTA"):
            # Guardamos con 'periodo' para que aparezca en la Sesión 3 (Actas)
            nuevo_dato = {
                "nombre": nom.upper(), 
                "cedula": ced, 
                "ficha": fic, 
                "programa": prog.upper(), 
                "radicado": rad, 
                "novedad": nov,
                "periodo": periodo_actual # MUY IMPORTANTE para el acta mensual
            }
            
            pd.DataFrame([nuevo_dato]).to_csv(
                ARCHIVO_DATOS, 
                mode='a', 
                header=not os.path.exists(ARCHIVO_DATOS), 
                index=False, 
                encoding='utf-8-sig'
            )
            
            st.success("✅ Guardado para el acta mensual.")
            
            # >>> LIMPIEZA DE SESIÓN (Solo ocurre tras guardar) <<<
            for key in ["nombre_input", "cedula_input", "ficha_input", "radicado_input", "programa_input", "datos_ocr"]:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.rerun() # Refresca la app y limpia los campos

        # --- BOTÓN GENERAR CARTA ---
        if c2.button("🖨️ GENERAR CARTA DE RETIRO"):
            try:
                doc = DocxTemplate("Plantilla_PQRS.docx")
                contexto_word = {
                    **ctx, 
                    "NOMBRE": nom, 
                    "CEDULA": ced, 
                    "FICHA": fic, 
                    "PROGRAMA": prog, 
                    "RADICADO": rad, 
                    "CUERPO": "Se tramita retiro voluntario según solicitud oficial."
                }
                doc.render(contexto_word)
                
                # Guardamos en un buffer para que el botón de descarga funcione bien
                b = io.BytesIO()
                doc.save(b)
                st.session_state["archivo_word"] = b.getvalue()
                st.session_state["nombre_archivo"] = f"Retiro_{ced}.docx"
                st.info("Documento listo para descargar abajo ↓")
            except Exception as e:
                st.error(f"Error al generar Word: {e}")

        # Aparece el botón de descarga solo si ya se generó el archivo
        if "archivo_word" in st.session_state:
            st.download_button(
                label="📥 Descargar Carta",
                data=st.session_state["archivo_word"],
                file_name=st.session_state["nombre_archivo"],
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
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
            df = pd.read_csv(ARCHIVO_DATOS, on_bad_lines='skip', sep=',', engine='python', encoding='utf-8-sig')
            st.table(df) # Muestra los datos en la app
            # --- COPIAR DESDE AQUÍ ---
        with st.expander("🗑️ ¿Te equivocaste? Borrar un registro específico"):
            st.warning("Cuidado: Esta acción eliminará el registro permanentemente de la base de datos.")
            
            # Usamos el 'df' que cargaste en la línea de arriba
            registro_a_eliminar = st.selectbox(
                "Selecciona el aprendiz que deseas eliminar:",
                options=df.index,
                format_func=lambda x: f"{df.loc[x, 'nombre']} | Cédula: {df.loc[x, 'cedula']}"
            )

            if st.button("❌ ELIMINAR REGISTRO SELECCIONADO", key="btn_borrar_registro"):
                try:
                    # Cargamos el archivo completo para borrar la fila
                    df_total = pd.read_csv(ARCHIVO_DATOS, on_bad_lines='skip', engine='python', encoding='utf-8-sig')
                    df_total = df_total.drop(registro_a_eliminar)
                    df_total.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
                    
                    st.success("Registro eliminado correctamente.")
                    st.rerun() # Esto recarga la página para que la tabla se actualice
                except Exception as e:
                    st.error(f"No se pudo eliminar: {e}")
        # --- HASTA AQUÍ ---
            if st.button("📝 GENERAR ACTA AUTOMÁTICA", key="btn_acta_auto"):
                try:
                    # Cargamos la plantilla
                    doc = DocxTemplate("Plantilla_Acta_Mensual.docx")
                    
                    # Creamos la tabla desde Python
                    subdoc = doc.new_subdoc()
                    tabla = subdoc.add_table(rows=1, cols=6)
                    tabla.style = 'Table Grid'
                    
                    # Títulos de la tabla
                    titulos = ['Nombre', 'Identificación', 'Ficha', 'Programa', 'Novedad', 'Radicado']
                    for i, texto in enumerate(titulos):
                        tabla.rows[0].cells[i].text = texto
                    
                    # Llenamos con los datos del sistema
                    for _, fila in df.iterrows():
                        celdas = tabla.add_row().cells
                        celdas[0].text = str(fila['nombre'])
                        celdas[1].text = str(fila['cedula'])
                        celdas[2].text = str(fila['ficha'])
                        celdas[3].text = str(fila['programa'])
                        celdas[4].text = "Retiro Voluntario"
                        celdas[5].text = str(fila['radicado'])
                    
                    # Insertamos la tabla en la etiqueta {{ TABLA_RETIROS }}
                    doc.render({**ctx, "TABLA_RETIROS": subdoc})
                    
                    b = io.BytesIO()
                    doc.save(b)
                    st.download_button("📥 Descargar Acta", b.getvalue(), f"Acta_{ctx['MES']}.docx")
                    st.success("✅ ¡Tabla generada exitosamente!")
                    
                except Exception as e:
                    st.error(f"Error técnico: {e}")





