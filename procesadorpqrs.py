import streamlit as st
from PIL import Image
import re
import io
import datetime
import pandas as pd
import os
import google.generativeai as genai
from google.cloud import documentai
from docxtpl import DocxTemplate

# ==========================================
# ⚙️ CONFIGURACIÓN FINAL - SENA GUAJIRA
# ==========================================
VERSION = "1.2.2"
CENTRO = "Centro Industrial y de Energías Alternativas"
REGIONAL = "Regional Guajira"
ARCHIVO_DATOS = "registro_pqrs.csv"

# Configuración de Gemini desde Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.error("❌ Falta GEMINI_API_KEY en Secrets.")

# --- FUNCIONES DE INTELIGENCIA ---
def redactar_con_ia(prompt_usuario):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash') 
        contexto = (
            "Eres un experto administrativo del SENA Regional Guajira. "
            "Redacta una respuesta formal, cordial y técnica. "
            "La situación a responder es: "
        )
        response = model.generate_content(contexto + prompt_usuario)
        return response.text
    except Exception as e:
        return f"Error con la IA: {e}"

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title=f"SENA Guajira v{VERSION}", layout="wide")

with st.sidebar:
    if os.path.exists("logo.png"): 
        st.image("logo.png", width=120)
    st.title("SENA - Riohacha")
    menu = st.radio("MENÚ PRINCIPAL", [
        "1. Retiros Voluntarios (Base de Datos)", 
        "2. Redactor Inteligente IA (Temas Varios)", 
        "3. Acta de Cierre Mensual"
    ])
    st.markdown("---")
    st.caption(f"v{VERSION} | {REGIONAL}\n{CENTRO}")

# Configuración de tiempo para el sistema
hoy = datetime.datetime.now()
nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_actual = nombres_meses[hoy.month - 1]
acta_num = hoy.month

ctx = {
    "DIA": hoy.day, 
    "MES": mes_actual.upper(), 
    "ANHO": hoy.year, 
    "ACTA": acta_num
}

# ==========================================
# OPCIÓN 1: RETIROS (PROCESADOR PQRS)
# ==========================================
if menu == "1. Retiros Voluntarios (Base de Datos)":
    st.title("📄 Generador de PQRS - SENA")
    st.info(f"📅 Periodo Actual: **{mes_actual}** | Acta Correspondiente: **{acta_num}**")

    # --- 1. CASILLAS PARA DIGITAR ---
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

    # --- 2. LÓGICA DE GENERACIÓN DEL WORD ---
    contexto = {
        "nombre": nom, "cedula": doc, "radicado": rad,
        "nis": nis, "ficha": fic, "programa": pro,
        "correo": correo, "telefono": tel, "acta": acta_num, "mes": mes_actual
    }

    st.markdown("---")

    try:
        # Se asume que el archivo tiene este nombre exacto en tu repo
        doc_tpl = DocxTemplate("Plantilla_PQRS.docx") 
        doc_tpl.render(contexto)

        buffer = io.BytesIO()
        doc_tpl.save(buffer)
        buffer.seek(0)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                label="📥 Descargar Formato Word",
                data=buffer,
                file_name=f"PQRS_{doc}_Acta_{acta_num}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        with c2:
            if st.button("💾 Registrar en Base de Datos"):
                if nom and doc:
                    # Aquí es donde integrarás tu lógica de Google Sheets después
                    st.cache_data.clear()
                    st.success(f"✅ ¡Datos de {nom} listos para el registro!")
                else:
                    st.warning("Por favor, ingrese Nombre y Documento.")

    except Exception as e:
        st.error(f"⚠️ Error: No se pudo encontrar 'Plantilla_PQRS.docx' o falta la librería docxtpl.")

# ==========================================
# OPCIÓN 2: REDACTOR IA
# ==========================================
elif menu == "2. Redactor Inteligente IA (Temas Varios)":
    st.header("🤖 Asistente de Redacción Gemini")
    st.warning("Esta sección usa 'Plantilla_Generica_IA.docx' y no guarda en la base de datos.")
    
    col_ia1, col_ia2 = st.columns(2)
    with col_ia1:
        nom_ia = st.text_input("Nombre")
        ced_ia = st.text_input("Identificación")
    with col_ia2:
        rad_ia = st.text_input("Radicado")
        prog_ia = st.text_input("Programa")

    st.markdown("### 📝 Instrucción de Redacción")
    prompt = st.text_area("Explica la situación", "Informa que el certificado está en proceso.")
    
    if st.button("✨ GENERAR TEXTO CON IA"):
        with st.spinner("Gemini redactando..."):
            st.session_state['cuerpo_ia'] = redactar_con_ia(f"Aprendiz: {nom_ia}. Situación: {prompt}")

    if 'cuerpo_ia' in st.session_state:
        cuerpo_final = st.text_area("Edita la redacción:", value=st.session_state['cuerpo_ia'], height=250)
        if st.button("🖨️ GENERAR WORD GENÉRICO"):
            try:
                doc_gen = DocxTemplate("Plantilla_Generica_IA.docx")
                doc_gen.render({**ctx, "NOMBRE": nom_ia.upper(), "CEDULA": ced_ia, "RADICADO": rad_ia, "PROGRAMA": prog_ia.upper(), "CUERPO": cuerpo_final})
                b = io.BytesIO(); doc_gen.save(b)
                st.download_button("📥 Descargar Documento IA", b.getvalue(), f"Respuesta_IA_{ced_ia}.docx")
            except Exception as e:
                st.error(f"Error al generar Word genérico: {e}")

# ==========================================
# OPCIÓN 3: ACTA MENSUAL
# ==========================================
else:
    st.header(f"📊 Acta de Retiros - {mes_actual}")
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS, on_bad_lines='skip', sep=',', engine='python', encoding='utf-8-sig')
        st.table(df)
        
        with st.expander("🗑️ Borrar un registro específico"):
            registro_a_eliminar = st.selectbox("Selecciona el aprendiz:", options=df.index,
                format_func=lambda x: f"{df.loc[x, 'nombre']} | Cédula: {df.loc[x, 'cedula']}")

            if st.button("❌ ELIMINAR REGISTRO", key="btn_borrar_registro"):
                try:
                    df_total = pd.read_csv(ARCHIVO_DATOS, on_bad_lines='skip', engine='python', encoding='utf-8-sig')
                    df_total = df_total.drop(registro_a_eliminar)
                    df_total.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
                    st.success("Registro eliminado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo eliminar: {e}")

        if st.button("📝 GENERAR ACTA AUTOMÁTICA", key="btn_acta_auto"):
            try:
                doc_acta = DocxTemplate("Plantilla_Acta_Mensual.docx")
                subdoc = doc_acta.new_subdoc()
                tabla = subdoc.add_table(rows=1, cols=6)
                tabla.style = 'Table Grid'
                
                titulos = ['Nombre', 'Identificación', 'Ficha', 'Programa', 'Novedad', 'Radicado']
                for i, texto in enumerate(titulos):
                    tabla.rows[0].cells[i].text = texto
                
                for _, fila in df.iterrows():
                    celdas = tabla.add_row().cells
                    celdas[0].text = str(fila.get('nombre', ''))
                    celdas[1].text = str(fila.get('cedula', ''))
                    celdas[2].text = str(fila.get('ficha', ''))
                    celdas[3].text = str(fila.get('programa', ''))
                    celdas[4].text = "Retiro Voluntario"
                    celdas[5].text = str(fila.get('radicado', ''))
                
                doc_acta.render({**ctx, "TABLA_RETIROS": subdoc})
                b_acta = io.BytesIO(); doc_acta.save(b_acta)
                st.download_button("📥 Descargar Acta", b_acta.getvalue(), f"Acta_{ctx['MES']}.docx")
            except Exception as e:
                st.error(f"Error técnico: {e}")
    else:
        st.info("No hay base de datos local aún.")

