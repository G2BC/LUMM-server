# Changelog

## [1.15.1](https://github.com/G2BC/LUMM-server/compare/v1.15.0...v1.15.1) (2026-04-01)


### Bug Fixes

* replace SpeciesChangeRequestService validation calls with SpeciesChangeRequestValidation for improved modularity ([4090e6e](https://github.com/G2BC/LUMM-server/commit/4090e6e4a8e090a386240a50876227b11dcea222))

## [1.15.0](https://github.com/G2BC/LUMM-server/compare/v1.14.0...v1.15.0) (2026-03-31)


### Features

* implement bilingual error handling and responses across services and routes for improved user experience ([abb5173](https://github.com/G2BC/LUMM-server/commit/abb5173d37e97fa4bf2410bd815579f76f688915))
* implement SpeciesPhotoRepository for managing species photo data with methods for saving, deleting, and retrieving photo IDs ([be3e35e](https://github.com/G2BC/LUMM-server/commit/be3e35eacf3489ff1078b8c576801b6d25f69a02))

## [1.14.0](https://github.com/G2BC/LUMM-server/compare/v1.13.0...v1.14.0) (2026-03-29)


### Features

* add inaturalist_taxon_id field to SpeciesDetailSchema for enhanced species data ([524e6ac](https://github.com/G2BC/LUMM-server/commit/524e6ac838345f1a3b96ea2fc4628f370c84082d))
* implement species deletion functionality with automatic rejection of pending change requests ([3c9af9f](https://github.com/G2BC/LUMM-server/commit/3c9af9feb93c8d952b7f7265cb061e353efa7f54))
* make scientific_name nullable and enforce lineage and mycobank_index_fungorum_id requirements in species creation ([256f2c6](https://github.com/G2BC/LUMM-server/commit/256f2c63d862428ff8fd6229cc4737d6b33d6a48))

## [1.13.0](https://github.com/G2BC/LUMM-server/compare/v1.12.0...v1.13.0) (2026-03-29)


### Features

* add devcontainer configuration for LUMM Server with Docker Compose setup and VSCode customizations ([7612ce6](https://github.com/G2BC/LUMM-server/commit/7612ce65c67e696da64878096f843d161ce5a958))
* enhance Docker development environment with PostgreSQL, Redis, and MinIO services, including initialization scripts and backup restoration ([5efb76d](https://github.com/G2BC/LUMM-server/commit/5efb76dc53a7bd7c4ee144622f5e0863daf3f004))


### Bug Fixes

* ensure DEEPL_API_KEY is checked in development environment for species change requests ([9ec5418](https://github.com/G2BC/LUMM-server/commit/9ec54181359e42a94c0518872be836fb923cf75e))

## [1.12.0](https://github.com/G2BC/LUMM-server/compare/v1.11.1...v1.12.0) (2026-03-28)


### Features

* add is_visible field to Species model for visibility control ([3d43217](https://github.com/G2BC/LUMM-server/commit/3d432177d6fa541c12d4ba8e748d668e0dd9a6fd))
* add is_visible field to species schemas for enhanced visibility control ([397fcea](https://github.com/G2BC/LUMM-server/commit/397fceafb19efc5dc3fa660750c0924a1b4816ef))
* add migration to include is_visible column in species table ([c3b8ebb](https://github.com/G2BC/LUMM-server/commit/c3b8ebbaeddf91b3649c1b166fbfa9d69a4f2946))
* enhance SpeciesRepository with is_visible filter for querying ([581ebd1](https://github.com/G2BC/LUMM-server/commit/581ebd1fc45735510a4bd69d9fd0df86153c82d6))
* implement species creation endpoint and enhance search functionality with is_visible filter ([9ba578b](https://github.com/G2BC/LUMM-server/commit/9ba578b15e7b9282bdac20b58b0319e112a0e86d))

## [1.11.1](https://github.com/G2BC/LUMM-server/compare/v1.11.0...v1.11.1) (2026-03-19)


### Bug Fixes

* update email content and language for user approval notifications ([9f581ed](https://github.com/G2BC/LUMM-server/commit/9f581eda7d7ca6822652e83cabf200c72402df25))

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
