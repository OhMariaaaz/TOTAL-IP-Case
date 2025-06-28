# objetivos:
# A rede de Hospitais Nube Saude está passando por um processo de transformação
# digital, visando automatizar processos de atendimento que atualmente ocorrem com o
# paciente indo presencialmente em uma das unidades para realizar a gestão da sua
# consulta. Em um evento de tecnologia, eles conheceram a Total IP
# (https://totalip.com.br/), empresa que desenvolve soluções de atendimento de Voz e
# Chat, além de possuir recursos de IA e optaram em abrir um projeto.
# Seu papel nesse projeto, é apresentar uma alternativa para que a rede de hospitais
# consiga atingir o seu objetivo de automatizar o atendimento, criando um fluxo macro
# lógico e integrado ao CRM, baseado as informações disponíveis da documentação de
# API (https://api.clinicorp.com/api-docs/), para atendimento via ligação receptiva e via
# whatsapp ativo e receptivo.
# Processos que devem ser considerados como prioritários:
# Agendamento de consultas;
# Confirmação de consultas;
# Além disso, discorra como a diretoria do Hospital vai poder avaliar os indicadores dessa
# transformação digital com a ferramenta da Total IP.
#
#
# URL base: https://api.clinicorp.com/api-docs/#/
#
#
# Endpoints:
#      - VER CONTATO DO CLIENTE CPF/TELEFONE (GET https://api.clinicorp.com/api-docs/#/patient/get_patient_get)
#      - VER CONSULTAS MARCADAS (GET https://api.clinicorp.com/api-docs/#/patient/get_patient_list_appointments)
#           - CONFIRMAR CONSULTA (GET https://api.clinicorp.com/api-docs/#/appointment/post_appointment_confirm_appointment)
#           - CANCELAR CONSULTA (DELETE https://api.clinicorp.com/api-docs/#/appointment/post_appointment_cancel_appointment)
#           - ALTERAR CONSULTA (GET https://api.clinicorp.com/api-docs/#/appointment/get_appointment_change_status)
#      - CONFIRMAR CONSULTA (GET https://api.clinicorp.com/api-docs/#/appointment/post_appointment_confirm_appointment)
#           - CANCELAR CONSULTA (DELETE https://api.clinicorp.com/api-docs/#/appointment/post_appointment_cancel_appointment)
#           - ALTERAR CONSULTA (GET https://api.clinicorp.com/api-docs/#/appointment/get_appointment_change_status)
#      - MARCAR CONSULTA
#           - VER CLINICAS DISPONIVEIS (GET https://api.clinicorp.com/api-docs/#/group/get_group_list_subscribers_clinics)
#           - VER CATEGORIAS DISPONIVEIS (GET https://api.clinicorp.com/api-docs/#/appointment/get_appointment_list_categories)
#           - VER DIAS DISPONIVEIS (GET https://api.clinicorp.com/api-docs/#/appointment/get_appointment_get_avaliable_days)
#           - VER HORARIOS DISPONIVEIS (https://api.clinicorp.com/api-docs/#/appointment/get_appointment_get_avaliable_times_calendar)
#           - CRIAR CONSULTA (POST https://api.clinicorp.com/api-docs/#/appointment/post_appointment_create_appointment_by_api) 

from flask import Flask, jsonify, request

app = Flask(__name__)

# Biblioteca com dicionarios de cada um dos registros
# futuramente substituido pela URL da API que desejamos
patients = [
    {
        'PatientId': 0,
        'Name': 'Test0',
        'Email': 'Test0',
        'Phone': 'Test0',
        'OtherDocumentId': 'teste1',
        'Status': 'Test0',
        'BirthDate': 'Test0'
    },
    {
        'PatientId': 1,
        'Name': 'Test1',
        'Email': 'Test1',
        'Phone': 'Test1',
        'OtherDocumentId': 'teste',
        'Status': 'Test1',
        'BirthDate': 'Test1'
    },
    {
        'PatientId': 2,
        'Name': 'Test2',
        'Email': 'Test2',
        'Phone': 'Test2',
        'OtherDocumentId': '2',
        'Status': 'Test2',
        'BirthDate': 'Test2'
    },
    {
        'PatientId': 3,
        'Name': 'Test3',
        'Email': 'Test3',
        'Phone': 'Test3',
        'OtherDocumentId': 'teste3',
        'Status': 'Test3',
        'BirthDate': 'Test3'
    }
]
appointments = [
    {
    'OtherPhones': '(31) 99345-6789',
    'ShedulingReason': 'Revisão de aparelho',
    'AtomicDate': 20210717,
    'CreateUserId': -1,
    'Date': '2021-07-17T10:00:00.000Z',
    'Id': 4791226171916292,
    'Type': 'CLOUDIA',
    'MobilePhone': '(31) 98712-3344',
    'SK_DateFirstTime': 920210717,
    'Deleted': '',
    'OtherDocumentId': 'teste4',
    'ToTime': '09:00',
    'FromTime': '09:30',
    'Email': 'joao.pedro@example.com',
    'Clinic_BusinessId': 5759793708400640,
    'Dentist_PersonId': 5670262998564864,
    'NotesPatient': 'Vai trazer documentação',
    'PatientName': 'João Pedro',
    'IsOnlineScheduling': True,
    'ShedulingAccepted': True
  },
  {
    'OtherPhones': '',
    'ShedulingReason': 'Canal',
    'AtomicDate': 20210718,
    'CreateUserId': -1,
    'Date': '2021-07-18T13:20:00.000Z',
    'Id': 4791226171916293,
    'Type': 'CLOUDIA',
    'MobilePhone': '(41) 99888-7654',
    'SK_DateFirstTime': 920210718,
    'Deleted': 'X',
    'OtherDocumentId': 'teste5',
    'ToTime': '14:30',
    'FromTime': '15:30',
    'Email': 'aline.ramos@example.com',
    'Clinic_BusinessId': 5759793708400640,
    'Dentist_PersonId': 5670262998564864,
    'NotesPatient': '',
    'PatientName': 'Aline Ramos',
    'IsOnlineScheduling': True,
    'ShedulingAccepted': False
  },
  {
    'OtherPhones': '(62) 99112-3344',
    'ShedulingReason': 'Clareamento',
    'AtomicDate': 20210719,
    'CreateUserId': -1,
    'Date': '2021-07-18T15:10:00.000Z',
    'Id': 4791226171916294,
    'Type': 'CLOUDIA',
    'MobilePhone': '(62) 98745-1122',
    'SK_DateFirstTime': 920210719,
    'Deleted': '',
    'OtherDocumentId': 'teste6',
    'ToTime': '16:00',
    'FromTime': '17:00',
    'Email': 'bruno.matos@example.com',
    'Clinic_BusinessId': 5759793708400640,
    'Dentist_PersonId': 5670262998564864,
    'NotesPatient': 'Solicita orçamento no final',
    'PatientName': 'Bruno Matos',
    'IsOnlineScheduling': True,
    'ShedulingAccepted': True
  },
  {
    'OtherPhones': '',
    'ShedulingReason': 'Consulta de rotina',
    'AtomicDate': 20210720,
    'CreateUserId': -1,
    'Date': '2021-07-19T08:45:00.000Z',
    'Id': 4791226171916295,
    'Type': 'CLOUDIA',
    'MobilePhone': '(48) 99999-1111',
    'SK_DateFirstTime': 920210720,
    'Deleted': '',
    'OtherDocumentId': 'teste7',
    'ToTime': '10:00',
    'FromTime': '11:00',
    'Email': 'lucas.farias@example.com',
    'Clinic_BusinessId': 5759793708400640,
    'Dentist_PersonId': 5670262998564864,
    'NotesPatient': '',
    'PatientName': 'Lucas Farias',
    'IsOnlineScheduling': True,
    'ShedulingAccepted': True
  },
  {
    'OtherPhones': '(27) 98777-8888',
    'ShedulingReason': 'Reparo de prótese',
    'AtomicDate': 20210721,
    'CreateUserId': -1,
    'Date': '2021-07-20T16:55:00.000Z',
    'Id': 4791226171916296,
    'Type': 'CLOUDIA',
    'MobilePhone': '(27) 98444-5544',
    'SK_DateFirstTime': 920210721,
    'Deleted': '',
    'OtherDocumentId': 'teste8',
    'ToTime': '17:30',
    'FromTime': '18:00',
    'Email': 'renata.alves@example.com',
    'Clinic_BusinessId': 5759793708400640,
    'Dentist_PersonId': 5670262998564864,
    'NotesPatient': 'Paciente vem do interior',
    'PatientName': 'Renata Alves',
    'IsOnlineScheduling': True,
    'ShedulingAccepted': True
  },
  {
    'OtherPhones': '',
    'ShedulingReason': 'Retorno avaliação',
    'AtomicDate': 20210722,
    'CreateUserId': -1,
    'Date': '2021-07-21T12:40:00.000Z',
    'Id': 4791226171916297,
    'Type': 'CLOUDIA',
    'MobilePhone': '(85) 99900-1234',
    'SK_DateFirstTime': 920210722,
    'Deleted': '',
    'OtherDocumentId': 'teste9',
    'ToTime': '13:00',
    'FromTime': '13:30',
    'Email': 'fernanda.gomes@example.com',
    'Clinic_BusinessId': 5759793708400640,
    'Dentist_PersonId': 5670262998564864,
    'NotesPatient': '',
    'PatientName': 'Fernanda Gomes',
    'IsOnlineScheduling': True,
    'ShedulingAccepted': False
  },
  {
    'OtherPhones': '(19) 98876-5432',
    'ShedulingReason': 'Restauração',
    'AtomicDate': 20210723,
    'CreateUserId': -1,
    'Date': '2021-07-22T08:15:00.000Z',
    'Id': 4791226171916298,
    'Type': 'CLOUDIA',
    'MobilePhone': '(19) 98712-3456',
    'SK_DateFirstTime': 920210723,
    'Deleted': '',
    'OtherDocumentId': 'teste5',
    'ToTime': '09:00',
    'FromTime': '10:00',
    'Email': 'eduardo.santos@example.com',
    'Clinic_BusinessId': 5759793708400640,
    'Dentist_PersonId': 5670262998564864,
    'NotesPatient': 'Quer saber sobre plano odontológico',
    'PatientName': 'Eduardo Santos',
    'IsOnlineScheduling': True,
    'ShedulingAccepted': True
  }
]

# Consultar tudo
@app.route('/TOTAL-IP-case',methods=['GET'])
def all_patient():
    return jsonify(patients)

# Consultar Paciente por Documento
@app.route('/TOTAL-IP-case/<string:OtherDocumentId>',methods=['GET'])
def find_patient(OtherDocumentId):
    for patient in patients:
        if patient.get('OtherDocumentId') == OtherDocumentId:
            return jsonify(patient)

# Consultar Consultas por Paciente
@app.route('/TOTAL-IP-case/patient-appointments/<string:OtherDocumentId>',methods=['GET'])
def find_patient_appointments(OtherDocumentId):
    patient_appointment = []
    for appointment in appointments:
        if appointment.get('OtherDocumentId') == OtherDocumentId:
            patient_appointment.append(appointment)
    return jsonify(patient_appointment)

def edit_appointment(Id)


app.run(port=5000,host='localhost',debug=True)
