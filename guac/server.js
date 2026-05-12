#!/usr/bin/env node

const GuacamoleLite = require('guacamole-lite');
const express = require('express');
const http = require('http');
const path = require('path');

const app = express();
const server = http.createServer(app);

const guacdOptions = { port: 4822 };

const args = process.argv.slice(2);
const key = args[0];

const clientOptions = {
    crypt: {
        cypher: 'AES-256-CBC',
        key: key
    }
};

const guacServer = new GuacamoleLite({ server }, guacdOptions, clientOptions);

app.use('/js', express.static(path.join(__dirname, 'node_modules/guacamole-common-js/dist/esm')));
app.use(express.static('public'));
server.listen(8080);
