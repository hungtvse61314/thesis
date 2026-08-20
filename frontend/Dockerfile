FROM node:23.7-alpine
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev"]
