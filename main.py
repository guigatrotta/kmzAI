import pandas as pd
import time
import simplekml
import googlemaps
import os
import streamlit as st
from zipfile import ZipFile
from xml.etree import ElementTree as ET


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# Chave da API do Google Maps fornecida
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
if not GOOGLE_API_KEY:
    st.error("Erro: variável de ambiente 'GOOGLE_API_KEY' não está definida.")
    st.stop()

def geocode_address_google(endereco, bairro):
    try:
        full_address = f"{endereco}, {bairro}, Curitiba, Paraná, Brasil"
        result = gmaps.geocode(full_address)
        if result:
            location = result[0]['geometry']['location']
            return location['lat'], location['lng']
    except Exception as e:
        st.warning(f"Erro ao geocodificar '{endereco}': {e}")
    return None, None

def gerar_kmz(df, caminho_saida):
    kml = simplekml.Kml()
    ignorados = []

    for _, row in df.iterrows():
        endereco = row['Endereco']
        bairro = row['Bairro']
        valor = row.get('Valor', '')
        area = row.get('Area', '')
        zoneamento = row.get('Zoneamento', '')
        link = row.get('Link', '')

        lat, lon = geocode_address_google(endereco, bairro)
        time.sleep(1)

        if lat and lon:
            valor_formatado = f"R$ {int(valor):,}".replace(",", ".") if pd.notna(valor) and str(valor).isdigit() else valor
            desc = f"Bairro: {bairro}<br>Valor: {valor_formatado}<br>Área: {area} m²<br>Zoneamento: {zoneamento}"
            if pd.notna(link) and str(link).startswith("http"):
                desc += f"<br><a href=\"{link}\">Ver imóvel</a>"
            p = kml.newpoint(name=endereco, coords=[(lon, lat)])
            p.description = desc
        else:
            ignorados.append(endereco)

    kml.save(caminho_saida)
    return ignorados

def combinar_kmz(lista_kmz, nome_saida):
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    doc_final = ET.Element('kml', xmlns=ns['kml'])
    doc_main = ET.SubElement(doc_final, 'Document')

    for kmz_file in lista_kmz:
        with ZipFile(kmz_file, 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith('.kml'):
                    zip_ref.extract(file, 'tmp_kml')
                    tree = ET.parse(f'tmp_kml/{file}')
                    root = tree.getroot()
                    for placemark in root.findall('.//kml:Placemark', ns):
                        doc_main.append(placemark)

    tree_final = ET.ElementTree(doc_final)
    tree_final.write("combinado.kml", encoding="utf-8", xml_declaration=True)
    with ZipFile(nome_saida, 'w') as kmz:
        kmz.write("combinado.kml")
    os.remove("combinado.kml")

def main():
    st.title("Gerador e Combinador de KMZ - Guia Amarela")

    st.header("1. Gerar KMZ de imóveis a partir de planilha")
    arquivo = st.file_uploader("Envie a planilha de imóveis combinados (.xlsx):", type=["xlsx"])

    if arquivo is not None:
        df = pd.read_excel(arquivo)
        nome_base = os.path.splitext(arquivo.name)[0]
        caminho_saida = f"{nome_base}_terrenos.kmz"

        if st.button("Extrair KMZ combinado dos terrenos"):
            with st.spinner("Gerando KMZ e consultando coordenadas via Google Maps..."):
                ignorados = gerar_kmz(df, caminho_saida)

            st.success("KMZ gerado com sucesso!")
            with open(caminho_saida, "rb") as f:
                st.download_button("Baixar KMZ", data=f, file_name=caminho_saida)

            if ignorados:
                st.warning("Alguns endereços não puderam ser geocodificados:")
                for i in ignorados:
                    st.text(f"- {i}")

    st.markdown("---")
    st.header("2. Combinar múltiplos arquivos KMZ em um só")
    arquivos_kmz = st.file_uploader("Envie os arquivos .kmz para combinar:", type=["kmz"], accept_multiple_files=True)

    if arquivos_kmz and st.button("Combinar KMZs"):
        nomes_temp = []
        for arq in arquivos_kmz:
            caminho_temp = f"temp_{arq.name}"
            with open(caminho_temp, "wb") as f:
                f.write(arq.read())
            nomes_temp.append(caminho_temp)

        nome_saida = "kmz_combinado_final.kmz"
        combinar_kmz(nomes_temp, nome_saida)

        st.success("KMZ combinado gerado com sucesso!")
        with open(nome_saida, "rb") as f:
            st.download_button("Baixar KMZ Combinado", data=f, file_name=nome_saida)

        for arq in nomes_temp:
            os.remove(arq)

if __name__ == "__main__":
    main()
