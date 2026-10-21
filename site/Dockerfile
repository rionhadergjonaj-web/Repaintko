FROM node:24-bookworm-slim
WORKDIR /app
COPY --chown=node:node package.json index.html version.json ./
COPY --chown=node:node web ./web
COPY --chown=node:node site ./site
RUN mkdir /data && chown node:node /data
USER node
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000 DATABASE_PATH=/data/community.sqlite
EXPOSE 3000
CMD ["node","site/server.mjs"]
