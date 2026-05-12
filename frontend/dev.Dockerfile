FROM node:24-slim

RUN useradd -m tidalcase

WORKDIR /app

COPY package*.json ./

RUN chown -R tidalcase:tidalcase /app

USER tidalcase

RUN npm install

CMD ["ng", "serve", "--host=0.0.0.0"]
