from app import app
from time import time
from flask import render_template, redirect, url_for, session, request, json, jsonify
import requests
import os
from ast import literal_eval # 보안 상의 이유로 eval 대신 더 안전한 literal_eval 사용


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mypage')
def mypage() :
    return render_template('mypage.html')
@app.route('/signin')
def singin() :
    return render_template('signin.html')

@app.route('/signup')
def singup() :
    return render_template('signup.html')

@app.route('/tutorials')
def tutorials() :
    return render_template('tutorial.html')

@app.route('/credential')
def credential() :
    conn = False
    cred_def_ids = None
    if 'connection' in session :
        conn = True
        with requests.get('http://0.0.0.0:8021/credential-definitions/created') as cred_def_res :
            cred_def_ids = cred_def_res.json()['credential_definition_ids']
            # print(cred_def_ids)
    return render_template('credential.html', connection=conn, credential_definition_ids=cred_def_ids)

@app.route('/credential-process', methods=['POST'])
def credential_process() :
    cred_attrs = request.get_json(force=True) # 대표자가 전송한 증명서 관련 데이터
    cred_def_id = cred_attrs['credential_definition_id'] # cred_def_id 가져오기
    del(cred_attrs['credential_definition_id']) # cred_attrs에서 cred_def_id 제거
    cred_attrs['timestamp'] = str(int(time())) # cred_attrs에 timestamp 추가
    conn_id = session['connection']['conn_id'] # connectino id 가져오기

    offer_request_body = {
        "connection_id": conn_id,
        "comment": f"Offer on cred def id {cred_def_id}",
        "auto_remove": "false",
        "credential_preview": {
            "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
            "attributes": [
                {"name": n, "value": v}
                for (n, v) in cred_attrs.items()
            ]
        },
        "filter": {"indy": {"cred_def_id": cred_def_id}},
        "trace": "false"
    }

    with requests.post('http://0.0.0.0:8021/issue-credential-2.0/send-offer', json=offer_request_body) as offer_res :
        result = offer_res.json()
        cred_ex_id = result['cred_ex_id']

        working_directory = os.getcwd() # 현재 working directory 경로 가져오기
        credential_file = os.path.join(working_directory, 'app', 'static', 'credential_file', cred_ex_id) # 경로 병합해 새 경로 생성

        with open(credential_file, 'w') as f :
            f.write(str(result))

    return cred_ex_id

@app.route('/credential/<cred_ex_id>')
def credential_cred_ex_id(cred_ex_id) :
    working_directory = os.getcwd() # 현재 working directory 경로 가져오기
    credential_file = os.path.join(working_directory, 'app', 'static', 'credential_file', cred_ex_id) # 경로 병합해 새 경로 생성

    with open(credential_file, 'r') as f :
        credential_body = f.read().replace("'", '"') # 파일 내용 가져오기 (str)
        credential_body = literal_eval(credential_body) # str -> dict
        credential_body = json.dumps(credential_body, indent=4) # dict -> JSON 문자열
    return render_template('credential_issued.html', cred_ex_id=cred_ex_id, credential_body=credential_body)

@app.route('/chat')
def chatting() :
    return render_template('chat.html')




## 발급기관(faber)와 플라스크 서버(alice) 간 연결 ##
@app.route('/create-connection', methods=['POST'])
def create_connection() :
    with requests.post("http://0.0.0.0:8021/connections/create-invitation") as create_res :
        print("faber: create-invitation OK")
        invitation = create_res.json()['invitation'] # invitation 부분만 꺼내오기
        conn_id = create_res.json()['connection_id'] # connection id만 꺼내오기

        with requests.post("http://0.0.0.0:8031/connections/receive-invitation", json=invitation) as receive_res :
            my_did = receive_res.json()['my_did']

    ret = {
        "conn_id": conn_id,
        "my_did": my_did
    }
    session['connection'] = ret
    return ret

@app.route('/session-pop', methods=['POST'])
def session_pop() :
    session.clear()
    return 'session pop'

@app.route('/delete-connection', methods=['DELETE'])
def delete_connection() :
    conn_id = session['connection']['conn_id']
    with requests.delete(f'http://0.0.0.0:8021/connections/{conn_id}') as delete_res :
        ret = delete_res.json()
        session.pop('connection', None)
    return ret

@app.route('/create-schema', methods=['POST'])
def create_schema() :
    current = os.getcwd() # 현재 working directory 경로 가져오기
    schema = os.path.join(current, 'app', 'static', 'cashtransaction_schema.json')
    with open(schema, 'r') as f :
        schema_body = f.read()
        print(schema_body)
        with requests.post('http://0.0.0.0:8021/schemas', json=schema_body) as schema_res :
            print(schema_res.json())
            # schema_id = schema_res.json()['schema_id']
            # print(schema_id)
    return 'hi'

# # schema 등록
# @app.route('/register/cash-transaction', methods=['POST'])
# def register_cash_transaction() :
#     schema_body = {
#         "schema_name": "cash transaction schema",
#         "schema_version": "01",
#         "attributes": ["creditor","debtor", "amount",
#         "debt_term", "CapstoneCredential_no","approved_date", "timestamp"],
#     }

#     with requests.post('http://0.0.0.0:8021/schemas', json=schema_body) as schema_res :
#         schema_id = schema_res.json()['schema_id']
#         print("schema_id: " + schema_id)
#         credential_definition_body = {
#             "schema_id": schema_id,
#             "support_revocation": False,
#             "revocation_registry_size": 100,
#         }

#         with requests.post('http://0.0.0.0:8021/credential-definitions', json=credential_definition_body) as creddef_res :
#             credential_definition_id = creddef_res.json()['credential_definition_id']
#             print("credential_definition_id: " + credential_definition_id)

#     return "cash tranaction format registered"

# @app.route("/register/schema", methods=['POST'])
# def schema() :
#     schema_body = {
#         "schema_name": "cash transaction schema",
#         "schema_version": "01",
#         "attributes": ["creditor","debtor", "amount",
#         "debt_term", "CapstoneCredential_no","approved_date", "timestamp"],
#     }

#     with requests.post('http://0.0.0.0:8021/schemas', json=schema_body) as schema_res :
#         schema_id = schema_res.json()['schema_id']
#         print("schema_id: " + schema_id)
#     return 'schema registered'

