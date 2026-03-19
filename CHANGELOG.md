# Changelog

## [1.11.0](https://github.com/G2BC/LUMM-server/compare/v1.10.1...v1.11.0) (2026-03-19)


### Features

* implement email notification for user approval with HTML template ([4d9663d](https://github.com/G2BC/LUMM-server/commit/4d9663db49569783836ac61e7c16e0fd38e61e88))

## [1.10.1](https://github.com/G2BC/LUMM-server/compare/v1.10.0...v1.10.1) (2026-03-19)


### Bug Fixes

* enhance user listing functionality with exclusion filter for current user ([e6ed78e](https://github.com/G2BC/LUMM-server/commit/e6ed78ea9cc3e9dba245ebace251070928638f46))

## [1.10.0](https://github.com/G2BC/LUMM-server/compare/v1.9.2...v1.10.0) (2026-03-19)


### Features

* add family and iucn_redlist fields to SpeciesDetailSchema for enhanced species data representation ([6e3771d](https://github.com/G2BC/LUMM-server/commit/6e3771d38517da0f493b2e6888a502baa27a0447))
* add species update endpoint and patch request schema for partial updates ([d720ac5](https://github.com/G2BC/LUMM-server/commit/d720ac58fed694628e37f26c558213aada732fcf))
* add user role update endpoint and schema for role management ([63743fd](https://github.com/G2BC/LUMM-server/commit/63743fdf87b056e56d770cca9042f141ae6916c7))
* enhance species selection with exclusion filter and similar species retrieval ([c74ee34](https://github.com/G2BC/LUMM-server/commit/c74ee3471b2bc20c8d1c61d179ec6ff138496e32))
* implement species selection endpoint with photo normalization and search functionality ([a8a23b2](https://github.com/G2BC/LUMM-server/commit/a8a23b27abe20e6e60b2c06b93cb3befddc009da))

## [1.9.2](https://github.com/G2BC/LUMM-server/compare/v1.9.1...v1.9.2) (2026-03-16)


### Bug Fixes

* enhance NCBI request handling with configurable retries and timeouts; update entrypoint for gunicorn settings ([895f447](https://github.com/G2BC/LUMM-server/commit/895f4471f80a736d56d6aab24444331e29b2442a))

## [1.9.1](https://github.com/G2BC/LUMM-server/compare/v1.9.0...v1.9.1) (2026-03-16)


### Bug Fixes

* validate species_id in get_ncbi_taxon_id method to ensure it is a non-empty digit ([1803e68](https://github.com/G2BC/LUMM-server/commit/1803e682627e1331ed6b54edf8b9e52a37d16385))

## [1.9.0](https://github.com/G2BC/LUMM-server/compare/v1.8.1...v1.9.0) (2026-03-16)


### Features

* integrate Sentry for error tracking and add sentry-sdk dependency ([f7ea33e](https://github.com/G2BC/LUMM-server/commit/f7ea33e5088341c4dce54acc06cc5bc70572c6a3))

## [1.8.1](https://github.com/G2BC/LUMM-server/compare/v1.8.0...v1.8.1) (2026-03-15)


### Bug Fixes

* update final prefix for species to streamline file organization ([0096724](https://github.com/G2BC/LUMM-server/commit/00967245a29f8764c29eeee66610b38c5f76d02a))

## [1.8.0](https://github.com/G2BC/LUMM-server/compare/v1.7.0...v1.8.0) (2026-03-15)


### Features

* add 'lumm' flag to species photo requests and update related schemas and services ([a5e8fc7](https://github.com/G2BC/LUMM-server/commit/a5e8fc7844f0011b91fb7d8292c44c197245b07d))

## [1.7.0](https://github.com/G2BC/LUMM-server/compare/v1.6.6...v1.7.0) (2026-03-15)


### Features

* add species photo management endpoints and schemas ([bb89b8d](https://github.com/G2BC/LUMM-server/commit/bb89b8d3b5ce5d97db46590c443c529ea99ff16a))

## Changelog
