import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions
from azure.cosmos import PartitionKey
from azure_ad_verify_token import verify_jwt
from jose import JWTError

import config

HOST = config.settings['host']
MASTER_KEY = config.settings['master_key']
DATABASE_ID = config.settings['database_id']
CONTAINER_ID = config.settings['container_id']

AZURE_AD_APP_ID = config.settings['azure_ad_app_id']
AZURE_AD_ISSUER = config.settings['azure_ad_issuer']
AZURE_AD_JWKS_URI = config.settings['azure_ad_jwks_uri']

def init_connection():
    client = cosmos_client.CosmosClient(HOST, {'masterKey': MASTER_KEY}, user_agent="CosmosDBPythonQuickstart",
                                        user_agent_overwrite=True)
    try:
        try:
            db = client.create_database(id=DATABASE_ID)
            print('Database with id \'{0}\' created'.format(DATABASE_ID))

        except exceptions.CosmosResourceExistsError:
            db = client.get_database_client(DATABASE_ID)
            print('Database with id \'{0}\' was found'.format(DATABASE_ID))

        try:
            container = db.create_container(id=CONTAINER_ID, partition_key=PartitionKey(path='/partitionKey'))
            print('Container with id \'{0}\' created'.format(CONTAINER_ID))

        except exceptions.CosmosResourceExistsError:
            container = db.get_container_client(CONTAINER_ID)
            print('Container with id \'{0}\' was found'.format(CONTAINER_ID))

        return container

    except exceptions.CosmosHttpResponseError as e:
        print('\nrun_sample has caught an error. {0}'.format(e.message))

    finally:
        print("\nConnection with Azure Cosmos DB was successfully established.")

def validate_jwt(token):
    try:
        payload = verify_jwt(
            token=token,
            valid_audiences=AZURE_AD_APP_ID,
            issuer=AZURE_AD_ISSUER,
            jwks_uri=AZURE_AD_JWKS_URI,
            verify=True,
        )
        user_id = payload['sub']
        if user_id is None:
            # raise HTTPException(
            #     status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
            # )
            raise Exception()
        return payload
    except JWTError:
        # raise HTTPException(
        #     status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        # )
        raise Exception()
