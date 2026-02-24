import streamlit as st
from PIL import Image
import re
import io
import datetime
import pandas as pd
import os
import google.generativeai as genai
from groq import Groq
from docxtpl import DocxTemplate

# ==========================================
# ⚙️ CONFIGURACIÓN Y RECURSOS
# ==========================================
VERSION = "1.5.0"
ARCHIVO_DATOS = "registro_pqrs.csv"

# Configuración de Motores (Google y Groq)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
if "GROQ_API_KEY" not in st.secrets:
    st.sidebar.warning("⚠️ Falta GROQ_API_KEY en Secrets para respaldo.")

def redactar_con_ia(prompt_usuario):
    # INTENTO 1: GEMINI 2.0 (El favorito)
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        ctx = "Eres un experto administrativo del SENA. Redacta una respuesta formal y cordial. Caso: "
        response = model.generate_content(ctx + prompt_usuario)
        return response.text
    except Exception as e:
        # INTENTO 2: SI GEMINI FALLA (CUOTA 429), USAR GROQ (LLAMA 3.3)
        if "429" in str(e) and "GROQ_API_KEY" in st.secrets:
            try:
                st.warning("🔄 Gemini saturado. Activando motor de respaldo Groq...")
                client_groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
                res = client_groq.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Eres un EXPERTO administrativo del SENA Regional Guajira. Redacta una respuesta formal y cordial. Caso:"},
                        {"role": "user", "content": prompt_usuario}
                    ],
                )
                return res.choices[0].message.content
            except Exception as e_groq:
                return f"❌ Error en ambos motores: {e_groq}"
        return f"❌ Error de cuota en Google: {e}. (Configura Groq para evitar esto)"

# --- INTERFAZ ---
st.set_page_config(page_title="SENA PQRS Pro", layout="wide")
hoy = datetime.datetime.now()
nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_actual = nombres_meses[hoy.month - 1]
acta_num = hoy.month
with st.sidebar:
    # Cargar y mostrar el logo
    try:
        imagen_logo = Image.open("logo.png")
        st.image(imagen_logo, use_container_width=True)
    except:
        st.error("No se encontró el archivo logo.png")
    
    
with st.sidebar:
    st.title("SENA - Centro Industrial y de Energias Alternativas")
    menu = st.radio("MENÚ", ["1. Procesador de PQRS (Retiro Voluntario)", "2. Redactor IA", "3. Acta de Cierre"])

# ==========================================
# OPCIÓN 1: PROCESADOR INDIVIDUAL
# ==========================================
if menu == "1. Procesador de PQRS (Retiro Voluntario)":
    st.title("📄 Generador de PQRS Individual")
    
    st.markdown("### ✍️ Datos del Aprendiz")
    col1, col2, col3 = st.columns(3)
    with col1:
        nom = st.text_input("Nombres y Apellidos")
        doc = st.text_input("Número de Documento")
        rad = st.text_input("Número de Radicado")
        direccion = st.text_input("Dirección de Residencia")
    with col2:
        nis = st.text_input("NIS")
        fic = st.text_input("Ficha")
        pro = st.text_input("Programa de Formación")
        proyecta = st.text_input("Proyecta:", value="Merlis Marbello")  # Valor por defecto
    with col3:
        correo = st.text_input("Correo Electrónico")
        tel = st.text_input("Teléfono")
        st.info(f"Acta: {acta_num} | Mes: {mes_actual}")
        copia_a = st.text_input("Copiar a:", value="Doralba Cardona") # Valor por defecto
        anexo = st.text_input("Anexos:", placeholder="Ej: Certificado médico, fotocopia cédula...")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Guardar en Base de Datos"):
            if nom and doc:
                nuevo = pd.DataFrame([{"nombre": nom.upper(), "cedula": doc, "radicado": rad, "nis": nis, "ficha": fic, "programa": pro.upper(),"direccion": direccion, "copia_a":copia_a, "anexo": anexo, "proyecta": proyecta, "correo": correo, "telefono": tel, "acta": acta_num, "mes": mes_actual}])
                if not os.path.exists(ARCHIVO_DATOS):
                    nuevo.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
                else:
                    nuevo.to_csv(ARCHIVO_DATOS, mode='a', header=False, index=False, encoding='utf-8-sig')
                st.success(f"✅ {nom} guardado.")
            else: st.warning("Faltan datos.")

    with c2:
        try:
            doc_tpl = DocxTemplate("Plantilla_PQRS.docx")
            doc_tpl.render({"nombre": nom, "cedula": doc, "radicado": rad, "nis": nis,"proyecta": proyecta, "ficha": fic, "programa": pro, "correo": correo, "direccion": direccion, "copia_a": copia_a, "anexo": anexo,"telefono": tel, "acta": acta_num, "mes": mes_actual})
            buf = io.BytesIO(); doc_tpl.save(buf); buf.seek(0)
            st.download_button("📥 Descargar Word Individual", buf, f"PQRS_{doc}.docx")
        except Exception as e: st.error(f"Error plantilla: {e}")

# ==========================================
# OPCIÓN 2: REDACTOR INTELIGENTE IA (CON TODAS LAS CASILLAS)
# ==========================================
if menu == "2. Redactor IA":
    st.title("🤖 Redactor Inteligente (Doble Motor)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        nom_ia = st.text_input("Nombre Completo", key="ia_nom")
        doc_ia = st.text_input("Documento", key="ia_doc")
        rad_ia = st.text_input("Radicado No.", key="ia_rad")
        direccion_ia = st.text_input("Dirección", key="ia_dir") # Nueva
    with col2:
        nis_ia = st.text_input("NIS", key="ia_nis")
        fic_ia = st.text_input("Ficha", key="ia_fic")
        pro_ia = st.text_input("Programa", key="ia_pro")
        proyecta_ia = st.text_input("proyecta:", value="Merlys Marbello") #valor por defecto
    with col3:
        correo_ia = st.text_input("Correo", key="ia_mail")
        tel_ia = st.text_input("Teléfono", key="ia_tel")
        copia_a_ia = st.text_input("Copiar a:", value="Doralba Cardona") # Valor por defecto
        anexo_ia = st.text_input("Anexos:", placeholder="Ej: Certificado médico, fotocopia cédula...")

    instruccion = st.text_area("¿Qué debe decir la respuesta?")

    if st.button("✨ Generar con IA"):
        if instruccion:
            with st.spinner("Redactando..."):
                prompt = f"Aprendiz: {nom_ia}. Caso: {instruccion}"
                st.session_state['texto_ia'] = redactar_con_ia(prompt)
        else: st.warning("Escribe una instrucción.")

    if 'texto_ia' in st.session_state:
        st.markdown("---")
        cuerpo_editado = st.text_area("Texto final:", value=st.session_state['texto_ia'], height=250)
        
        if st.button("📥 Descargar Word con IA"):
            try:
                # Etiquetas en MAYÚSCULAS para la plantilla Genérica
                ctx_ia = {
                    "NOMBRE": nom_ia.upper(), "CEDULA": doc_ia, "RADICADO": rad_ia,
                    "NIS": nis_ia, "FICHA": fic_ia, "PROGRAMA": pro_ia.upper(), "direccion": direccion_ia, "copia_a": copia_a_ia, "anexo": anexo_ia, "proyecta": proyecta_ia,
                    "CORREO": correo_ia, "TELEFONO": tel_ia, "CUERPO": cuerpo_editado
                }
                doc_gen = DocxTemplate("Plantilla_Generica_IA.docx")
                doc_gen.render(ctx_ia)
                buf_ia = io.BytesIO(); doc_gen.save(buf_ia); buf_ia.seek(0)
                st.download_button("Descargar Documento", buf_ia, f"Respuesta_{doc_ia}.docx")
            except Exception as e: st.error(f"Error: {e}")

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















