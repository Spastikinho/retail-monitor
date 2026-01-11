"""
OpenAPI Schema for Retail Monitor API.
Provides API documentation and TypeScript type generation support.
"""
from datetime import datetime

# OpenAPI 3.0 Schema Definition
OPENAPI_SCHEMA = {
    "openapi": "3.0.3",
    "info": {
        "title": "Retail Monitor API",
        "description": "API for retail price monitoring, scraping, and analytics",
        "version": "1.0.0",
        "contact": {
            "name": "Retail Monitor Support"
        }
    },
    "servers": [
        {
            "url": "/api/v1",
            "description": "API v1"
        }
    ],
    "paths": {
        "/health/": {
            "get": {
                "summary": "Health Check",
                "operationId": "healthCheck",
                "tags": ["System"],
                "responses": {
                    "200": {
                        "description": "Service is healthy",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HealthCheck"}
                            }
                        }
                    }
                }
            }
        },
        "/runs/": {
            "post": {
                "summary": "Create a new run",
                "operationId": "createRun",
                "tags": ["Runs"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/CreateRunRequest"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Run created successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CreateRunResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/runs/{run_id}/": {
            "get": {
                "summary": "Get run status and results",
                "operationId": "getRun",
                "tags": ["Runs"],
                "parameters": [
                    {
                        "name": "run_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Run details",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RunResponse"}
                            }
                        }
                    },
                    "404": {
                        "description": "Run not found"
                    }
                }
            }
        },
        "/runs/{run_id}/retry/": {
            "post": {
                "summary": "Retry failed URLs in a run",
                "operationId": "retryRun",
                "tags": ["Runs"],
                "parameters": [
                    {
                        "name": "run_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"}
                    }
                ],
                "responses": {
                    "201": {
                        "description": "New run created with failed URLs",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CreateRunResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/imports/": {
            "get": {
                "summary": "List imports",
                "operationId": "listImports",
                "tags": ["Imports"],
                "parameters": [
                    {"name": "status", "in": "query", "schema": {"type": "string"}},
                    {"name": "product_type", "in": "query", "schema": {"type": "string"}},
                    {"name": "period", "in": "query", "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}},
                    {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}}
                ],
                "responses": {
                    "200": {
                        "description": "List of imports",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ImportsListResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/imports/create/": {
            "post": {
                "summary": "Create imports from URLs",
                "operationId": "createImports",
                "tags": ["Imports"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/CreateImportsRequest"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Imports created",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CreateImportsResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/imports/{import_id}/": {
            "get": {
                "summary": "Get import details",
                "operationId": "getImport",
                "tags": ["Imports"],
                "parameters": [
                    {
                        "name": "import_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Import details",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ImportDetailResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/scrape/": {
            "post": {
                "summary": "Trigger scrape session",
                "operationId": "triggerScrape",
                "tags": ["Scraping"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TriggerScrapeRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Scrape session started",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/TriggerScrapeResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/scrape/{session_id}/status/": {
            "get": {
                "summary": "Get scrape session status",
                "operationId": "getScrapeStatus",
                "tags": ["Scraping"],
                "parameters": [
                    {
                        "name": "session_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Session status",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ScrapeStatusResponse"}
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "HealthCheck": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "healthy"},
                    "database": {"type": "string", "example": "ok"},
                    "timestamp": {"type": "string", "format": "date-time"}
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "error": {"type": "string"}
                }
            },
            "CreateRunRequest": {
                "type": "object",
                "required": ["urls"],
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string", "format": "uri"},
                        "maxItems": 20,
                        "description": "List of product URLs to process"
                    },
                    "product_type": {
                        "type": "string",
                        "enum": ["own", "competitor"],
                        "default": "competitor"
                    },
                    "group_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Optional monitoring group ID"
                    }
                }
            },
            "CreateRunResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "run_id": {"type": "string", "format": "uuid"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "items_count": {"type": "integer"},
                    "message": {"type": "string"}
                }
            },
            "RunItem": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "url": {"type": "string", "format": "uri"},
                    "retailer": {"type": "string", "nullable": True},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "processing", "completed", "failed"]
                    },
                    "product_title": {"type": "string", "nullable": True},
                    "price_final": {"type": "number", "nullable": True},
                    "rating": {"type": "number", "nullable": True},
                    "reviews_count": {"type": "integer", "nullable": True},
                    "error_message": {"type": "string", "nullable": True}
                }
            },
            "RunResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "run": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "processing", "completed", "failed"]
                            },
                            "progress": {
                                "type": "object",
                                "properties": {
                                    "total": {"type": "integer"},
                                    "completed": {"type": "integer"},
                                    "failed": {"type": "integer"},
                                    "percentage": {"type": "number"}
                                }
                            },
                            "created_at": {"type": "string", "format": "date-time"},
                            "started_at": {"type": "string", "format": "date-time", "nullable": True},
                            "finished_at": {"type": "string", "format": "date-time", "nullable": True}
                        }
                    },
                    "results": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/RunItem"}
                    },
                    "errors": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/RunItem"}
                    }
                }
            },
            "ManualImport": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "url": {"type": "string", "format": "uri"},
                    "retailer": {"type": "string", "nullable": True},
                    "product_type": {"type": "string", "enum": ["own", "competitor"]},
                    "product_title": {"type": "string"},
                    "custom_name": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "processing", "completed", "failed"]
                    },
                    "price_final": {"type": "number", "nullable": True},
                    "price_change": {"type": "number", "nullable": True},
                    "price_change_pct": {"type": "number", "nullable": True},
                    "rating": {"type": "number", "nullable": True},
                    "reviews_count": {"type": "integer", "nullable": True},
                    "in_stock": {"type": "boolean", "nullable": True},
                    "reviews_positive": {"type": "integer"},
                    "reviews_negative": {"type": "integer"},
                    "monitoring_period": {"type": "string", "nullable": True},
                    "created_at": {"type": "string", "format": "date-time"},
                    "processed_at": {"type": "string", "format": "date-time", "nullable": True},
                    "error_message": {"type": "string", "nullable": True}
                }
            },
            "ManualImportDetail": {
                "allOf": [
                    {"$ref": "#/components/schemas/ManualImport"},
                    {
                        "type": "object",
                        "properties": {
                            "notes": {"type": "string"},
                            "price_regular": {"type": "number", "nullable": True},
                            "price_promo": {"type": "number", "nullable": True},
                            "price_previous": {"type": "number", "nullable": True},
                            "reviews_neutral": {"type": "integer"},
                            "review_insights": {"type": "object"},
                            "reviews_data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "rating": {"type": "number"},
                                        "text": {"type": "string"},
                                        "author": {"type": "string"},
                                        "date": {"type": "string"},
                                        "pros": {"type": "string"},
                                        "cons": {"type": "string"}
                                    }
                                }
                            },
                            "is_recurring": {"type": "boolean"},
                            "group": {
                                "type": "object",
                                "nullable": True,
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"}
                                }
                            }
                        }
                    }
                ]
            },
            "ImportsListResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "total": {"type": "integer"},
                    "imports": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/ManualImport"}
                    }
                }
            },
            "CreateImportsRequest": {
                "type": "object",
                "required": ["urls"],
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string", "format": "uri"},
                        "maxItems": 20
                    },
                    "product_type": {
                        "type": "string",
                        "enum": ["own", "competitor"],
                        "default": "competitor"
                    },
                    "group_id": {"type": "string", "format": "uuid"}
                }
            },
            "CreateImportsResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "imports": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "format": "uuid"},
                                "url": {"type": "string"},
                                "retailer": {"type": "string", "nullable": True},
                                "status": {"type": "string"}
                            }
                        }
                    },
                    "errors": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "ImportDetailResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "import": {"$ref": "#/components/schemas/ManualImportDetail"}
                }
            },
            "TriggerScrapeRequest": {
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string", "format": "uuid"},
                    "retailer_id": {"type": "string", "format": "uuid"}
                }
            },
            "TriggerScrapeResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "session_id": {"type": "string", "format": "uuid"}
                }
            },
            "ScrapeStatusResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "session": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "running", "completed", "failed", "cancelled"]
                            },
                            "trigger_type": {"type": "string"},
                            "retailer": {"type": "string", "nullable": True},
                            "listings_total": {"type": "integer"},
                            "listings_success": {"type": "integer"},
                            "listings_failed": {"type": "integer"},
                            "started_at": {"type": "string", "format": "date-time", "nullable": True},
                            "finished_at": {"type": "string", "format": "date-time", "nullable": True},
                            "error_log": {"type": "string", "nullable": True}
                        }
                    }
                }
            }
        }
    }
}


def get_openapi_schema():
    """Return the OpenAPI schema as a dictionary."""
    return OPENAPI_SCHEMA
