import sys, os, io

save_stderr = sys.stderr
sys.stderr = io.StringIO()
import psycopg2
sys.stderr = save_stderr

TEMPLATE_DB_URL = "postgresql://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host=/cloudsql/{GCP_PROJECT}:{GCP_ZONE}:{GCLOUD_SQL_INSTANCE}"

#from app.utils.confenv import setVariables
#
#setVariables('environment/dev.env.yml')

WEBHOOK_ATTRIBUTES   = 'id,sub_id,name,target_url,object_types,conditions'
CONDITION_ATTRIBUTES = 'id,sub_id,attribute_uuid,attribute_name,operator,value'

SELECT = {'webhook'   : WEBHOOK_ATTRIBUTES,
          'condition' : CONDITION_ATTRIBUTES
         }

#####################################################################################################

def getQualifiers(target_table, sub_id):
    #if target_table == 'condition':
    #    columns = 'id,sub_id,attribute_uuid,attribute_name,operator,value'
    #else:
    #    columns = 'id,sub_id,name,target_url,object_types,conditions'
    columns = SELECT[target_table]
    criteria    = [('sub_id', '=', f'%(sub_id)s')]
    query_data  = {'sub_id' : sub_id }
    conditions  = 'WHERE '
    conditions += ' AND '.join([f'{item} {relation} {value_holder}' for item, relation, value_holder in criteria])
    dbconn = dbConnection()
    rows = []
    try:
        cur = dbconn.cursor()
        # query
        query_statement = f"select {columns} from {target_table} {conditions}"
        cur.execute(query_statement, query_data)
        rows = cur.fetchall()
        #print(rows)

        # close communication with the PostgreSQL database server
        cur.close()
        ## commit the changes
        #dbconn.commit()
    except Exception as error:
        print(error)
    finally:
        if dbconn is not None:
            dbconn.close()
    return rows

#####################################################################################################

def dbConnection():
    gcp_project = os.getenv('GCP_PROJECT')
    gcp_zone    = os.getenv('GCP_ZONE')
    db_instance = os.getenv('GCLOUD_SQL_INSTANCE')
    db_name     = os.getenv('DB_NAME')
    db_user     = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    database_uri = TEMPLATE_DB_URL.format( GCP_PROJECT=gcp_project, GCP_ZONE=gcp_zone,
                                           GCLOUD_SQL_INSTANCE=db_instance, DB_NAME=db_name,
                                           DB_USER=db_user, DB_PASSWORD=db_password)
    #print("Database URI: %s" % database_uri)
    # connect to the PostgreSQL server

    try:
       dbconn = psycopg2.connect(database_uri)
       return dbconn
    except:
       print("ERROR: Unable to get a Postgres DB Connection to %s / %s" % (db_instance, db_name))
       return None

#####################################################################################################
