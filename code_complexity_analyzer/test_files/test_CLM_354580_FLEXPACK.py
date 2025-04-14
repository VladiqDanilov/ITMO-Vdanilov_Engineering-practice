import json
import cx_Oracle
import pytest
import random

from core.conf import Stand
from core.http_request_backend import post_or_get_request_backend
from core.http_request_frontend import post_or_get_request_frontend, get_token_user_with_role,\
    get_token_user_without_role, token_access, role_req_dict
from core.db_helper import sql_query_return_one_row, sql_query_with_commit, version_verify, connection_to_db, \
    printException, sql_query_return_matrix, sql_query_return_one_row_for_core
from core.mbus_helper import create_copy_of_table, create_trigger_on_table_for_copy, drop_table, drop_trigger
from core.print_n_log_helper import outlog as outlog, get_testfile_name, syslog_insert_records


# Module level setup/teardown - нужно положить в корень вашего тестового файла.
def setup_module(module):
    print("""===[MODUL.SETUP]   ===>  на уровне модуля - тестового файла""")
    # запись в syslog o запуске данного теста
    syslog_insert_records(f"""Стартовал процесс {module.__name__}""")


def teardown_module(module):
    print("""===[MODUL.TEARDOWN]===> Teardown на уровне модуля - тестового файла""")
    # запись в syslog oб окончании данного теста
    syslog_insert_records(f"""Завершение процесс {module.__name__}""")


# проверяемые в тесте компоненты(подсистемы)
component_json = (
        {'component': "OAPI_BIS_API_BACKEND", 'component_id': 15560, 'version': '1.29.0'},
        {'component': "API_CLNT_BASE", 'component_id': 21, 'version': '1.182.0'},
        {'component': "SCR", 'component_id': 0, 'version': '1.209.0'},
        {'component': "BIS_NOTIFY", 'component_id': 1277, 'version': '1.24.0'},
        {'component': "BIS_BASE_1", 'component_id': 1383, 'version': '1.17.0'}
       # ,{'component': 'OAPI_BIS_BASE_API_FRONTEND ', 'component_id': '01079010', 'version': '1.2.0'}
    )

def print_component_version(component_json):
    print("Проверяемые компоненты ==>")
    print("   %-30s %-20s %-10s" % ('COMPONENT', 'COMPONENT_ID', 'VERSION'))
    print("   =============================================================== ")

    for component in component_json:
        print("   %-30s %-20s %-10s" % (component['component'], str(component['component_id']), component['version']))

class TestSuite_test_info_out(outlog):
    TS = "ТС: CLM-354580 UCELL_IMPL: Заказной пакет"
    TS_URL = "https://confluence.billing.ru/pages/viewpage.action?pageId=247031354"
    INFO = """
           """

    def test_info(self):
        print("\nTS ==> ", TestSuite_test_info_out.TS)
        print("TS_URL ==> ", TestSuite_test_info_out.TS_URL)
        print("INFO ==> ", TestSuite_test_info_out.INFO)
        print_component_version(component_json)


def pytest_check_configuration():
    # SECTION HELPER_FUNCTION ##############################################################################################
    res = 0
    token = token_access('GRANTED')
    reason = ''
    role_dict = role_req_dict(token)
    role = 'OAPI:v1:Subscriber:FlexpackActivate'
    if role in role_dict:
        res = res + 0
    else:
        res = res + 1
        reason = reason + f"\n Не найдено необходимой роли {role}"
    stat, rea = version_verify(component_json)
    if stat > 0:
        res = res + 1
        reason = reason + "\n" + rea
    return {'status': res, 'reason': reason}


# Тестовые данные
class TD():
    # Обязательная стандартная строка для получения тестовых данных из конфига
    testdata = Stand.config['test_data_settings'][get_testfile_name(__file__)]

    # из конфига получаем значения переменных
    p_subscriberId = testdata['p_subscriberId']
    p_pack_id_1 = testdata['p_pack_id_1']  # заказной пакет, уже подключен абоненту, тип пакета = 1
    p_pack_id_2 = testdata['p_pack_id_2']  # заказной пакет, тип пакета = 2, пакет используется для подключения при положительном ответе от CART
    p_pack_id_3 = testdata['p_pack_id_3']  # НЕ заказной пакет
    p_pack_id_4 = testdata['p_pack_id_4']  # заказной пакет, но нет записи в таблице FLEXPACKS
    p_pack_id_5 = testdata['p_pack_id_5']  # заказной пакет, есть запись в таблице FLEXPACKS,  нет записи в таблице FLEXPACK_RANGE
    p_pack_id_6 = testdata['p_pack_id_6']  # заказной пакет, тип пакета = 2, пакет используется для подключения при отрицательном ответе от CART
    p_flex_amount = 10.44
    p_flex_volume = 3
    p_trace_num_for_pack_1 = testdata['p_trace_num_for_pack_1']
    p_subscriberFlexpackId_1 = str(p_pack_id_1) + 't' + str(p_trace_num_for_pack_1)
    p_range_start_1 = 100  # нижняя граница первого интервала
    p_range_end_1 = 200  # верхняя граница первого интервала
    p_range_start_2 = 201  # нижняя граница второго интервала
    p_range_end_2 = 300  # верхняя граница второго интервала
    p_range_start_3 = 301  # нижняя граница третьего интервала
    p_range_end_3 = 500  # верхняя граница верхнего интервала
    p_volume_in_1_range = int(random.uniform(p_range_start_1, p_range_end_1))  # объём, попадающий в первый интервал
    p_volume_in_2_range = int(random.uniform(p_range_start_2, p_range_end_2))  # объём, попадающий во второй интервал
    p_volume_in_3_range = int(random.uniform(p_range_start_3, p_range_end_3))  # объём, попадающий в третий интервал
    p_volume_out_min = int(random.uniform(0, p_range_start_1))  # объём меньше нижней границы самого первого интервала
    p_volume_out_max = int(random.uniform(p_range_end_3, p_range_end_3 * 10))  # объём больше верхней границы самого последнего интервала
    p_rateplanId = sql_query_return_one_row_for_core(
        """select sh.rtpl_rtpl_id from subs_histories sh where sh.subs_subs_id={subscriberId} and sh.start_date<sysdate and sh.end_date>sysdate""".format(
            subscriberId=p_subscriberId))
    p_price_for_range_1 = 3
    p_price_for_range_2 = 2
    p_price_for_range_3 = 1
    p_dcpl_id = testdata['p_dcpl_id']

    # значения переменных для проверки сообщения в MBUS
    p_routing_key_for_pack_activate = 'ps.pack_activate'
    p_routing_key_for_order_pack = 'ps.bis2cart.order_pack_add'
    p_routing_key_from_CART = 'ps.cart2bis.order_pack_check'
    p_mbus_table_name = 'mbus.MBUS_MSG_BIS_NOTIFY'

    ordinary_table = p_mbus_table_name # специальная переменная для поиска по коду.
    ordinary_table2 = ordinary_table.split('.')[1]  # уберем mbus. из имени
    p_mbus_table_name_copy_name = 'AUTOTEST_' + ordinary_table2  + '_CLM_354580'
    p_mbus_table_name_trigger_name = 'AUTOTEST_' + ordinary_table2 + '_trigger'  + '_CLM_354580'


# Создание и настройка тестовых данных
def create_test_data():
    sql_query_with_commit(
        """update packs p set p.pcct_pcct_id=4, p.ptyp_ptyp_id=1 where p.pack_id in ({pack_id_2}, {pack_id_4}, {pack_id_5}, {pack_id_6})""".format(
            pack_id_2=TD.p_pack_id_2, pack_id_4=TD.p_pack_id_4, pack_id_5=TD.p_pack_id_5, pack_id_6=TD.p_pack_id_6))
    sql_query_with_commit(
        """update pack_types pt set pt.tarif_modify='Y' where pt.ptyp_id in (1)""".format())
    sql_query_with_commit(
        """update packs p set p.pcct_pcct_id=4, p.ptyp_ptyp_id=2 where p.pack_id in ({pack_id_1})""".format(pack_id_1=TD.p_pack_id_1))
    sql_query_with_commit(
        """update packs p set p.recurring_flag=1 where p.pack_id in ({pack_id_1}, {pack_id_2}, {pack_id_4}, {pack_id_5}, {pack_id_6})""".format(pack_id_1=TD.p_pack_id_1, pack_id_2=TD.p_pack_id_2, pack_id_4=TD.p_pack_id_4, pack_id_5=TD.p_pack_id_5, pack_id_6=TD.p_pack_id_6))
    sql_query_with_commit(
        """delete from pack_types_restrictions pt where (pt.ptyp_ptyp_id_1 in (select p.ptyp_ptyp_id from packs p where p.pack_id={pack_id_2}) or pt.ptyp_ptyp_id in (select p.ptyp_ptyp_id from packs p where p.pack_id={pack_id_2})) or (ptyp_ptyp_id=2 and ptyp_ptyp_id_1=2) """.format(pack_id_2=TD.p_pack_id_2))
    sql_query_with_commit(
        """begin insert into pack_types_restrictions (ptyp_ptyp_id, ptyp_ptyp_id_1, check_rules) values (2, 2, 1); end;""")
    sql_query_with_commit(
        """delete from pack_rtpl pr where pr.rtpl_rtpl_id=1191 and pr.pack_pack_id in ({pack_id_1}, {pack_id_2}, {pack_id_6}) """.format(pack_id_1=TD.p_pack_id_1, pack_id_2=TD.p_pack_id_2, pack_id_6=TD.p_pack_id_6))
    sql_query_with_commit(
        """begin insert into pack_rtpl (PACK_PACK_ID, RTPL_RTPL_ID, DEL_DATE) values ({pack_id_1}, {rateplanId}, to_date('31-12-2999', 'dd-mm-yyyy')); insert into pack_rtpl (PACK_PACK_ID, RTPL_RTPL_ID, DEL_DATE) values ({pack_id_2}, {rateplanId}, to_date('31-12-2999', 'dd-mm-yyyy')); insert into pack_rtpl (PACK_PACK_ID, RTPL_RTPL_ID, DEL_DATE) values ({pack_id_6}, {rateplanId}, to_date('31-12-2999', 'dd-mm-yyyy')); end;""".format(pack_id_1=TD.p_pack_id_1, pack_id_2=TD.p_pack_id_2, pack_id_6=TD.p_pack_id_6, rateplanId=TD.p_rateplanId[0]))
    sql_query_with_commit(
        """delete FLEXPACK_RANGE fr where fr.flpk_flpk_id in (select fp.flpk_id from FLEXPACKS fp where 
        fp.pack_pack_id in ({pack_id_1}, {pack_id_2}, {pack_id_4}, {pack_id_5}, {pack_id_6}))""".format(
            pack_id_1=TD.p_pack_id_1, pack_id_2=TD.p_pack_id_2, pack_id_4=TD.p_pack_id_4, pack_id_5=TD.p_pack_id_5, pack_id_6=TD.p_pack_id_6))
    sql_query_with_commit(
        """delete FLEXPACKS fl where fl.pack_pack_id in ({pack_id_1}, {pack_id_2}, {pack_id_4}, {pack_id_5}, {pack_id_6})""".format(pack_id_1=TD.p_pack_id_1, pack_id_2=TD.p_pack_id_2, pack_id_4=TD.p_pack_id_4, pack_id_5=TD.p_pack_id_5, pack_id_6=TD.p_pack_id_6))
    sql_query_with_commit(
        """begin insert into FLEXPACKS (FLPK_ID, PACK_PACK_ID, MUNT_MUNT_ID) values (10001, {pack_id_1}, 4); insert into 
        FLEXPACKS (FLPK_ID, PACK_PACK_ID, MUNT_MUNT_ID) values (10002, {pack_id_2}, 1); insert into 
        FLEXPACKS (FLPK_ID, PACK_PACK_ID, MUNT_MUNT_ID) values (10003, {pack_id_5}, 1); insert into 
        FLEXPACKS (FLPK_ID, PACK_PACK_ID, MUNT_MUNT_ID) values (10004, {pack_id_6}, 1); end;""".format(
            pack_id_1=TD.p_pack_id_1, pack_id_2=TD.p_pack_id_2, pack_id_5=TD.p_pack_id_5, pack_id_6=TD.p_pack_id_6))
    sql_query_with_commit(
        """begin insert into FLEXPACK_RANGE (FLRN_ID, FLRN_PARENT_ID, RANGE_START, RANGE_END, FLRN_PRICE, 
        FLPK_FLPK_ID) values (20001, null, {range_start_1}, {range_end_1}, {price_for_range_1}, 10002); insert into 
        FLEXPACK_RANGE ( FLRN_ID, FLRN_PARENT_ID, RANGE_START, RANGE_END, FLRN_PRICE, FLPK_FLPK_ID) values (20002, 
        20001, {range_start_2}, {range_end_2}, {price_for_range_2}, 10002); insert into FLEXPACK_RANGE (FLRN_ID, 
        FLRN_PARENT_ID, RANGE_START, RANGE_END, FLRN_PRICE, FLPK_FLPK_ID) values (20003, 20002, {range_start_3}, 
        {range_end_3}, {price_for_range_3}, 10002); insert into FLEXPACK_RANGE (FLRN_ID, FLRN_PARENT_ID, RANGE_START, 
        RANGE_END, FLRN_PRICE, FLPK_FLPK_ID) values (20004, null, {range_start_1}, {range_end_1}, 
        {price_for_range_3}, 10001); insert into FLEXPACK_RANGE (FLRN_ID, FLRN_PARENT_ID, RANGE_START, RANGE_END, 
        FLRN_PRICE, FLPK_FLPK_ID) values (20005, null, {range_start_1}, {range_end_1}, {price_for_range_1}, 
        10004); end;""".format( range_start_1=TD.p_range_start_1, range_end_1=TD.p_range_end_1, range_start_2=TD.p_range_start_2, range_end_2=TD.p_range_end_2, range_start_3=TD.p_range_start_3, range_end_3=TD.p_range_end_3, price_for_range_1=TD.p_price_for_range_1, price_for_range_2=TD.p_price_for_range_2, price_for_range_3=TD.p_price_for_range_3))
    sql_query_with_commit(
        """delete subs_packs sp where sp.pack_pack_id in ({pack_id_1}, {pack_id_2}, {pack_id_4}, {pack_id_5}, {pack_id_6}) and 
        sp.subs_subs_id = {subscriberId}""".format(
            pack_id_1=TD.p_pack_id_1, pack_id_2=TD.p_pack_id_2, pack_id_4=TD.p_pack_id_4, pack_id_5=TD.p_pack_id_5, pack_id_6=TD.p_pack_id_6, subscriberId=TD.p_subscriberId))
    sql_query_with_commit(
        """begin insert into subs_packs (SUBS_SUBS_ID, PACK_PACK_ID, NUMBER_HISTORY, START_DATE, END_DATE, NAVI_USER, NAVI_DATE, TRACE_NUMBER, ADD_COMMENT, CHANGE_USER, PACA_PACA_ID, PACA_DATE_FROM, EXT_SWITCH_ORDER_YN, PROD_PROD_ID, UPDATE_COMMENT, DELETE_COMMENT, ADD_ACTION_ID, UPDATE_ACTION_ID, DELETE_ACTION_ID, FLEX_AMOUNT, FLEX_VOLUME) values ({subscriberId}, {pack_id_1}, 1, to_date('15-07-2020 18:28:42', 'dd-mm-yyyy hh24:mi:ss'), to_date('31-12-2999', 'dd-mm-yyyy'), 'BIS', to_date('15-07-2020 18:28:42', 'dd-mm-yyyy hh24:mi:ss'), 52606996, null, null, null, null, null, null, null, null, 12370356, 12370357, 12370358, {flex_amount}, {flex_volume});  end;""".format(
            pack_id_1=TD.p_pack_id_1, subscriberId=TD.p_subscriberId, flex_amount=TD.p_flex_amount, flex_volume=TD.p_flex_volume))
    sql_query_with_commit(
        """update app_parameters a set a.value_string=null where a.prmt_id=2172""")
    sql_query_with_commit(
        """delete discount_plan_histories  dph where dph.dcpl_dcpl_id={dcpl_id}""".format(dcpl_id=TD.p_dcpl_id))
    sql_query_with_commit(
        """delete discount_plans dp where dp.dcpl_id={dcpl_id} or dp.pack_pack_id={pack_id_2}""".format(pack_id_2=TD.p_pack_id_2, dcpl_id= TD.p_dcpl_id))
    sql_query_with_commit(
        """begin insert into discount_plans (DCPL_ID, DEF, RTPL_RTPL_ID, PACK_PACK_ID, DCTP_DCTP_ID, DCMR_DCMR_ID, DCMR_DCMR_ID1, DCMR_DCMR_ID2, DATP_DATP_ID, DCCL_DCCL_ID, DCST_DCST_ID, DCPA_DCPA_ID, DCCA_DCCA_ID, DCPL_COMMENT, DCGR_DCGR_ID, AUTOMATIC_YN, BRT_INFORM, BRT_ACTION, PRIORITY, BRT_MIN_QUOTA, DPCT_DPCT_ID, DBSL_DBSL_ID, HISTORY_PERIOD, DELETE_UNUSED, DENY_PACK_ID, ALIGN_TUNT_ID, RNDT_RNDT_ID, COMMON_CLCR_DCTR_VOLUME_YN, BIS_INFORM, MSRR_MSRR_ID, DMCT_DMCT_ID, IGNORE_SUBS_PACK_CHARGES, ALIGN_QUOTA_BY_DCTV, IS_FINAL, ROLL_OVER_ALLOWED, ROLL_OVER_PACK_ID) values ({dcpl_id}, 'discount_plan_autotest', 0, {pack_id_2}, 4, 4, 0, 3, 0, 1, 1, 3, 1, 'discount_plan_autotest', null, 'N', null, 1, 0, 1.000000, 2, 3, null, 'Y', null, 1, null, 'N', null, 14, 0, 'N', 'N', 'N', 0, null);  end;""".format(pack_id_2=TD.p_pack_id_2, dcpl_id= TD.p_dcpl_id))
    sql_query_with_commit(
        """begin insert into discount_plan_histories (DCPL_DCPL_ID, NUMBER_HISTORY, DURATION, DURATION_WAIT, START_USE, END_USE, START_DATE, END_DATE, NAVI_USER, NAVI_DATE, CLCR_VOLUME) values ({dcpl_id}, 1, 99999, 0, to_date('01-12-2018', 'dd-mm-yyyy'), to_date('31-12-2999', 'dd-mm-yyyy'), to_date('01-12-2018', 'dd-mm-yyyy'), to_date('31-12-2999', 'dd-mm-yyyy'), 'BIS', to_date('26-11-2018 10:38:32', 'dd-mm-yyyy hh24:mi:ss'), 1.000000);  end;""".format(dcpl_id=TD.p_dcpl_id))

    p_sordId = sql_query_return_matrix(
        """select sop.sord_sord_id from SUBS_ORDER_PACKS sop where sop.pack_pack_id={pack_id_2}""".format(pack_id_2=TD.p_pack_id_2))
    for i in range(len(p_sordId)):
        sql_query_with_commit(
            """delete SUBS_ORDER_PACKS sop where sop.pack_pack_id={pack_id_2} and sop.sord_sord_id={sord_id}""".format(
                pack_id_2=TD.p_pack_id_2, sord_id=p_sordId[i][0]))
        sql_query_with_commit(
            """delete SUBS_ORDERS ss where ss.sord_id={sord_id}""".format(sord_id=p_sordId[i][0]))

    p_sordId = sql_query_return_matrix(
        """select sop.sord_sord_id from SUBS_ORDER_PACKS sop where sop.pack_pack_id={pack_id_6}""".format(pack_id_6=TD.p_pack_id_6))
    for i in range(len(p_sordId)):
        sql_query_with_commit(
            """delete SUBS_ORDER_PACKS sop where sop.pack_pack_id={pack_id_6} and sop.sord_sord_id={sord_id}""".format(
                pack_id_6=TD.p_pack_id_6, sord_id=p_sordId[i][0]))
        sql_query_with_commit(
            """delete SUBS_ORDERS ss where ss.sord_id={sord_id}""".format(sord_id=p_sordId[i][0]))

def setup_setting_for_MBUS():
    # включим нотификацию о подключении пакета и о заказе на подключение пакета в таблице BIS_EVENT_TO_MBUS
    sql_query_with_commit(
        """update BIS_EVENT_TO_MBUS t set t.flag_notify='Y' where t.bemb_id in (19, 61)""".format())
    # удалим сообщения из таблицы  MBUS_MSG_BIS_NOTIFY с routing_key= 'ps.pack_activate' и routing_key= 'ps.bis2cart.order_pack_add'
    sql_query_with_commit(
        """delete from {mbusTableName} m where m.routing_key LIKE '{routing_key_1}%' or m.routing_key LIKE '{routing_key_2}%'""".format(
            routing_key_1=TD.p_routing_key_for_pack_activate, routing_key_2=TD.p_routing_key_for_order_pack, mbusTableName=TD.p_mbus_table_name))
    # удаляем сообщения в таблице-копии
    sql_query_with_commit(
        """delete from {mbusTableName} m where m.routing_key LIKE '{routing_key_1}%' or m.routing_key LIKE '{routing_key_2}%'""".format(
            routing_key_1=TD.p_routing_key_for_pack_activate, routing_key_2=TD.p_routing_key_for_order_pack, mbusTableName=TD.p_mbus_table_name_copy_name))

def make_success_message_from_CART(p_routing_key_from_CART, p_orderId, p_errorCode):
    # моделируем положительный ответ от CART
    # p_errorCode = 0 - успешное подключение, p_errorCode = 1 - отказ в подключении пакета
    conn = connection_to_db()
    cr = conn.cursor()
    p_msg_body_fast = json.dumps({"orderId": p_orderId, "errorCode": p_errorCode})
    # Вызваем процедуру bis_subscriber_pg.process_cart_messages для эмуляции положительного ответа от CART на заявку о подключении пакета
    sql = """begin bis_subscriber_pg.process_cart_messages(routing_key => '{routing_key}',
                                          header => 'header_1',
                                          msg_body_fast => '{msg_body_fast}',
                                          msg_body_slow => null);
                end; """.format(routing_key=TD.p_routing_key_from_CART, msg_body_fast=p_msg_body_fast, p_errorCode=p_errorCode)
    try:
        cr.execute(sql)
    except cx_Oracle.DatabaseError as e:
        printException(e)
    conn.commit()
    conn.close()


#Проверка OAPI-функции BACKEND
@pytest.mark.OAPI_BIS_API_BACKEND
@pytest.mark.API_CLNT_BASE
@pytest.mark.BIS_NOTIFY
@pytest.mark.skipif(pytest_check_configuration()['status'] != 0, reason=pytest_check_configuration()['reason'])
class TestSuite_OAPI_FLEXPACK_BACKEND(outlog):
    subscriberFlexpackId_2 = ""
    subscriberFlexpackId_6 = ""
    p_orderId_2 = ""
    p_orderId_6 = ""
    @classmethod
    def setup_class(self):
        print(self.__name__, "=================== > setup_class ")
        #sql_query_with_commit("""drop table {tablecopy_name}""".format(tablecopy_name=p_mbus_table_name_copy_name))
        # подготовка тестовых данных
        create_test_data()
        # подготовка данных для проверки сообщения в MBUS
        setup_setting_for_MBUS()
        # Создание таблицы-копии:
        create_copy_of_table(TD.p_mbus_table_name, TD.p_mbus_table_name_copy_name)
        # Создание триггера:
        create_trigger_on_table_for_copy(TD.p_mbus_table_name, TD.p_mbus_table_name_copy_name, TD.p_mbus_table_name_trigger_name)

    @classmethod
    def teardown_class(self):
        print("\n", self.__name__, "====================================== > teardown_class \n")
        # Удаляем триггер и таблицу-копию
        drop_trigger(TD.p_mbus_table_name_trigger_name)
        drop_table(TD.p_mbus_table_name_copy_name)

    # Проверка OAPI-функции BACKEND: GET http://{{backendUrl}}/oapi-bis-backend-{{obab_version}}/backend/flexpacks/{flexpackId}/parameters получения параметров заказного пакета
    # получение параметров заказного пакета
    def test_get_flexpacks_parameters(self):
        backend_url = "flexpacks/{flexpackId}/parameters".format(flexpackId=TD.p_pack_id_1)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['deactivationDate'] == "2999-12-31T00:00:00"

    # заказной пакет не найден
    def test_get_flexpacks_parameters_FlexpackNotFound(self):
        backend_url = "flexpacks/{flexpackId}/parameters".format(flexpackId=TD.p_pack_id_3)
        res = post_or_get_request_backend('GET', backend_url, {})
        # print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 404
        jsonObj = json.loads(res.response_text)
        assert jsonObj['errorCode'] == "FlexpackNotFound"

   # Проверка OAPI-функции BACKEND: GET http://{{backendUrl}}/oapi-bis-backend-{{obab_version}}/backend/subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId} получения детальной информации по подключенному абоненту заказному пакету
    # получение детальной информации по подключенному абоненту заказному пакету (есть запись в таблице subs_packs)
    def test_get_subscriberflexpack(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId_1}".format(subscriberId=TD.p_subscriberId, subscriberFlexpackId_1=TD.p_subscriberFlexpackId_1)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['subscriberFlexpackId'] == TD.p_subscriberFlexpackId_1
        assert jsonObj['pack']['packId'] == TD.p_pack_id_1
        assert jsonObj['category']['packCategoryId'] == 4
        assert jsonObj['category']['name'] == "Заказной пакет"
        assert jsonObj['volume'] == TD.p_flex_volume
        assert jsonObj['amount'] == TD.p_flex_amount

   # указан не существующий абонент
    def test_get_subscriberflexpack_SubscriberNotFound(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId_1}".format(subscriberId=-1, subscriberFlexpackId_1=TD.p_subscriberFlexpackId_1)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 404
        jsonObj = json.loads(res.response_text)
        assert jsonObj['errorCode'] == "SubscriberNotFound"

   # Проверка OAPI-функции BACKEND: GET http://{{backendUrl}}/oapi-bis-backend-{{obab_version}}/backend/subscribers/{subscriberId}/flexpacks/availableForActivate/search получения заказных пакетов, доступных для подключения абоненту
    def test_get_flexpack_availableForActivate(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/availableForActivate/search".format(subscriberId=TD.p_subscriberId)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200

   # Проверка OAPI-функции BACKEND: POST http://{{backendUrl}}/oapi-bis-backend-{{obab_version}}/backend/subscribers/{subscriberId}/flexpacks/availableForActivate/search получения заказных пакетов, доступных для подключения абоненту
    def test_post_flexpack_availableForActivate(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/availableForActivate/search".format(subscriberId=TD.p_subscriberId)
        res = post_or_get_request_backend('POST', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200

   # Проверка OAPI-функции BACKEND: POST http://{{backendUrl}}/oapi-bis-backend-{{obab_version}}/backend/subscribers/{subscriberId}/flexpacks/activate/check проверки возможности подключения заказного пакета абоненту
    # без передачи обязательного входного параметра packI
    def test_post_flexpack_activateCheck_without_mandatory_param_packId(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 400

    # без передачи обязательного входного параметра ratePlanId
    def test_post_flexpack_activateCheck_without_mandatory_param_ratePlanId(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_3, "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 400

    # без передачи обязательного входного параметра volume
    def test_post_flexpack_activateCheck_without_mandatory_param_volume(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_3, "ratePlanId": TD.p_rateplanId[0]}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 400

   # пакет не заказной
    def test_post_flexpack_activateCheck_not_flexpack(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_3, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['conflicts'][0]['code'] == "FlexpackNotFound"

   # заказной пакет уже подключен
    def test_post_flexpack_activateCheck_already_activate(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_1, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['conflicts'][0]['code'] == "IncompatiblePacks"

   # пакет заказной, но нет записи в таблице FLEXPACKS
    def test_post_flexpack_activateCheck_not_in_FLEXPACKS(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_4, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['conflicts'][0]['code'] == "FlexpackNotFound"

   # заказной пакет, есть запись в таблице FLEXPACKS, нет записи в таблице FLEXPACK_RANGE
    def test_post_flexpack_activateCheck_not_in_FLEXPACK_RANGE(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_5, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['conflicts'][0]['code'] == "FlexpackNotFound"

   # volume < range_start (объём меньше нижней границы самого первого интервала)
    def test_post_flexpack_activateCheck_volume_out_min(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_2, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_out_min}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['conflicts'][0]['code'] == "BadVolume"

   # volume > range_end (объём больше верхней границы самого последнего интервала)
    def test_post_flexpack_activateCheck_volume_out_max(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_2, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_out_max}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['conflicts'][0]['code'] == "BadVolume"

   # все проверки пройдены, нет конфликтов для подключаемого заказного пакета
    def test_post_flexpack_activateCheck_not_conflicts(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_2, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_2_range}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['conflicts'] == []

   # Проверка OAPI-функции BACKEND: GET  http://{{backendUrl}}/oapi-bis-backend-{{obab_version}}/backend/flexpacks/{flexpackId}/amount?volume= получения стоимости переданного объема заказного пакета
    # без передачи обязательного входного параметра volume
    def test_get_flexpack_amount_without_mandatory_param(self):
        backend_url = "flexpacks/{flexpackId}/amount".format(flexpackId=TD.p_pack_id_3)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 400

   # пакет не заказной
    def test_get_flexpack_amount_not_flexpack(self):
        backend_url = "flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_3, volume = TD.p_volume_in_1_range)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 404
        jsonObj = json.loads(res.response_text)
        assert jsonObj['errorCode'] == "FlexpackNotFound"

   # пакет заказной, но нет записи в таблице FLEXPACKS
    def test_get_flexpack_amount_not_in_FLEXPACKS(self):
        backend_url = "flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_4, volume = TD.p_volume_in_1_range)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 404
        jsonObj = json.loads(res.response_text)
        assert jsonObj['errorCode'] == "FlexpackNotFound"

   # заказной пакет, есть запись в таблице FLEXPACKS, нет записи в таблице FLEXPACK_RANGE
    def test_get_flexpack_amount_not_in_FLEXPACK_RANGE(self):
        backend_url = "flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_5, volume = TD.p_volume_in_1_range)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 404
        jsonObj = json.loads(res.response_text)
        assert jsonObj['errorCode'] == "FlexpackNotFound"

   # volume < range_start (объём меньше нижней границы самого первого интервала)
    def test_get_flexpack_amount_volume_out_min(self):
        backend_url = "flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_2, volume = TD.p_volume_out_min)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 422
        jsonObj = json.loads(res.response_text)
        assert jsonObj['errorCode'] == "BadVolume"

   # volume > range_end (объём больше верхней границы самого последнего интервала)
    def test_get_flexpack_amount_volume_out_max(self):
        backend_url = "flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_2, volume = TD.p_volume_out_max)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 422
        jsonObj = json.loads(res.response_text)
        assert jsonObj['errorCode'] == "BadVolume"

   # объём попадает в первый интервал
    def test_get_flexpack_amount_volume_in_range_1(self):
        backend_url = "flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_2, volume = TD.p_volume_in_1_range)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Значение входного параметра volume = ', TD.p_volume_in_1_range)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['amount'] == TD.p_volume_in_1_range * TD.p_price_for_range_1

   # объём попадает во второй интервал
    def test_get_flexpack_amount_volume_in_range_2(self):
        backend_url = "flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_2, volume = TD.p_volume_in_2_range)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Значение входного параметра volume = ', TD.p_volume_in_2_range)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['amount'] == TD.p_range_end_1 * TD.p_price_for_range_1 + (TD.p_volume_in_2_range - TD.p_range_end_1) * TD.p_price_for_range_2

   # объём попадает во третий интервал
    def test_get_flexpack_amount_volume_in_range_3(self):
        backend_url = "flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_2, volume = TD.p_volume_in_3_range)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Значение входного параметра volume = ', TD.p_volume_in_3_range)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['amount'] == TD.p_range_end_1 * TD.p_price_for_range_1 + (TD.p_range_end_2 - TD.p_range_end_1) * TD.p_price_for_range_2 + (TD.p_volume_in_3_range - TD.p_range_end_2) * TD.p_price_for_range_3

######################################################################################################################################
# Проверка свей цепочки бизнес-процесса, когда от CART приходит положительный ответ на заявку на подключение пакета
######################################################################################################################################

   # Проверка OAPI-функции BACKEND: POST http://{{backendUrl}}/oapi-bis-backend-{{obab_version}}/backend//subscribers/{subscriberId}/flexpacks/activate подключения заказного пакета абоненту
    def post_flexpack_activate(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/activate".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_2, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_2_range}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_2 = jsonObj['subscriberFlexpackId']
        return TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_2

    # Проверка заявки на подключение заказного пакета абоненту, созданной в предыдущем тесте (получение детальной
    # информации по заказному пакету, когда созданы записи в таблицах SUBS_ORDERS и SUBS_ORDER_PACKS,
    # записи в subs_packs ещё нет)
    def get_subscriberflexpack_subs_order(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId_2}".format(subscriberId=TD.p_subscriberId, subscriberFlexpackId_2=TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_2)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['subscriberFlexpackId'] == TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_2
        assert jsonObj['pack']['packId'] == TD.p_pack_id_2
        assert jsonObj['category']['packCategoryId'] == 4
        assert jsonObj['category']['name'] == "Заказной пакет"
        assert jsonObj['volume'] == TD.p_volume_in_2_range
        assert jsonObj['amount'] == TD.p_range_end_1 * TD.p_price_for_range_1 + (TD.p_volume_in_2_range - TD.p_range_end_1) * TD.p_price_for_range_2

   #  Проверка создания сообщения в MBUS от BIS для CART Exchange = ps.msg_bis_notify, Routing Key = ps.bis2cart.order_pack_add по событию BIS_EVENT_TO_MBUS.BEMB_ID=61
    def get_MBUS_message_from_BIS_to_CART(self):
       # Проверим, что в буферную таблицу MBUS_MSG_BIS_NOTIFY добавилась новая запись с нотификацией о заказе на подключение пакета
       msg = sql_query_return_one_row(
           """select m.msg_body_fast from {mbusTableName} m where m.routing_key LIKE '{routing_key}%'""".format(
               routing_key=TD.p_routing_key_for_order_pack, mbusTableName=TD.p_mbus_table_name_copy_name))
       jsonObj = json.loads(msg[0])
       assert jsonObj["subscriberId"] == TD.p_subscriberId
       TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_2 = int(TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_2.replace(str(TD.p_pack_id_2), '').replace('o', ''))
       assert jsonObj["orderId"] == TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_2
       assert jsonObj["packId"] == TD.p_pack_id_2
       assert jsonObj["ratePlanId"] == TD.p_rateplanId[0]
       assert jsonObj["flexpack_amount"] == TD.p_range_end_1 * TD.p_price_for_range_1 + (TD.p_volume_in_2_range - TD.p_range_end_1) * TD.p_price_for_range_2
       return TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_2

    # Проверка, что заявка на подключение находится в статусе 5 ("Заказ обрабатывается")
    def subs_order_status_equal_5(self):
       status = sql_query_return_one_row(
       """select ss.sost_sost_id from SUBS_ORDERS ss where ss.subs_subs_id={subscriberId} and ss.sord_id={orderId_2}""".format(subscriberId=TD.p_subscriberId, orderId_2=TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_2))
       assert status[0] == 5

    #  Проверка подключения заказного пакета и отправки в MBUS сообщения от BIS об активации пакета, после успешного ответа от CART на заявку о подключении пакета
    def check_activation_pack_and_message_from_BIS(self):
        # моделируем положительный ответ от CART на заявку о подключении пакета
        make_success_message_from_CART(TD.p_routing_key_from_CART, TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_2, 0)

        # проверка, что пакет подключился
        p_trace_num_for_pack_2 = sql_query_return_one_row("""select sop.trace_number from SUBS_ORDER_PACKS sop where sop.pack_pack_id={pack_id_2} and sop.sord_sord_id={orderId_2}""".format(pack_id_2=TD.p_pack_id_2, orderId_2=TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_2))
        p_subscriberFlexpackId_2 = str(TD.p_pack_id_2) + 't' + str(p_trace_num_for_pack_2[0])
        backend_url = "subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId_3}".format(
            subscriberId=TD.p_subscriberId, subscriberFlexpackId_3=p_subscriberFlexpackId_2)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['subscriberFlexpackId'] == p_subscriberFlexpackId_2
        assert jsonObj['pack']['packId'] == TD.p_pack_id_2
        assert jsonObj['status']['packStatusId'] == 1
        assert jsonObj['category']['packCategoryId'] == 4
        assert jsonObj['category']['name'] == "Заказной пакет"
        assert jsonObj['volume'] == TD.p_volume_in_2_range
        assert jsonObj['amount'] == TD.p_range_end_1 * TD.p_price_for_range_1 + (TD.p_volume_in_2_range - TD.p_range_end_1) * TD.p_price_for_range_2

    # Проверка, что заявка на подключение после подключения пакета перешла в статус 2 ("Заказ обработан успешно")
        status = sql_query_return_one_row(
            """select ss.sost_sost_id from SUBS_ORDERS ss where ss.subs_subs_id={subscriberId} and ss.sord_id={p_orderId_2}""".format(
                    subscriberId=TD.p_subscriberId, p_orderId_2=TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_2))
        assert status[0] == 2

        # проверка отправки в MBUS сообщения от BIS об активации пакета
        msg = sql_query_return_one_row(
            """select m.msg_body_fast from {mbusTableName} m where m.routing_key LIKE '{routing_key}%'""".format(
                routing_key=TD.p_routing_key_for_pack_activate, mbusTableName=TD.p_mbus_table_name_copy_name))
        jsonObj = json.loads(msg[0])
        assert jsonObj["subscriberId"] == TD.p_subscriberId
        assert jsonObj["packId"] == TD.p_pack_id_2
        assert jsonObj["traceNumber"] == p_trace_num_for_pack_2[0]
        assert jsonObj["orderId"] == TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_2
        assert jsonObj["recurringFlag"] == 1
        assert jsonObj["ratePlanId"] == TD.p_rateplanId[0]
        assert jsonObj["packCategoryId"] == 4
        assert jsonObj["flexpack_amount"] == TD.p_range_end_1 * TD.p_price_for_range_1 + (TD.p_volume_in_2_range - TD.p_range_end_1) * TD.p_price_for_range_2

         # проверка создания call credit
        call_credit = sql_query_return_one_row(
            """select cc.volume from call_credits cc where cc.subs_subs_id={subscriberId} and cc.dcpl_dcpl_id={dcpl_id} and cc.trace_number={trace_num_for_pack_2}""".format(
                subscriberId=TD.p_subscriberId, dcpl_id=TD.p_dcpl_id, trace_num_for_pack_2=p_trace_num_for_pack_2[0]))
        assert call_credit[0] == TD.p_volume_in_2_range

    # Вызов проверки всей цепочки бизнес-процесса, когда от CART приходит положительный ответ на заявку на подключение пакета
    def test_positive_response_from_CART_for_activate_flexpack(self):
        # вызываем все шаги цепочки
        self.post_flexpack_activate()
        self.get_subscriberflexpack_subs_order()
        self.get_MBUS_message_from_BIS_to_CART()
        self.subs_order_status_equal_5()
        self.check_activation_pack_and_message_from_BIS()
        # следующий шаг проверяет, что после того, как заявка на подключение обработана успешно, можно опять подключить этот же пакет (и обрабатывает заявку, чтобы не оставалось необработанных заявок в БД)
        setup_setting_for_MBUS()
        self.post_flexpack_activate()
        self.get_subscriberflexpack_subs_order()
        self.get_MBUS_message_from_BIS_to_CART()
        self.subs_order_status_equal_5()
        self.check_activation_pack_and_message_from_BIS()


######################################################################################################################################
# Проверка свей цепочки бизнес-процесса, когда от CART приходит отрицательный ответ на заявку на подключение пакета
######################################################################################################################################

   # Проверка OAPI-функции BACKEND: POST http://{{backendUrl}}/oapi-bis-backend-{{obab_version}}/backend//subscribers/{subscriberId}/flexpacks/activate подключения заказного пакета абоненту
    # создаём заявку на подключения для проверки ситуации, когда от CART приходит отрицательный ответ
    def post_flexpack_activate_for_negative_response_from_CART(self):
        # почистим сообщения после предыдущего положительного сценария
        setup_setting_for_MBUS()
        backend_url = "subscribers/{subscriberId}/flexpacks/activate".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_6, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_backend('POST', backend_url, payload)
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_6 = jsonObj['subscriberFlexpackId']
        return TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_6

    # Проверка заявки на подключение заказного пакета абоненту, созданной в предыдущем тесте (получение детальной
    # информации по заказному пакету, когда созданы записи в таблицах SUBS_ORDERS и SUBS_ORDER_PACKS,
    # записи в subs_packs ещё нет)
    def get_subscriberflexpack_subs_order_for_negative_response_from_CART(self):
        backend_url = "subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId_6}".format(subscriberId=TD.p_subscriberId, subscriberFlexpackId_6=TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_6)
        res = post_or_get_request_backend('GET', backend_url, {})
        print('Ответ OAPI-функции', res.response_text)
        assert res.status_code == 200
        jsonObj = json.loads(res.response_text)
        assert jsonObj['subscriberFlexpackId'] == TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_6
        assert jsonObj['pack']['packId'] == TD.p_pack_id_6
        assert jsonObj['category']['packCategoryId'] == 4
        assert jsonObj['category']['name'] == "Заказной пакет"
        assert jsonObj['volume'] == TD.p_volume_in_1_range
        assert jsonObj['amount'] == TD.p_volume_in_1_range * TD.p_price_for_range_1

   #  Проверка создания сообщения в MBUS от BIS для CART Exchange = ps.msg_bis_notify, Routing Key = ps.bis2cart.order_pack_add по событию BIS_EVENT_TO_MBUS.BEMB_ID=61
    def get_MBUS_message_from_BIS_to_CART_for_negative_response_from_CART(self):
       # Проверим, что в буферную таблицу MBUS_MSG_BIS_NOTIFY добавилась новая запись с нотификацией о заказе на подключение пакета
       msg = sql_query_return_one_row(
           """select m.msg_body_fast from {mbusTableName} m where m.routing_key LIKE '{routing_key}%'""".format(
               routing_key=TD.p_routing_key_for_order_pack, mbusTableName=TD.p_mbus_table_name_copy_name))
       jsonObj = json.loads(msg[0])
       assert jsonObj["subscriberId"] == TD.p_subscriberId
       TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_6 = int(TestSuite_OAPI_FLEXPACK_BACKEND.subscriberFlexpackId_6.replace(str(TD.p_pack_id_6), '').replace('o', ''))
       assert jsonObj["orderId"] == TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_6
       assert jsonObj["packId"] == TD.p_pack_id_6
       assert jsonObj["ratePlanId"] == TD.p_rateplanId[0]
       assert jsonObj["flexpack_amount"] == TD.p_volume_in_1_range * TD.p_price_for_range_1
       return TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_6

    def subs_order_status_equal_5_for_negative_response_from_CART(self):
    # Проверка, что заявка на подключение находится в статусе 5 ("Заказ обрабатывается")
       status = sql_query_return_one_row(
       """select ss.sost_sost_id from SUBS_ORDERS ss where ss.subs_subs_id={subscriberId} and ss.sord_id={orderId_6}""".format(subscriberId=TD.p_subscriberId, orderId_6=TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_6))
       assert status[0] == 5

    #  Проверка, что заказной пакет не подключился, когда от CART пришёл отрицательный ответ на заявку о подключении пакета
    def check_activation_pack_and_message_from_BIS_for_negative_response_from_CART(self):
        # моделируем отрицательный ответ от CART на заявку о подключении пакета
        make_success_message_from_CART(TD.p_routing_key_from_CART, TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_6, 1)

        # Проверка, что заявка на подключение после подключения пакета перешла в статус 6 ("Заказ отклонен по балансу")
        status = sql_query_return_one_row(
            """select ss.sost_sost_id from SUBS_ORDERS ss where ss.subs_subs_id={subscriberId} and ss.sord_id={orderId_6}""".format(
                subscriberId=TD.p_subscriberId, orderId_6=TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_6))
        assert status[0] == 6

        # проверка, что пакет НЕ подключился
        p_trace_num_for_pack_6 = sql_query_return_one_row("""select sop.trace_number from SUBS_ORDER_PACKS sop where sop.pack_pack_id={pack_id_6} and sop.sord_sord_id={orderId_6}""".format(pack_id_6=TD.p_pack_id_6, orderId_6=TestSuite_OAPI_FLEXPACK_BACKEND.p_orderId_6))
        not_activate = sql_query_return_one_row(
            """select (select sp.number_history from subs_packs sp where sp.subs_subs_id={subscriberId} and sp.pack_pack_id={pack_id_6} and sp.trace_number={trace_num_for_pack_6}) from dual""".format(
                subscriberId=TD.p_subscriberId, pack_id_6=TD.p_pack_id_6, trace_num_for_pack_6=p_trace_num_for_pack_6[0]))
        assert not_activate[0] is None

    # проверка, что не создался call credit
        call_credit = sql_query_return_one_row(
            """select (select cc.volume from call_credits cc where cc.subs_subs_id={subscriberId} and cc.dcpl_dcpl_id={dcpl_id} and cc.trace_number={trace_num_for_pack_6}) from dual""".format(
                subscriberId=TD.p_subscriberId, dcpl_id=TD.p_dcpl_id, trace_num_for_pack_6=p_trace_num_for_pack_6[0]))
        assert call_credit[0] is None

    # Вызов проверки всей цепочки бизнес-процесса, когда от CART приходит отрицательный ответ на заявку на подключение пакета
    def test_negative_response_from_CART_for_activate_flexpack(self):
        # вызываем все шаги цепочки
        self.post_flexpack_activate_for_negative_response_from_CART()
        self.get_subscriberflexpack_subs_order_for_negative_response_from_CART()
        self.get_MBUS_message_from_BIS_to_CART_for_negative_response_from_CART()
        self.subs_order_status_equal_5_for_negative_response_from_CART()
        self.check_activation_pack_and_message_from_BIS_for_negative_response_from_CART()
        # следующий шаг проверяет, что после того, как заявка на подключение обработана с ошибкой, можно опять подключить этот же пакет
        setup_setting_for_MBUS()
        self.post_flexpack_activate_for_negative_response_from_CART()
        self.get_subscriberflexpack_subs_order_for_negative_response_from_CART()
        self.get_MBUS_message_from_BIS_to_CART_for_negative_response_from_CART()
        self.subs_order_status_equal_5_for_negative_response_from_CART()
        self.check_activation_pack_and_message_from_BIS_for_negative_response_from_CART()

#Проверка OAPI-функция FRONTEND
@pytest.mark.OAPI_BIS_BASE_API_FRONTEND
@pytest.mark.skipif(pytest_check_configuration()['status'] != 0, reason=pytest_check_configuration()['reason'])
class TestSuite_OAPI_FLEXPACK_FRONTEND(outlog):
    key_with_role = get_token_user_with_role()
    key_without_role = get_token_user_without_role()

    @classmethod
    def setup_class(self):
        print(self.__name__, "=================== > setup_class ")
        # подготовка тестовых данных
        #create_test_data()

    # Проверка frontend-вызова OAPI-функции GET http://{{frontendUrl}}/ps/v1/bis-base/flexpacks/{flexpackId}/parameters для пользоателя, у которого есть роль OAPI:v1:Subscriber:FlexpackActivate
    def test_get_flexpacks_parameters_frontend_with_role(self):

        front_url = "bis-base/flexpacks/{flexpackId}/parameters".format(flexpackId=TD.p_pack_id_1)
        res = post_or_get_request_frontend('GET', front_url, {}, self.key_with_role)
        print('OAPI status_code = ', res.status_code)
        assert res.status_code == 200
#
#     # Проверка frontend-вызова OAPI-функции GET http://{{frontendUrl}}/ps/v1/bis-base/flexpacks/{flexpackId}/parameters для пользоателя, у которого отсутствует роль OAPI:v1:Subscriber:FlexpackActivate
    def test_get_flexpacks_parameters_frontend_without_role(self):

        front_url = "bis-base/flexpacks/{flexpackId}/parameters".format(flexpackId=TD.p_pack_id_1)
        res = post_or_get_request_frontend('GET', front_url, {}, self.key_without_role)
        print('OAPI status_code = ', res.status_code)
        if res.status_code != 403:
            print('Ответ OAPI: ', res.response_text)
        assert res.status_code == 403

    # Проверка frontend-вызова OAPI-функции GET http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId} для пользоателя, у которого есть роль OAPI:v1:Subscriber:FlexpackBase
    def test_get_subscriberflexpack_frontend_with_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId_1}".format(subscriberId=TD.p_subscriberId, subscriberFlexpackId_1 = TD.p_subscriberFlexpackId_1)
        res = post_or_get_request_frontend('GET', front_url, {}, self.key_with_role)
        print('OAPI status_code = ', res.status_code)
        assert res.status_code == 200

    # Проверка frontend-вызова OAPI-функции GET http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId} для пользоателя, у которого отсутствует роль OAPI:v1:Subscriber:FlexpackBase
    def test_get_subscriberflexpack_frontend_without_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/{subscriberFlexpackId_1}".format(subscriberId=TD.p_subscriberId, subscriberFlexpackId_1 = TD.p_subscriberFlexpackId_1)
        res = post_or_get_request_frontend('GET', front_url, {}, self.key_without_role)
        print('OAPI status_code = ', res.status_code)
        if res.status_code != 403:
            print('Ответ OAPI: ', res.response_text)
        assert res.status_code == 403

    # Проверка frontend-вызова OAPI-функции GET http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/availableForActivate для пользоателя, у которого есть роль OAPI:v1:Subscriber:FlexpackActivate
    def test_get_flexpack_availableForActivate_frontend_with_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/availableForActivate".format(subscriberId=TD.p_subscriberId)
        res = post_or_get_request_frontend('GET', front_url, {}, self.key_with_role)
        print('OAPI status_code = ', res.status_code)
        assert res.status_code == 200

    # Проверка frontend-вызова OAPI-функции GET http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/availableForActivate для пользоателя, у которого отсутствует роль OAPI:v1:Subscriber:FlexpackActivate
    def test_get_flexpack_availableForActivate_frontend_without_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/availableForActivate".format(subscriberId=TD.p_subscriberId)
        res = post_or_get_request_frontend('GET', front_url, {}, self.key_without_role)
        print('OAPI status_code = ', res.status_code)
        if res.status_code != 403:
            print('Ответ OAPI: ', res.response_text)
        assert res.status_code == 403

    # Проверка frontend-вызова OAPI-функции POST http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/availableForActivate/search для пользоателя, у которого есть роль OAPI:v1:Subscriber:FlexpackActivate
    def test_post_flexpack_availableForActivate_frontend_with_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/availableForActivate/search".format(subscriberId=TD.p_subscriberId)
        res = post_or_get_request_frontend('POST', front_url, {}, self.key_with_role)
        print('OAPI status_code = ', res.status_code)
        assert res.status_code == 200

    # Проверка frontend-вызова OAPI-функции POST http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/availableForActivate/search для пользоателя, у которого отсутствует роль OAPI:v1:Subscriber:FlexpackActivate
    def test_post_flexpack_availableForActivate_frontend_without_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/availableForActivate/search".format(subscriberId=TD.p_subscriberId)
        res = post_or_get_request_frontend('POST', front_url, {}, self.key_without_role)
        print('OAPI status_code = ', res.status_code)
        if res.status_code != 403:
            print('Ответ OAPI: ', res.response_text)
        assert res.status_code == 403

    # Проверка frontend-вызова OAPI-функции POST http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/activate/check для пользоателя, у которого есть роль OAPI:v1:Subscriber:FlexpackActivate
    def test_post_flexpack_activateCheck_frontend_with_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_2, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_frontend('POST', front_url, payload, self.key_with_role)
        print('OAPI status_code = ', res.status_code)
        assert res.status_code == 200

    # Проверка frontend-вызова OAPI-функции POST http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/activate/check для пользоателя, у которого отсутствует роль OAPI:v1:Subscriber:FlexpackActivate
    def test_post_flexpack_activateCheck_frontend_without_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/activate/check".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_2, "ratePlanId":TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_frontend('POST', front_url, payload, self.key_without_role)
        print('OAPI status_code = ', res.status_code)
        if res.status_code != 403:
            print('Ответ OAPI: ', res.response_text)
        assert res.status_code == 403

    # Проверка frontend-вызова OAPI-функции GET http://{{frontendUrl}}/ps/v1/bis-base/flexpacks/{flexpackId}/amount?volume= для пользоателя, у которого есть роль OAPI:v1:Subscriber:FlexpackActivate
    def test_get_flexpack_amount_frontend_with_role(self):

        front_url = "bis-base/flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_2, volume = TD.p_volume_in_1_range)
        res = post_or_get_request_frontend('GET', front_url, {}, self.key_with_role)
        print('OAPI status_code = ', res.status_code)
        assert res.status_code == 200

    # Проверка frontend-вызова OAPI-функции GET http://{{frontendUrl}}/ps/v1/bis-base/flexpacks/{flexpackId}/amount?volume= для пользоателя, у которого отсутствует роль OAPI:v1:Subscriber:FlexpackActivate
    def test_get_flexpack_amount_frontend_without_role(self):

        front_url = "bis-base/flexpacks/{flexpackId}/amount?volume={volume}".format(flexpackId=TD.p_pack_id_2, volume = TD.p_volume_in_1_range)
        res = post_or_get_request_frontend('GET', front_url, {}, self.key_without_role)
        print('OAPI status_code = ', res.status_code)
        if res.status_code != 403:
            print('Ответ OAPI: ', res.response_text)
        assert res.status_code == 403

    # Проверка frontend-вызова OAPI-функции POST http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/activate для пользоателя, у которого есть роль OAPI:v1:Subscriber:FlexpackActivate
    def test_post_flexpack_activate_frontend_with_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/activate".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_6, "ratePlanId":TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_frontend('POST', front_url, payload, self.key_with_role)
        print('OAPI status_code = ', res.status_code)
        assert res.status_code == 200

    # Проверка frontend-вызова OAPI-функции POST  http://{{frontendUrl}}/ps/v1/bis-base/subscribers/{subscriberId}/flexpacks/activate для пользоателя, у которого отсутствует роль OAPI:v1:Subscriber:FlexpackActivate
    def test_post_flexpack_activate_frontend_without_role(self):

        front_url = "bis-base/subscribers/{subscriberId}/flexpacks/activate".format(subscriberId=TD.p_subscriberId)
        payload = {"packId": TD.p_pack_id_2, "ratePlanId": TD.p_rateplanId[0], "volume": TD.p_volume_in_1_range}
        res = post_or_get_request_frontend('POST', front_url, payload, self.key_without_role)
        print('OAPI status_code = ', res.status_code)
        if res.status_code != 403:
            print('Ответ OAPI: ', res.response_text)
        assert res.status_code == 403
