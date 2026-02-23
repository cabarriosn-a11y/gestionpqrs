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

import streamlit as st
from docxtpl import DocxTemplate
import io

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.title("📄 Generador de PQRS - SENA")
st.markdown("Complete los campos para generar el documento oficial.")

# --- 1. LÓGICA AUTOMÁTICA DEL ACTA POR MES ---
meses_lista = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

col_mes, col_vacia = st.columns([1, 2])
with col_mes:
    mes = st.selectbox("Seleccione el Mes de la PQRS", meses_lista)
    # El número de acta es la posición en la lista + 1
    acta_num = meses_lista.index(mes) + 1
    st.info(f"📅 Acta Número: **{acta_num}**")

# --- 2. CASILLAS PARA DIGITAR (9 CAMPOS) ---
st.markdown("### ✍️ Datos del Aprendiz / Solicitante")
col1, col2, col3 = st.columns(3)

with col1:
    nom = st.text_input("Nombres y Apellidos")
    doc = st.text_input("Número de Documento")
    rad = st.text_input("Número de Radicado")

with col2:
    nis = st.text_input("NIS")
    fic = st.text_input("Ficha")
    pro = st.text_input("Programa de Formación")

with col3:
    correo = st.text_input("Correo Electrónico")
    tel = st.text_input("Teléfono de Contacto")
    st.text_input("Número de Acta (Auto)", value=acta_num, disabled=True)

# --- 3. PROCESAMIENTO DEL WORD ---
# Preparamos los datos para la plantilla
contexto = {
    "nombre": nom,
    "cedula": doc,
    "radicado": rad,
    "nis": nis,
    "ficha": fic,
    "programa": pro,
    "correo": correo,
    "telefono": tel,
    "acta": acta_num,
    "mes": mes
}

st.markdown("---")

try:
    # Cargamos tu plantilla oficial
    doc_tpl = DocxTemplate("Plantilla_PQRS.docx") 
    doc_tpl.render(contexto)

    # Creamos el archivo en memoria
    buffer = io.BytesIO()
    doc_tpl.save(buffer)
    buffer.seek(0)

    # Botones de acción
    c1, c2 = st.columns(2)
    
    with c1:
        st.download_button(
            label="📥 Generar y Descargar Word",
            data=buffer,
            file_name=f"PQRS_{doc}_Acta_{acta_num}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    with c2:
        if st.button("💾 Registrar en Base de Datos"):
            if nom and doc:
                st.success(f"¡Datos de {nom} listos para el Acta {acta_num}!")
            else:
                st.warning("Por favor, ingrese al menos Nombre y Documento.")

except Exception as e:
    st.error(f"⚠️ Error: No se pudo encontrar el archivo 'Plantilla_PQRS.docx' en la carpeta.")

# --- 4. HISTORIAL (Solo si no es Retiro Voluntario) ---
# Si tienes la variable 'menu' definida en tu sidebar, úsala aquí:
if 'menu' in locals() and menu != "RETIROS VOLUNTARIOS":
    st.markdown("---")
    st.subheader("📊 Historial de Registros")
    # Aquí puedes poner tu tabla de datos
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
  # --- 1. CONFIGURACIÓN DE FECHA Y ACTA AUTOMÁTICA ---
        # (Esto detecta el mes real hoy: febrero = Acta 2)
        nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        fecha_actual = datetime.now()
        mes_actual = nombres_meses[fecha_actual.month - 1]
        acta_num = fecha_actual.month

        st.markdown(f"### 📋 Generación de Acta: {mes_actual} (No. {acta_num})")

        # --- 2. CASILLAS VACÍAS PARA DIGITAR (9 CAMPOS) ---
        col1, col2, col3 = st.columns(3)

        with col1:
            nom = st.text_input("Nombres y Apellidos")
            doc = st.text_input("Número de Documento")
            rad = st.text_input("Número de Radicado")

        with col2:
            nis = st.text_input("NIS")
            fic = st.text_input("Ficha")
            pro = st.text_input("Programa de Formación")

        with col3:
            correo = st.text_input("Correo Electrónico")
            tel = st.text_input("Teléfono de Contacto")
            # El acta se muestra automática y no se deja editar
            st.text_input("Número de Acta", value=acta_num, disabled=True)

        # --- 3. LÓGICA DE GENERACIÓN DEL WORD ---
        contexto = {
            "nombre": nom,
            "cedula": doc,
            "radicado": rad,
            "nis": nis,
            "ficha": fic,
            "programa": pro,
            "correo": correo,
            "telefono": tel,
            "acta": acta_num,
            "mes": mes_actual
        }

        try:
            # IMPORTANTE: El nombre del archivo debe ser exacto
            doc_tpl = DocxTemplate("Plantilla.PQRS..docx") 
            doc_tpl.render(contexto)

            buffer = io.BytesIO()
            doc_tpl.save(buffer)
            buffer.seek(0)

            st.markdown("---")
            c1, c2 = st.columns(2)
            
            with c1:
                st.download_button(
                    label="📥 Descargar Formato Word",
                    data=buffer,
                    file_name=f"PQRS_{doc}_Acta_{acta_num}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
            with c2:
                if st.button("💾 Finalizar y Guardar"):
                    # Aquí es donde se limpia el cache para que la tabla de Google se actualice
                    st.cache_data.clear() 
                    st.success(f"✅ ¡Datos de {nom} preparados para el registro!")

        except Exception as e:
            st.error(f"⚠️ No se pudo procesar el Word: {e}")
# --- FIN DE LA SECCIÓN 1 ---
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















































