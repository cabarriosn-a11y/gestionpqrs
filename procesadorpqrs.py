import streamlit as st
from PIL import Image
import re
from PIL import Image
import io
import datetime
import pandas as pd
import os
import google.generativeai as genai
from google.cloud import documentai  # Esta es la nueva

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
def extraer_con_document_ai(archivo_bytes):
    try:
        client = documentai.DocumentProcessorServiceClient.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        proyecto_id = st.secrets["gcp_service_account"]["project_id"]
        procesador_id = "24ff861fd38e6fa5"
        name = f"projects/{proyecto_id}/locations/us/processors/{procesador_id}"

        raw_document = documentai.RawDocument(content=archivo_bytes, mime_type="image/tiff")
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        
        result = client.process_document(request=request)
        document = result.document

        datos = {"nombre": "", "cedula": "", "ficha": "", "radicado": "", "nis": ""}

        for page in document.pages:
            for field in page.form_fields:
                k = field.field_name.text_anchor.content.strip().replace("\n", " ")
                v = field.field_value.text_anchor.content.strip().replace("\n", " ")

                # Mapeo para tus PQRS
                i# --- REGLAS SEGÚN TUS 2 FORMATOS ---

                # 1. Nombres y Apellidos
                # Filtramos para que no tome 'Nombre del centro' o 'Nombre de la empresa'
                if "nombre" in k or "aprendiz" in k:
                    if not any(excluir in k for excluir in ["centro", "municipio", "empresa", "programa", "instructor"]):
                        datos["nombre"] = v.upper()

                # 2. Número de Documento
                if any(x in k for x in ["cédula", "identificación", "cc", "documento", "nº id"]):
                    datos["cedula"] = v

                # 3. Radicado (Clave en tus PQRS)
                if "radicado" in k or "no. radicado" in k:
                    datos["radicado"] = v

                # 4. NIS
                if "nis" in k or "n.i.s" in k:
                    datos["nis"] = v

                # 5. Ficha
                if "ficha" in k or "no. ficha" in k or "código" in k:
                    # A veces la ficha viene pegada al programa, extraemos solo números si es necesario
                    datos["ficha"] = v

                # 6. Programa de Formación
                if "programa" in k or "formación" in k:
                    if "nombre" in k or "denominación" in k:
                        datos["programa"] = v
        return datos
    except Exception as e:
        st.error(f"Error con Google: {e}")
        return {}

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
# --- 1. Subida del archivo ---
archivo = st.file_uploader("Subir Formulario", type=["tif", "png", "jpg"])

if archivo:
    # 2. PROCESAMIENTO (Solo si no lo hemos hecho ya para este archivo)
    if "archivo_actual" not in st.session_state or st.session_state.archivo_actual != archivo.name:
        with st.spinner("🤖 Analizando con Google Document AI..."):
            img_bytes = archivo.getvalue()
            datos = extraer_con_document_ai(img_bytes)
            
            if datos:
                st.session_state.data_ocr = datos
                st.session_state.archivo_actual = archivo.name
            else:
                st.error("No se pudieron extraer datos. Revisa la conexión.")

    # 3. MOSTRAR CASILLAS (Solo si ya tenemos datos en memoria)
    if "data_ocr" in st.session_state:
        d = st.session_state.data_ocr
        
        st.markdown("### 📋 Datos Extraídos")
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Nombre Aprendiz", value=d.get("nombre", ""))
            cedula = st.text_input("Cédula", value=d.get("cedula", ""))
            ficha = st.text_input("Ficha", value=d.get("ficha", ""))
            
        with col2:
            radicado = st.text_input("Número de Radicado", value=d.get("radicado", ""))
            nis = st.text_input("N.I.S", value=d.get("nis", ""))
            programa = st.text_input("Programa de Formación")

        if st.button("💾 Guardar Registro"):
            # Aquí pones tu lógica de guardar en Excel
            st.success(f"Registro de {nombre} guardado.")
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




























