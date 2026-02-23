import streamlit as st
from PIL import Image
import re
import io
import datetime
import pandas as pd
import os
import google.generativeai as genai
from docxtpl import DocxTemplate

# ==========================================
# ⚙️ CONFIGURACIÓN Y RECURSOS
# ==========================================
VERSION = "1.4.0"
ARCHIVO_DATOS = "registro_pqrs.csv"

# Configuración de Gemini - USANDO EL MODELO MÁS RECIENTE
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.error("❌ Falta GEMINI_API_KEY en Secrets.")

def redactar_con_ia(prompt_usuario):
    try:
        # LLAMADA AL ÚLTIMO MODELO GEMINI 2.0 FLASH
        model = genai.GenerativeModel('gemini-2.0-flash') 
        contexto = "Eres un experto administrativo del SENA. Redacta una respuesta formal, técnica y cordial. Caso: "
        response = model.generate_content(contexto + prompt_usuario)
        return response.text
    except Exception as e:
        # Si el modelo 2.0 no está disponible en tu región/cuenta, intenta con 1.5 como respaldo automático
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt_usuario)
            return response.text
        except:
            return f"Error de conexión con la IA: {e}"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title=f"SENA Guajira v{VERSION}", layout="wide")

# --- LÓGICA DE TIEMPO ---
hoy = datetime.datetime.now()
nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_actual = nombres_meses[hoy.month - 1]
acta_num = hoy.month

# --- SIDEBAR ---
with st.sidebar:
    st.title("SENA - Riohacha")
    menu = st.radio("MENÚ PRINCIPAL", [
        "1. Procesador de PQRS (Individual)", 
        "2. Redactor Inteligente IA", 
        "3. Acta de Cierre Mensual (Tabla)"
    ])
    st.markdown("---")
    st.caption(f"v{VERSION} | Regional Guajira")

# ==========================================
# OPCIÓN 1: PROCESADOR INDIVIDUAL
# ==========================================
if menu == "1. Procesador de PQRS (Individual)":
    st.title("📄 Generador de PQRS Individual")
    
    st.markdown("### ✍️ Datos del Aprendiz")
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
        tel = st.text_input("Teléfono")
        st.info(f"Acta: {acta_num} | Mes: {mes_actual}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Guardar en Base de Datos"):
            if nom and doc:
                nuevo = pd.DataFrame([{"nombre": nom.upper(), "cedula": doc, "radicado": rad, "nis": nis, "ficha": fic, "programa": pro.upper(), "correo": correo, "telefono": tel, "acta": acta_num, "mes": mes_actual}])
                if not os.path.exists(ARCHIVO_DATOS):
                    nuevo.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
                else:
                    nuevo.to_csv(ARCHIVO_DATOS, mode='a', header=False, index=False, encoding='utf-8-sig')
                st.success(f"✅ {nom} guardado.")
            else: st.warning("Faltan datos.")

    with c2:
        try:
            doc_tpl = DocxTemplate("Plantilla_PQRS.docx")
            doc_tpl.render({"nombre": nom, "cedula": doc, "radicado": rad, "nis": nis, "ficha": fic, "programa": pro, "correo": correo, "telefono": tel, "acta": acta_num, "mes": mes_actual})
            buf = io.BytesIO(); doc_tpl.save(buf); buf.seek(0)
            st.download_button("📥 Descargar Word Individual", buf, f"PQRS_{doc}.docx")
        except Exception as e: st.error(f"Error plantilla: {e}")

# ==========================================
# OPCIÓN 2: REDACTOR INTELIGENTE IA (CON TODAS LAS CASILLAS)
# ==========================================
elif menu == "2. Redactor Inteligente IA":
    st.title("🤖 Redactor con Gemini 2.0 Flash")
    
    st.markdown("### 📋 Datos para la Plantilla")
    col1, col2, col3 = st.columns(3)
    with col1:
        nom_ia = st.text_input("Nombre Completo", key="ia_nom")
        doc_ia = st.text_input("Documento", key="ia_doc")
        rad_ia = st.text_input("Radicado No.", key="ia_rad")
    with col2:
        nis_ia = st.text_input("NIS", key="ia_nis")
        fic_ia = st.text_input("Ficha", key="ia_fic")
        pro_ia = st.text_input("Programa", key="ia_pro")
    with col3:
        correo_ia = st.text_input("Correo", key="ia_mail")
        tel_ia = st.text_input("Teléfono", key="ia_tel")

    st.markdown("### 📝 Instrucción para la IA")
    instruccion = st.text_area("¿Qué debe decir la respuesta?", placeholder="Ej: Negar retiro por falta de documentos...")

    if st.button("✨ Generar con Gemini 2.0"):
        if instruccion:
            with st.spinner("IA redactando..."):
                prompt_final = f"Aprendiz: {nom_ia}. Caso: {instruccion}"
                st.session_state['texto_ia'] = redactar_con_ia(prompt_final)
        else: st.warning("Escribe una instrucción.")

    if 'texto_ia' in st.session_state:
        st.markdown("---")
        cuerpo_editado = st.text_area("Revisión del texto:", value=st.session_state['texto_ia'], height=250)
        
        try:
            contexto_ia = {
                "NOMBRE": nom_ia.upper(), "CEDULA": doc_ia, "RADICADO": rad_ia,
                "NIS": nis_ia, "FICHA": fic_ia, "PROGRAMA": pro_ia.upper(),
                "CORREO": correo_ia, "TELEFONO": tel_ia, "CUERPO": cuerpo_editado
            }
            doc_gen = DocxTemplate("Plantilla_Generica_IA.docx")
            doc_gen.render(contexto_ia)
            buf_ia = io.BytesIO(); doc_gen.save(buf_ia); buf_ia.seek(0)
            st.download_button("📥 Descargar Respuesta IA", buf_ia, f"Respuesta_{doc_ia}.docx")
        except Exception as e: st.error(f"Error Word: {e}")

# ==========================================
# OPCIÓN 3: TABLA Y ACTA DE CIERRE
# ==========================================
else:
    st.header(f"📊 Historial Acta No. {acta_num}")
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS)
        st.dataframe(df, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            with st.expander("🗑️ Borrar registro"):
                idx = st.selectbox("Seleccionar:", options=df.index, format_func=lambda x: f"{df.loc[x, 'nombre']}")
                if st.button("❌ Eliminar"):
                    df = df.drop(idx)
                    df.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
                    st.rerun()

        with col_b:
            if st.button("📝 GENERAR ACTA MENSUAL"):
                try:
                    doc_m = DocxTemplate("Plantilla_Acta_Mensual.docx")
                    sub = doc_m.new_subdoc()
                    tbl = sub.add_table(rows=1, cols=6); tbl.style = 'Table Grid'
                    for i, t in enumerate(['Nombre', 'ID', 'Ficha', 'Programa', 'Novedad', 'Radicado']):
                        tbl.rows[0].cells[i].text = t
                    for _, f in df.iterrows():
                        row = tbl.add_row().cells
                        row[0].text, row[1].text, row[2].text = str(f['nombre']), str(f['cedula']), str(f['ficha'])
                        row[3].text, row[4].text, row[5].text = str(f['programa']), "Retiro Voluntario", str(f['radicado'])
                    
                    doc_m.render({"DIA": hoy.day, "MES": mes_actual, "ANHO": hoy.year, "ACTA": acta_num, "TABLA_RETIROS": sub})
                    b_m = io.BytesIO(); doc_m.save(b_m); b_m.seek(0)
                    st.download_button("📥 Descargar Acta Cierre", b_m, f"Acta_{mes_actual}.docx")
                except Exception as e: st.error(f"Error: {e}")
    else: st.info("Sin registros.")
