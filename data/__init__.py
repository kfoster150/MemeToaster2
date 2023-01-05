from os import environ, path
from random import choice

import boto3
from pandas import DataFrame
from psycopg import connect

def sql_connect():

    __VERSION__ = environ["VERSION"]

    if __VERSION__ == "EC2":

        port = 5432
        user = "postgres"
        dbname = "test"

        ssm = boto3.client("ssm", region_name="us-west-1")
        host = ssm.get_parameter(Name="POSTGRESQL_HOST",
                                WithDecryption=True)["Parameter"]["Value"]
        password = ssm.get_parameter(Name="POSTGRESQL_PASSWORD",
                                WithDecryption=True)["Parameter"]["Value"]
    else:
        port = 5432
        user = "kenny"
        dbname = "MemeToasterTest"

        POSTGRESQL_HOST = "localhost"
        POSTGRESQL_PASSWORD = "admin"

    conn = connect(
        host = POSTGRESQL_HOST,
        port = port,
        user = user,
        password = POSTGRESQL_PASSWORD,
        dbname = dbname
    )

    return(conn)


def sql_tags(conn,
             tagsOnly = True,
             output = "Tuples"):

    if tagsOnly == True:
        query = "SELECT tag FROM tag;"
        columns = ["tag"]
    else:
        query = "SELECT * FROM tag"
        columns = ["id","tag"]
    

    with conn.cursor() as curs:
        curs.execute(query)
        tags = curs.fetchall()

    if output == "DataFrame":
        tags = DataFrame(tags, columns = columns)

    return(tags)


def sql_tags_counts(conn, output = "Tuples"):

    query_str = """
SELECT tg.tag, count(tf.filename_id)
FROM tag_filename AS tf
LEFT JOIN tag AS tg
ON tf.tag_id = tg.id
WHERE tg.tag <> ''
GROUP BY tg.tag
ORDER BY count(tf.filename_id) DESC, tg.tag;"""

    with conn.cursor() as curs:
        curs.execute(query_str)
        tags = curs.fetchall()

    if output == "DataFrame":
        tags = DataFrame(tags, columns = ['tag','count'])

    return(tags)

def query_filename_by_tag(tag, conn):
    query_by_tag = """
    SELECT filename FROM filename AS f
        LEFT JOIN tag_filename AS tf
        ON f.id = tf.filename_id
            LEFT JOIN tag
            ON tf.tag_id = tag.id
    WHERE tag.tag = %s;"""

    with conn.cursor() as curs:
        curs.execute(query_by_tag, (tag,))
        images = [im[0] for im in curs.fetchall()]

    imageChoice = choice(images)

    return(imageChoice)


def create_tag_list(conn):

    ##### Create tags list
    tagsList = sql_tags_counts(conn = conn)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(id) FROM tag;")
        num_tags = cur.fetchone()[0]
        cur.execute("SELECT COUNT(id) FROM filename;")
        num_pics = cur.fetchone()[0]

    # Write to StringIO, Create S3 session, and upload
    inptstr = 'empty.txt'
    with open(inptstr, 'w') as newfile:

        newfile.write(f"Number of tags: {num_tags}\n\n")
        newfile.write(f"Total number of pictures: {num_pics}\n\n")
        newfile.write("Number of pictures per tag:\n\n")

        for tag, count in tagsList:
            newfile.write(f"{tag}\n{count}\n\n")

    s3 = boto3.Session().resource('s3')

    s3.Bucket('memetoaster').upload_file(inptstr, "tags.txt")

conn = sql_connect()
create_tag_list(conn)
conn.close()