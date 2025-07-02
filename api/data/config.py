import json

# --- Dados de Pacientes ---
# Tenta carregar dados de pacientes. Se o arquivo não existir, inicializa vazio.
try:
    with open('api/data/json_files/patient/get.json', 'r', encoding='utf-8') as f:
        patients_get = json.load(f)
except FileNotFoundError:
    patients_get = {}
    print("Aviso: 'api/data/json_files/patient/get.json' não encontrado. Pacientes inicializados vazios.")
except json.JSONDecodeError:
    patients_get = {}
    print("Erro: Falha ao decodificar 'api/data/json_files/patient/get.json'. Verifique a sintaxe JSON.")

try:
    with open('api/data/json_files/patient/list_appointments.json', 'r', encoding='utf-8') as f:
        patient_list_appointments = json.load(f)
except FileNotFoundError:
    patient_list_appointments = []
    print("Aviso: 'api/data/json_files/patient/list_appointments.json' não encontrado. Lista de agendamentos de paciente inicializada vazia.")
except json.JSONDecodeError:
    patient_list_appointments = []
    print("Erro: Falha ao decodificar 'api/data/json_files/patient/list_appointments.json'. Verifique a sintaxe JSON.")

# --- Dados de Agendamentos ---
# Carrega informações de agendamentos, tratando erros.
try:
    with open('api/data/json_files/appointment/list.json', 'r', encoding='utf-8') as f:
        appointments_list = json.load(f)
except FileNotFoundError:
    appointments_list = []
    print("Aviso: 'api/data/json_files/appointment/list.json' não encontrado. Lista de agendamentos inicializada vazia.")
except json.JSONDecodeError:
    appointments_list = []
    print("Erro: Falha ao decodificar 'api/data/json_files/appointment/list.json'. Verifique a sintaxe JSON.")

try:
    with open('api/data/json_files/appointment/get_appointment.json', 'r', encoding='utf-8') as f:
        get_appointment_data = json.load(f)
except FileNotFoundError:
    get_appointment_data = {}
    print("Aviso: 'api/data/json_files/appointment/get_appointment.json' não encontrado. Dados de agendamento específico inicializados vazios.")
except json.JSONDecodeError:
    get_appointment_data = {}
    print("Erro: Falha ao decodificar 'api/data/json_files/appointment/get_appointment.json'. Verifique a sintaxe JSON.")

try:
    with open('api/data/json_files/appointment/get_avaliable_days.json', 'r', encoding='utf-8') as f:
        get_available_days_data = json.load(f)
except FileNotFoundError:
    get_available_days_data = []
    print("Aviso: 'api/data/json_files/appointment/get_avaliable_days.json' não encontrado. Dias disponíveis inicializados vazios.")
except json.JSONDecodeError:
    get_available_days_data = []
    print("Erro: Falha ao decodificar 'api/data/json_files/appointment/get_avaliable_days.json'. Verifique a sintaxe JSON.")

try:
    with open('api/data/json_files/appointment/get_avaliable_times_calendar.json', 'r', encoding='utf-8') as f:
        get_available_times_calendar_data = json.load(f)
except FileNotFoundError:
    get_available_times_calendar_data = {}
    print("Aviso: 'api/data/json_files/appointment/get_avaliable_times_calendar.json' não encontrado. Horários disponíveis inicializados vazios.")
except json.JSONDecodeError:
    get_available_times_calendar_data = {}
    print("Erro: Falha ao decodificar 'api/data/json_files/appointment/get_avaliable_times_calendar.json'. Verifique a sintaxe JSON.")

try:
    with open('api/data/json_files/appointment/list_categories.json', 'r', encoding='utf-8') as f:
        list_categories_data = json.load(f)
except FileNotFoundError:
    list_categories_data = []
    print("Aviso: 'api/data/json_files/appointment/list_categories.json' não encontrado. Categorias de agendamento inicializadas vazias.")
except json.JSONDecodeError:
    list_categories_data = []
    print("Erro: Falha ao decodificar 'api/data/json_files/appointment/list_categories.json'. Verifique a sintaxe JSON.")

try:
    with open('api/data/json_files/appointment/status_list.json', 'r', encoding='utf-8') as f:
        status_list_data = json.load(f)
except FileNotFoundError:
    status_list_data = []
    print("Aviso: 'api/data/json_files/appointment/status_list.json' não encontrado. Lista de status inicializada vazia.")
except json.JSONDecodeError:
    status_list_data = []
    print("Erro: Falha ao decodificar 'api/data/json_files/appointment/status_list.json'. Verifique a sintaxe JSON.")

# --- Dados de Negócios (Clínicas) ---
# Carrega informações sobre as clínicas/negócios.
try:
    with open('api/data/json_files/business/list_available_times.json', 'r', encoding='utf-8') as f:
        business_list_available_times = json.load(f)
except FileNotFoundError:
    business_list_available_times = {}
    print("Aviso: 'api/data/json_files/business/list_available_times.json' não encontrado. Horários disponíveis de negócio inicializados vazios.")
except json.JSONDecodeError:
    business_list_available_times = {}
    print("Erro: Falha ao decodificar 'api/data/json_files/business/list_available_times.json'. Verifique a sintaxe JSON.")

try:
    with open('api/data/json_files/business/list.json', 'r', encoding='utf-8') as f:
        business_list = json.load(f)
except FileNotFoundError:
    business_list = []
    print("Aviso: 'api/data/json_files/business/list.json' não encontrado. Lista de negócios inicializada vazia.")
except json.JSONDecodeError:
    business_list = []
    print("Erro: Falha ao decodificar 'api/data/json_files/business/list.json'. Verifique a sintaxe JSON.")
    