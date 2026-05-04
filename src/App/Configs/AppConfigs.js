// App Configurations

export const SERVER = {
  PROTOCOL: process.env.REACT_APP_SERVER_PROTOCOL,
  SERVER_URL: process.env.REACT_APP_SERVER_URL,
  PORT: process.env.REACT_APP_SERVER_PORT,
  API_PREFIX: process.env.REACT_APP_API_PREFIX,
};

export const HTTP_METHODS = {
  GET: "GET",
  POST: "POST",
  PATCH: "PATCH",
  PUT: "PUT",
  DELETE: "DELETE",
  OPTIONS: "OPTIONS",
};

export let MASTER_DATA_SERVER = {
  SERVER_URL: process.env.REACT_APP_SERVER_URL,
  PORT: process.env.REACT_APP_SERVER_PORT,
  MASTER_ROUTE: process.env.REACT_APP_API_MASTER_ROUTE,
  PROTOCOL: process.env.REACT_APP_SERVER_PROTOCOL,
  PREFIX: process.env.REACT_APP_API_PREFIX,
};

/**
 * Build a base URL, omitting the port when it is the protocol default
 * (443 for https, 80 for http) to avoid malformed URLs on UAT/prod.
 */
function buildBaseUrl(protocol, host, port, prefix) {
  const isDefaultPort =
    (protocol === "https" && String(port) === "443") ||
    (protocol === "http" && String(port) === "80");
  const authority = isDefaultPort ? host : `${host}:${port}`;
  return `${protocol}://${authority}/${prefix}`;
}

export const BACKEND_SERVER_URL = buildBaseUrl(
  MASTER_DATA_SERVER.PROTOCOL,
  MASTER_DATA_SERVER.SERVER_URL,
  MASTER_DATA_SERVER.PORT,
  MASTER_DATA_SERVER.PREFIX
);

export const MASTER_DATA_SERVER_URL = {
  MASTER_DATA_SERVER_URL: buildBaseUrl(
    MASTER_DATA_SERVER.PROTOCOL,
    MASTER_DATA_SERVER.SERVER_URL,
    MASTER_DATA_SERVER.PORT,
    MASTER_DATA_SERVER.MASTER_ROUTE
  ),
};

export const BASE_URL = buildBaseUrl(
  SERVER.PROTOCOL,
  SERVER.SERVER_URL,
  SERVER.PORT,
  SERVER.API_PREFIX
);

export const BASE_URL_WITHOUT_PREFIX = BASE_URL.replace(
  `/${SERVER.API_PREFIX}`,
  ""
);

/* Cache setting details */
export const CACHE_SETTINGS = {
  cache: "no-cache",
};

/* Core setting details */
export const CORS_SETTINGS = {
  mode: "cors",
  credentials: "same-origin",
};

/* Header details with Auth token */
export let HEADER_JSON = {
  Accept: "application/json",
  Authorization: JSON.parse(
    localStorage.getItem(`${process.env.REACT_APP_TOKEN_PREFIX}-auth-token`)
  ),
  source: "workflow",
  req: "list",
};

export let HEADER_JSON_MAIL = {
  Accept: "application/json",
  "Content-Type": "application/json",
  Authorization: JSON.parse(sessionStorage.getItem("auth-token-mail")),
  source: "workflow",
  req: "list",
};

/* Type of credentials include */
const CREDENTIALS_INCLUDE = "include";
export const STANDARD_METHOD_OPTIONS = {
  credentials: CREDENTIALS_INCLUDE,
};