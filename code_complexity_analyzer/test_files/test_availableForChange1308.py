import pytest
import requests
import cx_Oracle
from core.db_helper import sql_query_return_one_row_in_json, version_verify, sql_query_return_matrix_json_rows, \
    table_count_row, sql_query_return_one_row
from core.http_request_frontend import get_token_user_with_role
from core.print_n_log_helper import syslog_insert_records
import random
import string

# проверяемые в тесте компоненты(подсистемы)
component_json = (
    {'component': "BIS_BASE_1", 'component_id': 1383, 'version': '1.17.0'},
)
# Класс для хранения данных
class technicalData:
    NumberClassIds = '1'  # Константа NumberClassIds по умолчанию
    #phoneNumberId:
    phoneNumberId = 165545
    # StandardId:
    STND_ID = 1
    PhoneNumbers = None  # Список предполагаемых номеров телефона (по умолчанию None)

    @staticmethod
    def update_phone_numbers(phone_numbers):
        """
        Метод для обновления списка предполагаемых номеров и возврата
        обновленного списка.
        """
        technicalData.PhoneNumbers = phone_numbers
        return technicalData.PhoneNumbers  # Обновленный список

# Проверка подключения к базе данных
def check_db_connection():
    try:
        sql = "SELECT NAME FROM dealers d"
        result = sql_query_return_one_row_in_json(sql)
        if result:
            print("Успешно")
            print(result.values())
        else:
            print("Ошибка Подключения")
    except Exception as e:
        print(f"Database failed: {e}")
check_db_connection()

def pytest_check_configuration():
    # при успешной конфигурации функция должна вернуть {'status': 0, 'reason': ''reason''},
    # при не успешной {'status': число > 0, 'reason': Список причин }
    # проверка версий подсистем
    status = 0
    reason = ' '
    print("""Выполняется проверка pytest_check_configuration()""")
    res, reason_check = version_verify(component_json)
    if res > 0:
        status += 1
        reason = reason + "\n" + reason_check
    return {'status': status, 'reason': reason}

@pytest.mark.OAPI_BIS_BASE_API_FRONTEND
@pytest.mark.CHANGE_PHONE_NUMBER
@pytest.mark.skipif(pytest_check_configuration()['status'] != 0, reason=pytest_check_configuration()['reason'])
#главный класс с тестами
class TestSuite_AvailableForChange:
# Переменные класса для использования в тестах
    #p_activation_code_random = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(10))
    # Значение NumberClassIds по умолчанию
    NumberClassIds = '1'

    @classmethod
    def setup_class(cls):
        print(cls.__name__, "=================== > setup_class")
        # подготовка тестовых данных, если необходимо
        check_db_connection()

    @classmethod
    def teardown_class(cls):
        print("\n", cls.__name__, "====================================== > teardown_class")
        # очистка данных или параметров после выполнения тестов, если необходимо

    # токен
    @pytest.fixture(scope="class")
    def key_with_role(self):
        return get_token_user_with_role()

    @pytest.fixture(scope="class")
    def agent_id(self):
        # Получение AgentId
        result = TD.get_agent_id()
        assert result, "SQL query returned no results"
        return result

    @pytest.fixture(scope="class")
    def subscriber_id(self):
        # получения имени Subscriber
        result = TD.get_subscriber_id()
        assert result, "SQL query returned no results"
        return result


    def test_availableForChange_case1(self, key_with_role, agent_id, subscriber_id):
        # Использование данных из класса technicalData
        phoneNumberId = technicalData.phoneNumberId
        STND_ID = technicalData.STND_ID

        # Получаем AgentId с использованием класса TD
        AgentId = TD.get_agent_id()
        assert AgentId, "SQL query returned no results"

        # Получаем subscriberId с использованием класса TD
        subscriberId = TD.get_subscriber_id()
        assert subscriberId, "SQL query returned no results"

            # Формируем URL для API-запроса
            url = f"http://192.168.2.114:8080/OAPI/v1/cbss/subscribers/{subscriberId}/phoneNumbers/{phoneNumberId}/availableForChange/search"

        # минимальное кол-во параметров
        params = {
            "authToken": key_with_role,
            "agentId": AgentId,
            "standardId": STND_ID,
            "numberCategoryId": 1,
            "listMode": 1,
        }
        '''
        headers = {
            "Authorization": key_with_role
        }
        '''

        response = requests.post(url, params=params)

        print(f"Response status code: {response.status_code}")

        assert response.json(), "Ответ не должен быть пустым"
        assert response.status_code == 200, f"Ожидали код 200, но получили {response.status_code}"

        # Печатаем json-ки
        response_data = response.json()
        print(f"Response data: {response_data}")

    def test_availableForChange_case3(self, key_with_role, agent_id, subscriber_id):
        """
        Тест проверяет доступность смены номера для subscriberId.
        Используются минимальные параметры запроса, включая NumberClassIds.
        """
        # Использование данных из класса technicalData
        phoneNumberId = technicalData.phoneNumberId
        STND_ID = technicalData.STND_ID
        NumberClassIds = technicalData.NumberClassIds

        # Формируем URL для API-запроса
        url = f"http://192.168.2.114:8080/OAPI/v1/cbss/subscribers/{subscriber_id}/phoneNumbers/{phoneNumberId}/availableForChange/search"
        params = {
            "authToken": key_with_role,
            "agentId": agent_id,
            "standardId": STND_ID,
            "numberCategoryId": 1,
            "listMode": 1,
            "NumberClassIds": NumberClassIds,
        }

        # Выполнение POST-запроса
        response = requests.post(url, params=params)

        print(f"Response status code: {response.status_code}")
        assert response.status_code == 200, f"Ожидали код 200, но получили {response.status_code}"
        assert response.json(), "Ответ не должен быть пустым"

        # Печатаем JSON-ответ
        response_data = response.json()
        print(f"Response data: {response_data}")

    def test_availableForChange_case4(self, key_with_role, agent_id, subscriber_id):
        # Использование данных из класса technicalData
        phoneNumberId = technicalData.phoneNumberId
        STND_ID = technicalData.STND_ID


        # NumberClassIds и PhoneNumbers из класса Техданные
        NumberClassIds = technicalData.NumberClassIds
        PhoneNumbers = technicalData.PhoneNumbers  # По умолчанию None
        print(PhoneNumbers)

        # Получаем AgentId с использованием класса TD
        AgentId = TD.get_agent_id()
        assert AgentId, "SQL query returned no results"

        # Получаем subscriberId с использованием класса TD
        subscriberId = TD.get_subscriber_id()
        assert subscriberId, "SQL query returned no results"

        # Формируем URL для API-запроса
        url = f"http://192.168.2.114:8080/OAPI/v1/cbss/subscribers/{subscriberId}/phoneNumbers/{phoneNumberId}/availableForChange/search"

        # минимальное кол-во параметров
        params = {
            "authToken": key_with_role,
            "agentId": agent_id,
            "standardId": STND_ID,
            "numberCategoryId": 1,
            "listMode": 1,
            "NumberClassIds": NumberClassIds,
            "phoneNumbers": PhoneNumbers,  # парам phoneNumbers
        }


        response = requests.post(url, params=params)

        print(f"Response status code: {response.status_code}")

        assert response.json(), "Ответ не должен быть пустым"
        assert response.status_code == 200, f"Ожидали код 200, но получили {response.status_code}"

        # Печатаем json-ки
        response_data = response.json()
        print(f"Response data: {response_data}")

    def test_availableForChange_case4_realListofNums(self, key_with_role, agent_id, subscriber_id):
        """
        Тест проверяет доступность смены номера для конкретного subscriberId.
         с передачей списка предполагаемых номеров.
        """
        # Использование данных из класса technicalData
        phoneNumberId = technicalData.phoneNumberId
        STND_ID = technicalData.STND_ID


        # NumberClassIds и PhoneNumbers из класса Техданные
        NumberClassIds = technicalData.NumberClassIds

        PhoneNumbers = technicalData.update_phone_numbers(["994065077", "994065077", "994811001"])

        print(PhoneNumbers)
        # Получаем AgentId с использованием класса TD
        agent_id = 1036
        #assert AgentId, "SQL query returned no results"

        # Получаем subscriberId с использованием класса TD
        subscriberId = TD.get_subscriber_id()
        assert subscriberId, "SQL query returned no results"

        # Формируем URL для API-запроса
        url = f"http://192.168.2.114:8080/OAPI/v1/cbss/subscribers/{subscriberId}/phoneNumbers/{phoneNumberId}/availableForChange/search"

        # минимальное кол-во параметров
        params = {
            "authToken": key_with_role,
            "agentId": agent_id,
            "standardId": STND_ID,
            "numberCategoryId": 1,
            "listMode": 1,
            "NumberClassIds": NumberClassIds,
            "phoneNumbers": PhoneNumbers,  # парам phoneNumbers
        }


        response = requests.post(url, params=params)

        print(f"Response status code: {response.status_code}")

        assert response.json(), "Ответ не должен быть пустым"
        assert response.status_code == 200, f"Ожидали код 200, но получили {response.status_code}"

        # Печатаем json-ки
        response_data = response.json()
        print(f"Response data: {response_data}")




class TD():
    #testdata_common = Stand.config
    #testdata = Stand.config['test_data_settings'][get_testfile_name(__file__)]

    @staticmethod
    def get_agent_id():
        AgentId = sql_query_return_one_row_in_json("""select distinct ns.trgt_delr_id, 
                                               ns.trgt_slpt_id, d.dlrt_dlrt_id
                                               from number_sets ns, dealers d, dealer_types dt
                                               where ns.nsts_nsts_id in (2, 4)and d.delr_id = ns.trgt_delr_id
                                               and (dt.dlrt_id = 2 or dt.dlrt_id = 1000) 
                                               and ns.trgt_delr_id > 1000 order by ns.trgt_delr_id""")
        return AgentId["TRGT_DELR_ID"]

    @staticmethod
    def get_subscriber_id():

        subscriberId = sql_query_return_one_row_in_json("""select ss.subs_id, ss.sbst_sbst_id, ss.sbst_sbst_id, ss.stnd_stnd_id, ns.msisdn, ns.nsts_nsts_id, ns.nset_id
                                            from subscribers ss, number_sets ns, phone_histories ph
                                            where ss.subs_id = ph.subs_subs_id
                                            and ph.nset_nset_id = ns.nset_id
                                            and ph.end_date > sysdate
                                            and ss.sbst_sbst_id = 2
                                            and ss.stnd_stnd_id=5"""
                                                   )
        print("SUBS_ID", subscriberId)
        return subscriberId["SUBS_ID"]
    """
    def get_phonenumber_id():
        phoneNumberId
    """
