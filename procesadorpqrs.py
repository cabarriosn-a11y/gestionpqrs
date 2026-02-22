import streamlit as st
import pytesseract
from PIL import Image
import re
from PIL import Image
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

# --- ESTA ES LA FUNCIÓN QUE TE DA EL NAMEERROR SI NO ESTÁ AQUÍ ARRIBA ---
def extraer_datos_multiformato(img):
    # Forzamos lectura en español para detectar tildes y etiquetas del SENA
    texto = pytesseract.image_to_string(img, lang='spa')
    datos = {"nombre": "", "cedula": "", "ficha": "", "radicado": "", "nis": "", "email": ""}

    # 🔍 Búsqueda de Radicado y NIS
    rad = re.search(r"(?:Radicado|No\.\s*Radicado)\s*\n?([\d-]+)", texto, re.IGNORECASE)
    if rad: datos["radicado"] = rad.group(1).strip()

    nis = re.search(r"N\.?I\.?S\s*\n?([\d-]+)", texto, re.IGNORECASE)
    if nis: datos["nis"] = nis.group(1).strip()

    # 🔍 Búsqueda de Nombre (Portal PQRS vs Oficina Virtual)
    if "Nombre Persona" in texto:
        nom = re.search(r"Nombre Persona\s*\n+(.*)", texto, re.IGNORECASE)
        if nom: datos["nombre"] = nom.group(1).strip().upper()
    else:
        n = re.search(r"Nombres\s*\n+(.*)", texto, re.IGNORECASE)
        a = re.search(r"Apellidos\s*\n+(.*)", texto, re.IGNORECASE)
        if n and a: datos["nombre"] = f"{n.group(1).strip()} {a.group(1).strip()}".upper()

    # 🔍 Búsqueda de Cédula y Ficha
    ced = re.search(r"(?:Identificación|Identificacion)\s*\n?(\d+)", texto, re.IGNORECASE)
    if ced: datos["cedula"] = ced.group(1).strip()

    fic = re.search(r"Ficha\s*(?:de\s*Curso)?\s*\n?(\d+)", texto, re.IGNORECASE)
    if fic: datos["ficha"] = fic.group(1).strip()

    return datos
def extraer_datos_retiros(img):
    # Usamos 'spa' porque tus documentos son del SENA en español
    texto = pytesseract.image_to_string(img, lang='spa')
    
    # Creamos un diccionario vacío para los datos
    d = {"nombre": "", "cedula": "", "ficha": "", "radicado": "", "nis": "", "email": "", "tel": ""}

    # --- LÓGICA DE BÚSQUEDA (REGEX) ---
    # Nombre: Busca "Nombre Persona" (PQRS) o "Nombres"+"Apellidos" (Oficina Virtual)
    if "Nombre Persona" in texto:
        res = re.search(r"Nombre Persona\s*\n+(.*)", texto)
        if res: d["nombre"] = res.group(1).strip().upper()
    else:
        n = re.search(r"Nombres\s*\n+(.*)", texto)
        a = re.search(r"Apellidos\s*\n+(.*)", texto)
        if n and a: d["nombre"] = f"{n.group(1).strip()} {a.group(1).strip()}".upper()

    # Radicado y NIS (Busca números con guiones)
    rad = re.search(r"Radicado\s*\n?([\d-]+)", texto)
    if rad: d["radicado"] = rad.group(1).strip()
    
    nis = re.search(r"NIS\s*\n?([\d-]+)", texto)
    if nis: d["nis"] = nis.group(1).strip()

    # Cédula e Identificación
    ced = re.search(r"(?:Identificación|Identificacion)\s*\n?(\d+)", texto)
    if ced: d["cedula"] = ced.group(1).strip()

    # Ficha de curso
    fic = re.search(r"Ficha\s*\n?(\d+)", texto)
    if fic: d["ficha"] = fic.group(1).strip()

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
    st.header("📄 Procesamiento de Formularios SENA")

    # --- PASO 1: INICIALIZAR VARIABLES (Para evitar el AttributeError) ---
    if 'v_form' not in st.session_state:
        st.session_state.v_form = 0 # Aquí es donde nace la variable para que no dé error
    if 'data_ocr' not in st.session_state:
        st.session_state.data_ocr = {}
    if 'archivo_id' not in st.session_state:
        st.session_state.archivo_id = None

    # --- PASO 2: CARGADOR DE ARCHIVOS ---
    v = st.session_state.v_form # Ahora sí puedes usar 'v' porque ya existe arriba
    archivo = st.file_uploader("Subir Formulario", type=["tif", "png", "jpg"], key=f"u_{v}")

    if archivo:
        # Detectar si el archivo es nuevo
        if st.session_state.archivo_id != archivo.name:
            with st.spinner("🤖 IA extrayendo datos..."):
                img = Image.open(archivo)
                # Llamas a tu función de extracción multiformato
                st.session_state.data_ocr = extraer_datos_multiformato(img) 
                st.session_state.archivo_id = archivo.name
                st.rerun() # Refresca para que los datos caigan en las casillas

        # --- PASO 3: FORMULARIO ---
        d = st.session_state.data_ocr
        
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre Aprendiz", value=d.get("nombre", ""), key=f"n_{v}")
            ced = st.text_input("Cédula", value=d.get("cedula", ""), key=f"c_{v}")
            fic = st.text_input("Ficha", value=d.get("ficha", ""), key=f"f_{v}")
        with col2:
            rad = st.text_input("Radicado", value=d.get("radicado", ""), key=f"r_{v}")
            nis = st.text_input("NIS", value=d.get("nis", ""), key=f"i_{v}")
            prog = st.text_input("Programa", key=f"p_{v}")

        # --- PASO 4: BOTÓN GUARDAR Y LIMPIAR ---
        if st.button("💾 GUARDAR Y LIMPIAR TODO"):
            # Lógica para guardar en tu CSV (Recuerda definir periodo_actual)
            nuevo = {"nombre": nom, "cedula": ced, "ficha": fic, "radicado": rad, "periodo": periodo_actual}
            pd.DataFrame([nuevo]).to_csv(ARCHIVO_DATOS, mode='a', header=not os.path.exists(ARCHIVO_DATOS), index=False, encoding='utf-8-sig')
            
            st.success("✅ Datos guardados correctamente.")
            
            # LIMPIEZA TOTAL
            st.session_state.v_form += 1 # Al cambiar la versión, las casillas quedan vacías
            st.session_state.data_ocr = {}
            st.session_state.archivo_id = None
            st.rerun()

        d = st.session_state.get("data_ocr", {})
        v = st.session_state.v_form

        # --- FORMULARIO AUTOMÁTICO ---
        # Aquí es donde la magia ocurre: los 'value' se llenan con lo que leyó la IA
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre Aprendiz", value=d.get("nombre", ""), key=f"n_{v}")
            ced = st.text_input("Cédula", value=d.get("cedula", ""), key=f"c_{v}")
            fic = st.text_input("Ficha", value=d.get("ficha", ""), key=f"f_{v}")
        with col2:
            rad = st.text_input("Radicado", value=d.get("radicado", ""), key=f"r_{v}")
            nis = st.text_input("NIS", value=d.get("nis", ""), key=f"i_{v}")
            prog = st.text_input("Programa de Formación", key=f"p_{v}")

        # --- BOTÓN GUARDAR ---
        if st.button("💾 GUARDAR Y LIMPIAR TODO"):
            # Lógica para guardar en tu base de datos CSV
            nuevo = {"nombre": nom, "cedula": ced, "ficha": fic, "radicado": rad, "periodo": periodo_actual}
            pd.DataFrame([nuevo]).to_csv(ARCHIVO_DATOS, mode='a', header=not os.path.exists(ARCHIVO_DATOS), index=False, encoding='utf-8-sig')
            
            st.success("✅ Datos guardados en la base de datos.")
            st.session_state.v_form += 1 # Esto limpia el formulario para el siguiente aprendiz
            st.session_state.data_ocr = {}
            st.session_state.id_archivo = None
            st.rerun()
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



















