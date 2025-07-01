import os
from flask import Flask, json, request, jsonify, abort
import requests
from data import config
from datetime import date, timedelta
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse # Importação adicionada
import datetime
import json
import re

# --- Configurações Iniciais ---
account_sid = os.environ.get('TWILIO_ACCOUNT_SID', 'x')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN', 'x')
client = Client(account_sid, auth_token)

app = Flask(__name__)

# --- Armazenamento de Estado da Conversa (ATENÇÃO: Volátil!) ---
# Para um sistema real, use um banco de dados (ex: Redis) para persistir o estado.
# Este dicionário armazenará o estado da conversa para cada número de telefone.
conversation_states = {} # { 'whatsapp:+55119XXXXXXXX': {'state': 'menu', 'data': {}}, ... }


# --- FUNÇÕES API WHATSAPP ---

@app.route('/TOTAL-IP-case/message', methods=['POST'])
def get_message():
    """
    Recebe mensagens POST do webhook do Twilio (WhatsApp).
    Processa a mensagem e direciona para a lógica do bot.
    """
    incoming_message_body = request.form.get('Body')
    sender_phone = request.form.get('From')
    profile_name = request.form.get('ProfileName')

    print(f"Mensagem recebida de {profile_name} ({sender_phone}): {incoming_message_body}")

    # Inicializa a resposta TwiML.
    resp = MessagingResponse()

    # Processa a mensagem e obtém a resposta do bot.
    # Passamos a instância de 'resp' para a função de tratamento de mensagem.
    bot_response_text = handle_whatsapp_message(sender_phone, incoming_message_body, resp)

    return str(resp) # Retorna o XML TwiML para o Twilio.

def send_message(to_number, message_body):
    """
    Envia uma mensagem de texto via Twilio (WhatsApp).
    """
    try:
        message = client.messages.create(
            from_='whatsapp:+14155238886',
            body=message_body,
            to=to_number
        )
        print(f"Mensagem enviada para {to_number}. SID: {message.sid}")
        return message
    except Exception as e:
        print(f"Erro ao enviar mensagem para {to_number}: {e}")
        return None

def handle_whatsapp_message(sender_phone, message_body, twiml_response):
    """
    Função principal que gerencia o fluxo da conversa no WhatsApp.
    Usa 'conversation_states' para manter o contexto.
    """
    current_state = conversation_states.get(sender_phone, {'state': 'initial', 'data': {}})
    state = current_state['state']
    data = current_state['data']

    # Normaliza a mensagem para facilitar a comparação.
    message_body_lower = message_body.lower().strip()

    response_text = ""

    if state == 'initial':
        # Envia o menu principal e muda o estado.
        response_text = get_main_menu_text()
        conversation_states[sender_phone] = {'state': 'menu_awaiting_choice', 'data': {}}
    
    elif state == 'menu_awaiting_choice':
        if message_body_lower == '1':
            response_text = "Ótimo! Para agendar uma nova consulta, preciso de alguns dados. Por favor, digite o Nome do Paciente:"
            conversation_states[sender_phone] = {'state': 'create_appointment_patient_name', 'data': {'current_appointment': {}}}
        elif message_body_lower == '2':
            response_text = "Para alterar uma consulta existente, por favor, digite o CPF do paciente (apenas números):"
            conversation_states[sender_phone] = {'state': 'update_appointment_awaiting_cpf', 'data': {}}
        elif message_body_lower == '3':
            response_text = "Para listar agendamentos, por favor, digite o CPF do paciente (apenas números):"
            conversation_states[sender_phone] = {'state': 'list_appointments_awaiting_cpf', 'data': {}}
        elif message_body_lower == '4':
            response_text = "Saindo do sistema. Até mais!"
            conversation_states.pop(sender_phone, None) # Remove o estado da conversa.
        else:
            response_text = "Opção inválida. " + get_main_menu_text()
    
    # --- Fluxo de Criação de Agendamento ---
    elif state == 'create_appointment_patient_name':
        data['current_appointment']['PatientName'] = message_body
        response_text = "Agora, o Email do Paciente:"
        conversation_states[sender_phone]['state'] = 'create_appointment_email'
    
    elif state == 'create_appointment_email':
        if re.fullmatch(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", message_body):
            data['current_appointment']['Email'] = message_body
            response_text = "Telefone Celular (apenas números, ex: 5511987654321):"
            conversation_states[sender_phone]['state'] = 'create_appointment_mobile_phone'
        else:
            response_text = "Email inválido. Por favor, digite um email válido:"

    elif state == 'create_appointment_mobile_phone':
        if re.fullmatch(r"^\d+$", message_body):
            data['current_appointment']['MobilePhone'] = message_body
            response_text = "Outro telefone de contato (se não houver, digite 'nenhum'):"
            conversation_states[sender_phone]['state'] = 'create_appointment_other_phones'
        else:
            response_text = "Telefone inválido. Use apenas números:"
            
    elif state == 'create_appointment_other_phones':
        data['current_appointment']['OtherPhones'] = message_body if message_body_lower != 'nenhum' else None
        response_text = "Documento (apenas números, ex: CPF):"
        conversation_states[sender_phone]['state'] = 'create_appointment_document_id'

    elif state == 'create_appointment_document_id':
        if re.fullmatch(r"^\d+$", message_body):
            data['current_appointment']['OtherDocumentId'] = message_body
            response_text = "Razão do Agendamento:"
            conversation_states[sender_phone]['state'] = 'create_appointment_reason'
        else:
            response_text = "Documento inválido. Use apenas números:"
            
    elif state == 'create_appointment_reason':
        data['current_appointment']['ShedulingReason'] = message_body
        data['current_appointment']['NotesPatient'] = "" # Inicializa Notas do Paciente vazio.
        
        clinic_options = "\n--- Clínicas Disponíveis ---\n"
        if not config.business_list:
            clinic_options += "Nenhuma clínica disponível para seleção. Por favor, configure 'business_list' em data.py."
            # Voltar ao menu ou encerrar se não há clínicas
            response_text = clinic_options + "\nPor favor, digite 'menu' para voltar."
            conversation_states[sender_phone] = {'state': 'menu_awaiting_choice', 'data': {}}
        else:
            for business in config.business_list:
                clinic_options += f"{business.get('id')} - Nome: {business.get('BusinessName')}\n"
            response_text = clinic_options + "Digite o NÚMERO da Clínica desejada:"
            conversation_states[sender_phone]['state'] = 'create_appointment_clinic_id'
            conversation_states[sender_phone]['data']['clinic_list'] = config.business_list # Salva a lista para validação.

    elif state == 'create_appointment_clinic_id':
        if re.fullmatch(r"^\d+$", message_body):
            clinic_id = int(message_body)
            clinic_list = data.get('clinic_list', [])
            id_exists = any(business['id'] == clinic_id for business in clinic_list)
            
            if id_exists:
                data['current_appointment']['Clinic_BusinessId'] = clinic_id
                
                # Inicia a seleção de data.
                available_days = config.get_available_days_data
                if not available_days:
                    response_text = "Não há datas disponíveis para agendamento. Por favor, digite 'menu' para voltar."
                    conversation_states[sender_phone] = {'state': 'menu_awaiting_choice', 'data': {}}
                else:
                    date_options = "\n--- Datas Disponíveis para Agendamento ---\n"
                    for i, date_info in enumerate(available_days):
                        date_display = datetime.datetime.strptime(date_info["Date"], "%Y-%m-%d").strftime("%d-%m-%Y")
                        date_options += f"{i + 1}. {date_display} ({date_info['Week']})\n"
                    
                    response_text = date_options + "Digite o NÚMERO da data desejada:"
                    conversation_states[sender_phone]['state'] = 'create_appointment_date_selection'
                    conversation_states[sender_phone]['data']['available_days'] = available_days
            else:
                response_text = "ID inválido. Por favor, digite um ID que esteja na lista de clínicas disponíveis:"
        else:
            response_text = "Entrada inválida. Por favor, digite um NÚMERO para o ID da Clínica:"

    elif state == 'create_appointment_date_selection':
        available_days = data.get('available_days', [])
        if re.fullmatch(r"^\d+$", message_body):
            choice = int(message_body)
            if 1 <= choice <= len(available_days):
                selected_date_info = available_days[choice - 1]
                data['current_appointment']['Date_Info'] = selected_date_info # Armazena para uso posterior
                
                # Lista de horários disponíveis para a data.
                filtered_times = [t for t in selected_date_info["AvailableTimes"] if t["isSelectable"] and t["isAvailable"]]
                
                if not filtered_times:
                    response_text = "Não há horários disponíveis para esta data. Por favor, escolha outra data do menu ou digite 'menu' para voltar."
                    # Volta ao estado de seleção de data.
                    conversation_states[sender_phone]['state'] = 'create_appointment_date_selection'
                else:
                    time_options = f"\n--- Horários Disponíveis para {selected_date_info['Week']} ({selected_date_info['Date']}) ---\n"
                    for i, time_slot in enumerate(filtered_times):
                        time_options += f"{i + 1}. {time_slot['from']} - {time_slot['to']}\n"
                    
                    response_text = time_options + "Digite o NÚMERO do horário desejado:"
                    conversation_states[sender_phone]['state'] = 'create_appointment_time_selection'
                    conversation_states[sender_phone]['data']['filtered_times'] = filtered_times
            else:
                response_text = "Opção inválida. Por favor, escolha um número da lista de datas:"
        else:
            response_text = "Entrada inválida. Por favor, digite um número."

    elif state == 'create_appointment_time_selection':
        filtered_times = data.get('filtered_times', [])
        if re.fullmatch(r"^\d+$", message_body):
            time_choice = int(message_body)
            if 1 <= time_choice <= len(filtered_times):
                selected_time_info = filtered_times[time_choice - 1]
                data['current_appointment']['FromTime'] = selected_time_info['from']
                data['current_appointment']['ToTime'] = selected_time_info['to']
                
                # Continua a coleta de dados.
                response_text = "ID do Dentista/Profissional (apenas números):"
                conversation_states[sender_phone]['state'] = 'create_appointment_dentist_id'
            else:
                response_text = "Opção inválida. Por favor, escolha um número da lista de horários:"
        else:
            response_text = "Entrada inválida. Por favor, digite um número."

    elif state == 'create_appointment_dentist_id':
        if re.fullmatch(r"^\d+$", message_body):
            data['current_appointment']['Dentist_PersonId'] = int(message_body)
            response_text = "ID do Usuário Criador (apenas números):"
            conversation_states[sender_phone]['state'] = 'create_appointment_creator_id'
        else:
            response_text = "Entrada inválida. Digite um número:"

    elif state == 'create_appointment_creator_id':
        if re.fullmatch(r"^\d+$", message_body):
            data['current_appointment']['CreateUserId'] = int(message_body)
            response_text = "É Agendamento Online? (sim/não):"
            conversation_states[sender_phone]['state'] = 'create_appointment_is_online'
        else:
            response_text = "Entrada inválida. Digite um número:"
    
    elif state == 'create_appointment_is_online':
        if message_body_lower in ['sim', 'não']:
            data['current_appointment']['IsOnlineScheduling'] = (message_body_lower == 'sim')
            response_text = "Agendamento Aceito? (sim/não):"
            conversation_states[sender_phone]['state'] = 'create_appointment_is_accepted'
        else:
            response_text = "Entrada inválida. Digite 'sim' ou 'não':"

    elif state == 'create_appointment_is_accepted':
        if message_body_lower in ['sim', 'não']:
            data['current_appointment']['ShedulingAccepted'] = (message_body_lower == 'sim')
            
            # --- FINALIZAÇÃO DA CRIAÇÃO DE AGENDAMENTO ---
            final_appointment_data = data['current_appointment']
            
            # Formata os campos de data/hora para a API
            appointment_date_obj = datetime.datetime.strptime(final_appointment_data['Date_Info']["Date"], "%Y-%m-%d").date()
            final_appointment_data['AtomicDate'] = int(appointment_date_obj.strftime("%Y%m%d"))
            
            time_obj = datetime.datetime.strptime(final_appointment_data['FromTime'], "%H:%M").time()
            date_time_combined = datetime.datetime.combine(appointment_date_obj, time_obj)
            final_appointment_data['Date'] = date_time_combined.isoformat() + ".000Z"
            
            final_appointment_data['SK_DateFirstTime'] = int(appointment_date_obj.strftime("%Y%m%d") + final_appointment_data['FromTime'].replace(":", ""))
            
            # Remove a chave temporária 'Date_Info'
            final_appointment_data.pop('Date_Info', None) 
            
            # Campos padrão que podem ser adicionados
            final_appointment_data.setdefault('Id', None)
            final_appointment_data.setdefault('Type', "CLINICORP_INTEGRATION")
            final_appointment_data.setdefault('Deleted', None)

            # Envia para a API.
            success, api_response = _make_api_request('POST', '/patient/appointments/create_appointment_by_api', final_appointment_data)
            
            if success:
                response_text = "Agendamento criado com sucesso!\n"
                response_text += f"ID do Agendamento: {api_response['appointment'].get('Id')}\n"
                response_text += f"Paciente: {api_response['appointment'].get('PatientName')}\n"
                response_text += f"Data: {api_response['appointment'].get('Date', '').split('T')[0]}\n"
                response_text += f"Horário: {api_response['appointment'].get('FromTime')}\n"
            else:
                response_text = f"Falha ao criar agendamento: {api_response}"
            
            response_text += "\n" + get_main_menu_text()
            conversation_states[sender_phone] = {'state': 'menu_awaiting_choice', 'data': {}} # Volta ao menu.
        else:
            response_text = "Entrada inválida. Digite 'sim' ou 'não':"

    # --- Fluxo de Alteração de Agendamento ---
    elif state == 'update_appointment_awaiting_cpf':
        if re.fullmatch(r"^\d+$", message_body):
            cpf = message_body
            success, patient_appointments = _make_api_request('GET', f'/patient/appointments/{cpf}')
            
            if success and patient_appointments:
                data['patient_appointments'] = patient_appointments
                data['cpf'] = cpf
                
                appointments_list_text = "\n--- Seus Agendamentos Encontrados ---\n"
                for i, appt in enumerate(patient_appointments):
                    appointments_list_text += f"Consulta - {i}\n"
                    appointments_list_text += f"ID: {appt.get('Id')}\n"
                    appointments_list_text += f"Paciente: {appt.get('PatientName')}\n"
                    appointments_list_text += f"Data: {appt.get('Date', '').split('T')[0]} | Hora: {appt.get('FromTime')}\n"
                    appointments_list_text += f"Razão: {appt.get('ShedulingReason')}\n"
                    appointments_list_text += "------------------------------------\n"
                
                response_text = appointments_list_text + "\nDigite o NÚMERO da consulta que você quer alterar (ou 'cancelar'):"
                conversation_states[sender_phone]['state'] = 'update_appointment_select_index'
            else:
                response_text = f"Nenhum agendamento encontrado para o CPF {cpf} ou erro na API. " + get_main_menu_text()
                conversation_states[sender_phone] = {'state': 'menu_awaiting_choice', 'data': {}}
        else:
            response_text = "CPF inválido. Use apenas números:"
    
    elif state == 'update_appointment_select_index':
        if message_body_lower == 'cancelar':
            response_text = "Alteração cancelada. " + get_main_menu_text()
            conversation_states[sender_phone] = {'state': 'menu_awaiting_choice', 'data': {}}
        elif re.fullmatch(r"^\d+$", message_body):
            index = int(message_body)
            patient_appointments = data.get('patient_appointments', [])
            
            if 0 <= index < len(patient_appointments):
                selected_appointment = patient_appointments[index]
                data['current_appointment_to_update'] = selected_appointment
                
                response_text = f"Agendamento selecionado:\nID: {selected_appointment.get('Id')}\nRazão atual: {selected_appointment.get('ShedulingReason')}\n"
                response_text += "Nova Razão do Agendamento (ou 'manter'):"
                conversation_states[sender_phone]['state'] = 'update_appointment_reason'
            else:
                response_text = "Número de consulta inválido. Por favor, digite um número da lista ou 'cancelar'."
        else:
            response_text = "Entrada inválida. Digite um número ou 'cancelar'."

    elif state == 'update_appointment_reason':
        current_appointment = data['current_appointment_to_update']
        if message_body_lower != 'manter':
            current_appointment['ShedulingReason'] = message_body
        
        response_text = f"Notas atuais: {current_appointment.get('NotesPatient', 'Nenhuma')}\nNovas Notas sobre o Paciente (ou 'manter'):"
        conversation_states[sender_phone]['state'] = 'update_appointment_notes'
    
    elif state == 'update_appointment_notes':
        current_appointment = data['current_appointment_to_update']
        if message_body_lower != 'manter':
            current_appointment['NotesPatient'] = message_body
        
        response_text = "Deseja alterar a data e/ou hora? (sim/não):"
        conversation_states[sender_phone]['state'] = 'update_appointment_change_date_time_choice'

    elif state == 'update_appointment_change_date_time_choice':
        if message_body_lower == 'sim':
            available_days = config.get_available_days_data
            if not available_days:
                response_text = "Não há datas disponíveis para agendamento. "
                response_text += "Continuando com outros campos... ID da Clínica atual: " + str(data['current_appointment_to_update'].get('Clinic_BusinessId', 'Não informado')) + "\nNovo ID da Clínica (número, ou 'manter'):"
                conversation_states[sender_phone]['state'] = 'update_appointment_clinic_id'
            else:
                date_options = "\n--- Datas Disponíveis para Agendamento ---\n"
                for i, date_info in enumerate(available_days):
                    date_display = datetime.datetime.strptime(date_info["Date"], "%Y-%m-%d").strftime("%d-%m-%Y")
                    date_options += f"{i + 1}. {date_display} ({date_info['Week']})\n"
                response_text = date_options + "Digite o NÚMERO da nova data desejada:"
                conversation_states[sender_phone]['state'] = 'update_appointment_date_selection'
                conversation_states[sender_phone]['data']['available_days'] = available_days
        elif message_body_lower == 'não':
            response_text = "ID da Clínica atual: " + str(data['current_appointment_to_update'].get('Clinic_BusinessId', 'Não informado')) + "\nNovo ID da Clínica (número, ou 'manter'):"
            conversation_states[sender_phone]['state'] = 'update_appointment_clinic_id'
        else:
            response_text = "Entrada inválida. Digite 'sim' ou 'não':"

    elif state == 'update_appointment_date_selection':
        available_days = data.get('available_days', [])
        if re.fullmatch(r"^\d+$", message_body):
            choice = int(message_body)
            if 1 <= choice <= len(available_days):
                selected_date_info = available_days[choice - 1]
                data['current_appointment_to_update']['Date_Info_New'] = selected_date_info # Armazena nova data temporariamente
                
                filtered_times = [t for t in selected_date_info["AvailableTimes"] if t["isSelectable"] and t["isAvailable"]]
                if not filtered_times:
                    response_text = "Não há horários disponíveis para esta data. Por favor, escolha outra data ou 'manter' para pular a alteração de data/hora."
                    conversation_states[sender_phone]['state'] = 'update_appointment_date_selection'
                else:
                    time_options = f"\n--- Horários Disponíveis para {selected_date_info['Week']} ({selected_date_info['Date']}) ---\n"
                    for i, time_slot in enumerate(filtered_times):
                        time_options += f"{i + 1}. {time_slot['from']} - {time_slot['to']}\n"
                    response_text = time_options + "Digite o NÚMERO do novo horário desejado:"
                    conversation_states[sender_phone]['state'] = 'update_appointment_time_selection'
                    conversation_states[sender_phone]['data']['filtered_times'] = filtered_times
            else:
                response_text = "Opção inválida. Escolha um número da lista de datas ou 'manter'."
        elif message_body_lower == 'manter':
            response_text = "Data e hora mantidas. ID da Clínica atual: " + str(data['current_appointment_to_update'].get('Clinic_BusinessId', 'Não informado')) + "\nNovo ID da Clínica (número, ou 'manter'):"
            conversation_states[sender_phone]['state'] = 'update_appointment_clinic_id'
        else:
            response_text = "Entrada inválida. Digite um número da lista ou 'manter'."

    elif state == 'update_appointment_time_selection':
        filtered_times = data.get('filtered_times', [])
        current_appointment = data['current_appointment_to_update']
        if re.fullmatch(r"^\d+$", message_body):
            time_choice = int(message_body)
            if 1 <= time_choice <= len(filtered_times):
                selected_time_info = filtered_times[time_choice - 1]
                current_appointment['FromTime'] = selected_time_info['from']
                current_appointment['ToTime'] = selected_time_info['to']
                
                # Recalcula campos de data/hora
                appointment_date_obj = datetime.datetime.strptime(current_appointment['Date_Info_New']["Date"], "%Y-%m-%d").date()
                time_obj = datetime.datetime.strptime(current_appointment['FromTime'], "%H:%M").time()
                date_time_combined = datetime.datetime.combine(appointment_date_obj, time_obj)
                current_appointment['Date'] = date_time_combined.isoformat() + ".000Z"
                current_appointment['AtomicDate'] = int(appointment_date_obj.strftime("%Y%m%d"))
                current_appointment['SK_DateFirstTime'] = int(appointment_date_obj.strftime("%Y%m%d") + current_appointment['FromTime'].replace(":", ""))
                current_appointment.pop('Date_Info_New', None) # Remove temporária
                
                response_text = "ID da Clínica atual: " + str(current_appointment.get('Clinic_BusinessId', 'Não informado')) + "\nNovo ID da Clínica (número, ou 'manter'):"
                conversation_states[sender_phone]['state'] = 'update_appointment_clinic_id'
            else:
                response_text = "Opção inválida. Escolha um número da lista de horários ou 'manter' para pular."
        elif message_body_lower == 'manter':
            response_text = "Hora mantida. ID da Clínica atual: " + str(current_appointment.get('Clinic_BusinessId', 'Não informado')) + "\nNovo ID da Clínica (número, ou 'manter'):"
            conversation_states[sender_phone]['state'] = 'update_appointment_clinic_id'
        else:
            response_text = "Entrada inválida. Digite um número da lista ou 'manter'."
            
    elif state == 'update_appointment_clinic_id':
        current_appointment = data['current_appointment_to_update']
        if message_body_lower != 'manter':
            if re.fullmatch(r"^\d+$", message_body):
                new_clinic_id = int(message_body)
                id_exists = any(business['id'] == new_clinic_id for business in config.business_list)
                if id_exists:
                    current_appointment['Clinic_BusinessId'] = new_clinic_id
                else:
                    response_text = "ID da clínica inválido. Digite um ID da lista ou 'manter'."
                    twiml_response.message(response_text)
                    return response_text # Early exit to prevent state change if invalid.
            else:
                response_text = "Entrada inválida. Digite um número para o ID da Clínica ou 'manter'."
                twiml_response.message(response_text)
                return response_text

        response_text = f"ID do Dentista/Profissional atual: {current_appointment.get('Dentist_PersonId', 'Não informado')}\nNovo ID do Dentista/Profissional (número, ou 'manter'):"
        conversation_states[sender_phone]['state'] = 'update_appointment_dentist_id'

    elif state == 'update_appointment_dentist_id':
        current_appointment = data['current_appointment_to_update']
        if message_body_lower != 'manter':
            if re.fullmatch(r"^\d+$", message_body):
                current_appointment['Dentist_PersonId'] = int(message_body)
            else:
                response_text = "Entrada inválida. Digite um número para o ID do Dentista/Profissional ou 'manter'."
                twiml_response.message(response_text)
                return response_text

        response_text = f"Agendamento Aceito? atual: {'Sim' if current_appointment.get('ShedulingAccepted') else 'Não'}\nAgendamento Aceito? (sim/não, ou 'manter'):"
        conversation_states[sender_phone]['state'] = 'update_appointment_is_accepted'
    
    elif state == 'update_appointment_is_accepted':
        current_appointment = data['current_appointment_to_update']
        if message_body_lower == 'sim':
            current_appointment['ShedulingAccepted'] = True
        elif message_body_lower == 'não':
            current_appointment['ShedulingAccepted'] = False
        elif message_body_lower == 'manter':
            pass # Mantém o valor atual
        else:
            response_text = "Entrada inválida. Digite 'sim', 'não' ou 'manter':"
            twiml_response.message(response_text)
            return response_text

        # --- FINALIZAÇÃO DA ATUALIZAÇÃO DE AGENDAMENTO ---
        appointment_id = current_appointment.get('Id')
        success, api_response = _make_api_request('PUT', f'/patient/appointments/update_appointment_by_api/{appointment_id}', current_appointment)
        
        if success:
            response_text = "Agendamento atualizado com sucesso!\n"
            response_text += f"ID: {api_response['appointment'].get('Id')}\n"
            response_text += f"Paciente: {api_response['appointment'].get('PatientName')}\n"
            response_text += f"Razão: {api_response['appointment'].get('ShedulingReason')}\n"
            response_text += f"Data: {api_response['appointment'].get('Date', '').split('T')[0]}\n"
            response_text += f"Horário: {api_response['appointment'].get('FromTime')}\n"
        else:
            response_text = f"Falha ao atualizar agendamento: {api_response}"
        
        response_text += "\n" + get_main_menu_text()
        conversation_states[sender_phone] = {'state': 'menu_awaiting_choice', 'data': {}}

    # --- Fluxo de Listagem de Agendamento ---
    elif state == 'list_appointments_awaiting_cpf':
        if re.fullmatch(r"^\d+$", message_body):
            cpf = message_body
            success, patient_appointments = _make_api_request('GET', f'/patient/appointments/{cpf}')
            
            if success and patient_appointments:
                response_text = "\n--- Seus Agendamentos Encontrados ---\n"
                for i, appt in enumerate(patient_appointments):
                    response_text += f"Consulta - {i}\n"
                    response_text += f"ID do Agendamento: {appt.get('Id')}\n"
                    response_text += f"Nome do Paciente: {appt.get('PatientName')}\n"
                    response_text += f"Data: {appt.get('Date', '').split('T')[0]} | Hora Início: {appt.get('FromTime')} | Hora Fim: {appt.get('ToTime')}\n"
                    response_text += f"Razão do Agendamento: {appt.get('ShedulingReason')}\n"
                    response_text += f"Notas do Paciente: {appt.get('NotesPatient', 'N/A')}\n"
                    response_text += f"Email: {appt.get('Email', 'N/A')}\n"
                    response_text += f"Telefone: {appt.get('MobilePhone', 'N/A')}\n"
                    response_text += f"Aceito: {'Sim' if appt.get('ShedulingAccepted') else 'Não'}\n"
                    response_text += "------------------------------------\n"
            else:
                response_text = f"Nenhum agendamento encontrado para o CPF {cpf} ou erro na comunicação com a API."
                if not success:
                    response_text += f" Detalhes: {patient_appointments}"
            
            response_text += "\n" + get_main_menu_text()
            conversation_states[sender_phone] = {'state': 'menu_awaiting_choice', 'data': {}}
        else:
            response_text = "CPF inválido. Use apenas números:"
    
    # Resposta padrão para inputs inesperados ou para retornar ao menu.
    else:
        if message_body_lower == 'menu':
            response_text = get_main_menu_text()
            conversation_states[sender_phone] = {'state': 'menu_awaiting_choice', 'data': {}}
        else:
            response_text = "Desculpe, não entendi. Por favor, digite 'menu' para ver as opções."
            
    twiml_response.message(response_text)
    return response_text # Retorna o texto para depuração no console.


def get_main_menu_text():
    """Retorna o texto do menu principal."""
    return (
        "Bem-vindo ao Sistema de Agendamento!\n"
        "--- Menu Principal ---\n"
        "1. Agendar Nova Consulta\n"
        "2. Alterar Consulta Existente\n"
        "3. Listar Agendamentos de um Paciente\n"
        "4. Sair"
    )

# --- FUNÇÕES AUXILIARES GLOBAIS ---
# Mantenho estas funções, mas a get_validated_input e clear_screen
# não serão mais usadas para interação com o WhatsApp diretamente.

def get_validated_input(prompt, validation_regex=None, error_message="Entrada inválida. Por favor, tente novamente."):
    """
    OBS: Esta função não será mais usada diretamente para o WhatsApp.
    Ela é útil para interações via console (como em testes manuais do Flask).
    """
    while True:
        user_input = input(prompt).strip()
        if validation_regex:
            if re.fullmatch(validation_regex, user_input):
                return user_input
            else:
                print(error_message)
        else:
            return user_input

def clear_screen():
    """
    OBS: Esta função não será mais usada para o WhatsApp.
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def _get_patient_by_document_id(other_document_id):
    for patient in config.patients_get:
        if patient.get('OtherDocumentId') == other_document_id:
            return patient
    return None

def _get_appointments_by_patient_document_id(other_document_id):
    patient_appointment_list = []
    for appointment in config.get_appointment_data:
        if appointment.get('OtherDocumentId') == other_document_id:
            patient_appointment_list.append(appointment)
    return patient_appointment_list

def _get_appointment_by_id(appointment_id):
    for appointment in config.get_appointment_data:
        if str(appointment.get('Id')) == str(appointment_id):
            return appointment
    return None

def _make_api_request(method, endpoint, json_data=None):
    base_url = "http://localhost:5000/TOTAL-IP-case"
    url = f"{base_url}{endpoint}"
    headers = {"Content-Type": "application/json"}

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, data=json.dumps(json_data))
        elif method == 'PUT':
            response = requests.put(url, headers=headers, data=json.dumps(json_data))
        else:
            return False, f"Método HTTP '{method}' não suportado."

        if 200 <= response.status_code < 300:
            return True, response.json()
        else:
            error_message = response.json().get('message', response.text) if response.content else f"Erro HTTP: {response.status_code}"
            return False, f"Falha na requisição {method} para {endpoint}. Status: {response.status_code}. Erro: {error_message}"

    except requests.exceptions.ConnectionError:
        return False, "Erro de conexão: Certifique-se de que o servidor Flask está rodando em localhost:5000."
    except requests.exceptions.RequestException as e:
        return False, f"Erro na requisição à API: {e}"
    except json.JSONDecodeError:
        return False, f"Erro ao decodificar JSON da resposta da API: {response.text}"


# --- ROTAS DA API FLASK (inalteradas na sua lógica) ---
@app.route('/TOTAL-IP-case/patient', methods=['GET'])
def all_patient():
    return jsonify(config.patients_get), 200

@app.route('/TOTAL-IP-case/patient/<string:OtherDocumentId>', methods=['GET'])
def find_patient_api(OtherDocumentId):
    patient = _get_patient_by_document_id(OtherDocumentId)
    if patient:
        return jsonify(patient), 200
    else:
        return jsonify({"message": f"Paciente com documento {OtherDocumentId} não encontrado."}), 404

@app.route('/TOTAL-IP-case/patient/appointments/<string:OtherDocumentId>', methods=['GET'])
def find_patient_appointments_api(OtherDocumentId):
    appointments = _get_appointments_by_patient_document_id(OtherDocumentId)
    return jsonify(appointments), 200

@app.route('/TOTAL-IP-case/appointments/<int:id>', methods=['GET'])
def get_appointment_api(id):
    appointment_data = _get_appointment_by_id(id)
    if appointment_data:
        return jsonify(appointment_data), 200
    else:
        return jsonify({"message": f"Agendamento com ID {id} não encontrado."}), 404

@app.route('/TOTAL-IP-case/patient/appointments/check_tomorrow_appointments', methods=['GET'])
def check_tomorrow_appointments():
    """
    Verifica agendamentos para o dia seguinte e envia mensagens de confirmação via Twilio.
    Esta rota continua a mesma, mas agora usa a função refatorada `send_message`.
    """
    tomorrow_date = date.today() + timedelta(days=1)
    sent_messages = []

    print(f"Verificando agendamentos para amanhã: {tomorrow_date.strftime('%d/%m/%Y')}")

    for appointment in config.get_appointment_data:
        appointment_date_str = appointment.get('Date', '').split('T')[0]
        
        if appointment_date_str == str(tomorrow_date):
            id_appointment = appointment.get('Id')
            patient = _get_patient_by_document_id(appointment.get('OtherDocumentId'))

            if patient:
                phone = patient.get('MobilePhone') # Usamos MobilePhone que é para o WhatsApp.
                name = patient.get('Name')
                
                body_message = f"Olá, {name}! Seu agendamento para amanhã ({tomorrow_date.strftime('%d/%m/%Y')}) está confirmado. Horário: {appointment.get('FromTime')}."

                # AQUI USAMOS A send_message refatorada.
                message_sent = send_message(f'whatsapp:+{phone}', body_message)
                
                if message_sent:
                    sent_messages.append({"appointment_id": id_appointment, "status": "sent", "sid": message_sent.sid})
                else:
                    sent_messages.append({"appointment_id": id_appointment, "status": "failed", "error": "Falha no envio da mensagem Twilio."})
            else:
                print(f"Paciente não encontrado para agendamento ID: {id_appointment}. Impossível enviar mensagem.")
    
    return jsonify({"message": "Verificação de agendamentos para amanhã concluída.", "details": sent_messages}), 200

@app.route('/TOTAL-IP-case/patient/appointments/create_appointment_by_api', methods=['POST'])
def create_appointment_api():
    if not request.is_json:
        return jsonify({"message": "Requisição deve ser JSON"}), 400

    new_appointment_data = request.get_json()

    required_fields = ["PatientName", "Email", "MobilePhone", "OtherDocumentId", 
                       "ShedulingReason", "Clinic_BusinessId", "FromTime", "ToTime", "Date"]
    for field in required_fields:
        if field not in new_appointment_data:
            return jsonify({"message": f"Campo '{field}' é obrigatório."}), 400

    import uuid
    new_appointment_data['Id'] = str(uuid.uuid4())
    
    new_appointment_data.setdefault('OtherPhones', None)
    new_appointment_data.setdefault('NotesPatient', None)
    new_appointment_data.setdefault('Type', "CLINICORP_INTEGRATION")
    new_appointment_data.setdefault('Deleted', None)
    new_appointment_data.setdefault('Dentist_PersonId', 0)
    new_appointment_data.setdefault('CreateUserId', 0)
    new_appointment_data.setdefault('IsOnlineScheduling', False)
    new_appointment_data.setdefault('ShedulingAccepted', False)

    try:
        appointment_date_str = new_appointment_data['Date'].split('T')[0]
        appointment_date = datetime.datetime.strptime(appointment_date_str, "%Y-%m-%d").date()
        
        time_obj = datetime.datetime.strptime(new_appointment_data['FromTime'], "%H:%M").time()
        date_time_combined = datetime.datetime.combine(appointment_date, time_obj)
        new_appointment_data['Date'] = date_time_combined.isoformat() + ".000Z"
        
        new_appointment_data['AtomicDate'] = int(appointment_date.strftime("%Y%m%d"))
        new_appointment_data['SK_DateFirstTime'] = int(appointment_date.strftime("%Y%m%d") + new_appointment_data['FromTime'].replace(":", ""))
    except ValueError as e:
        return jsonify({"message": f"Erro de formato de data/hora: {e}. Verifique 'Date' e 'FromTime'."}), 400
    
    config.get_appointment_data.append(new_appointment_data)

    return jsonify({"message": "Agendamento criado com sucesso!", "appointment": new_appointment_data}), 201

@app.route('/TOTAL-IP-case/patient/appointments/update_appointment_by_api/<int:appointment_id>', methods=['PUT'])
def update_appointment_api(appointment_id):
    old_appointment = _get_appointment_by_id(appointment_id)
    if old_appointment is None:
        return jsonify({"message": f"Agendamento com ID {appointment_id} não encontrado para atualização."}), 404

    if not request.is_json:
        return jsonify({"message": "Requisição deve ser JSON"}), 400
    
    update_data = request.get_json()

    allowed_fields = [
        "ShedulingReason", "NotesPatient", "FromTime", "ToTime", "Date",
        "Clinic_BusinessId", "Dentist_PersonId", "IsOnlineScheduling", "ShedulingAccepted",
    ]

    for key, value in update_data.items():
        if key in allowed_fields:
            if key in ["FromTime", "ToTime", "Date"] and value:
                try:
                    if 'Date' in update_data:
                        appointment_date_str = update_data['Date'].split('T')[0]
                        appointment_date_obj = datetime.datetime.strptime(appointment_date_str, "%Y-%m-%d").date()
                        
                        time_to_combine = update_data.get('FromTime', old_appointment.get('FromTime'))
                        if not time_to_combine:
                             return jsonify({"message": "Campo 'FromTime' é necessário para atualizar 'Date'."}), 400
                        
                        time_obj = datetime.datetime.strptime(time_to_combine, "%H:%M").time()
                        date_time_combined = datetime.datetime.combine(appointment_date_obj, time_obj)
                        old_appointment['Date'] = date_time_combined.isoformat() + ".000Z"
                        
                        old_appointment['AtomicDate'] = int(appointment_date_obj.strftime("%Y%m%d"))
                        old_appointment['SK_DateFirstTime'] = int(appointment_date_obj.strftime("%Y%m%d") + time_to_combine.replace(":", ""))
                    
                    if 'FromTime' in update_data:
                        old_appointment['FromTime'] = update_data['FromTime']
                    if 'ToTime' in update_data:
                        old_appointment['ToTime'] = update_data['ToTime']

                except ValueError as e:
                    return jsonify({"message": f"Erro de formato de data/hora na atualização: {e}. Verifique 'Date', 'FromTime', 'ToTime'."}), 400
            else:
                old_appointment[key] = value

    return jsonify({"message": "Agendamento atualizado com sucesso!", "appointment": old_appointment}), 200


# --- FUNÇÕES PARA INTERAÇÃO NO TERMINAL (CONSOLE MENU) ---
# Estas funções foram mantidas, mas NÃO serão mais usadas para interação
# principal com o usuário via WhatsApp. São úteis para testar via console.

def _prompt_for_date_and_time(available_days_data):
    selected_date_info = None
    selected_time_info = None
    appointment_date_obj = None

    if not available_days_data:
        print("Não há datas disponíveis para agendamento.")
        return None, None, None

    while True:
        print("\n--- Datas Disponíveis para Agendamento ---")
        for i, date_info in enumerate(available_days_data):
            date_display = datetime.datetime.strptime(date_info["Date"], "%Y-%m-%d").strftime("%d-%m-%Y")
            print(f"{i + 1}. {date_display} ({date_info['Week']})")
        print("0. Voltar ao menu anterior (Cancelar seleção de data/hora)")

        try:
            choice_input = input("Escolha o número da data desejada: ")
            if choice_input == '0':
                print("Seleção de data/hora cancelada.")
                return None, None, None
            
            choice = int(choice_input)
            if 1 <= choice <= len(available_days_data):
                selected_date_info = available_days_data[choice - 1]
                appointment_date_obj = datetime.datetime.strptime(selected_date_info["Date"], "%Y-%m-%d").date()
                print(f"\nVocê selecionou: {appointment_date_obj.strftime('%d-%m-%Y')} ({selected_date_info['Week']})")

                while True:
                    print(f"\n--- Horários Disponíveis para {selected_date_info['Week']} ({selected_date_info['Date']}) ---")
                    filtered_times = [
                        time for time in selected_date_info["AvailableTimes"]
                        if time["isSelectable"] and time["isAvailable"]
                    ]

                    if not filtered_times:
                        print("Não há horários disponíveis para esta data. Por favor, escolha outra data.")
                        selected_date_info = None
                        break
                    
                    for i, time_slot in enumerate(filtered_times):
                        print(f"{i + 1}. {time_slot['from']} - {time_slot['to']}")
                    print("0. Voltar para seleção de data")

                    try:
                        time_choice_input = input("Escolha o número do horário desejado: ")
                        if time_choice_input == '0':
                            print("Voltando para a seleção de data.")
                            break
                        
                        time_choice = int(time_choice_input)
                        if 1 <= time_choice <= len(filtered_times):
                            selected_time_info = filtered_times[time_choice - 1]
                            print(f"Você selecionou o horário: {selected_time_info['from']} - {selected_time_info['to']}")
                            return selected_date_info, selected_time_info, appointment_date_obj
                        else:
                            print("Opção inválida. Escolha um número da lista.")
                    except ValueError:
                        print("Entrada inválida. Digite um número.")
            else:
                print("Opção inválida. Escolha um número da lista.")
        except ValueError:
            print("Entrada inválida. Digite um número.")


def create_appointment_console_input():
    print("\n--- Criar Novo Agendamento ---")

    patient_name = get_validated_input("Nome do Paciente: ")
    email = get_validated_input("Email do Paciente: ", validation_regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", error_message="Email inválido.")
    mobile_phone = get_validated_input("Telefone Celular (apenas números, ex: 5511987654321): ", validation_regex=r"^\d+$", error_message="Telefone inválido. Use apenas números.")
    other_phones = input("Outro telefone de contato (opcional): ").strip()
    other_document_id = get_validated_input("Documento (apenas números, ex: CPF): ", validation_regex=r"^\d+$", error_message="Documento inválido. Use apenas números.")
    sheduling_reason = input("Razão do Agendamento: ").strip()
    notes_patient = input("Notas sobre o Paciente (opcional): ").strip()

    clinic_business_id = None
    while True:
        print("\n--- Clínicas Disponíveis ---")
        if not config.business_list:
            print("Nenhuma clínica disponível. Configure 'business_list' em data.py.")
            return None
        for business in config.business_list:
            print(f"{business.get('id')} - Nome: {business.get('BusinessName')}")
        try:
            clinic_choice = get_validated_input("Digite o NÚMERO da Clínica desejada: ", validation_regex=r"^\d+$", error_message="Entrada inválida. Digite um NÚMERO.")
            clinic_business_id = int(clinic_choice)
            id_exists = any(business['id'] == clinic_business_id for business in config.business_list)
            if id_exists:
                selected_business = next((b for b in config.business_list if b['id'] == clinic_business_id), None)
                print(f"Clínica selecionada: {selected_business['BusinessName']}")
                break
            else:
                print("ID inválido. Digite um ID da lista de clínicas.")
        except ValueError:
            print("Entrada inválida. Digite um NÚMERO para o ID da Clínica.")
    
    selected_date_info, selected_time_info, appointment_date = _prompt_for_date_and_time(config.get_available_days_data)
    if not selected_date_info or not selected_time_info:
        print("Seleção de data e hora cancelada. Abortando criação.")
        return None

    dentist_person_id = int(get_validated_input("ID do Dentista/Profissional (apenas números): ", validation_regex=r"^\d+$", error_message="Entrada inválida. Digite um número."))
    create_user_id = int(get_validated_input("ID do Usuário Criador (apenas números): ", validation_regex=r"^\d+$", error_message="Entrada inválida. Digite um número."))

    is_online_scheduling_input = get_validated_input("É Agendamento Online? (sim/não): ", validation_regex=r"^(sim|não)$", error_message="Entrada inválida. Digite 'sim' ou 'não'.").lower()
    is_online_scheduling = is_online_scheduling_input == 'sim'

    sheduling_accepted_input = get_validated_input("Agendamento Aceito? (sim/não): ", validation_regex=r"^(sim|não)$", error_message="Entrada inválida. Digite 'sim' ou 'não'.").lower()
    sheduling_accepted = sheduling_accepted_input == 'sim'

    atomic_date = int(appointment_date.strftime("%Y%m%d"))
    time_obj = datetime.datetime.strptime(selected_time_info['from'], "%H:%M").time()
    date_time_combined = datetime.datetime.combine(appointment_date, time_obj)
    date_time_iso = date_time_combined.isoformat() + ".000Z"
    sk_date_first_time = int(appointment_date.strftime("%Y%m%d") + selected_time_info['from'].replace(":", ""))

    appointment_data = {
        "OtherPhones": other_phones if other_phones else None,
        "ShedulingReason": sheduling_reason,
        "AtomicDate": atomic_date,
        "CreateUserId": create_user_id,
        "Date": date_time_iso,
        "Id": None,
        "Type": "CLINICORP_INTEGRATION",
        "MobilePhone": mobile_phone,
        "SK_DateFirstTime": sk_date_first_time,
        "Deleted": None,
        "OtherDocumentId": other_document_id,
        "ToTime": selected_time_info['to'],
        "FromTime": selected_time_info['from'],
        "Email": email,
        "Clinic_BusinessId": clinic_business_id,
        "Dentist_PersonId": dentist_person_id,
        "NotesPatient": notes_patient,
        "PatientName": patient_name,
        "IsOnlineScheduling": is_online_scheduling,
        "ShedulingAccepted": sheduling_accepted
    }
    return appointment_data


def update_appointment_console_input(current_appointment_data):
    if current_appointment_data is None:
        print("Erro: Nenhum agendamento fornecido para atualização.")
        return None

    updated_appointment = current_appointment_data.copy()

    print("\n--- Alterar Agendamento Existente ---")
    print("Preencha o novo valor ou deixe em branco para manter o atual.")
    print(f"Agendamento para: {updated_appointment.get('PatientName')} (ID: {updated_appointment.get('Id')})")

    print(f"Razão do Agendamento atual: {updated_appointment.get('ShedulingReason')}")
    sheduling_reason = input("Nova Razão do Agendamento (deixe em branco para manter): ").strip()
    if sheduling_reason:
        updated_appointment['ShedulingReason'] = sheduling_reason

    print(f"Notas sobre o Paciente atuais: {updated_appointment.get('NotesPatient')}")
    notes_patient = input("Novas Notas sobre o Paciente (deixe em branco para manter): ").strip()
    if notes_patient:
        updated_appointment['NotesPatient'] = notes_patient

    print("\nDeseja alterar a data e/ou hora do agendamento? (sim/não)")
    change_date_time = input().lower().strip()

    if change_date_time == 'sim':
        selected_date_info, selected_time_info, appointment_date = _prompt_for_date_and_time(config.get_available_days_data)
        if selected_date_info and selected_time_info:
            updated_appointment['FromTime'] = selected_time_info['from']
            updated_appointment['ToTime'] = selected_time_info['to']
            updated_appointment['AtomicDate'] = int(appointment_date.strftime("%Y%m%d"))
            
            time_obj = datetime.datetime.strptime(selected_time_info['from'], "%H:%M").time()
            date_time_combined = datetime.datetime.combine(appointment_date, time_obj)
            updated_appointment['Date'] = date_time_combined.isoformat() + ".000Z"
            
            updated_appointment['SK_DateFirstTime'] = int(appointment_date.strftime("%Y%m%d") + selected_time_info['from'].replace(":", ""))
        else:
            print("Alteração de data e hora cancelada ou falha.")

    print(f"\nID da Clínica atual: {updated_appointment.get('Clinic_BusinessId', 'Não informado')}")
    while True:
        clinic_business_id_input = input("Novo ID da Clínica (número, deixe em branco para manter): ").strip()
        if not clinic_business_id_input:
            break
        try:
            new_clinic_id = int(clinic_business_id_input)
            id_exists = any(business['id'] == new_clinic_id for business in config.business_list)
            if id_exists:
                updated_appointment['Clinic_BusinessId'] = new_clinic_id
                break
            else:
                print("ID da clínica inválido. Digite um ID da lista.")
        except ValueError:
            print("Entrada inválida. Digite um número para o ID da Clínica.")

    print(f"ID do Dentista/Profissional atual: {updated_appointment.get('Dentist_PersonId', 'Não informado')}")
    while True:
        dentist_person_id_input = input("Novo ID do Dentista/Profissional (número, deixe em branco para manter): ").strip()
        if not dentist_person_id_input:
            break
        try:
            updated_appointment['Dentist_PersonId'] = int(dentist_person_id_input)
            break
        except ValueError:
            print("Entrada inválida. Digite um número.")
            
    print(f"Agendamento Aceito? atual: {'Sim' if updated_appointment.get('ShedulingAccepted') else 'Não'}")
    sheduling_accepted_input = input("Agendamento Aceito? (sim/não, deixe em branco para manter): ").lower().strip()
    if sheduling_accepted_input == 'sim':
        updated_appointment['ShedulingAccepted'] = True
    elif sheduling_accepted_input == 'não':
        updated_appointment['ShedulingAccepted'] = False

    print("\nColeta de dados para atualização concluída.")
    return updated_appointment


# --- REMOÇÃO DO MENU CONSOLE VIA ROTA E FUNÇÃO run_console_menu ---
# As rotas e funções de console_input não serão mais chamadas automaticamente
# através da API ou de main_menu_web_entry_point.
# Elas estão aqui para referência ou uso em testes manuais.

# @app.route('/TOTAL-IP-case') # Esta rota foi removida/adaptada para a nova lógica.
# def main_menu_web_entry_point():
#     check_tomorrow_appointments()
#     run_console_menu()
#     return "Console Menu Iniciado (Verifique o terminal onde o Flask está rodando)", 200

# A função run_console_menu original foi descontinuada para interação WhatsApp.
# Se precisar dela para testes de console, copie e cole, e chame-a diretamente no `main.py`
# em vez de `initializer_host()`.
def run_console_menu_for_testing():
    """
    Versão do menu de console para testes manuais.
    Não integrada com o fluxo de mensagens do WhatsApp.
    """
    print("Bem-vindo ao Sistema de Agendamento (Console)!")

    while True:
        print("\n--- Menu Principal ---")
        print("1. Agendar Nova Consulta")
        print("2. Alterar Consulta Existente")
        print("3. Listar Agendamentos de um Paciente")
        print("4. Sair")

        choice = input("Escolha uma opção: ").strip()
        clear_screen()

        if choice == '1':
            new_appointment_data = create_appointment_console_input()
            if new_appointment_data:
                success, response_data = _make_api_request('POST', '/patient/appointments/create_appointment_by_api', new_appointment_data)
                
                if success:
                    print("\nAgendamento criado com sucesso via API!")
                    print("Resposta da API:", response_data)
                else:
                    print("\nFalha ao criar agendamento via API.")
                    print("Erro:", response_data)
            else:
                print("Criação de agendamento cancelada ou dados insuficientes.")
            
        elif choice == '2':
            print("--- Alterar Agendamento ---")
            other_document_id = get_validated_input("CPF do paciente (apenas números): ", validation_regex=r"^\d+$", error_message="CPF inválido. Use apenas números.").strip()
            
            success, patient_appointments = _make_api_request('GET', f'/patient/appointments/{other_document_id}')

            if success and patient_appointments:
                print("\n--- Seus Agendamentos Encontrados ---")
                for indice, appointment in enumerate(patient_appointments):
                    print(f"Consulta - {indice}")
                    print("------------------------------------")
                    print(f"ID do Agendamento: {appointment.get('Id')}")
                    print(f"Nome do Paciente: {appointment.get('PatientName')}")
                    print(f"Data: {appointment.get('Date', '').split('T')[0]} | Hora Início: {appointment.get('FromTime')} | Hora Fim: {appointment.get('ToTime')}")
                    print(f"Razão do Agendamento: {appointment.get('ShedulingReason')}")
                    print("------------------------------------")

                try:
                    appointment_index_input = input("\nNÚMERO da consulta que você quer alterar (ou '0' para cancelar): ").strip()
                    if appointment_index_input == '0':
                        print("Operação de alteração cancelada.")
                        continue
                    
                    appointment_index_to_update = int(appointment_index_input)
                    
                    if 0 <= appointment_index_to_update < len(patient_appointments):
                        selected_appointment = patient_appointments[appointment_index_to_update]
                        
                        updated_data_from_console = update_appointment_console_input(selected_appointment)
                        
                        if updated_data_from_console:
                            success, response_data = _make_api_request('PUT', f'/patient/appointments/update_appointment_by_api/{updated_data_from_console.get("Id")}', updated_data_from_console)
                            
                            if success:
                                print("\nAgendamento atualizado com sucesso via API!")
                                print("Resposta da API:", response_data)
                            else:
                                print("\nFalha ao atualizar agendamento via API.")
                                print("Erro:", response_data)
                        else:
                            print("Atualização de agendamento cancelada.")

                    else:
                        print("Número de consulta inválido.")
                except ValueError:
                    print("Entrada inválida. Digite um número.")
            else:
                print("\nNenhum agendamento encontrado ou erro na comunicação com a API.")
                if not success:
                    print("Detalhes do erro:", patient_appointments)
        
        elif choice == '3':
            print("--- Listar Agendamentos de um Paciente ---")
            other_document_id = get_validated_input("CPF do paciente (apenas números): ", validation_regex=r"^\d+$", error_message="CPF inválido. Use apenas números.").strip()

            success, patient_appointments = _make_api_request('GET', f'/patient/appointments/{other_document_id}')

            if success and patient_appointments:
                print("\n--- Seus Agendamentos Encontrados ---")
                for i, appointment in enumerate(patient_appointments):
                    print(f"Consulta - {i}")
                    print("------------------------------------")
                    print(f"ID do Agendamento: {appointment.get('Id')}")
                    print(f"Nome do Paciente: {appointment.get('PatientName')}")
                    print(f"Data: {appointment.get('Date', '').split('T')[0]} | Hora Início: {appointment.get('FromTime')} | Hora Fim: {appointment.get('ToTime')}")
                    print(f"Razão do Agendamento: {appointment.get('ShedulingReason')}")
                    print(f"Notas do Paciente: {appointment.get('NotesPatient')}")
                    print(f"Email do Paciente: {appointment.get('Email')}")
                    print(f"Telefone Celular: {appointment.get('MobilePhone')}")
                    print(f"Aceito: {'Sim' if appointment.get('ShedulingAccepted') else 'Não'}")
                    print(f"Agendamento Online: {'Sim' if appointment.get('IsOnlineScheduling') else 'Não'}")
                    print(f"Tipo: {appointment.get('Type')}")
                    print(f"ID do Documento: {appointment.get('OtherDocumentId')}")
                    print(f"ID da Clínica: {appointment.get('Clinic_BusinessId')}")
                    print(f"ID do Dentista/Pessoa: {appointment.get('Dentist_PersonId')}")
                    print(f"Data Atômica: {appointment.get('AtomicDate')}")
                    print(f"ID do Usuário Criador: {appointment.get('CreateUserId')}")
                    print(f"SK_DateFirstTime: {appointment.get('SK_DateFirstTime')}")
                    print("------------------------------------")
            else:
                print("\nNenhum agendamento encontrado ou erro na comunicação com a API.")
                if not success:
                    print("Detalhes do erro:", patient_appointments)

        elif choice == '4':
            print("Saindo do Sistema de Agendamento. Até mais!")
            break
        else:
            print("Opção inválida. Por favor, escolha um número entre 1 e 4.")

# --- Inicialização do Servidor Flask ---
def initializer_host():
    """
    Inicializa o servidor Flask.
    """
    print("\nIniciando servidor Flask em http://localhost:5000...")
    app.run(port=5000, host='localhost', debug=True, use_reloader=False)