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
VERSION = "1.3.0"
CENTRO = "Centro Industrial y de Energías Alternativas"
REGIONAL = "Regional Guajira"
ARCHIVO_DATOS = "registro_pqrs.csv"

# Configuración de Gemini desde Secrets de Streamlit
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.error("❌ Falta GEMINI_API_KEY en Secrets.")

# --- FUNCIONES DE INTELIGENCIA ---

def redactar_con_ia(prompt_usuario):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash') 
        contexto = (
            "Eres un experto administrativo del SENA Regional Guajira. "
            "Redacta una respuesta formal, cordial y técnica. "
            "La situación a responder es: "
        )
        response = model.generate_content(contexto + prompt_usuario)
        return response.text
    except Exception as e:
        return f"Error con Gemini 2.5: {e}."

@st.cache_data(show_spinner=False)
def extraer_datos(_img):
    texto = pytesseract.image_to_string(_img, lang='eng')
    d = {"nombre": "", "cedula": "", "ficha": "", "programa": "", "radicado": "", "nis": "", "correo": "", "telefono": ""}
    
    m_rad = re.search(r'(\d-\d{4}-\d+)', texto); d["radicado"] = m_rad.group(1) if m_rad else ""
    m_nis = re.search(r'(\d{4}-\d{2}-\d+)', texto); d["nis"] = m_nis.group(1) if m_nis else ""
    m_cor = re.search(r'([a-zA-Z0-9._%+-]+\s?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto)
    if m_cor: d["correo"] = m_cor.group(1).replace(" ", "").upper()
    m_ced = re.search(r'(?:Identificaci|Documento|No\.\s*de)[^\d]*(\d{7,10})', texto, re.IGNORECASE)
    if m_ced: d["cedula"] = m_ced.group(1)

    lineas = [l.strip() for l in texto.split('\n') if len(l.strip()) > 2]
    n_ov, a_ov = "", ""
    for i, l in enumerate(lineas):
        if "Nombres" == l.strip() and i+1 < len(lineas): n_ov = lineas[i+1]
        if "Apellidos" == l.strip() and i+1 < len(lineas): a_ov = lineas[i+1]
        if "Nombre Persona" in l and i+1 < len(lineas): d["nombre"] = lineas[i+1]
    if n_ov and a_ov: d["nombre"] = f"{n_ov} {a_ov}"
    
    d["nombre"] = re.sub(r'SAN\s*ANTONIO|BARRIO|MUNICIPIO|MIRANDA|CAUCA|CORREO|TELEFONO', '', d["nombre"], flags=re.IGNORECASE).strip()
    d["nombre"] = re.sub(r'[^a-zA-Z\s]', '', d["nombre"]).strip()

    m_fic = re.search(r'(?:Ficha|Curso)\s*\D*(\d{7,10})', texto, re.IGNORECASE)
    d["ficha"] = m_fic.group(1) if m_fic else ""
    
    return d

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title=f"SENA Guajira v{VERSION}", layout="wide")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=120)
    st.title("SENA - Riohacha")
    menu = st.radio("MENÚ PRINCIPAL", [
        "1. Retiros Voluntarios (Registro)", 
        "2. Redactor Inteligente IA", 
        "3. Acta de Cierre Mensual",
        "4. 📚 Histórico General"
    ])
    st.markdown("---")
    st.caption(f"v{VERSION} | {REGIONAL}\n{CENTRO}")

hoy = datetime.datetime.now()
meses = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]
periodo_actual = f"{meses[hoy.month-1]} {hoy.year}"
ctx = {"DIA": hoy.day, "MES": meses[hoy.month-1], "ANHO": hoy.year, "ACTA": hoy.month}

# ==========================================
# OPCIÓN 1: RETIROS (Ahora con etiqueta de periodo)
# ==========================================
if menu == "1. Retiros Voluntarios (Registro)":
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
            # El periodo se asigna automáticamente
            periodo = periodo_actual 

        c1, c2 = st.columns(2)
        if c1.button("💾 GUARDAR EN LISTA"):
            nuevo = pd.DataFrame([{
                "nombre": nom.upper(), 
                "cedula": ced, 
                "ficha": fic, 
                "programa": prog.upper(), 
                "radicado": rad, 
                "novedad": "Retiro Voluntario",
                "periodo": periodo # <--- NUEVO: Guarda el mes y año
            }])
            nuevo.to_csv(ARCHIVO_DATOS, mode='a', header=not os.path.exists(ARCHIVO_DATOS), index=False, encoding='utf-8-sig')
            st.success(f"✅ Guardado en el historial de {periodo}")
        
        if c2.button("🖨️ GENERAR CARTA DE RETIRO"):
            doc = DocxTemplate("Plantilla_PQRS.docx")
            doc.render({**ctx, "NOMBRE": nom, "CEDULA": ced, "FICHA": fic, "PROGRAMA": prog, "RADICADO": rad, "CUERPO": "Se tramita retiro voluntario según solicitud oficial."})
            b = io.BytesIO(); doc.save(b); st.download_button("📥 Descargar Carta", b.getvalue(), f"Retiro_{ced}.docx")

# ==========================================
# OPCIÓN 2: REDACTOR IA (Se mantiene igual)
# ==========================================
elif menu == "2. Redactor Inteligente IA":
    st.header("🤖 Asistente de Redacción Gemini")
    prompt = st.text_area("Explica la situación para redactar:", "Informa que el certificado está en proceso de firma.")
    if st.button("✨ GENERAR TEXTO"):
        with st.spinner("Redactando..."):
            res = redactar_con_ia(prompt)
            st.write(res)

# ==========================================
# OPCIÓN 3: ACTA MENSUAL (Con Borrado Individual)
# ==========================================
elif menu == "3. Acta de Cierre Mensual":
    st.header(f"📊 Generación de Acta - {periodo_actual}")
    
    if os.path.exists(ARCHIVO_DATOS):
        try:
            # --- CARGA ROBUSTA PARA EVITAR EL PARSERERROR ---
            df_full = pd.read_csv(
                ARCHIVO_DATOS, 
                on_bad_lines='skip', 
                engine='python', 
                encoding='utf-8-sig'
            )
            
            # Filtramos solo lo del mes actual para el acta
            # Aseguramos que la columna 'periodo' exista para evitar errores
            if 'periodo' in df_full.columns:
                df_mes = df_full[df_full['periodo'] == periodo_actual]
            else:
                st.error("No se encontró la columna 'periodo' en la base de datos.")
                df_mes = pd.DataFrame()

            if not df_mes.empty:
                # --- BORRADO INDIVIDUAL ---
                with st.expander("🗑️ Corregir error (Borrar un registro específico)"):
                    registro_idx = st.selectbox(
                        "Selecciona para eliminar:", 
                        options=df_mes.index, 
                        format_func=lambda x: f"{df_mes.loc[x, 'nombre']} - {df_mes.loc[x, 'cedula']}"
                    )
                    
                    if st.button("❌ Eliminar este registro"):
                        df_full = df_full.drop(registro_idx)
                        df_full.to_csv(ARCHIVO_DATOS, index=False, encoding='utf-8-sig')
                        st.success("Registro eliminado correctamente.")
                        st.rerun()

                # Mostrar tabla de datos del mes
                st.table(df_mes)
                
                # --- GENERACIÓN DE WORD (DOCX) ---
                if st.button("📝 GENERAR ACTA AUTOMÁTICA (SUBDOC)"):
                    try:
                        from docxtpl import DocxTemplate
                        
                        # Carga de plantilla
                        doc = DocxTemplate("Plantilla_Acta_Mensual.docx")
                        subdoc = doc.new_subdoc()
                        
                        # Construcción de la tabla en el subdocumento
                        tabla = subdoc.add_table(rows=1, cols=6)
                        tabla.style = 'Table Grid'
                        
                        titulos = ['Nombre', 'Identificación', 'Ficha', 'Programa', 'Novedad', 'Radicado']
                        for i, t in enumerate(titulos):
                            tabla.rows[0].cells[i].text = t
                        
                        for _, fila in df_mes.iterrows():
                            c = tabla.add_row().cells
                            c[0].text = str(fila.get('nombre', ''))
                            c[1].text = str(fila.get('cedula', ''))
                            c[2].text = str(fila.get('ficha', ''))
                            c[3].text = str(fila.get('programa', ''))
                            c[4].text = "Retiro Voluntario" # O el campo que definas
                            c[5].text = str(fila.get('radicado', ''))
                        
                        # Renderizado del documento con el contexto
                        # Asegúrate que 'ctx' esté definido previamente en tu código
                        contexto_final = {**ctx, "TABLA_RETIROS": subdoc}
                        doc.render(contexto_final)
                        
                        # Preparar descarga
                        b = io.BytesIO()
                        doc.save(b)
                        st.download_button(
                            label="📥 Descargar Acta de Cierre", 
                            data=b.getvalue(), 
                            file_name=f"Acta_Cierre_{periodo_actual}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                        st.success("¡Acta generada con éxito!")

                    except FileNotFoundError:
                        st.error("No se encontró el archivo 'Plantilla_Acta_Mensual.docx'. Por favor súbelo al servidor.")
                    except Exception as e:
                        st.error(f"Error al generar el Word: {e}")
            else:
                st.warning(f"No hay registros guardados para {periodo_actual}")

        except Exception as e:
            st.error(f"Error crítico al leer los datos: {e}")
            st.info("Sugerencia: Abre el archivo CSV en Excel, verifica que no haya filas extrañas y guárdalo nuevamente.")
    else:
        st.info("Aún no existe base de datos de registros.")

# ==========================================
# OPCIÓN 4: HISTÓRICO GENERAL (Nuevo Menú)
# ==========================================
else:
    st.header("📚 Consulta de Históricos por Mes")
    if os.path.exists(ARCHIVO_DATOS):
        df_hist = pd.read_csv(ARCHIVO_DATOS)
        lista_periodos = df_hist['periodo'].unique()
        
        sel_periodo = st.selectbox("Selecciona el mes a consultar:", lista_periodos)
        df_filtrado = df_hist[df_hist['periodo'] == sel_periodo]
        
        st.subheader(f"Registros encontrados: {len(df_filtrado)}")
        st.dataframe(df_filtrado)
        
        csv = df_filtrado.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar Excel (CSV) de este mes", csv, f"Historico_{sel_periodo}.csv")
    else:
        st.info("No hay registros históricos todavía.")

