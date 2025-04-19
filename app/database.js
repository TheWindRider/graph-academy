import neo4j from "neo4j-driver"


const db_driver = neo4j.driver(
    process.env.NEO4J_URL,
    neo4j.auth.basic(
        process.env.NEO4J_USERNAME,
        process.env.NEO4J_PASSWORD,
    ),
);

export default db_driver;
