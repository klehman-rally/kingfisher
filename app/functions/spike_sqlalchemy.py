
from os import getenv

from sqlalchemy import Boolean, Column, DateTime, Integer, LargeBinary, String
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    # Equivalent URL:
    # postgres://<DB_USER>:<DB_PASS>@/<DB_NAME>?host=/cloudsql/<GCP_PROJECT>:<GCP_ZONE>:<GCLOUD_SQL_INSTANCE>'
    URL(
        drivername='postgres',
        username=getenv('DB_USER'),
        password=getenv('DB_PASSWORD'),
        database=getenv('DB_NAME'),
        query={
            'host': '/cloudsql/{}:{}:{}'.format(
                getenv('GCP_PROJECT'),
                getenv('GCP_ZONE'),
                getenv('GCLOUD_SQL_INSTANCE')
            )
        }
    ),
)




Session = sessionmaker(bind=engine)

Base = declarative_base()


class Spiky(Base):
    __tablename__ = "spikemaster"

    foo_id = Column(Integer, primary_key=True)
    #count  = Column(Integer)
    #ready  = Column(Boolean)

    def __init__(self, foo_id):
        self.foo_id = foo_id
        #self.count  = 42
        #self.ready  = True

    #def __repr__(self):
    #    return '<foo_id {}>'.format(self.foo_id)

Base.metadata.create_all(engine)



#def thunderSpike(request):
#    print("I am here!")



def spikeTheDatabase(request):
    table_name = "Spiky"
    print("hello from the spike")
    if engine.dialect.has_table(engine, table_name):
        print(f"{table_name} exists")
    else:
        print(f"{table_name} does not exist. It was all lies.")

    session = Session()
    foo_id = 8822
    spiky = Spiky(foo_id)
    try:
        session.add(spiky)
        session.commit()
    except Exception as exc:
        print("failed to add spiky with id %s" % foo_id)

    if engine.dialect.has_table(engine, table_name):
        print(f"after instance creation, {table_name} exists")

        #foo1 = session.query(Spiky).filter(Spiky.foo_id == foo_id).first()
        foo1 = session.query(Spiky).first()
    else:
        print(f"after instance creation, {table_name} does not exist. It was all lies.")
    print("the spiky test function is done")

