import { ApolloServer } from "apollo-server";
import { Neo4jGraphQL } from "@neo4j/graphql";
import { readFileSync } from "fs";
import db_driver from "./database.js";


// Load schema from .graphql file
const typeDefs = readFileSync("app/schema.graphql").toString("utf-8");

// Pass our GraphQL type definitions and Neo4j driver instance.
const neoSchema = new Neo4jGraphQL({ typeDefs, db_driver });

// Generate an executable GraphQL schema object and start Apollo Server.
const server = new ApolloServer({
    schema: await neoSchema.getSchema(),
    context: async ({ req }) => ({ req, executionContext: db_driver }),
});

server.listen().then(({ url }) => {
    console.log(`GraphQL server ready at ${url}`);
});
