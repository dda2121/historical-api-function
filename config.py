import os

settings = {
    'host': os.environ.get('ACCOUNT_HOST', 'https://smart-house-no-sql-db.documents.azure.com:443/'),
    'master_key': os.environ.get('ACCOUNT_KEY', '4dkhGd3D4X3tIayKQ5JPAluZsydNvygNtU6QlR09KmIfoQUvu484thNwvTk0dDjaImBaE1Ug48k6ACDb94d1Jw=='),
    'database_id': os.environ.get('COSMOS_DATABASE', 'ToDoList'),
    'container_id': os.environ.get('COSMOS_CONTAINER', 'Items'),
    'azure_ad_app_id': '4dc0d731-4607-43b9-98a0-106360218432',
    'azure_ad_issuer': 'https://smarthouseadb2c.b2clogin.com/695e8875-da3e-4110-938f-1cfdfa3bb92e/v2.0/',
    'azure_ad_jwks_uri': 'https://smarthouseadb2c.b2clogin.com/smarthouseadb2c.onmicrosoft.com/B2C_1_SignUpSignIn/discovery/v2.0/keys'
}