FROM mirrors.sangfor.com/node:22-slim AS base
ARG NPM_REGISTRY_URL="http://mirrors.sangfor.com/nexus/repository/npm"
ENV COREPACK_NPM_REGISTRY $NPM_REGISTRY_URL
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
RUN pnpm config set registry="http://mirrors.sangfor.com/nexus/repository/npm"
COPY . /app
WORKDIR /app

FROM base AS prod-deps
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --prod --frozen-lockfile

FROM base AS build
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
RUN pnpm run build

FROM mirrors.sangfor.com/nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
