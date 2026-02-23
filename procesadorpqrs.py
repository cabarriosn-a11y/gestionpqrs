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
VERSION = "1.3.1"
ARCHIVO_DATOS = "registro_pqrs.csv"

# Configuración de Gemini
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.error("❌ Falta GEMINI_API_KEY en Secrets.")

# Función de IA
def redactar_con_ia(prompt_usuario):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash') 
        contexto = "Redacta una respuesta formal administrativa para el SENA Regional Guajira sobre: "
        response = model.generate_content(contexto + prompt_usuario)
        return response.text
    except Exception as e:
        return f"Error con la IA: {e}"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title=f"SENA Guajira v{VERSION}", layout="wide")

# --- LÓGICA DE TIEMPO ---
hoy = datetime.datetime.now()
nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
mes_actual = nombres_meses[hoy.month - 1]
acta_num = hoy.month

# --- SIDEBAR / MENÚ ---
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
    st.info(f"📅 Sistema: **{mes_actual}** | Acta No. **{acta_num}**")

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
        st.text_input("Acta", value=acta_num, disabled=True)

    if st.button("💾 Finalizar y Guardar en Tabla"):
        if nom and doc:
            nuevo_registro = pd.DataFrame([{
                "nombre": nom.upper(), "cedula": doc, "radicado": rad,
                "nis": nis, "ficha": fic, "programa": pro.upper(),
                "correo": correo, "telefono": tel, "acta": acta_num, "mes": mes_actual
            }])
            if not os.path.exists(ARCHIVO_DATOS):
                nuevo_registro.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
            else:
                nuevo_registro.to_csv(ARCHIVO_DATOS, mode='a', header=False, index=False, encoding='utf-8-sig')
            st.success(f"✅ ¡{nom} registrado en la base de datos!")
        else:
            st.warning("⚠️ Escribe al menos Nombre y Cédula para guardar.")

    st.markdown("---")
    if st.button("📥 Generar Documento Word Individual"):
        try:
            contexto = {
                "nombre": nom, "cedula": doc, "radicado": rad, "nis": nis, 
                "ficha": fic, "programa": pro, "correo": correo, 
                "telefono": tel, "acta": acta_num, "mes": mes_actual
            }
            doc_tpl = DocxTemplate("Plantilla_PQRS.docx")
            doc_tpl.render(contexto)
            buf = io.BytesIO(); doc_tpl.save(buf); buf.seek(0)
            st.download_button("Click aquí para descargar PQRS", buf, f"PQRS_{doc}.docx")
        except Exception as e:
            st.error(f"Error con Plantilla_PQRS.docx: {e}")

# ==========================================
# OPCIÓN 2: REDACTOR IA
# ==========================================
elif menu == "2. Redactor Inteligente IA":
    st.title("🤖 Redactor con Inteligencia Artificial")
    st.markdown("Complete los datos del aprendiz y describa la situación para generar la respuesta.")

    col1, col2, col3 = st.columns(3)
    with col1:
        nom_ia = st.text_input("Nombres y Apellidos", key="ia_nom")
        doc_ia = st.text_input("Número de Documento", key="ia_doc")
        rad_ia = st.text_input("Número de Radicado", key="ia_rad")
    with col2:
        nis_ia = st.text_input("NIS", key="ia_nis")
        fic_ia = st.text_input("Ficha", key="ia_fic")
        pro_ia = st.text_input("Programa de Formación", key="ia_pro")
    with col3:
        correo_ia = st.text_input("Correo Electrónico", key="ia_mail")
        tel_ia = st.text_input("Teléfono", key="ia_tel")
        st.info(f"Mes: {mes_actual}")

    st.markdown("### 📝 Instrucción para la IA")
    instruccion = st.text_area("Describa qué debe decir la carta:", 
                               placeholder="Ejemplo: Informar al aprendiz que su solicitud de traslado fue negada por falta de cupos en el centro receptor.")

    if st.button("✨ Generar Respuesta con IA"):
        if instruccion:
            with st.spinner("La IA está redactando la respuesta formal..."):
                prompt_final = f"Aprendiz: {nom_ia}. Programa: {pro_ia}. Caso: {instruccion}"
                st.session_state['texto_ia'] = redactar_con_ia(prompt_final)
        else:
            st.warning("Por favor, describa la situación antes de generar.")

    if 'texto_ia' in st.session_state:
        st.markdown("---")
        st.subheader("🖋️ Respuesta Generada (Editable)")
        cuerpo_editado = st.text_area("Puede corregir el texto aquí antes de descargar:", 
                                     value=st.session_state['texto_ia'], height=300)
        
        try:
            # Diccionario para Plantilla_Generica_IA.docx
            # Nota: Se usan las etiquetas exactas de tu archivo
            contexto_ia = {
                "NOMBRE": nom_ia.upper(),
                "CEDULA": doc_ia,
                "RADICADO": rad_ia,
                "NIS": nis_ia,
                "FICHA": fic_ia,
                "PROGRAMA": pro_ia.upper(),
                "CORREO": correo_ia,
                "TELEFONO": tel_ia,
                "CUERPO": cuerpo_editado
            }
            
            doc_gen = DocxTemplate("Plantilla_Generica_IA.docx")
            doc_gen.render(contexto_ia)
            
            buf_ia = io.BytesIO()
            doc_gen.save(buf_ia)
            buf_ia.seek(0)
            
            st.download_button(
                label="📥 Descargar Documento IA (Word)",
                data=buf_ia,
                file_name=f"Respuesta_IA_{doc_ia}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error al generar el Word de IA: {e}")
# ==========================================
# OPCIÓN 3: ACTA DE CIERRE (TABLA)
# ==========================================
else:
    st.header(f"📊 Historial de Registros - Acta No. {acta_num}")
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS)
        st.dataframe(df, use_container_width=True)

        col_a, col_b = st.columns(2)
        
        with col_a:
            with st.expander("🗑️ Borrar un registro"):
                idx_borrar = st.selectbox("Selecciona aprendiz para eliminar:", options=df.index,
                                          format_func=lambda x: f"{df.loc[x, 'nombre']} ({df.loc[x, 'cedula']})")
                if st.button("❌ Confirmar Borrado"):
                    df = df.drop(idx_borrar)
                    df.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
                    st.rerun()

        with col_b:
            if st.button("📝 GENERAR ACTA DE CIERRE (WORD)"):
                try:
                    doc_m = DocxTemplate("Plantilla_Acta_Mensual.docx")
                    sub = doc_m.new_subdoc()
                    tbl = sub.add_table(rows=1, cols=6); tbl.style = 'Table Grid'
                    
                    titulos = ['Nombre', 'Identificación', 'Ficha', 'Programa', 'Novedad', 'Radicado']
                    for i, t in enumerate(titulos):
                        tbl.rows[0].cells[i].text = t
                    
                    for _, f in df.iterrows():
                        row = tbl.add_row().cells
                        row[0].text = str(f.get('nombre',''))
                        row[1].text = str(f.get('cedula',''))
                        row[2].text = str(f.get('ficha',''))
                        row[3].text = str(f.get('programa',''))
                        row[4].text = "Retiro Voluntario"
                        row[5].text = str(f.get('radicado',''))
                    
                    # Etiquetas según tu Plantilla_Acta_Mensual.docx
                    doc_m.render({"DIA": hoy.day, "MES": mes_actual, "ANHO": hoy.year, "ACTA": acta_num, "TABLA_RETIROS": sub})
                    b_m = io.BytesIO(); doc_m.save(b_m)
                    st.download_button("📥 Descargar Acta Completa", b_m.getvalue(), f"Acta_Cierre_{mes_actual}.docx")
                except Exception as e: st.error(f"Error al procesar acta: {e}")
    else:
        st.info("Aún no hay registros en la base de datos local.")

