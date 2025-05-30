// MongoDB Schema for Dynamic Settings and Configurations
// Flexible settings storage for companies, users, and system configurations

// Company Settings Collection
db.createCollection("company_settings", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["company_id", "settings", "created_at"],
            properties: {
                _id: { bsonType: "objectId" },
                company_id: { bsonType: "string" },
                settings: {
                    bsonType: "object",
                    properties: {
                        // AI Configuration
                        ai_settings: {
                            bsonType: "object",
                            properties: {
                                auto_analysis_enabled: { bsonType: "bool", default: true },
                                confidence_threshold: { bsonType: "double", minimum: 0.0, maximum: 1.0 },
                                analysis_models: {
                                    bsonType: "array",
                                    items: { bsonType: "string" }
                                },
                                prompt_templates: { bsonType: "object" },
                                cache_ttl_hours: { bsonType: "int", default: 24 }
                            }
                        },
                        // Workflow Configuration
                        workflow_settings: {
                            bsonType: "object",
                            properties: {
                                tender_approval_workflow: { bsonType: "object" },
                                supplier_evaluation_process: { bsonType: "object" },
                                document_review_stages: { bsonType: "object" },
                                automated_notifications: { bsonType: "object" }
                            }
                        },
                        // Security Configuration
                        security_settings: {
                            bsonType: "object",
                            properties: {
                                session_timeout_minutes: { bsonType: "int", default: 480 },
                                max_failed_login_attempts: { bsonType: "int", default: 5 },
                                password_policy: { bsonType: "object" },
                                ip_whitelist: {
                                    bsonType: "array",
                                    items: { bsonType: "string" }
                                },
                                two_factor_required: { bsonType: "bool", default: false }
                            }
                        },
                        // Integration Settings
                        integrations: {
                            bsonType: "object",
                            properties: {
                                email_provider: { bsonType: "object" },
                                calendar_sync: { bsonType: "object" },
                                document_storage: { bsonType: "object" },
                                api_endpoints: { bsonType: "object" },
                                webhooks: {
                                    bsonType: "array",
                                    items: {
                                        bsonType: "object",
                                        properties: {
                                            name: { bsonType: "string" },
                                            url: { bsonType: "string" },
                                            events: {
                                                bsonType: "array",
                                                items: { bsonType: "string" }
                                            },
                                            active: { bsonType: "bool" }
                                        }
                                    }
                                }
                            }
                        },
                        // UI/UX Preferences
                        ui_preferences: {
                            bsonType: "object",
                            properties: {
                                theme: { bsonType: "string", default: "light" },
                                language: { bsonType: "string", default: "es" },
                                timezone: { bsonType: "string", default: "America/Mexico_City" },
                                dashboard_layout: { bsonType: "object" },
                                default_views: { bsonType: "object" }
                            }
                        },
                        // Business Rules
                        business_rules: {
                            bsonType: "object",
                            properties: {
                                tender_minimum_amount: { bsonType: "double" },
                                supplier_rating_weights: { bsonType: "object" },
                                approval_thresholds: { bsonType: "object" },
                                compliance_requirements: { bsonType: "object" }
                            }
                        }
                    }
                },
                version: { bsonType: "int", default: 1 },
                created_at: { bsonType: "date" },
                updated_at: { bsonType: "date" },
                updated_by: { bsonType: "string" }
            }
        }
    }
});

db.company_settings.createIndex({ "company_id": 1 }, { unique: true });
db.company_settings.createIndex({ "version": -1 });

// User Preferences Collection
db.createCollection("user_preferences", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["user_id", "company_id", "preferences", "created_at"],
            properties: {
                _id: { bsonType: "objectId" },
                user_id: { bsonType: "string" },
                company_id: { bsonType: "string" },
                preferences: {
                    bsonType: "object",
                    properties: {
                        // Dashboard Preferences
                        dashboard: {
                            bsonType: "object",
                            properties: {
                                widgets: {
                                    bsonType: "array",
                                    items: {
                                        bsonType: "object",
                                        properties: {
                                            widget_id: { bsonType: "string" },
                                            position: { bsonType: "object" },
                                            size: { bsonType: "object" },
                                            visible: { bsonType: "bool" },
                                            config: { bsonType: "object" }
                                        }
                                    }
                                },
                                refresh_interval: { bsonType: "int", default: 300 }
                            }
                        },
                        // Notification Preferences
                        notifications: {
                            bsonType: "object",
                            properties: {
                                email_enabled: { bsonType: "bool", default: true },
                                push_enabled: { bsonType: "bool", default: true },
                                sms_enabled: { bsonType: "bool", default: false },
                                frequency: { bsonType: "string", default: "immediate" },
                                quiet_hours: {
                                    bsonType: "object",
                                    properties: {
                                        enabled: { bsonType: "bool" },
                                        start_time: { bsonType: "string" },
                                        end_time: { bsonType: "string" }
                                    }
                                },
                                categories: {
                                    bsonType: "object",
                                    properties: {
                                        tender_updates: { bsonType: "bool" },
                                        ai_analysis: { bsonType: "bool" },
                                        system_alerts: { bsonType: "bool" },
                                        workflow_updates: { bsonType: "bool" }
                                    }
                                }
                            }
                        },
                        // Table and List Preferences
                        tables: {
                            bsonType: "object",
                            properties: {
                                items_per_page: { bsonType: "int", default: 25 },
                                column_preferences: { bsonType: "object" },
                                sort_preferences: { bsonType: "object" },
                                filter_presets: {
                                    bsonType: "array",
                                    items: {
                                        bsonType: "object",
                                        properties: {
                                            name: { bsonType: "string" },
                                            filters: { bsonType: "object" },
                                            default: { bsonType: "bool" }
                                        }
                                    }
                                }
                            }
                        },
                        // Quick Actions
                        quick_actions: {
                            bsonType: "array",
                            items: {
                                bsonType: "object",
                                properties: {
                                    action_id: { bsonType: "string" },
                                    label: { bsonType: "string" },
                                    icon: { bsonType: "string" },
                                    url: { bsonType: "string" },
                                    order: { bsonType: "int" }
                                }
                            }
                        }
                    }
                },
                created_at: { bsonType: "date" },
                updated_at: { bsonType: "date" }
            }
        }
    }
});

db.user_preferences.createIndex({ "user_id": 1, "company_id": 1 }, { unique: true });

// System Configuration Collection
db.createCollection("system_config", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["config_key", "config_value", "created_at"],
            properties: {
                _id: { bsonType: "objectId" },
                config_key: { bsonType: "string" },
                config_value: {},
                description: { bsonType: "string" },
                category: { bsonType: "string" },
                environment: { bsonType: "string", default: "production" },
                encrypted: { bsonType: "bool", default: false },
                version: { bsonType: "int", default: 1 },
                created_at: { bsonType: "date" },
                updated_at: { bsonType: "date" },
                updated_by: { bsonType: "string" }
            }
        }
    }
});

db.system_config.createIndex({ "config_key": 1, "environment": 1 }, { unique: true });
db.system_config.createIndex({ "category": 1 });
