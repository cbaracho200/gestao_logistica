import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import base64
import io
from datetime import datetime
import xmltodict
import json
import numpy as np
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
import os
import random
import string
from groq import Groq
import os


st.set_page_config(page_title="Logístic GPT-App", page_icon="🔎",layout="wide", initial_sidebar_state="expanded")

GROQ_API_KEY= st.secrets["GROQ_API_KEY"]
st.title("Logístic GPT-App")
st.divider()
client = Groq(api_key=GROQ_API_KEY)


with st.sidebar:
    st.logo("https://w7.pngwing.com/pngs/683/780/png-transparent-emotional-intelligence-knowledge-artificial-intelligence-concept-technology-blue-electronics-flower-thumbnail.png")
    st.caption("🧠 Sistema de Inteligência")

# Constantes atualizadas
DB_FILE = "tracking_db.json"

STATUS_OPTIONS = [
    "No Navio de Origem",
    "Desembarcando",
    "Embarcando",
    "Em caminho ao destino",
    "Entregue"
]

class TrackingSystem:
    def __init__(self):
        self.db_file = DB_FILE
        self.db = {}
        self.load_database()

    def load_database(self):
        try:
            if os.path.exists(self.db_file) and os.path.getsize(self.db_file) > 0:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self.db = json.load(f)
            else:
                self.db = {}
                self.save_database()
        except Exception as e:
            st.error(f"Erro ao carregar banco de dados: {str(e)}")
            self.db = {}

    def save_database(self):
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.db, f, ensure_ascii=False, indent=4)
        except Exception as e:
            st.error(f"Erro ao salvar banco de dados: {str(e)}")

    def get_all_trackings(self):
        """Retorna todos os rastreamentos ordenados por data"""
        try:
            sorted_trackings = sorted(
                self.db.items(),
                key=lambda x: x[1]['created_at'],
                reverse=True
            )
            return sorted_trackings
        except Exception as e:
            st.error(f"Erro ao recuperar rastreamentos: {str(e)}")
            return []

    def add_tracking(self, cte_data, shipping_info):
        """Adiciona um novo registro com informações de transporte"""
        try:
            tracking_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            tracking_data = {
                "tracking_number": tracking_number,
                "cte_data": cte_data,
                "status": "No Navio de Origem",
                "shipping_info": shipping_info,
                "history": [{
                    "status": "No Navio de Origem",
                    "timestamp": timestamp,
                    "comment": "Registro inicial"
                }],
                "created_at": timestamp,
                "updated_at": timestamp
            }
            
            self.db[tracking_number] = tracking_data
            self.save_database()
            return tracking_number
        except Exception as e:
            st.error(f"Erro ao adicionar rastreamento: {str(e)}")
            return None



    def update_tracking(self, tracking_number, new_status, comment=""):
        """Atualiza o status de um rastreamento"""
        if tracking_number in self.db:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.db[tracking_number]["status"] = new_status
            self.db[tracking_number]["updated_at"] = timestamp
            self.db[tracking_number]["history"].append({
                "status": new_status,
                "timestamp": timestamp,
                "comment": comment
            })
            self.save_database()
            return True
        return False

    def delete_tracking(self, tracking_number):
        """Remove um registro de rastreamento"""
        if tracking_number in self.db:
            del self.db[tracking_number]
            self.save_database()
            return True
        return False

    def get_tracking(self, tracking_number):
        """Recupera informações de um rastreamento"""
        return self.db.get(tracking_number)

    def search_tracking(self, search_term):
        """Pesquisa registros de rastreamento"""
        results = {}
        search_term = search_term.lower()
        for tracking_number, data in self.db.items():
            # Busca em vários campos
            if (search_term in tracking_number.lower() or
                search_term in str(data['cte_data']).lower() or
                search_term in data['status'].lower()):
                results[tracking_number] = data
        return results

def show_sidebar_tracking_list():
    """Exibe lista de rastreamentos no sidebar"""
    st.sidebar.header("Rastreamentos Ativos")
    
    tracking_system = st.session_state.get('tracking_system')
    if not tracking_system:
        return
    
    trackings = tracking_system.get_all_trackings()
    
    if trackings:
        for tracking_number, data in trackings:
            with st.sidebar.expander(f"CT-e: {data['cte_data'].get('Numero_CTe', 'N/A')}"):
                st.write(f"**Status:** {data.get('status', 'N/A')}")
                
                # Verifica se existem informações de shipping
                shipping_info = data.get('shipping_info', {})
                if shipping_info:
                    st.write(f"**Balsa:** {shipping_info.get('vessel_name', 'N/A')}")
                    st.write(f"**Origem:** {shipping_info.get('origin', 'N/A')}")
                    st.write(f"**Destino:** {shipping_info.get('destination', 'N/A')}")
                    st.write(f"**Data Prevista:** {shipping_info.get('expected_date', 'N/A')}")
                else:
                    st.write("*Informações de transporte não disponíveis*")
    else:
        st.sidebar.info("Nenhum rastreamento cadastrado")

def extract_cte_data(xml_content):
    """Extrai dados específicos do CT-e"""
    try:
        data = xmltodict.parse(xml_content)
        cte = data['cteProc']['CTe']
        info = cte['infCte']
        
        basic_info = {
            'Chave_CTe': info['@Id'].replace('CTe', ''),
            'Numero_CTe': info['ide']['nCT'],
            'Serie': info['ide']['serie'],
            'Data_Emissao': info['ide']['dhEmi'],
            'CFOP': info['ide']['CFOP'],
            'Natureza_Operacao': info['ide']['natOp'],
            'Modal': info['ide']['modal'],
            'Tipo_Servico': info['ide']['tpServ'],
            'Municipio_Origem': info['ide']['xMunIni'],
            'UF_Origem': info['ide']['UFIni'],
            'Municipio_Destino': info['ide']['xMunFim'],
            'UF_Destino': info['ide']['UFFim']
        }
        
        emit_info = {
            'Emitente_CNPJ': info['emit']['CNPJ'],
            'Emitente_Nome': info['emit']['xNome'],
            'Emitente_IE': info['emit']['IE']
        }
        
        rem_info = {
            'Remetente_CNPJ': info['rem']['CNPJ'],
            'Remetente_Nome': info['rem']['xNome'],
            'Remetente_IE': info['rem']['IE']
        }
        
        dest_info = {
            'Destinatario_CNPJ': info['dest']['CNPJ'],
            'Destinatario_Nome': info['dest']['xNome'],
            'Destinatario_IE': info['dest']['IE']
        }
        
        values_info = {
            'Valor_Total': info['vPrest']['vTPrest'],
            'Valor_Receber': info['vPrest']['vRec']
        }
        
        if 'infCTeNorm' in info and 'infCarga' in info['infCTeNorm']:
            carga_info = {
                'Valor_Carga': info['infCTeNorm']['infCarga']['vCarga'],
                'Produto_Predominante': info['infCTeNorm']['infCarga']['proPred']
            }
        else:
            carga_info = {}

        # Extrair informações do container se disponível
        container_info = {}
        if 'infDoc' in info.get('infCTeNorm', {}):
            infDoc = info['infCTeNorm']['infDoc']
            if 'infNFe' in infDoc:
                for nfe in (infDoc['infNFe'] if isinstance(infDoc['infNFe'], list) else [infDoc['infNFe']]):
                    if 'infUnidTransp' in nfe and 'infUnidCarga' in nfe['infUnidTransp']:
                        container_info = {
                            'Container_ID': nfe['infUnidTransp']['infUnidCarga'].get('idUnidCarga', ''),
                            'Lacre': nfe['infUnidTransp']['infUnidCarga'].get('lacUnidCarga', {}).get('nLacre', '')
                        }
                        break

        cte_data = {**basic_info, **emit_info, **rem_info, **dest_info, 
                   **values_info, **carga_info, **container_info}
        
        return pd.DataFrame([cte_data])
    
    except Exception as e:
        st.error(f"Erro ao processar XML: {str(e)}")
        return None

def main():
    st.title('Sistema de Rastreamento de Containers')
    
    # Inicializa o sistema de rastreamento
    if 'tracking_system' not in st.session_state:
        st.session_state.tracking_system = TrackingSystem()
    
    # Mostra lista de rastreamentos no sidebar
    show_sidebar_tracking_list()
    
    # Menu principal com key única
    menu = ["Processar CT-e", "Gerenciar Rastreamentos"]
    choice = st.sidebar.selectbox(
        "Escolha a operação",
        menu,
        key="main_menu_select"
    )
    
    if choice == "Processar CT-e":
        st.subheader("Upload e Processamento de CT-e")
        uploaded_file = st.file_uploader(
            "Escolha o arquivo XML do CT-e",
            type=['xml'],
            key="xml_uploader"
        )
        
        if uploaded_file is not None:
            try:
                xml_content = uploaded_file.read().decode('utf-8')
                df = extract_cte_data(xml_content)
                
                if df is not None:
                    st.write("Dados extraídos do CT-e:")
                    st.dataframe(df, key="cte_data_preview")
                    
                    # Formulário para informações de transporte
                    st.subheader("Informações de Transporte Marítimo")
                    with st.form(key="shipping_info_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            vessel_name = st.text_input(
                                "Nome da Balsa/Navio",
                                key="vessel_name_input"
                            )
                            origin = st.text_input(
                                "Porto de Origem",
                                key="origin_input"
                            )
                        with col2:
                            destination = st.text_input(
                                "Porto de Destino",
                                key="destination_input"
                            )
                            expected_date = st.date_input(
                                "Data Prevista de Chegada",
                                key="expected_date_input"
                            )
                        
                        shipping_info = {
                            "vessel_name": vessel_name,
                            "origin": origin,
                            "destination": destination,
                            "expected_date": expected_date.strftime("%Y-%m-%d")
                        }
                        
                        submit_button = st.form_submit_button("Gerar Rastreamento")
                        
                        if submit_button:
                            if not vessel_name or not origin or not destination:
                                st.error("Por favor, preencha todos os campos obrigatórios.")
                            else:
                                tracking_number = st.session_state.tracking_system.add_tracking(
                                    df.to_dict('records')[0],
                                    shipping_info
                                )
                                if tracking_number:
                                    st.success(f"Rastreamento gerado com sucesso! Número: {tracking_number}")
                                    st.rerun()
            
            except Exception as e:
                st.error(f"Erro ao processar arquivo: {str(e)}")
                st.write("Detalhes do erro:", str(e))
    
    elif choice == "Gerenciar Rastreamentos":
        st.subheader("Gerenciamento de Rastreamentos")
        
        search_term = st.text_input(
            "Buscar rastreamento",
            key="search_tracking_input"
        )
        
        if search_term:
            results = st.session_state.tracking_system.search_tracking(search_term)
            if results:
                for tracking_number, data in results.items():
                    with st.expander(f"Rastreamento: {tracking_number}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Informações do CT-e**")
                            st.json(data.get('cte_data', {}))
                        
                        with col2:
                            st.write("**Informações de Transporte**")
                            st.json(data.get('shipping_info', {}))
                        
                        st.write("**Status Atual:**", data.get('status', 'N/A'))
                        new_status = st.selectbox(
                            "Atualizar Status",
                            STATUS_OPTIONS,
                            key=f"status_select_{tracking_number}"  # Key única para cada tracking
                        )
                        
                        comment = st.text_area(
                            "Comentário",
                            key=f"comment_area_{tracking_number}"  # Key única para cada tracking
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(
                                "Atualizar",
                                key=f"update_button_{tracking_number}"  # Key única para cada tracking
                            ):
                                if st.session_state.tracking_system.update_tracking(
                                    tracking_number, new_status, comment
                                ):
                                    st.success("Atualizado com sucesso!")
                                    st.rerun()
                        
                        with col2:
                            if st.button(
                                "Excluir",
                                key=f"delete_button_{tracking_number}"  # Key única para cada tracking
                            ):
                                if st.session_state.tracking_system.delete_tracking(tracking_number):
                                    st.success("Excluído com sucesso!")
                                    st.rerun()
                        
                        if 'history' in data:
                            st.write("**Histórico:**")
                            history_df = pd.DataFrame(data['history'])
                            st.dataframe(
                                history_df,
                                key=f"history_df_{tracking_number}"  # Key única para cada tracking
                            )
            else:
                st.warning("Nenhum resultado encontrado.")

if __name__ == '__main__':
    main()
